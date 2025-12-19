#!/usr/bin/env python3
"""NBA Assists Props Model - EV-leaning version

Analyzes player assists props using REAL NBA stats + The Odds API lines.
Outputs a card-based HTML report consistent with other props models.

Targets:
- Positive expected value leaning plays
- High selectivity (A.I. Score >= MIN_AI_SCORE)
- ~60% hit-rate target for MIN_AI_SCORE tier (calibrated via probability mapping)
"""

import json
import os
import re
import statistics
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import pytz
import requests
from dotenv import load_dotenv

# NBA API for real stats
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats, playergamelog
from nba_api.stats.static import players

# Ensure pandas is available for nba_api DataFrames
import pandas as pd  # noqa: F401

# Load environment variables
load_dotenv()

# =============================================================================
# Configuration
# =============================================================================

API_KEY = os.getenv("ODDS_API_KEY")
if not API_KEY:
    # Keep the script importable so scheduled runs can still execute and log.
    # The key is required when fetching odds (get_player_props()).
    print("⚠️  ODDS_API_KEY environment variable not set. Odds fetching will fail until it's provided.")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "nba_assists_props.html")
PLAYER_STATS_CACHE = os.path.join(SCRIPT_DIR, "nba_player_assists_stats_cache.json")
TEAM_ASSISTS_CACHE = os.path.join(SCRIPT_DIR, "nba_team_assists_cache.json")
TRACKING_FILE = os.path.join(SCRIPT_DIR, "nba_assists_props_tracking.json")

# Model Parameters - STRICT FOR PROFITABILITY
MIN_AI_SCORE = 7.5  # Adjusted to allow more high-value plays
TOP_PLAYS_COUNT = 5
RECENT_GAMES_WINDOW = 10
CURRENT_SEASON = "2025-26"

# Edge requirements
MIN_EDGE_OVER_LINE = 1.5
MIN_EDGE_UNDER_LINE = 1.0
MIN_RECENT_FORM_EDGE = 1.2


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"

# =============================================================================
# TRACKING FUNCTIONS
# =============================================================================

def load_tracking_data():
    """Load tracking data from JSON file"""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return {'picks': [], 'summary': {}}

def save_tracking_data(tracking_data):
    """Save tracking data to JSON file"""
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)

