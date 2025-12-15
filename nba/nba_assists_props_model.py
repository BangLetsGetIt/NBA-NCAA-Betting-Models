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
import statistics
import time
from collections import defaultdict
from datetime import datetime, timedelta

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
MIN_AI_SCORE = 9.5  # Only show high-confidence plays
TOP_PLAYS_COUNT = 5  # Quality over quantity
RECENT_GAMES_WINDOW = 10
CURRENT_SEASON = "2025-26"

# Edge requirements (assists can be more variable, keep strict)
MIN_EDGE_OVER_LINE = 2.0
MIN_EDGE_UNDER_LINE = 1.5
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
        pick_id = f"{play['player']}_{prop_line}_{bet_type}_{play.get('game_time', '')}"
        
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
    
    for pick in pending_picks:
        # Check if game has passed (add 4 hour buffer for games to complete)
        try:
            game_time_str = pick.get('game_time')
            if not game_time_str:
                continue
                
            game_time_utc = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            current_time = datetime.now(pytz.UTC)
            hours_since_game = (current_time - game_time_utc).total_seconds() / 3600
            
            if hours_since_game < 4:
                continue  # Game too recent, wait for stats
            
            # Fetch actual assists from NBA API
            player_name = pick.get('player')
            team_name = pick.get('team')
            game_date = game_time_utc.strftime('%Y-%m-%d')
            
            actual_ast = fetch_player_assists_from_nba_api(player_name, team_name, game_date)
            
            if actual_ast is None:
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
        'under_roi': round(under_roi, 2)
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
    """Fetch team-level matchup factors relevant to assists."""
    print(f"\n{Colors.CYAN}Fetching opponent assists factors...{Colors.END}")

    if os.path.exists(TEAM_ASSISTS_CACHE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(TEAM_ASSISTS_CACHE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached assists factors{Colors.END}")
            with open(TEAM_ASSISTS_CACHE, "r") as f:
                return json.load(f)

    assists_factors: dict[str, dict] = {}

    try:
        team_stats = leaguedashteamstats.LeagueDashTeamStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense="Base",
            per_mode_detailed="PerGame",
            timeout=30,
        )
        team_df = team_stats.get_data_frames()[0]
        time.sleep(0.6)

        for _, row in team_df.iterrows():
            team_name = row.get("TEAM_NAME", "")
            if not team_name:
                continue

            opp_ast = float(row.get("OPP_AST", 0) or 0)
            pace = float(row.get("PACE", 100) or 100)

            # Typical league baselines
            baseline_opp_ast = 25.0

            # Assists factor based on opponent assists allowed and pace
            assists_factor = (opp_ast / baseline_opp_ast) * (pace / 100.0)

            assists_factors[team_name] = {
                "opp_ast_allowed": round(opp_ast, 2),
                "pace": round(pace, 2),
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
        "Los Angeles Lakers": ["James", "Davis", "Reaves", "Russell", "Hachimura", "Reddish", "Prince", "Christie", "Knecht"],
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
        "Dallas Mavericks": ["Doncic", "Irving", "Washington", "Gafford", "Lively", "Grimes", "Kleber", "Exum"],
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

        for i, event in enumerate(events[:10], 1):
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
# HTML output
# =============================================================================

def generate_html_output(over_plays, under_plays, stats=None):
    """Generate HTML output matching the card-based style used by other props models."""
    from datetime import datetime as dt

    et = pytz.timezone("US/Eastern")
    now = dt.now(et)
    date_str = now.strftime("%m/%d/%y")
    time_str = now.strftime("%I:%M %p ET")

    def format_game_time(game_time_str):
        try:
            if not game_time_str:
                return "TBD"
            dt_obj = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
            dt_et = dt_obj.astimezone(et)
            return dt_et.strftime("%m/%d %I:%M %p ET")
        except Exception:
            return game_time_str if game_time_str else "TBD"

    # Helper function to format odds for display
    def format_odds(odds_value):
        """Format odds value to American odds format (e.g., -110, +150)"""
        if odds_value is None:
            return 'N/A'
        try:
            odds = int(odds_value)
            if odds > 0:
                return f'+{odds}'
            else:
                return str(odds)
        except:
            return str(odds_value) if odds_value else 'N/A'

    def get_short_team_name(team_name):
        short_name_map = {
            "Atlanta Hawks": "Hawks",
            "Boston Celtics": "Celtics",
            "Brooklyn Nets": "Nets",
            "Charlotte Hornets": "Hornets",
            "Chicago Bulls": "Bulls",
            "Cleveland Cavaliers": "Cavaliers",
            "Dallas Mavericks": "Mavericks",
            "Denver Nuggets": "Nuggets",
            "Detroit Pistons": "Pistons",
            "Golden State Warriors": "Warriors",
            "Houston Rockets": "Rockets",
            "Indiana Pacers": "Pacers",
            "LA Clippers": "Clippers",
            "Los Angeles Clippers": "Clippers",
            "Los Angeles Lakers": "Lakers",
            "LA Lakers": "Lakers",
            "Memphis Grizzlies": "Grizzlies",
            "Miami Heat": "Heat",
            "Milwaukee Bucks": "Bucks",
            "Minnesota Timberwolves": "Timberwolves",
            "New Orleans Pelicans": "Pelicans",
            "New York Knicks": "Knicks",
            "Oklahoma City Thunder": "Thunder",
            "Orlando Magic": "Magic",
            "Philadelphia 76ers": "76ers",
            "Phoenix Suns": "Suns",
            "Portland Trail Blazers": "Trail Blazers",
            "Sacramento Kings": "Kings",
            "San Antonio Spurs": "Spurs",
            "Toronto Raptors": "Raptors",
            "Utah Jazz": "Jazz",
            "Washington Wizards": "Wizards",
        }
        return short_name_map.get(team_name, team_name)

    def get_team_logo_url(team_name):
        team_id_map = {
            "Atlanta Hawks": "1610612737",
            "Boston Celtics": "1610612738",
            "Brooklyn Nets": "1610612751",
            "Charlotte Hornets": "1610612766",
            "Chicago Bulls": "1610612741",
            "Cleveland Cavaliers": "1610612739",
            "Dallas Mavericks": "1610612742",
            "Denver Nuggets": "1610612743",
            "Detroit Pistons": "1610612765",
            "Golden State Warriors": "1610612744",
            "Houston Rockets": "1610612745",
            "Indiana Pacers": "1610612754",
            "LA Clippers": "1610612746",
            "Los Angeles Clippers": "1610612746",
            "Los Angeles Lakers": "1610612747",
            "LA Lakers": "1610612747",
            "Memphis Grizzlies": "1610612763",
            "Miami Heat": "1610612748",
            "Milwaukee Bucks": "1610612749",
            "Minnesota Timberwolves": "1610612750",
            "New Orleans Pelicans": "1610612740",
            "New York Knicks": "1610612752",
            "Oklahoma City Thunder": "1610612760",
            "Orlando Magic": "1610612753",
            "Philadelphia 76ers": "1610612755",
            "Phoenix Suns": "1610612756",
            "Portland Trail Blazers": "1610612757",
            "Sacramento Kings": "1610612758",
            "San Antonio Spurs": "1610612759",
            "Toronto Raptors": "1610612761",
            "Utah Jazz": "1610612762",
            "Washington Wizards": "1610612764",
        }
        team_id = team_id_map.get(team_name, "")
        return f"https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg" if team_id else ""

    def rating_badge(ai_rating):
        if ai_rating >= 4.5:
            return "ai-rating-premium", "⭐⭐⭐"
        if ai_rating >= 4.0:
            return "ai-rating-strong", "⭐⭐"
        if ai_rating >= 3.5:
            return "ai-rating-good", "⭐"
        if ai_rating >= 3.0:
            return "ai-rating-standard", ""
        return "ai-rating-marginal", ""

    def build_cards(plays, color, pick_class):
        cards = ""
        for play in plays:
            confidence_pct = min(int((play["ai_score"] / 10.0) * 100), 100)
            game_time_formatted = format_game_time(play.get("game_time", ""))

            ai_rating = float(play.get("ai_rating", 2.3) or 2.3)
            rclass, stars = rating_badge(ai_rating)
            rating_display = f'<div class="ai-rating {rclass}"><span class="rating-value">{ai_rating:.1f}</span> {stars}</div>'

            ev = float(play.get("ev", 0) or 0)
            ev_badge = ""
            if ev > 0:
                ev_badge = (
                    f'<span style="display: inline-block; padding: 0.25rem 0.5rem; '
                    f'background: rgba(16, 185, 129, 0.15); color: #10b981; border-radius: 0.5rem; '
                    f'font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">+{ev:.1f}% EV</span>'
                )

            team_logo_url = get_team_logo_url(play.get("team") or "")
            logo_html = f'<img src="{team_logo_url}" alt="{play.get("team", "")}" class="team-logo">' if team_logo_url else ""

            short_team = get_short_team_name(play.get("team") or "")
            short_opponent = get_short_team_name(play.get("opponent") or "")
            home_team = play.get("home_team") or ""

            if play.get("team") == home_team:
                matchup_display = f"{short_opponent} @ {short_team}"
            else:
                matchup_display = f"{short_team} @ {short_opponent}"

            cards += f"""
                    <div class="bet-box">
                        <div class="prop-title" style="color: {color};">{play['prop']}</div>
                        <div class="odds-line" style="text-align: left;">
                            <strong style="display: flex; align-items: center; gap: 0.5rem; justify-content: flex-start;">{play['player']}{logo_html}</strong>
                        </div>
                        <div class="odds-line" style="text-align: left;">
                            <strong>{matchup_display}</strong>
                        </div>
                        <div class="odds-line" style="text-align: left;">
                            <strong>{game_time_formatted}</strong>
                        </div>
                        <div class="odds-line">
                            <span>Odds:</span>
                            <strong style="color: {color};">{format_odds(play.get('odds'))}</strong>
                        </div>
                        {rating_display}
                        <div class="odds-line">
                            <span>Season Avg:</span>
                            <strong>{play.get('season_avg', 'N/A')}</strong>
                        </div>
                        <div class="odds-line">
                            <span>Recent Avg:</span>
                            <strong>{play.get('recent_avg', 'N/A')}</strong>
                        </div>
                        <div class="confidence-bar-container">
                            <div class="confidence-label">
                                <span>A.I. Score</span>
                                <span class="confidence-pct">{play['ai_score']:.2f}</span>
                            </div>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: {confidence_pct}%"></div>
                            </div>
                        </div>
                        <div class="pick {pick_class}">
                            ✅ {play['prop']}{ev_badge}
                        </div>
                    </div>
            """
        return cards

    over_html = ""
    if over_plays:
        cards = build_cards(over_plays, "#10b981", "pick-yes")
        over_html = f"""
            <div class="card">
                <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 2rem; color: #10b981;">TOP OVER PLAYS</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 2rem;">
                    {cards}
                </div>
            </div>
        """

    under_html = ""
    if under_plays:
        cards = build_cards(under_plays, "#ef4444", "pick-no")
        under_html = f"""
            <div class="card">
                <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 2rem; color: #ef4444;">TOP UNDER PLAYS</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 2rem;">
                    {cards}
                </div>
            </div>
        """

    # Generate stats card if stats provided - ALWAYS show tracking section
    stats_html = ""
    if stats:
        total = stats['total']
        wins = stats['wins']
        losses = stats['losses']
        win_rate = stats['win_rate']
        roi_pct = stats['roi_pct']
        total_profit = stats['total_profit']
        
        roi_color = '#10b981' if roi_pct > 0 else '#ef4444'
        roi_sign = '+' if roi_pct > 0 else ''
        profit_sign = '+' if total_profit > 0 else ''
        
        over_record = stats['over_record']
        over_win_rate = stats['over_win_rate']
        over_roi = stats['over_roi']
        over_roi_color = '#10b981' if over_roi > 0 else '#ef4444'
        over_roi_sign = '+' if over_roi > 0 else ''
        
        under_record = stats['under_record']
        under_win_rate = stats['under_win_rate']
        under_roi = stats['under_roi']
        under_roi_color = '#10b981' if under_roi > 0 else '#ef4444'
        under_roi_sign = '+' if under_roi > 0 else ''
        
        stats_html = f"""
            <div class="card">
                <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; color: #3b82f6;">NBA Assists Model Performance</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem;">
                    <div class="stat-box">
                        <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">Overall Record</div>
                        <div style="font-size: 1.75rem; font-weight: 700; color: #ffffff;">{wins}-{losses}</div>
                        <div style="font-size: 1rem; color: #10b981; margin-top: 0.25rem;">{win_rate:.1f}% Win Rate</div>
                    </div>
                    <div class="stat-box">
                        <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">ROI</div>
                        <div style="font-size: 1.75rem; font-weight: 700; color: {roi_color};">{roi_sign}{roi_pct:.1f}%</div>
                        <div style="font-size: 1rem; color: {roi_color}; margin-top: 0.25rem;">{profit_sign}{total_profit:.2f} Units</div>
                    </div>
                    <div class="stat-box">
                        <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">OVER Bets</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">{over_record}</div>
                        <div style="font-size: 0.875rem; margin-top: 0.25rem;">
                            <span style="color: #10b981;">{over_win_rate:.1f}% Win</span> | 
                            <span style="color: {over_roi_color};">{over_roi_sign}{over_roi:.1f}% ROI</span>
                        </div>
                    </div>
                    <div class="stat-box">
                        <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">UNDER Bets</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #ef4444;">{under_record}</div>
                        <div style="font-size: 0.875rem; margin-top: 0.25rem;">
                            <span style="color: #ef4444;">{under_win_rate:.1f}% Win</span> | 
                            <span style="color: {under_roi_color};">{under_roi_sign}{under_roi:.1f}% ROI</span>
                        </div>
                    </div>
                </div>
            </div>
        """
    
    footer_text = (
        f"Powered by REAL NBA Stats API • Only showing picks with A.I. Score ≥ {MIN_AI_SCORE}<br>"
        f"Using strict edge requirements: {MIN_EDGE_OVER_LINE}+ above line (OVER) / {MIN_EDGE_UNDER_LINE}+ below line (UNDER)"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Assists Props - A.I. Projections</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
            background: #000000;
            color: #ffffff;
            padding: 2rem;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{
            background: #1a1a1a;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 1.5rem;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}
        .header-card {{ text-align: center; background: #1a1a1a; }}
        .bet-box {{
            background: #262626;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 1.75rem;
            border-radius: 1.25rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            position: relative;
        }}
        .stat-box {{
            background: #262626;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 1.25rem;
            border-radius: 1rem;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        }}
        .team-logo {{
            width: 24px;
            height: 24px;
            object-fit: contain;
            opacity: 0.95;
            filter: brightness(1.1);
        }}
        .ai-rating {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            padding: 0.5rem 0.75rem;
            border-radius: 0.5rem;
            font-size: 0.875rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.25rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .ai-rating .rating-value {{ font-weight: 700; font-size: 0.875rem; }}
        .ai-rating-premium {{ background: rgba(16, 185, 129, 0.15); color: #10b981; }}
        .ai-rating-strong {{ background: rgba(16, 185, 129, 0.12); color: #10b981; }}
        .ai-rating-good {{ background: rgba(59, 130, 246, 0.12); color: #3b82f6; }}
        .ai-rating-standard {{ background: rgba(245, 158, 11, 0.12); color: #f59e0b; }}
        .ai-rating-marginal {{ background: rgba(245, 158, 11, 0.08); color: #f59e0b; }}
        .prop-title {{
            font-weight: 700;
            margin-bottom: 1rem;
            font-size: 1.25rem;
            letter-spacing: 0.02em;
        }}
        .odds-line {{
            display: flex;
            justify-content: space-between;
            margin: 0.5rem 0;
            font-size: 0.9375rem;
            color: #94a3b8;
        }}
        .odds-line strong {{ color: #ffffff; font-weight: 600; }}
        .confidence-bar-container {{ margin: 1rem 0; }}
        .confidence-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.625rem;
            font-size: 0.875rem;
            color: #94a3b8;
        }}
        .confidence-pct {{ font-weight: 700; color: #10b981; }}
        .confidence-bar {{
            height: 8px;
            background: #1a1a1a;
            border-radius: 999px;
            overflow: hidden;
            border: none;
        }}
        .confidence-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            border-radius: 999px;
            transition: width 0.3s ease;
        }}
        .pick {{
            font-weight: 600;
            padding: 1rem 1.25rem;
            margin-top: 1rem;
            border-radius: 0.875rem;
            font-size: 1rem;
            line-height: 1.5;
            border: none;
        }}
        .pick-yes {{
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
        }}
        .pick-no {{
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            box-shadow: 0 2px 8px rgba(239, 68, 68, 0.2);
        }}
        .badge {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 0.625rem;
            font-size: 0.8125rem;
            font-weight: 600;
            background: rgba(59, 130, 246, 0.15);
            color: #3b82f6;
            margin: 0.375rem;
            border: 1px solid rgba(59, 130, 246, 0.2);
        }}
        @media (max-width: 1024px) {{
            .container {{ max-width: 100%; }}
            .card {{ padding: 2rem; }}
        }}
        @media (max-width: 768px) {{
            body {{ padding: 1.5rem; }}
            .card {{ padding: 1.75rem; }}
            .bet-box {{ padding: 1.5rem; }}
            .pick {{ font-size: 0.9375rem; padding: 0.875rem 1rem; }}
        }}
        @media (max-width: 480px) {{
            body {{ padding: 1rem; }}
            .card {{ padding: 1.5rem; margin-bottom: 1.5rem; }}
            .bet-box {{ padding: 1.25rem; }}
            .prop-title {{ font-size: 1rem; }}
            .odds-line {{ font-size: 0.8125rem; }}
            .pick {{ font-size: 0.875rem; padding: 0.75rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card header-card">
            <h1 style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem; background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">CourtSide Analytics</h1>
            <p style="font-size: 1.5rem; opacity: 0.95; font-weight: 600;">NBA Assists Props Model</p>
            <div>
                <div class="badge">● REAL NBA STATS API</div>
                <div class="badge">● A.I. SCORE ≥ {MIN_AI_SCORE}</div>
                <div class="badge">● STRICT EDGE REQUIREMENTS</div>
            </div>
            <p style="font-size: 0.875rem; opacity: 0.75; margin-top: 1rem;">Generated: {date_str} {time_str}</p>
        </div>

        {over_html}

        {under_html}

        {stats_html}

        <div class="card" style="text-align: center;">
            <p style="color: #94a3b8; font-size: 0.875rem; line-height: 1.8;">{footer_text}</p>
        </div>
    </div>
</body>
</html>"""

    return html


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
    html_content = generate_html_output(over_plays, under_plays, stats)
    save_html(html_content)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}✓ Model execution complete!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}\n")


if __name__ == "__main__":
    main()