def track_new_picks(over_plays, under_plays):
    """Track new picks in the tracking file"""
    tracking_data = load_tracking_data()
    
    print(f"\n{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"{Colors.CYAN}📊 TRACKING NEW PICKS{Colors.END}")
    print(f"{Colors.CYAN}{'='*90}{Colors.END}")
    
    new_count = 0
    updated_count = 0
    
    for play in over_plays + under_plays:
        # Extract prop line from prop string (e.g., "OVER 8.5 AST" -> 8.5)
        prop_str = play.get('prop', '')
        bet_type = 'over' if 'OVER' in prop_str else 'under'
        
        # Parse prop line from string
        import re
        match = re.search(r'(\d+\.?\d*)', prop_str)
        prop_line = float(match.group(1)) if match else 0
        
        # Generate unique pick ID
        pick_id = f"{play['player']}_{bet_type}_{play.get('game_time', '')}"
        
        # Check if pick already exists
        existing_pick = next((p for p in tracking_data['picks'] if p.get('pick_id') == pick_id), None)
        
        if existing_pick:
            # Update latest odds if different
            if existing_pick.get('latest_odds') != play.get('odds'):
                existing_pick['latest_odds'] = play.get('odds')
                existing_pick['last_updated'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
                updated_count += 1
        else:
            # Add new pick
            new_pick = {
                'pick_id': pick_id,
                'player': play['player'],
                'prop_line': prop_line,
                'bet_type': bet_type,
                'team': play.get('team'),
                'opponent': play.get('opponent'),
                'ai_score': play.get('ai_score'),
                'odds': play.get('odds'),
                'opening_odds': play.get('odds'),
                'latest_odds': play.get('odds'),
                'game_time': play.get('game_time'),
                'tracked_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
                'status': 'pending',
                'result': None,
                'actual_ast': None
            }
            tracking_data['picks'].append(new_pick)
            new_count += 1
    
    save_tracking_data(tracking_data)
    
    if new_count > 0:
        print(f"{Colors.GREEN}✓ Tracked {new_count} new picks{Colors.END}")
    if updated_count > 0:
        print(f"{Colors.YELLOW}✓ Updated odds for {updated_count} existing picks{Colors.END}")
    if new_count == 0 and updated_count == 0:
        print(f"{Colors.CYAN}No new picks to track{Colors.END}")

def fetch_player_assists_from_nba_api(player_name, team_name, game_date_str):
    """
    Fetch actual player assists from NBA API for a specific game
    Returns the actual assists count or None if not found
    """
    try:
        # Find player ID
        player_list = players.get_players()
        player_info = None
        
        # Match player name (handle variations)
        name_parts = player_name.lower().split()
        for p in player_list:
            p_name = p['full_name'].lower()
            p_parts = p_name.split()
            if len(name_parts) >= 2 and len(p_parts) >= 2:
                if name_parts[0] in p_parts[0] and name_parts[-1] in p_parts[-1]:
                    player_info = p
                    break
        
        if not player_info:
            print(f"{Colors.YELLOW}    Could not find player {player_name} in NBA API{Colors.END}")
            return None
        
        player_id = player_info['id']
        
        # Get player game log
        game_log = playergamelog.PlayerGameLog(player_id=player_id, season=CURRENT_SEASON, timeout=30)
        df = game_log.get_data_frames()[0]
        
        if df.empty:
            return None
        
        # Find the game by date
        target_date = datetime.strptime(game_date_str, '%Y-%m-%d').date()
        
        for _, row in df.iterrows():
            game_date_str_nba = row.get('GAME_DATE', '')
            if not game_date_str_nba:
                continue
            
            # Parse NBA date format (usually "DEC 11, 2025" or similar)
            try:
                game_date = datetime.strptime(game_date_str_nba, '%b %d, %Y').date()
            except:
                try:
                    game_date = datetime.strptime(game_date_str_nba, '%Y-%m-%d').date()
                except:
                    continue
            
            if game_date == target_date:
                assists = row.get('AST', 0)
                return int(assists) if assists else 0
        
        return None
        
    except Exception as e:
        print(f"{Colors.YELLOW}  Error fetching stats from NBA API for {player_name}: {str(e)}{Colors.END}")
        return None

def grade_pending_picks():
    """Grade pending picks by fetching actual stats from NBA API"""
    tracking_data = load_tracking_data()
    pending_picks = [p for p in tracking_data['picks'] if p.get('status') == 'pending']
    
    if not pending_picks:
        print(f"\n{Colors.GREEN}✓ No pending picks to grade{Colors.END}")
        return
    
    print(f"\n{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"{Colors.CYAN}🎯 GRADING PENDING PICKS{Colors.END}")
    print(f"{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"\n{Colors.YELLOW}📋 Found {len(pending_picks)} pending picks...{Colors.END}\n")
    
    graded_count = 0
    completed_teams_cache = {}
    
    for pick in pending_picks:
        # Check if game has passed (add 4 hour buffer for games to complete)
        try:
            game_time_str = pick.get('game_time')
            if not game_time_str:
                continue
                
            game_time_utc = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            current_time = datetime.now(pytz.UTC)
            hours_since_game = (current_time - game_time_utc).total_seconds() / 3600
            
            # Determine game status early to skip buffer if final
            et_tz = pytz.timezone('US/Eastern')
            game_date = game_time_utc.astimezone(et_tz).strftime('%Y-%m-%d')
            
            if game_date not in completed_teams_cache:
                completed_teams_cache[game_date] = fetch_completed_teams_for_date(game_date)
            
            # Check if team's game is completed
            is_game_final = False
            team_name = pick.get('team')
            if team_name in completed_teams_cache[game_date]:
                is_game_final = True
            
            if hours_since_game < 4 and not is_game_final:
                continue  # Game too recent and not final, wait
            
            # Fetch actual assists from NBA API
            player_name = pick.get('player')
            # game_date already calculated
            
            actual_ast = fetch_player_assists_from_nba_api(player_name, team_name, game_date)
            
            if actual_ast is None:
                # Check DNP
                if game_date not in completed_teams_cache:
                    completed_teams_cache[game_date] = fetch_completed_teams_for_date(game_date)
                
                if team_name in completed_teams_cache[game_date]:
                    print(f"{Colors.YELLOW}  ⚠️  Player {player_name} has no stats but game is final -> Marking as DNP/Void{Colors.END}")
                    pick['status'] = 'void'
                    pick['result'] = 'DNP'
                    pick['profit_loss'] = 0
                    # pick['actual_ast'] = 0
                    graded_count += 1
                    continue
                
                print(f"{Colors.YELLOW}  ⚠ Could not find stats for {player_name} on {game_date}{Colors.END}")
                continue
            
            # Grade the pick
            prop_line = pick.get('prop_line')
            bet_type = pick.get('bet_type')
            
            if bet_type == 'over':
                is_win = actual_ast > prop_line
            else:  # under
                is_win = actual_ast < prop_line
            
            # Calculate profit/loss - USE OPENING ODDS (the odds the bet was actually placed at)
            odds = pick.get('opening_odds') or pick.get('odds', -110)
            if is_win:
                if odds > 0:
                    profit_loss = int(odds)  # Store as cents
                else:
                    profit_loss = int((100.0 / abs(odds)) * 100)  # Store as cents
                status = 'win'
                result = 'WIN'
                result_color = Colors.GREEN
            else:
                profit_loss = -100  # Lost 1 unit (100 cents)
                status = 'loss'
                result = 'LOSS'
                result_color = Colors.RED
            
            # Update pick - CRITICAL: Always set profit_loss when grading
            pick['status'] = status
            pick['result'] = result
            pick['actual_ast'] = actual_ast
            pick['profit_loss'] = profit_loss
            pick['updated_at'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
            
            print(f"    {result_color}{result}{Colors.END}: {player_name} had {actual_ast} assists (line: {prop_line}, bet: {bet_type.upper()}) | Profit: {profit_loss/100.0:.2f} units")
            graded_count += 1
            
        except Exception as e:
            print(f"{Colors.RED}  Error grading pick {pick.get('player')}: {e}{Colors.END}")
            continue
    
    if graded_count > 0:
        save_tracking_data(tracking_data)
        print(f"\n{Colors.GREEN}✓ Graded {graded_count} picks{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}No picks ready for grading yet{Colors.END}")

    return graded_count

def backfill_profit_loss():
    """Backfill profit_loss for graded picks that are missing it - CRITICAL for accurate ROI"""
    tracking_data = load_tracking_data()
    updated_count = 0
    
    for pick in tracking_data['picks']:
        # Only process picks that are graded but missing profit_loss
        if pick.get('status') in ['win', 'loss'] and 'profit_loss' not in pick:
            # USE OPENING ODDS (the odds the bet was actually placed at)
            odds = pick.get('opening_odds') or pick.get('odds', -110)
            if pick.get('status') == 'win':
                if odds > 0:
                    profit_loss = int(odds)
                else:
                    profit_loss = int((100.0 / abs(odds)) * 100)
            else:  # loss
                profit_loss = -100
            
            pick['profit_loss'] = profit_loss
            pick['profit_loss_backfilled'] = True
            updated_count += 1
    
    if updated_count > 0:
        save_tracking_data(tracking_data)
        print(f"{Colors.GREEN}✓ Backfilled profit_loss for {updated_count} picks{Colors.END}")
    
    return updated_count

def calculate_tracking_stats(tracking_data):
    """Calculate performance statistics from tracking data - CRITICAL: Requires profit_loss field"""
    completed_picks = [p for p in tracking_data['picks'] if p.get('status') in ['win', 'loss']]
    
    if not completed_picks:
        return {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'roi': 0.0,
            'roi_pct': 0.0,
            'over_record': '0-0',
            'over_win_rate': 0.0,
            'over_roi': 0.0,
            'under_record': '0-0',
            'under_win_rate': 0.0,
            'under_roi': 0.0
        }
    
    # Validate that all completed picks have profit_loss
    missing_profit = [p for p in completed_picks if 'profit_loss' not in p]
    if missing_profit:
        print(f"{Colors.YELLOW}⚠ WARNING: {len(missing_profit)} completed picks missing profit_loss - ROI may be inaccurate{Colors.END}")
        print(f"{Colors.YELLOW}  Run backfill_profit_loss() to fix this{Colors.END}")
    
    wins = sum(1 for p in completed_picks if p.get('status') == 'win')
    losses = sum(1 for p in completed_picks if p.get('status') == 'loss')
    total = wins + losses
    win_rate = (wins / total * 100) if total > 0 else 0.0
    
    # Calculate profit in units (cents / 100) - only use picks with profit_loss
    total_profit_cents = 0
    for p in completed_picks:
        if 'profit_loss' in p:
            total_profit_cents += p['profit_loss']
        else:
            # Calculate on the fly if missing (fallback) - use opening_odds
            odds = p.get('opening_odds') or p.get('odds', -110)
            if p.get('status') == 'win':
                if odds > 0:
                    total_profit_cents += int(odds)
                else:
                    total_profit_cents += int((100.0 / abs(odds)) * 100)
            else:
                total_profit_cents -= 100
    
    total_profit_units = total_profit_cents / 100.0
    
    # ROI = (profit / total bets) * 100
    roi_pct = (total_profit_units / total * 100) if total > 0 else 0.0
    
    # Calculate OVER stats
    over_picks = [p for p in completed_picks if p.get('bet_type') == 'over']
    over_wins = sum(1 for p in over_picks if p.get('status') == 'win')
    over_losses = sum(1 for p in over_picks if p.get('status') == 'loss')
    over_total = over_wins + over_losses
    over_win_rate = (over_wins / over_total * 100) if over_total > 0 else 0.0
    
    over_profit_cents = 0
    for p in over_picks:
        if 'profit_loss' in p:
            over_profit_cents += p['profit_loss']
        else:
            odds = p.get('opening_odds') or p.get('odds', -110)
            if p.get('status') == 'win':
                if odds > 0:
                    over_profit_cents += int(odds)
                else:
                    over_profit_cents += int((100.0 / abs(odds)) * 100)
            else:
                over_profit_cents -= 100
    
    over_profit_units = over_profit_cents / 100.0
    over_roi = (over_profit_units / over_total * 100) if over_total > 0 else 0.0
    
    # Calculate UNDER stats
    under_picks = [p for p in completed_picks if p.get('bet_type') == 'under']
    under_wins = sum(1 for p in under_picks if p.get('status') == 'win')
    under_losses = sum(1 for p in under_picks if p.get('status') == 'loss')
    under_total = under_wins + under_losses
    under_win_rate = (under_wins / under_total * 100) if under_total > 0 else 0.0
    
    under_profit_cents = 0
    for p in under_picks:
        if 'profit_loss' in p:
            under_profit_cents += p['profit_loss']
        else:
            odds = p.get('opening_odds') or p.get('odds', -110)
            if p.get('status') == 'win':
                if odds > 0:
                    under_profit_cents += int(odds)
                else:
                    under_profit_cents += int((100.0 / abs(odds)) * 100)
            else:
                under_profit_cents -= 100
    
    under_profit_units = under_profit_cents / 100.0
    under_roi = (under_profit_units / under_total * 100) if under_total > 0 else 0.0
    
    # --- DAILY PERFORMANCE TRACKING ---
    from datetime import datetime, timedelta
    import pytz
    
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    today_str = now_et.strftime('%Y-%m-%d')
    yesterday_str = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def calc_daily_stats(target_date_str):
        daily_picks = []
        for p in completed_picks:
            gt_str = p.get('game_time', '')
            if not gt_str: continue
            try:
                dt_utc = datetime.fromisoformat(gt_str.replace('Z', '+00:00'))
                dt_et = dt_utc.astimezone(et_tz)
                if dt_et.strftime('%Y-%m-%d') == target_date_str:
                    daily_picks.append(p)
            except:
                continue
                
        d_wins = sum(1 for p in daily_picks if p.get('status') == 'win')
        d_losses = sum(1 for p in daily_picks if p.get('status') == 'loss')
        d_total = d_wins + d_losses
        d_profit_cents = 0
        for p in daily_picks:
            if 'profit_loss' in p:
                d_profit_cents += p['profit_loss']
            else:
                odds = p.get('opening_odds') or p.get('odds', -110)
                if p.get('status') == 'win':
                    if odds > 0: d_profit_cents += int(odds)
                    else: d_profit_cents += int((100.0 / abs(odds)) * 100)
                else:
                    d_profit_cents -= 100
        
        d_profit = d_profit_cents / 100.0
        d_roi = (d_profit / d_total * 100) if d_total > 0 else 0.0
        
        return {
            'record': f"{d_wins}-{d_losses}",
            'profit': d_profit,
            'roi': d_roi,
            'count': d_total
        }

    today_stats = calc_daily_stats(today_str)
    yesterday_stats = calc_daily_stats(yesterday_str)

    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'win_rate': round(win_rate, 2),
        'total_profit': round(total_profit_units, 2),
        'roi': round(total_profit_units, 2),
        'roi_pct': round(roi_pct, 2),
        'over_record': f'{over_wins}-{over_losses}',
        'over_win_rate': round(over_win_rate, 2),
        'over_roi': round(over_roi, 2),
        'under_record': f'{under_wins}-{under_losses}',
        'under_win_rate': round(under_win_rate, 2),
        'under_roi': round(under_roi, 2),
        'today': today_stats,
        'yesterday': yesterday_stats
    }

def calculate_recent_performance(picks_list, count):
    """Calculate performance stats for last N picks (most recent first)"""
    # Filter to only completed picks (props don't have pushes)
    completed = [p for p in picks_list if p.get('status', '').lower() in ['win', 'loss']]
    
    # Take first N picks (most recent first since list should be sorted reverse=True)
    recent = completed[:count] if len(completed) >= count else completed
    
    wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
    total = wins + losses
    
    # Calculate profit (profit_loss is in cents, convert to units)
    profit_cents = sum(p.get('profit_loss', 0) for p in recent if p.get('profit_loss') is not None)
    profit_units = profit_cents / 100.0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    # ROI calculation: profit_cents / (total * 100) * 100 (assuming 100 cents = 1 unit bet)
    roi = (profit_cents / (total * 100) * 100) if total > 0 else 0
    
    return {
        'record': f"{wins}-{losses}",
        'win_rate': win_rate,
        'profit': profit_units,
        'roi': roi,
        'count': len(recent)
    }

# =============================================================================
# Data Fetching
# =============================================================================

def get_nba_player_assists_stats():
    """Fetch REAL NBA player assists stats from NBA API.

    Returns:
        dict keyed by player full name:
            season_ast_avg, recent_ast_avg, ast_per_36, consistency_score,
            minutes, games_played, team_abbrev
    """
    print(f"\n{Colors.CYAN}Fetching REAL NBA player assists statistics...{Colors.END}")

    # Cache first (6 hours)
    if os.path.exists(PLAYER_STATS_CACHE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(PLAYER_STATS_CACHE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached player assists stats (less than 6 hours old){Colors.END}")
            with open(PLAYER_STATS_CACHE, "r") as f:
                return json.load(f)

    player_stats: dict[str, dict] = {}

    try:
        print(f"{Colors.CYAN}  Fetching season assists stats...{Colors.END}")
        season_stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense="Base",
            per_mode_detailed="PerGame",
            timeout=30,
        )
        season_df = season_stats.get_data_frames()[0]
        time.sleep(0.6)

        print(f"{Colors.CYAN}  Fetching recent form (last {RECENT_GAMES_WINDOW} games)...{Colors.END}")
        recent_stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense="Base",
            per_mode_detailed="PerGame",
            last_n_games=RECENT_GAMES_WINDOW,
            timeout=30,
        )
        recent_df = recent_stats.get_data_frames()[0]
        time.sleep(0.6)

        for _, row in season_df.iterrows():
            player_name = row.get("PLAYER_NAME", "")
            if not player_name:
                continue

            season_ast = float(row.get("AST", 0) or 0)
            games_played = int(row.get("GP", 0) or 0)
            team_abbrev = row.get("TEAM_ABBREVIATION", "")
            minutes = float(row.get("MIN", 0) or 0)

            recent_row = recent_df[recent_df["PLAYER_NAME"] == player_name]
            if not recent_row.empty:
                recent_ast = float(recent_row.iloc[0].get("AST", season_ast) or season_ast)
            else:
                recent_ast = season_ast

            ast_per_36 = (season_ast / minutes * 36) if minutes > 0 else 0.0
            # Normalize consistency around a strong playmaker baseline (8 ast/36)
            consistency = min(1.0, ast_per_36 / 8.0) if ast_per_36 > 0 else 0.3

            player_stats[player_name] = {
                "season_ast_avg": round(season_ast, 2),
                "recent_ast_avg": round(recent_ast, 2),
                "ast_per_36": round(ast_per_36, 2),
                "consistency_score": round(consistency, 2),
                "games_played": games_played,
                "team": team_abbrev,
                "minutes": round(minutes, 1),
            }

        with open(PLAYER_STATS_CACHE, "w") as f:
            json.dump(player_stats, f, indent=2)

        print(f"{Colors.GREEN}✓ Fetched REAL assists stats for {len(player_stats)} players{Colors.END}")
        return player_stats

    except Exception as e:
        print(f"{Colors.RED}✗ Error fetching NBA player assists stats: {e}{Colors.END}")
        import traceback

        traceback.print_exc()
        if os.path.exists(PLAYER_STATS_CACHE):
            print(f"{Colors.YELLOW}  Loading from cache as fallback...{Colors.END}")
            with open(PLAYER_STATS_CACHE, "r") as f:
                return json.load(f)
        return {}


def get_opponent_assists_factors():
    """Fetch team-level matchup factors relevant to assists (what opponents allow)."""
    print(f"\n{Colors.CYAN}Fetching opponent assists factors...{Colors.END}")

    if os.path.exists(TEAM_ASSISTS_CACHE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(TEAM_ASSISTS_CACHE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached assists factors{Colors.END}")
            with open(TEAM_ASSISTS_CACHE, "r") as f:
                return json.load(f)

    assists_factors: dict[str, dict] = {}

    try:
        # NBA team names (filter out WNBA teams)
        nba_teams = {
            'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets',
            'Chicago Bulls', 'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets',
            'Detroit Pistons', 'Golden State Warriors', 'Houston Rockets', 'Indiana Pacers',
            'LA Clippers', 'Los Angeles Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies',
            'Miami Heat', 'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans',
            'New York Knicks', 'Oklahoma City Thunder', 'Orlando Magic', 'Philadelphia 76ers',
            'Phoenix Suns', 'Portland Trail Blazers', 'Sacramento Kings', 'San Antonio Spurs',
            'Toronto Raptors', 'Utah Jazz', 'Washington Wizards'
        }

        # Fetch opponent stats (what each team ALLOWS)
        opp_stats = leaguedashteamstats.LeagueDashTeamStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense="Opponent",
            timeout=30,
        )
        opp_df = opp_stats.get_data_frames()[0]
        time.sleep(0.6)

        # Fetch advanced stats for pace
        adv_stats = leaguedashteamstats.LeagueDashTeamStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense="Advanced",
            timeout=30,
        )
        adv_df = adv_stats.get_data_frames()[0]
        time.sleep(0.6)

        # Create lookup for advanced stats
        adv_lookup = {}
        for _, row in adv_df.iterrows():
            team_name = row.get("TEAM_NAME", "")
            if team_name:
                adv_lookup[team_name] = {
                    "pace": row.get("PACE", 100)
                }

        # Process opponent stats
        for _, row in opp_df.iterrows():
            team_name = row.get("TEAM_NAME", "")
            if not team_name or team_name not in nba_teams:
                continue

            # Opponent assists allowed PER GAME
            opp_ast_total = float(row.get("OPP_AST", 0) or 0)
            games_played = row.get("GP", 1)
            opp_ast_per_game = opp_ast_total / games_played if games_played > 0 else 0

            # Get pace from advanced stats
            adv_data = adv_lookup.get(team_name, {})
            pace = float(adv_data.get("pace", 100))

            # Typical league baselines
            baseline_opp_ast = 25.0

            # Assists factor based on opponent assists allowed and pace
            assists_factor = (opp_ast_per_game / baseline_opp_ast) * (pace / 100.0)

            assists_factors[team_name] = {
                "opp_ast_allowed": round(opp_ast_per_game, 1),
                "pace": round(pace, 1),
                "assists_factor": round(assists_factor, 3),
            }

        with open(TEAM_ASSISTS_CACHE, "w") as f:
            json.dump(assists_factors, f, indent=2)

        print(f"{Colors.GREEN}✓ Fetched assists factors for {len(assists_factors)} teams{Colors.END}")
        return assists_factors

    except Exception as e:
        print(f"{Colors.YELLOW}⚠ Could not fetch assists factors: {e}{Colors.END}")
        if os.path.exists(TEAM_ASSISTS_CACHE):
            with open(TEAM_ASSISTS_CACHE, "r") as f:
                return json.load(f)
        return {}


def fetch_completed_teams_for_date(date_str):
    """
    Returns a set of team names that have played on this date.
    Used to determine if a game is final for DNP logic.
    """
    try:
        print(f"  Fetching team stats to verify completed games for {date_str}...")
        stats = leaguedashteamstats.LeagueDashTeamStats(
            date_from_nullable=date_str,
            date_to_nullable=date_str
        ).get_data_frames()[0]
        
        if stats.empty:
            return set()
            
        # Return set of TEAM_NAME
        return set(stats['TEAM_NAME'].unique())
    except Exception as e:
        print(f"  Error fetching completed teams: {e}")
        return set()


# =============================================================================
# Team mapping helpers
# =============================================================================

def get_nba_team_rosters():
    """A lightweight roster mapping used only to match Odds API players to teams."""
    # NOTE: This is heuristic and intentionally simple.
    return {
        "Boston Celtics": ["Tatum", "Brown", "White", "Holiday", "Porzingis", "Horford", "Hauser", "Pritchard"],
        "Washington Wizards": ["Kuzma", "Poole", "Coulibaly", "Bagley", "Jones", "Kispert", "Sarr", "Carrington"],
        "Golden State Warriors": ["Curry", "Wiggins", "Green", "Kuminga", "Podziemski", "Looney", "Payton", "Melton"],
        "Philadelphia 76ers": ["Embiid", "Maxey", "Harris", "Oubre", "Batum", "McCain", "Drummond", "Reed", "Martin", "George"],
        "Brooklyn Nets": ["Johnson", "Claxton", "Thomas", "Finney-Smith", "Sharpe", "Whitehead", "Clowney", "Schroder", "Wilson"],
        "Utah Jazz": ["Markkanen", "Sexton", "Clarkson", "Collins", "Kessler", "Hendricks", "Williams"],
        "Los Angeles Lakers": ["James", "Reaves", "Russell", "Hachimura", "Reddish", "Prince", "Christie", "Knecht"],
        "Toronto Raptors": ["Quickley", "Poeltl", "Dick", "Battle", "Agbaji", "Shead", "Brown"],
        "Minnesota Timberwolves": ["Edwards", "Gobert", "McDaniels", "Conley", "Reid", "Alexander-Walker", "DiVincenzo", "Randle"],
        "New Orleans Pelicans": ["Williamson", "Ingram", "McCollum", "Murphy", "Alvarado", "Hawkins", "Jones"],
        "Miami Heat": ["Butler", "Adebayo", "Herro", "Rozier", "Love", "Highsmith", "Robinson", "Jovic", "Ware"],
        "Orlando Magic": ["Banchero", "Wagner", "Carter", "Isaac", "Suggs", "Anthony", "Fultz", "Caldwell-Pope"],
        "New York Knicks": ["Brunson", "Towns", "Bridges", "Hart", "Anunoby", "McBride", "Achiuwa"],
        "Phoenix Suns": ["Durant", "Booker", "Beal", "Nurkic", "Allen", "Gordon", "Okogie", "O'Neale"],
        "Oklahoma City Thunder": ["Gilgeous-Alexander", "Williams", "Holmgren", "Wallace", "Joe", "Dort", "Caruso", "Hartenstein"],
        "San Antonio Spurs": ["Wembanyama", "Vassell", "Johnson", "Sochan", "Jones", "Branham", "Collins", "Castle", "Fox", "Barnes", "Harper"],
        "Los Angeles Clippers": ["Leonard", "Harden", "Westbrook", "Zubac", "Mann", "Powell", "Coffey", "Dunn"],
        "Denver Nuggets": ["Jokic", "Murray", "Porter", "Gordon", "Watson", "Braun", "Strawther", "Westbrook"],
        "Dallas Mavericks": ["Doncic", "Irving", "Davis", "Washington", "Gafford", "Lively", "Grimes", "Kleber", "Exum"],
        "Sacramento Kings": ["Sabonis", "Murray", "DeRozan", "Huerter", "Monk", "McDermott"],
        "Memphis Grizzlies": ["Morant", "Bane", "Jackson", "Smart", "Williams", "Konchar", "Edey", "Wells"],
        "Cleveland Cavaliers": ["Mitchell", "Garland", "Mobley", "Allen", "LeVert", "Strus", "Okoro", "Wade"],
        "Milwaukee Bucks": ["Antetokounmpo", "Lillard", "Middleton", "Lopez", "Portis", "Connaughton", "Trent"],
        "Indiana Pacers": ["Haliburton", "Turner", "Mathurin", "Nembhard", "Nesmith", "Siakam", "Brown", "Walker"],
        "Atlanta Hawks": ["Young", "Murray", "Johnson", "Hunter", "Bogdanovic", "Okongwu", "Daniels", "Risacher"],
        "Chicago Bulls": ["LaVine", "Vucevic", "Williams", "Dosunmu", "White", "Giddey", "Ball", "Smith"],
        "Charlotte Hornets": ["Ball", "Miller", "Bridges", "Williams", "Richards", "Martin", "Knueppel", "Green"],
        "Detroit Pistons": ["Cunningham", "Ivey", "Duren", "Harris", "Beasley", "Stewart", "Thompson", "Holland", "Robinson"],
        "Houston Rockets": ["Green", "Smith", "Sengun", "VanVleet", "Dillon", "Thompson", "Whitmore", "Eason", "Sheppard"],
        "Portland Trail Blazers": ["Simons", "Grant", "Sharpe", "Ayton", "Thybulle", "Camara", "Henderson", "Clingan"],
    }


def match_player_to_team(player_name: str, home_team: str, away_team: str, rosters: dict):
    """Match a player to their team based on name matching with rosters."""
    full_name_lower = player_name.lower()

    if home_team in rosters:
        for roster_name in rosters[home_team]:
            roster_lower = roster_name.lower()
            if roster_lower in full_name_lower or full_name_lower.endswith(roster_lower):
                return home_team, away_team

    if away_team in rosters:
        for roster_name in rosters[away_team]:
            roster_lower = roster_name.lower()
            if roster_lower in full_name_lower or full_name_lower.endswith(roster_lower):
                return away_team, home_team

    return home_team, away_team


# =============================================================================
# Probability / EV / Rating
# =============================================================================

def calculate_probability_edge(ai_score, season_avg, recent_avg, prop_line, odds, bet_type):
    """Probability edge = |model_prob - market_implied_prob|."""
    if odds is None:
        odds = -110

    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)

    base_prob = 0.50
    ai_multiplier = max(0.0, (ai_score - 9.0) / 1.0)

    if bet_type == "over":
        edge = season_avg - prop_line
    else:
        edge = prop_line - season_avg

    edge_factor = min(abs(edge) / 2.0, 1.0)

    recent_factor = 0.0
    if bet_type == "over" and recent_avg > season_avg:
        recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
    elif bet_type == "under" and recent_avg < season_avg:
        recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)

    model_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15) + recent_factor
    model_prob = min(max(model_prob, 0.40), 0.70)

    return abs(model_prob - implied_prob)


def calculate_ai_rating_props(play):
    """Calculate A.I. Rating for props models (probability-based edges) in 2.3-4.9 range."""
    prob_edge = play.get("probability_edge")

    if prob_edge is None:
        ev = abs(play.get("ev", 0))
        prob_edge = ev / 100.0

    if prob_edge >= 0.15:
        normalized_edge = 5.0
    else:
        normalized_edge = prob_edge / 0.03
        normalized_edge = min(5.0, max(0.0, normalized_edge))

    data_quality = 1.0 if play.get("ai_score", 0) >= 9.0 else 0.85

    confidence = 1.0
    ai_score = play.get("ai_score", 0)
    ev = abs(play.get("ev", 0))

    if ai_score >= 9.8 and ev >= 12:
        confidence = 1.12
    elif ai_score >= 9.5 and ev >= 10:
        confidence = 1.08
    elif ai_score >= 9.0 and ev >= 8:
        confidence = 1.05
    elif ai_score >= 9.0:
        confidence = 1.0
    else:
        confidence = 0.95

    confidence = max(0.9, min(1.15, confidence))

    composite_rating = normalized_edge * data_quality * confidence

    ai_rating = 2.3 + (composite_rating / 5.0) * 2.6
    ai_rating = max(2.3, min(4.9, ai_rating))

    return round(ai_rating, 1)


def calculate_ev(ai_score, prop_line, season_avg, recent_avg, odds, bet_type):
    """Expected value using the standard props mapping; tuned for ~60% at AI 9.5+."""
    if odds is None:
        odds = -110

    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)

    base_prob = 0.50
    ai_multiplier = max(0.0, (ai_score - 9.0) / 1.0)

    if bet_type == "over":
        edge = season_avg - prop_line
    else:
        edge = prop_line - season_avg

    edge_factor = min(abs(edge) / 2.0, 1.0)

    recent_factor = 0.0
    if bet_type == "over" and recent_avg > season_avg:
        recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
    elif bet_type == "under" and recent_avg < season_avg:
        recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)

    true_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15) + recent_factor
    true_prob = min(max(true_prob, 0.40), 0.70)

    if odds > 0:
        ev = (true_prob * (odds / 100)) - (1 - true_prob)
    else:
        ev = (true_prob * (100 / abs(odds))) - (1 - true_prob)

    return ev * 100


# =============================================================================
# Odds fetching
# =============================================================================

def get_player_props():
    """Fetch player assists prop odds from The Odds API.

    Returns list of dicts each containing:
    player, prop_line, over_price, under_price, team, opponent, home_team, away_team, game_time
    """
    print(f"\n{Colors.CYAN}Fetching player assists prop odds...{Colors.END}")
    rosters = get_nba_team_rosters()

    events_url = "https://api.the-odds-api.com/v4/sports/basketball_nba/events"
    events_params = {"apiKey": API_KEY}

    if not API_KEY:
        print(f"{Colors.RED}✗ Missing ODDS_API_KEY; cannot fetch props.{Colors.END}")
        return []

    try:
        events_response = requests.get(events_url, params=events_params, timeout=10)
        if events_response.status_code != 200:
            print(f"{Colors.RED}✗ API Error: {events_response.status_code}{Colors.END}")
            return []

        events = events_response.json()
        print(f"{Colors.CYAN}  Found {len(events)} upcoming games{Colors.END}")

        all_props = []

        # Filter for upcoming games only
        upcoming_events = []
        current_time_utc = datetime.now(timezone.utc)
        
        for event in events:
            try:
                commence_time = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
                if commence_time > current_time_utc:
                    upcoming_events.append(event)
            except:
                continue
                
        print(f"{Colors.CYAN}  Filtered to {len(upcoming_events)} upcoming games{Colors.END}")

        for i, event in enumerate(upcoming_events[:10], 1):
            event_id = event["id"]
            home_team = event["home_team"]
            away_team = event["away_team"]

            odds_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
            odds_params = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "player_assists",
                "oddsFormat": "american",
            }

            odds_response = requests.get(odds_url, params=odds_params, timeout=15)

            if odds_response.status_code == 200:
                odds_data = odds_response.json()
                bookmakers = odds_data.get("bookmakers") or []
                if bookmakers:
                    fanduel = next((b for b in bookmakers if b.get("key") == "fanduel"), bookmakers[0])
                    for market in fanduel.get("markets", []):
                        if market.get("key") != "player_assists":
                            continue

                        # Group over/under outcomes by (player, line)
                        grouped: dict[tuple[str, float], dict] = {}
                        for outcome in market.get("outcomes", []):
                            player_name = outcome.get("description")
                            point = outcome.get("point")
                            if player_name is None or point is None:
                                continue

                            side = (outcome.get("name") or "").strip().lower()
                            price = outcome.get("price", -110)

                            key = (player_name, float(point))
                            if key not in grouped:
                                player_team, player_opponent = match_player_to_team(
                                    player_name, home_team, away_team, rosters
                                )
                                grouped[key] = {
                                    "player": player_name,
                                    "prop_line": float(point),
                                    "over_price": None,
                                    "under_price": None,
                                    "team": player_team,
                                    "opponent": player_opponent,
                                    "home_team": home_team,
                                    "away_team": away_team,
                                    "game_time": event.get("commence_time"),
                                }

                            if side == "over":
                                grouped[key]["over_price"] = price
                            elif side == "under":
                                grouped[key]["under_price"] = price

                        all_props.extend(grouped.values())

            print(f"{Colors.CYAN}  Game {i}/{len(events[:10])}: {away_team} @ {home_team}{Colors.END}")

        print(f"{Colors.GREEN}✓ Fetched {len(all_props)} player assists props (grouped){Colors.END}")
        return all_props

    except Exception as e:
        print(f"{Colors.RED}✗ Error fetching props: {e}{Colors.END}")
        return []


# =============================================================================
# Model logic
# =============================================================================

def calculate_ai_score(player_data, prop_line, bet_type, opponent_assists=None):
    """Calculate A.I. Score for assists props using REAL stats.

    Factors:
    - Season vs line edge (strict)
    - Recent form vs line
    - Assists per 36
    - Consistency
    - Opponent assists factor (pace + assists allowed)
    - Position factor (guards typically higher assists)

    Returns score 0-10.
    """
    score = 4.0

    season_avg = float(player_data.get("season_ast_avg", 0) or 0)
    recent_avg = float(player_data.get("recent_ast_avg", 0) or 0)
    ast_per_36 = float(player_data.get("ast_per_36", 0) or 0)
    consistency = float(player_data.get("consistency_score", 0.3) or 0.3)
    games_played = int(player_data.get("games_played", 0) or 0)
    minutes = float(player_data.get("minutes", 0) or 0)

    if games_played < 5:
        return 0.0

    if minutes < 15:
        return 0.0

    if bet_type == "over":
        edge_above = season_avg - prop_line
        if edge_above >= MIN_EDGE_OVER_LINE:
            score += 3.5
        elif edge_above >= 1.5:
            score += 2.5
        elif edge_above >= 1.0:
            score += 1.5
        elif edge_above >= 0.5:
            score += 0.5
        else:
            score -= 2.0
            if recent_avg < prop_line + 0.5:
                return 0.0

        recent_edge = recent_avg - prop_line
        if recent_edge >= MIN_RECENT_FORM_EDGE:
            score += 2.5
        elif recent_edge >= 1.0:
            score += 1.5
        elif recent_avg > season_avg + 0.8:
            score += 1.0
        elif recent_avg >= prop_line:
            score += 0.5
        else:
            score -= 1.5

        # Assists rate bonus (guards/playmakers typically higher)
        if ast_per_36 >= 10.0:
            score += 1.5
        elif ast_per_36 >= 8.0:
            score += 1.0
        elif ast_per_36 >= 6.0:
            score += 0.5

        score += consistency * 0.8

        if opponent_assists:
            factor = opponent_assists.get("assists_factor", 1.0) or 1.0
            if factor > 1.05:
                score += 1.0
            elif factor < 0.95:
                score -= 0.5

    else:  # under
        edge_below = prop_line - season_avg
        if edge_below >= MIN_EDGE_UNDER_LINE:
            score += 3.5
        elif edge_below >= 1.2:
            score += 2.5
        elif edge_below >= 0.8:
            score += 1.5
        elif edge_below >= 0.4:
            score += 0.5
        else:
            score -= 2.0
            if recent_avg > prop_line - 0.5:
                return 0.0

        recent_edge = prop_line - recent_avg
        if recent_edge >= MIN_RECENT_FORM_EDGE:
            score += 2.5
        elif recent_edge >= 1.0:
            score += 1.5
        elif recent_avg < season_avg - 0.8:
            score += 1.0
        elif recent_avg <= prop_line:
            score += 0.5
        else:
            score -= 1.5

        if ast_per_36 < 4.0:
            score += 1.0
        elif ast_per_36 < 6.0:
            score += 0.5

        score += (1.0 - consistency) * 0.5

        if opponent_assists:
            factor = opponent_assists.get("assists_factor", 1.0) or 1.0
            if factor < 0.95:
                score += 1.0
            elif factor > 1.05:
                score -= 0.5

    final_score = min(10.0, max(0.0, score))

    if bet_type == "over" and season_avg < prop_line + 0.5:
        final_score = min(final_score, 8.5)
    elif bet_type == "under" and season_avg > prop_line - 0.5:
        final_score = min(final_score, 8.5)

    return round(final_score, 2)


def analyze_props(props_list, player_stats, assists_factors):
    """Analyze all player assists props using REAL NBA stats."""
    print(f"\n{Colors.CYAN}Analyzing {len(props_list)} player props with REAL stats...{Colors.END}")

    over_plays = []
    under_plays = []
    skipped_no_stats = 0
    skipped_low_score = 0

    for prop in props_list:
        player_name = prop.get("player")
        prop_line = prop.get("prop_line")
        opponent_team = prop.get("opponent")
        if not player_name or prop_line is None or not opponent_team:
            continue

        player_data = player_stats.get(player_name)
        if not player_data:
            # Fuzzy match by last name
            for name, stats in player_stats.items():
                if player_name.split()[-1].lower() in name.lower() or name.split()[-1].lower() in player_name.lower():
                    player_data = stats
                    break

            if not player_data:
                skipped_no_stats += 1
                continue

        opponent_assists = None
        if opponent_team in assists_factors:
            opponent_assists = assists_factors[opponent_team]
        else:
            for team_name, factors in assists_factors.items():
                if opponent_team.lower() in team_name.lower() or team_name.lower() in opponent_team.lower():
                    opponent_assists = factors
                    break

        season_avg = float(player_data.get("season_ast_avg", 0) or 0)
        recent_avg = float(player_data.get("recent_ast_avg", 0) or 0)

        # OVER
        over_score = calculate_ai_score(player_data, prop_line, "over", opponent_assists)
        if over_score >= MIN_AI_SCORE:
            if season_avg >= prop_line + 0.5 and recent_avg >= prop_line + 0.3:
                over_odds = prop.get("over_price")
                if over_odds is None:
                    over_odds = prop.get("under_price")

                ev = calculate_ev(over_score, prop_line, season_avg, recent_avg, over_odds, "over")
                prob_edge = calculate_probability_edge(over_score, season_avg, recent_avg, prop_line, over_odds, "over")

                play = {
                    "player": player_name,
                    "prop": f"OVER {prop_line} AST",
                    "team": prop.get("team"),
                    "opponent": opponent_team,
                    "home_team": prop.get("home_team"),
                    "away_team": prop.get("away_team"),
                    "ai_score": over_score,
                    "odds": over_odds if over_odds is not None else -110,
                    "game_time": prop.get("game_time"),
                    "season_avg": round(season_avg, 2),
                    "recent_avg": round(recent_avg, 2),
                    "edge": round(season_avg - prop_line, 2),
                    "ev": round(ev, 2),
                    "probability_edge": prob_edge,
                }
                play["ai_rating"] = calculate_ai_rating_props(play)
                over_plays.append(play)
            else:
                skipped_low_score += 1
        else:
            skipped_low_score += 1

        # UNDER
        under_score = calculate_ai_score(player_data, prop_line, "under", opponent_assists)
        if under_score >= MIN_AI_SCORE:
            if season_avg <= prop_line - 0.5 and recent_avg <= prop_line - 0.3:
                under_odds = prop.get("under_price")
                if under_odds is None:
                    under_odds = prop.get("over_price")

                ev = calculate_ev(under_score, prop_line, season_avg, recent_avg, under_odds, "under")
                prob_edge = calculate_probability_edge(under_score, season_avg, recent_avg, prop_line, under_odds, "under")

                play = {
                    "player": player_name,
                    "prop": f"UNDER {prop_line} AST",
                    "team": prop.get("team"),
                    "opponent": opponent_team,
                    "home_team": prop.get("home_team"),
                    "away_team": prop.get("away_team"),
                    "ai_score": under_score,
                    "odds": under_odds if under_odds is not None else -110,
                    "game_time": prop.get("game_time"),
                    "season_avg": round(season_avg, 2),
                    "recent_avg": round(recent_avg, 2),
                    "edge": round(prop_line - season_avg, 2),
                    "ev": round(ev, 2),
                    "probability_edge": prob_edge,
                }
                play["ai_rating"] = calculate_ai_rating_props(play)
                under_plays.append(play)
            else:
                skipped_low_score += 1
        else:
            skipped_low_score += 1

    # Deduplicate
    seen_over = set()
    unique_over = []
    for play in over_plays:
        key = f"{play['player']}_{play['prop']}"
        if key not in seen_over:
            seen_over.add(key)
            unique_over.append(play)

    seen_under = set()
    unique_under = []
    for play in under_plays:
        key = f"{play['player']}_{play['prop']}"
        if key not in seen_under:
            seen_under.add(key)
            unique_under.append(play)

    def get_sort_score(p):
        return (p.get("ai_rating", 2.3), p.get("ai_score", 0), p.get("ev", 0))

    unique_over.sort(key=get_sort_score, reverse=True)
    unique_under.sort(key=get_sort_score, reverse=True)

    over_plays = unique_over[:TOP_PLAYS_COUNT]
    under_plays = unique_under[:TOP_PLAYS_COUNT]

    print(f"{Colors.GREEN}✓ Found {len(over_plays)} top OVER plays (A.I. Score >= {MIN_AI_SCORE}){Colors.END}")
    print(f"{Colors.GREEN}✓ Found {len(under_plays)} top UNDER plays (A.I. Score >= {MIN_AI_SCORE}){Colors.END}")
    if skipped_no_stats:
        print(f"{Colors.YELLOW}  Skipped {skipped_no_stats} props (no player stats found){Colors.END}")
    if skipped_low_score:
        print(f"{Colors.YELLOW}  Skipped {skipped_low_score} props (score below {MIN_AI_SCORE} or failed checks){Colors.END}")

    return over_plays, under_plays


# =============================================================================
# HTML Helper Functions
# =============================================================================

def get_team_abbreviation(team_name):
    """Get the team abbreviation for ESPN logo URLs."""
    abbrev_map = {
        "Atlanta Hawks": "atl", "Boston Celtics": "bos", "Brooklyn Nets": "bkn",
        "Charlotte Hornets": "cha", "Chicago Bulls": "chi", "Cleveland Cavaliers": "cle",
        "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det",
        "Golden State Warriors": "gs", "Houston Rockets": "hou", "Indiana Pacers": "ind",
        "LA Clippers": "lac", "Los Angeles Clippers": "lac", "Los Angeles Lakers": "lal",
        "LA Lakers": "lal", "Memphis Grizzlies": "mem", "Miami Heat": "mia",
        "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min", "New Orleans Pelicans": "no",
        "New York Knicks": "ny", "Oklahoma City Thunder": "okc", "Orlando Magic": "orl",
        "Philadelphia 76ers": "phi", "Phoenix Suns": "phx", "Portland Trail Blazers": "por",
        "Sacramento Kings": "sac", "San Antonio Spurs": "sa", "Toronto Raptors": "tor",
        "Utah Jazz": "utah", "Washington Wizards": "wsh"
    }
    return abbrev_map.get(team_name, "nba").lower()


def format_game_datetime(game_time_str):
    """Format the game time string into a readable format."""
    try:
        if not game_time_str:
            return 'TBD'
        et = pytz.timezone('US/Eastern')
        dt_obj = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        dt_et = dt_obj.astimezone(et)
        return dt_et.strftime("%a %m/%d %I:%M %p ET")
    except Exception:
        return game_time_str if game_time_str else 'TBD'


def calculate_player_stats(player_name, tracking_data):
    """Calculate player-specific stats from tracking data."""
    if not tracking_data:
        return None
    
    picks = tracking_data.get('picks', [])
    player_picks = [p for p in picks if p.get('player') == player_name and p.get('result') in ['win', 'loss']]
    
    if not player_picks:
        return None
    
    wins = sum(1 for p in player_picks if p.get('result') == 'win')
    losses = len(player_picks) - wins
    
    total_profit = sum(p.get('profit_loss', 0) for p in player_picks)
    player_roi = (total_profit / len(player_picks)) * 100 if player_picks else 0
    
    return {
        'season_record': f'{wins}-{losses}',
        'player_roi': round(player_roi, 1)
    }


def generate_reasoning_tags(play, player_data, opponent_factors):
    """Generate reasoning tags based on various factors."""
    tags = []
    
    # Edge-based tags
    edge = play.get('edge', 0)
    if abs(edge) >= 3.0:
        tags.append({"text": "Strong Edge", "color": "green"})
    elif abs(edge) >= 2.0:
        tags.append({"text": "Good Edge", "color": "blue"})
    
    # AI score tags
    ai_score = play.get('ai_score', 0)
    if ai_score >= 9.5:
        tags.append({"text": "Premium Pick", "color": "green"})
    elif ai_score >= 9.0:
        tags.append({"text": "High Confidence", "color": "blue"})
    
    # Recent form tag
    recent_avg = play.get('recent_avg', 0)
    season_avg = play.get('season_avg', 0)
    if recent_avg and season_avg:
        if recent_avg > season_avg * 1.1:
            tags.append({"text": "Hot Streak", "color": "green"})
        elif recent_avg < season_avg * 0.9:
            tags.append({"text": "Cold Streak", "color": "red"})
    
    # Opponent factor tags (for assists - opp_ast_allowed)
    if opponent_factors:
        opp_ast = opponent_factors.get('opp_ast_allowed', 0)
        if opp_ast > 26:
            tags.append({"text": "Weak AST Defense", "color": "green"})
        elif opp_ast < 22:
            tags.append({"text": "Strong AST Defense", "color": "red"})
    
    return tags


# =============================================================================
# HTML output
# =============================================================================

def generate_html_output(over_plays, under_plays, stats=None, tracking_data=None, ast_factors=None, player_stats=None):
    """Generate HTML output matching the modern styling guide"""
    from datetime import datetime as dt
    et = pytz.timezone('US/Eastern')
    now = dt.now(et)
    
    # Helper function to format odds for display
    def format_odds(odds_value):
        if odds_value is None:
            return 'N/A'
        try:
            odds = int(odds_value)
            return f'+{odds}' if odds > 0 else str(odds)
        except:
            return str(odds_value) if odds_value else 'N/A'
    
    # Helper function to get short team name
    def get_short_team_name(team_name):
        short_name_map = {
            "Atlanta Hawks": "Hawks", "Boston Celtics": "Celtics", "Brooklyn Nets": "Nets",
            "Charlotte Hornets": "Hornets", "Chicago Bulls": "Bulls", "Cleveland Cavaliers": "Cavaliers",
            "Dallas Mavericks": "Mavericks", "Denver Nuggets": "Nuggets", "Detroit Pistons": "Pistons",
            "Golden State Warriors": "Warriors", "Houston Rockets": "Rockets", "Indiana Pacers": "Pacers",
            "LA Clippers": "Clippers", "Los Angeles Clippers": "Clippers", "Los Angeles Lakers": "Lakers",
            "LA Lakers": "Lakers", "Memphis Grizzlies": "Grizzlies", "Miami Heat": "Heat",
            "Milwaukee Bucks": "Bucks", "Minnesota Timberwolves": "Timberwolves", "New Orleans Pelicans": "Pelicans",
            "New York Knicks": "Knicks", "Oklahoma City Thunder": "Thunder", "Orlando Magic": "Magic",
            "Philadelphia 76ers": "76ers", "Phoenix Suns": "Suns", "Portland Trail Blazers": "Trail Blazers",
            "Sacramento Kings": "Kings", "San Antonio Spurs": "Spurs", "Toronto Raptors": "Raptors",
            "Utah Jazz": "Jazz", "Washington Wizards": "Wizards"
        }
        return short_name_map.get(team_name, team_name)
    
    player_stats_lookup = player_stats or {}
    defense_lookup = ast_factors or {}
    
    # Get completed picks and calculate recent performance
    completed_picks = []
    if tracking_data:
        completed_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() in ['win', 'loss']]
        # Sort by date (most recent first) - assuming picks have a date field
        completed_picks.sort(key=lambda x: x.get('game_time', ''), reverse=True)
    
    # Calculate Last 10, Last 20, and Last 50 picks performance
    last_10 = calculate_recent_performance(completed_picks, 10)
    last_20 = calculate_recent_performance(completed_picks, 20)
    last_50 = calculate_recent_performance(completed_picks, 50)
    

    daily_tracking_html = ""
    if stats and 'today' in stats:
        t_stats = stats.get('today', {'record':'0-0', 'profit':0, 'roi':0})
        y_stats = stats.get('yesterday', {'record':'0-0', 'profit':0, 'roi':0})
        
        t_profit_class = "txt-green" if t_stats['profit'] > 0 else ("txt-red" if t_stats['profit'] < 0 else "")
        y_profit_class = "txt-green" if y_stats['profit'] > 0 else ("txt-red" if y_stats['profit'] < 0 else "")

        daily_tracking_html = f"""
        <section style="margin-top: 2rem;">
            <div class="section-title">📅 Daily Performance</div>
            <div class="metrics-grid" style="grid-template-columns: repeat(2, 1fr);">
                <!-- Today -->
                <div class="prop-card" style="padding: 1rem; margin:0;">
                    <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">TODAY</div>
                    <div style="text-align:center;">
                        <div style="font-weight:700; font-size:1.1rem;">{t_stats['record']}</div>
                        <div class="{t_profit_class}">{t_stats['profit']:+.1f}u</div>
                        <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">{t_stats['roi']:.1f}% ROI</div>
                    </div>
                </div>
                <!-- Yesterday -->
                <div class="prop-card" style="padding: 1rem; margin:0;">
                    <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">YESTERDAY</div>
                    <div style="text-align:center;">
                        <div style="font-weight:700; font-size:1.1rem;">{y_stats['record']}</div>
                        <div class="{y_profit_class}">{y_stats['profit']:+.1f}u</div>
                         <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">{y_stats['roi']:.1f}% ROI</div>
                    </div>
                </div>
            </div>
        </section>
        """

    
    # CSS Styles (defined separately to avoid f-string brace escaping issues)
    css_styles = """
        :root {
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-blue: #60a5fa;
            --border-color: #333333;
        }

        body {
            margin: 0;
            padding: 20px;
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            -webkit-font-smoothing: antialiased;
        }

        .container { max-width: 800px; margin: 0 auto; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
        }
        h1 { margin: 0; font-size: 24px; font-weight: 700; margin-bottom: 5px; }
        .subheader { font-size: 18px; font-weight: 600; color: var(--text-primary); margin-bottom: 5px; }
        .date-sub { color: var(--text-secondary); font-size: 14px; margin-top: 5px; }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 30px;
        }
        .stat-box {
            background-color: var(--bg-card);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            border: 1px solid var(--border-color);
        }
        .stat-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 5px; }
        .stat-value { font-size: 20px; font-weight: 700; }

        .section-title {
            font-size: 18px;
            margin-bottom: 15px;
            display: flex; align-items: center;
        }
        .section-title span.highlight { color: var(--accent-green); margin-left: 8px; font-size: 14px; }

        .prop-card {
            background-color: var(--bg-card);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
        }

        .card-header {
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: var(--bg-card-secondary);
            border-bottom: 1px solid var(--border-color);
        }

        .header-left { display: flex; align-items: center; gap: 12px; }
        .team-logo { width: 45px; height: 45px; border-radius: 50%; padding: 2px; object-fit: contain; }
        .player-info h2 { margin: 0; font-size: 18px; line-height: 1.2; }
        .matchup-info { color: var(--text-secondary); font-size: 13px; margin-top: 2px; }
        .game-meta { text-align: right; }
        .game-date-time { font-size: 12px; color: var(--text-secondary); background: #333; padding: 6px 10px; border-radius: 6px; font-weight: 500; white-space: nowrap; }

        .card-body { padding: 20px; }
        .bet-main-row { margin-bottom: 15px; }
        .bet-selection { font-size: 22px; font-weight: 800; }
        .bet-selection .line { color: var(--text-primary); }
        .bet-odds { font-size: 18px; color: var(--text-secondary); font-weight: 500; margin-left: 8px; }

        .model-subtext { color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid var(--border-color); }
        .model-subtext strong { color: var(--text-primary); }

        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }
        .metric-item { background-color: var(--bg-main); padding: 10px; border-radius: 8px; text-align: center; }
        .metric-lbl { display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }
        .metric-val { font-size: 16px; font-weight: 700; }

        .player-stats { background-color: var(--bg-card-secondary); border-radius: 8px; padding: 12px 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border-color); }
        .player-stats-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
        .player-stats-value { font-size: 16px; font-weight: 700; }
        .player-stats-item { text-align: center; flex: 1; }
        .player-stats-divider { width: 1px; height: 30px; background-color: var(--border-color); }

        .tags-container { display: flex; flex-wrap: wrap; gap: 8px; }
        .tag { font-size: 12px; padding: 6px 10px; border-radius: 6px; font-weight: 500; }

        .txt-green { color: var(--accent-green); }
        .txt-red { color: var(--accent-red); }
        
        .tag-green { background-color: rgba(74, 222, 128, 0.15); color: var(--accent-green); }
        .tag-red { background-color: rgba(248, 113, 113, 0.15); color: var(--accent-red); }
        .tag-blue { background-color: rgba(96, 165, 250, 0.15); color: var(--accent-blue); }
        
        .metric-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
        }
        .text-red { color: var(--accent-red); }
        .tracking-section { margin-top: 3rem; }
        .tracking-header { 
            font-size: 1.5rem; 
            font-weight: 700; 
            color: var(--text-primary); 
            margin-bottom: 1.5rem; 
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        .metrics-row {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
        }
        .metric-title {
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
        }
        .metric-value {
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--text-primary);
        }
        .metric-value.good { color: var(--accent-green); }

        @media (max-width: 600px) {
            .summary-grid { grid-template-columns: repeat(2, 1fr); }
            .stat-box:last-child { grid-column: span 2; }
            .card-header { padding: 12px 15px; }
            .team-logo { width: 38px; height: 38px; }
            .player-info h2 { font-size: 16px; }
        }
    """
    
    # Pre-format header stats to avoid f-string syntax errors
    s_wins = stats.get('wins', 0)
    s_losses = stats.get('losses', 0)
    s_wr = round(stats.get('win_rate', 0.0), 1)
    s_prof = stats.get('total_profit', 0.0)
    s_prof_str = f"{s_prof:+.1f}u"
    s_prof_color = 'var(--accent-green)' if s_prof > 0 else 'var(--accent-red)'

    # Define Header
    html_header = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics - NBA Assists</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
{css_styles}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">NBA Assists Model</div>
            <div class="date-sub">Profitable Version &bull; Season {CURRENT_SEASON}</div>
        </div>
        <div style="text-align: right;">
            <div class="metric-title">SEASON RECORD</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                {s_wins}-{s_losses} ({s_wr}%)
            </div>
            <div style="font-size: 0.9rem; color: {s_prof_color};">
                 {s_prof_str}
            </div>
        </div>
    </header>
"""


    # Generate OVER plays cards
    over_html = ""
    if over_plays:
        over_html = '<section><div class="section-title">Top Value Plays <span class="highlight">Min AI Score: {}</span></div>'.format(MIN_AI_SCORE)
        
        for play in over_plays:
            prop_str = play.get('prop', '')
            line_match = re.search(r'(\d+\.?\d*)\s*AST', prop_str)
            prop_line_display = line_match.group(0) if line_match else prop_str.replace('OVER ', '').replace('UNDER ', '')
            
            game_datetime_str = format_game_datetime(play.get('game_time', ''))
            team_abbrev = get_team_abbreviation(play.get('team', ''))
            logo_url = f"https://a.espncdn.com/i/teamlogos/nba/500/{team_abbrev}.png"
            
            short_team = get_short_team_name(play.get('team', ''))
            short_opponent = get_short_team_name(play.get('opponent', ''))
            home_team = play.get('home_team', '')
            matchup_display = f"{short_opponent} @ {short_team}" if play.get('team') == home_team else f"{short_team} @ {short_opponent}"
            
            player_data = player_stats_lookup.get(play.get('player'))
            opponent_factors = defense_lookup.get(play.get('opponent'))
            
            player_stats_data = calculate_player_stats(play.get('player'), tracking_data) if tracking_data else None
            tags = generate_reasoning_tags(play, player_data, opponent_factors)
            tags_html = "".join([f'<span class="tag tag-{tag["color"]}">{tag["text"]}</span>\n' for tag in tags])
            
            season_avg = play.get('season_avg', 0)
            edge = play.get('edge', 0)
            model_prediction = season_avg + edge if edge > 0 else season_avg - abs(edge)
            ai_score = play.get('ai_score', 0)
            win_prob = min(70, max(40, 50 + (ai_score - 9.5) * 3))
            
            player_stats_html = ""
            if player_stats_data:
                player_roi_sign = '+' if player_stats_data['player_roi'] > 0 else ''
                player_stats_html = f'''
                <div class="player-stats">
                    <div class="player-stats-item">
                        <div class="player-stats-label">This Season</div>
                        <div class="player-stats-value">{player_stats_data['season_record']}</div>
                    </div>
                    <div class="player-stats-divider"></div>
                    <div class="player-stats-item">
                        <div class="player-stats-label">Player ROI</div>
                        <div class="player-stats-value txt-green">{player_roi_sign}{player_stats_data['player_roi']:.1f}%</div>
                    </div>
                </div>'''
            
            ev = play.get('ev', 0)
            ev_display = f"{ev:+.1f}%" if ev != 0 else "0.0%"
            ev_color_class = "txt-green" if ev > 0 else "txt-red" if ev < 0 else ""
            
            over_html += f'''
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                    <img src="{logo_url}" alt="{play.get('team', '')} Logo" class="team-logo">
                    <div class="player-info">
                        <h2>{play.get('player', '')}</h2>
                        <div class="matchup-info">{matchup_display}</div>
                    </div>
                </div>
                <div class="game-meta">
                    <div class="game-date-time">{game_datetime_str}</div>
                </div>
            </div>
            <div class="card-body">
                <div class="bet-main-row">
                    <div class="bet-selection">
                        <span class="txt-green">OVER</span> 
                        <span class="line">{prop_line_display}</span> 
                        <span class="bet-odds">{format_odds(play.get('odds'))}</span>
                    </div>
                </div>
                <div class="model-subtext">
                    Model Predicts: <strong>{model_prediction:.1f} AST</strong> (Edge: {edge:+.1f})
                </div>
                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="metric-lbl">AI SCORE</span>
                        <span class="metric-val txt-green">{play.get('ai_score', 0):.1f}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">EV</span>
                        <span class="metric-val {ev_color_class}">{ev_display}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">WIN %</span>
                        <span class="metric-val">{int(win_prob)}%</span>
                    </div>
                </div>
                {player_stats_html}
                <div class="tags-container">
                    {tags_html}
                </div>
            </div>
        </div>'''
        
        over_html += "</section>"

    # Generate UNDER plays cards
    under_html = ""
    if under_plays:
        for play in under_plays:
            prop_str = play.get('prop', '')
            line_match = re.search(r'(\d+\.?\d*)\s*AST', prop_str)
            prop_line_display = line_match.group(0) if line_match else prop_str.replace('OVER ', '').replace('UNDER ', '')
            
            game_datetime_str = format_game_datetime(play.get('game_time', ''))
            team_abbrev = get_team_abbreviation(play.get('team', ''))
            logo_url = f"https://a.espncdn.com/i/teamlogos/nba/500/{team_abbrev}.png"
            
            short_team = get_short_team_name(play.get('team', ''))
            short_opponent = get_short_team_name(play.get('opponent', ''))
            home_team = play.get('home_team', '')
            matchup_display = f"{short_opponent} @ {short_team}" if play.get('team') == home_team else f"{short_team} @ {short_opponent}"
            
            player_data = player_stats_lookup.get(play.get('player'))
            opponent_factors = defense_lookup.get(play.get('opponent'))
            
            player_stats_data = calculate_player_stats(play.get('player'), tracking_data) if tracking_data else None
            tags = generate_reasoning_tags(play, player_data, opponent_factors)
            tags_html = "".join([f'<span class="tag tag-{tag["color"]}">{tag["text"]}</span>\n' for tag in tags])
            
            season_avg = play.get('season_avg', 0)
            edge = play.get('edge', 0)
            model_prediction = season_avg - abs(edge)
            ai_score = play.get('ai_score', 0)
            win_prob = min(70, max(40, 50 + (ai_score - 9.5) * 3))
            
            player_stats_html = ""
            if player_stats_data:
                player_roi_sign = '+' if player_stats_data['player_roi'] > 0 else ''
                player_stats_html = f'''
                <div class="player-stats">
                    <div class="player-stats-item">
                        <div class="player-stats-label">This Season</div>
                        <div class="player-stats-value">{player_stats_data['season_record']}</div>
                    </div>
                    <div class="player-stats-divider"></div>
                    <div class="player-stats-item">
                        <div class="player-stats-label">Player ROI</div>
                        <div class="player-stats-value txt-green">{player_roi_sign}{player_stats_data['player_roi']:.1f}%</div>
                    </div>
                </div>'''
            
            ev = play.get('ev', 0)
            ev_display = f"{ev:+.1f}%" if ev != 0 else "0.0%"
            ev_color_class = "txt-green" if ev > 0 else "txt-red" if ev < 0 else ""
            
            under_html += f'''
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                    <img src="{logo_url}" alt="{play.get('team', '')} Logo" class="team-logo">
                    <div class="player-info">
                        <h2>{play.get('player', '')}</h2>
                        <div class="matchup-info">{matchup_display}</div>
                    </div>
                </div>
                <div class="game-meta">
                    <div class="game-date-time">{game_datetime_str}</div>
                </div>
            </div>
            <div class="card-body">
                <div class="bet-main-row">
                    <div class="bet-selection">
                        <span class="txt-red">UNDER</span> 
                        <span class="line">{prop_line_display}</span> 
                        <span class="bet-odds">{format_odds(play.get('odds'))}</span>
                    </div>
                </div>
                <div class="model-subtext">
                    Model Predicts: <strong>{model_prediction:.1f} AST</strong> (Edge: {edge:.1f})
                </div>
                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="metric-lbl">AI SCORE</span>
                        <span class="metric-val txt-green">{play.get('ai_score', 0):.1f}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">EV</span>
                        <span class="metric-val {ev_color_class}">{ev_display}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">WIN %</span>
                        <span class="metric-val">{int(win_prob)}%</span>
                    </div>
                </div>
                {player_stats_html}
                <div class="tags-container">
                    {tags_html}
                </div>
            </div>
        </div>'''

    # Summary stats grid
    summary_html = ""
    if stats and stats.get('total', 0) > 0:
        roi_pct = stats.get('roi_pct', 0)
        win_rate = stats.get('win_rate', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        roi_color_class = "txt-green" if roi_pct > 0 else "txt-red"
        roi_sign = '+' if roi_pct > 0 else ''
        summary_html = f'''
    <section>
        <div class="summary-grid">
            <div class="stat-box">
                <div class="stat-label">Season ROI</div>
                <div class="stat-value {roi_color_class}">{roi_sign}{roi_pct:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value">{win_rate:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Record</div>
                <div class="stat-value">{wins}-{losses}</div>
            </div>
        </div>
    </section>'''
    
    # Model performance section
    performance_html = ""
    if stats and stats.get('total', 0) > 0:
        total = stats['total']
        wins = stats['wins']
        losses = stats['losses']
        win_rate = stats['win_rate']
        roi_pct = stats['roi_pct']
        
        roi_color_class = "txt-green" if roi_pct > 0 else "txt-red"
        roi_sign = '+' if roi_pct > 0 else ''
        
        over_record = stats['over_record']
        over_roi = stats['over_roi']
        over_roi_color_class = "txt-green" if over_roi > 0 else "txt-red"
        over_roi_sign = '+' if over_roi > 0 else ''
        
        under_record = stats['under_record']
        under_roi = stats['under_roi']
        under_roi_color_class = "txt-green" if under_roi > 0 else "txt-red"
        under_roi_sign = '+' if under_roi > 0 else ''
        
        performance_html = f'''
    <section>
        <div class="section-title">NBA Assists Model Performance</div>
        <div class="summary-grid">
            <div class="stat-box">
                <div class="stat-label">Overall Record</div>
                <div class="stat-value">{wins}-{losses}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">ROI</div>
                <div class="stat-value {roi_color_class}">{roi_sign}{roi_pct:.1f}%</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">OVER: {over_record}</div>
                <div class="stat-value {over_roi_color_class}">{over_roi_sign}{over_roi:.1f}% ROI</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">UNDER: {under_record}</div>
                <div class="stat-value {under_roi_color_class}">{under_roi_sign}{under_roi:.1f}% ROI</div>
            </div>
        </div>
    </section>'''
    
    # Tracking section HTML
    tracking_html = ""
    if tracking_data and completed_picks:
        # Format win rate classes
        last_10_wr_class = 'good' if last_10['win_rate'] >= 55 else ('text-red' if last_10['win_rate'] < 50 else '')
        last_10_profit_class = 'good' if last_10['profit'] > 0 else ('text-red' if last_10['profit'] < 0 else '')
        last_10_roi_class = 'good' if last_10['roi'] > 0 else ('text-red' if last_10['roi'] < 0 else '')
        
        last_20_wr_class = 'good' if last_20['win_rate'] >= 55 else ('text-red' if last_20['win_rate'] < 50 else '')
        last_20_profit_class = 'good' if last_20['profit'] > 0 else ('text-red' if last_20['profit'] < 0 else '')
        last_20_roi_class = 'good' if last_20['roi'] > 0 else ('text-red' if last_20['roi'] < 0 else '')
        
        last_50_wr_class = 'good' if last_50['win_rate'] >= 55 else ('text-red' if last_50['win_rate'] < 50 else '')
        last_50_profit_class = 'good' if last_50['profit'] > 0 else ('text-red' if last_50['profit'] < 0 else '')
        last_50_roi_class = 'good' if last_50['roi'] > 0 else ('text-red' if last_50['roi'] < 0 else '')
        
        tracking_html = f'''
        <!-- PERFORMANCE STATS (Last 10/20/50) -->
        <div class="tracking-section">
            <div class="tracking-header">🔥 Recent Form</div>
            
            <div class="metrics-row" style="margin-bottom: 1.5rem;">
                <!-- Last 10 -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 10</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div>
                            <div class="metric-label">Record</div>
                            <div class="metric-value">{last_10['record']}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {last_10_wr_class}">{last_10['win_rate']:.0f}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {last_10_profit_class}">{last_10['profit']:+.1f}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {last_10_roi_class}">{last_10['roi']:+.1f}%</div>
                        </div>
                    </div>
                </div>

                <!-- Last 20 -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 20</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div>
                            <div class="metric-label">Record</div>
                            <div class="metric-value">{last_20['record']}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {last_20_wr_class}">{last_20['win_rate']:.0f}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {last_20_profit_class}">{last_20['profit']:+.1f}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {last_20_roi_class}">{last_20['roi']:+.1f}%</div>
                        </div>
                    </div>
                </div>

                <!-- Last 50 -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 50</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div>
                            <div class="metric-label">Record</div>
                            <div class="metric-value">{last_50['record']}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {last_50_wr_class}">{last_50['win_rate']:.0f}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {last_50_profit_class}">{last_50['profit']:+.1f}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {last_50_roi_class}">{last_50['roi']:+.1f}%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-blue: #60a5fa;
            --border-color: #333333;
        }}

        body {{
            margin: 0;
            padding: 20px;
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            -webkit-font-smoothing: antialiased;
        }}

        .container {{ max-width: 800px; margin: 0 auto; }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
        }}
        h1 {{ margin: 0; font-size: 24px; font-weight: 700; margin-bottom: 5px; }}
        .subheader {{ font-size: 18px; font-weight: 600; color: var(--text-primary); margin-bottom: 5px; }}
        .date-sub {{ color: var(--text-secondary); font-size: 14px; margin-top: 5px; }}

        /* Summary Stats */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            background-color: var(--bg-card);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            border: 1px solid var(--border-color);
        }}
        .stat-label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 5px; }}
        .stat-value {{ font-size: 20px; font-weight: 700; }}

        .section-title {{
            font-size: 18px;
            margin-bottom: 15px;
            display: flex; align-items: center;
        }}
        .section-title span.highlight {{ color: var(--accent-green); margin-left: 8px; font-size: 14px; }}

        /* Prop Card */
        .prop-card {{
            background-color: var(--bg-card);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
        }}

        .card-header {{
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: var(--bg-card-secondary);
            border-bottom: 1px solid var(--border-color);
        }}

        .header-left {{ display: flex; align-items: center; gap: 12px; }}
        .team-logo {{ width: 45px; height: 45px; border-radius: 50%; padding: 2px; object-fit: contain; }}
        .player-info h2 {{ margin: 0; font-size: 18px; line-height: 1.2; }}
        .matchup-info {{ color: var(--text-secondary); font-size: 13px; margin-top: 2px; }}
        .game-meta {{ text-align: right; }}
        .game-date-time {{ font-size: 12px; color: var(--text-secondary); background: #333; padding: 6px 10px; border-radius: 6px; font-weight: 500; white-space: nowrap; }}

        .card-body {{ padding: 20px; }}
        .bet-main-row {{ margin-bottom: 15px; }}
        .bet-selection {{ font-size: 22px; font-weight: 800; }}
        .bet-selection .line {{ color: var(--text-primary); }}
        .bet-odds {{ font-size: 18px; color: var(--text-secondary); font-weight: 500; margin-left: 8px; }}

        .model-subtext {{ color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid var(--border-color); }}
        .model-subtext strong {{ color: var(--text-primary); }}

        .metrics-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }}
        .metric-item {{ background-color: var(--bg-main); padding: 10px; border-radius: 8px; text-align: center; }}
        .metric-lbl {{ display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }}
        .metric-val {{ font-size: 16px; font-weight: 700; }}

        .player-stats {{ background-color: var(--bg-card-secondary); border-radius: 8px; padding: 12px 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border-color); }}
        .player-stats-label {{ font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }}
        .player-stats-value {{ font-size: 16px; font-weight: 700; }}
        .player-stats-item {{ text-align: center; flex: 1; }}
        .player-stats-divider {{ width: 1px; height: 30px; background-color: var(--border-color); }}

        .tags-container {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .tag {{ font-size: 12px; padding: 6px 10px; border-radius: 6px; font-weight: 500; }}

        .txt-green {{ color: var(--accent-green); }}
        .txt-red {{ color: var(--accent-red); }}
        
        .tag-green {{ background-color: rgba(74, 222, 128, 0.15); color: var(--accent-green); }}
        .tag-red {{ background-color: rgba(248, 113, 113, 0.15); color: var(--accent-red); }}
        .tag-blue {{ background-color: rgba(96, 165, 250, 0.15); color: var(--accent-blue); }}
        
        .metric-label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
        }}
        .text-red {{ color: var(--accent-red); }}
        .tracking-section {{ margin-top: 3rem; }}
        .tracking-header {{ 
            font-size: 1.5rem; 
            font-weight: 700; 
            color: var(--text-primary); 
            margin-bottom: 1.5rem; 
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }}
        .metrics-row {{
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
        }}
        .metric-title {{
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
        }}
        .metric-value {{
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--text-primary);
        }}
        .metric-value.good {{ color: var(--accent-green); }}

        @media (max-width: 600px) {{
            .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .stat-box:last-child {{ grid-column: span 2; }}
            .card-header {{ padding: 12px 15px; }}
            .team-logo {{ width: 38px; height: 38px; }}
            .player-info h2 {{ font-size: 16px; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">NBA Assists Model</div>
            <div class="date-sub">Profitable Version • Season {CURRENT_SEASON}</div>
        </div>
        <div style="text-align: right;">
            <div class="metric-title">SEASON RECORD</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                {stats['wins']}-{stats['losses']} ({stats['win_rate']:.1f}%)
            </div>
            <div style="font-size: 0.9rem; color: {'var(--accent-green)' if stats['total_profit'] > 0 else 'var(--accent-red)'};">
                 {stats['total_profit']:+.1f}u
            </div>
        </div>
    </header>'''

    full_html = html_header
    full_html += summary_html
    if over_html: full_html += over_html
    if under_html: full_html += under_html
    full_html += daily_tracking_html
    full_html += tracking_html
    full_html += performance_html
    full_html += "</div></body></html>"

    return full_html


def save_html(html_content: str) -> bool:
    try:
        with open(OUTPUT_HTML, "w") as f:
            f.write(html_content)
        print(f"\n{Colors.GREEN}✓ HTML report saved: {OUTPUT_HTML}{Colors.END}")
        return True
    except Exception as e:
        print(f"\n{Colors.RED}✗ Error saving HTML: {e}{Colors.END}")
        return False


# =============================================================================
# Main
# =============================================================================

def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}NBA ASSISTS PROPS A.I. MODEL{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

    # Grade pending picks first (before generating new ones)
    grade_pending_picks()
    
    # CRITICAL: Backfill profit_loss for any graded picks missing it (fixes ROI calculation)
    backfill_profit_loss()

    player_stats = get_nba_player_assists_stats()
    assists_factors = get_opponent_assists_factors()
    props_list = get_player_props()

    over_plays, under_plays = analyze_props(props_list, player_stats, assists_factors)

    # Track new picks
    track_new_picks(over_plays, under_plays)
    
    # Calculate tracking stats for HTML display
    tracking_data = load_tracking_data()
    stats = calculate_tracking_stats(tracking_data)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}TOP OVER PLAYS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")

    for i, play in enumerate(over_plays[:10], 1):
        ai_rating = play.get("ai_rating", 2.3)
        rating_stars = "⭐" * (int(ai_rating) - 2) if ai_rating >= 3.0 else ""
        print(
            f"  {Colors.CYAN}{i:2d}. {play['player']:25s}{Colors.END} | "
            f"{Colors.GREEN}{play['prop']:15s}{Colors.END} | "
            f"{play.get('team',''):25s} vs {play.get('opponent',''):25s} | "
            f"{Colors.BOLD}A.I.: {play['ai_score']:.2f}{Colors.END} | "
            f"Rating: {ai_rating:.1f} {rating_stars}"
        )

    print(f"\n{Colors.BOLD}{Colors.RED}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.RED}TOP UNDER PLAYS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.RED}{'='*80}{Colors.END}")

    for i, play in enumerate(under_plays[:10], 1):
        ai_rating = play.get("ai_rating", 2.3)
        rating_stars = "⭐" * (int(ai_rating) - 2) if ai_rating >= 3.0 else ""
        print(
            f"  {Colors.CYAN}{i:2d}. {play['player']:25s}{Colors.END} | "
            f"{Colors.RED}{play['prop']:15s}{Colors.END} | "
            f"{play.get('team',''):25s} vs {play.get('opponent',''):25s} | "
            f"{Colors.BOLD}A.I.: {play['ai_score']:.2f}{Colors.END} | "
            f"Rating: {ai_rating:.1f} {rating_stars}"
        )

    print(f"\n{Colors.CYAN}Generating HTML report...{Colors.END}")
    html_content = generate_html_output(over_plays, under_plays, stats, tracking_data, assists_factors, player_stats)
    save_html(html_content)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}✓ Model execution complete!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}\n")


if __name__ == "__main__":
    main()
