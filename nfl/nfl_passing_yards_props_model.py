#!/usr/bin/env python3
"""
NFL Passing Yards Props Model - SHARP +EV VERSION
Analyzes player passing yards props using advanced stats and strictly positive EV logic.
Focuses on volume (attempts), efficiency, and matchup edges.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
import pytz
import requests
from dotenv import load_dotenv

# Import grader for automated tracking
from props_grader import grade_props_tracking_file

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('ODDS_API_KEY')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "nfl_passing_yards_props.html")
PLAYER_STATS_CACHE = os.path.join(SCRIPT_DIR, "nfl_player_passing_yards_stats_cache.json")
TRACKING_FILE = os.path.join(SCRIPT_DIR, "nfl_passing_yards_props_tracking.json")

# Model Parameters - SHARP +EV (Passing yards => larger numbers)
MIN_EDGE_OVER = 15.0    # Must project 15+ yards OVER the line
MIN_EDGE_UNDER = 20.0   # Must project 20+ yards UNDER the line
MIN_CONSISTENCY = 0.5   # Player must be somewhat consistent
MIN_AI_SCORE = 7.0      # 0-10 Scale
UNIT_SIZE = 100         # $100 units for ROI calc
CURRENT_SEASON = "2024" # Adjust as needed

# ANSI Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

# =============================================================================
# TRACKING SYSTEM
# =============================================================================

def load_tracking_data():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'picks': []}
    return {'picks': []}

def save_tracking_data(data):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def track_new_picks(recommendations, odds_data):
    """Track new picks that aren't already pending/completed"""
    data = load_tracking_data()
    existing_ids = set(p['pick_id'] for p in data['picks'])
    
    new_picks_count = 0
    
    current_time = datetime.now(pytz.timezone('US/Eastern')).isoformat()
    
    for rec in recommendations:
        # Unique ID: Player_PropLine_Type_Date
        # Ensure we have a date
        commence_time = rec.get('commence_time', '')
        game_date = commence_time[:10] if commence_time else datetime.now().strftime('%Y-%m-%d')
        
        pick_id = f"{rec['player']}_{rec['line']}_{rec['type']}_{game_date}"
        
        if pick_id not in existing_ids:
            new_pick = {
                'pick_id': pick_id,
                'player': rec['player'],
                'pick_type': 'Passing Yards',
                'bet_type': rec['type'].lower(), # 'over'/'under'
                'line': rec['line'],
                'prop_line': rec['line'], # Grader expects this
                'odds': rec['odds'],
                'opening_odds': rec['odds'],
                'bookmaker': rec.get('bookmaker', 'N/A'),
                'edge': rec['edge'],
                'ai_score': rec['ai_score'],
                'team': rec['team'],
                'opponent': rec.get('opponent', 'UNK'),
                'matchup': rec.get('matchup', ''),
                'game_date': commence_time,
                'game_time': commence_time, # Grader expects this
                'date_placed': current_time,
                'status': 'pending',
                'result': None,
                'profit_loss': 0,
                'actual_val': None,
                'bet_size_units': 1.0
            }
            data['picks'].append(new_pick)
            new_picks_count += 1
            existing_ids.add(pick_id)
        else:
            # Update existing pick if needed (e.g. check for duplicate analysis runs)
            pass
            
    if new_picks_count > 0:
        save_tracking_data(data)
        print(f"{Colors.GREEN}✓ Tracked {new_picks_count} new picks{Colors.END}")
    else:
        print(f"{Colors.CYAN}No new picks to track{Colors.END}")

def backfill_profit_loss():
    """Backfill profit_loss for graded picks that are missing it"""
    tracking_data = load_tracking_data()
    updated_count = 0
    
    for pick in tracking_data['picks']:
        if pick.get('status') in ['win', 'loss'] and 'profit_loss' not in pick:
            odds = pick.get('opening_odds') or pick.get('odds', -110)
            if pick.get('status') == 'win':
                if odds > 0:
                    profit_loss = int(odds)
                else:
                    profit_loss = int((100.0 / abs(odds)) * 100)
            else: # loss
                profit_loss = -100
            
            pick['profit_loss'] = profit_loss
            updated_count += 1
            
    if updated_count > 0:
        save_tracking_data(tracking_data)
        print(f"{Colors.GREEN}✓ Backfilled profit_loss for {updated_count} picks{Colors.END}")

def calculate_tracking_stats(data):
    picks = data.get('picks', [])
    completed = [p for p in picks if p['status'] in ['win', 'loss']] # Exclude pushes
    
    wins = sum(1 for p in completed if p['status'] == 'win')
    losses = sum(1 for p in completed if p['status'] == 'loss')
    
    total_profit_cents = 0
    for p in completed:
        val = p.get('profit_loss')
        if val is None:
            # Fallback calculation
            odds = p.get('opening_odds') or p.get('odds', -110)
            if p.get('status') == 'win':
                if odds > 0: total_profit_cents += int(odds)
                else: total_profit_cents += int((100.0 / abs(odds)) * 100)
            else:
                total_profit_cents -= 100
        else:
            if val is not None: total_profit_cents += val
        
    # CLV Calc
    clv_wins = 0
    clv_total = 0
    
    for p in completed:
        opening = p.get('opening_odds', 0)
        closing = p.get('closing_odds', p.get('latest_odds', 0))
        
        if opening != 0 and closing != 0:
            clv_total += 1
            # Better payout = CLV Win
            # For negative odds, higher is better (e.g. -110 > -150)
            # For positive odds, higher is better (e.1. +150 > +110)
            # Actually simple numeric comparison works for both?
            # -110 > -150 (True)
            # +150 > +110 (True)
            # +110 > -110 (True)
            if opening > closing:
                clv_wins += 1
        
    total_profit_units = total_profit_cents / 100.0
    roi_pct = (total_profit_units / len(completed) * 100) if completed else 0.0
    win_rate = (wins / len(completed) * 100) if completed else 0.0
    clv_rate = (clv_wins / clv_total * 100) if clv_total > 0 else 0.0
    
    # --- Daily Stats ---
    from datetime import datetime, timedelta
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    today_str = now_et.strftime('%Y-%m-%d')
    yesterday_str = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def calc_daily(target_date):
        d_picks = []
        for p in completed:
            gt = p.get('game_time', '')
            if not gt: continue
            try:
                dt_utc = datetime.fromisoformat(gt.replace('Z', '+00:00'))
                dt_et = dt_utc.astimezone(et_tz)
                if dt_et.strftime('%Y-%m-%d') == target_date:
                    d_picks.append(p)
            except:
                continue
        
        d_wins = sum(1 for p in d_picks if p.get('status') == 'win')
        d_losses = sum(1 for p in d_picks if p.get('status') == 'loss')
        d_profit_cents = 0
        for p in d_picks:
            val = p.get('profit_loss')
            if val is not None: d_profit_cents += val
            else:
                odds = p.get('opening_odds') or p.get('odds', -110)
                if p.get('status') == 'win':
                    if odds > 0: d_profit_cents += int(odds)
                    else: d_profit_cents += int((100.0 / abs(odds)) * 100)
                else: d_profit_cents -= 100
        
        d_profit = d_profit_cents / 100.0
        d_roi = (d_profit / len(d_picks) * 100) if d_picks else 0.0
        return {'record': f"{d_wins}-{d_losses}", 'profit': d_profit, 'roi': d_roi}
    
    return {
        'wins': wins, 'losses': len(completed) - wins, 'total': len(completed),
        'win_rate': round(win_rate, 1),
        'profit': round(total_profit_units, 2),
        'roi': round(roi_pct, 1),
        'clv_rate': round(clv_rate, 1),
        'today': calc_daily(today_str),
        'yesterday': calc_daily(yesterday_str)
    }

def calculate_recent_performance(picks_list, count):
    """Calculate performance stats for last N picks (most recent first)"""
    completed = [p for p in picks_list if p.get('status', '').lower() in ['win', 'loss']]
    # Sort reverse chronological if not already (assuming list passed in is sorted)
    # The caller usually sorts, but let's be safe if we rely on input order
    # Here we assume updated 'completed' list is sorted most recent first.
    
    recent = completed[:count] if len(completed) >= count else completed
    
    wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
    total = wins + losses
    
    profit_cents = sum(p.get('profit_loss', 0) for p in recent if p.get('profit_loss') is not None)
    profit_units = profit_cents / 100.0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    # Approx ROI
    roi = (profit_units / total * 100) if total > 0 else 0
    
    return {
        'record': f"{wins}-{losses}",
        'win_rate': win_rate,
        'profit': profit_units,
        'roi': roi,
        'count': len(recent)
    }

# =============================================================================
# DATA FETCHING
# =============================================================================

def load_player_stats():
    """Load cached player stats"""
    if os.path.exists(PLAYER_STATS_CACHE):
        with open(PLAYER_STATS_CACHE, 'r') as f:
            return json.load(f)
    print(f"{Colors.YELLOW}⚠ No player stats cache found at {PLAYER_STATS_CACHE}{Colors.END}")
    print(f"  Run 'python3 fetch_nfl_player_stats.py' first.")
    return {}

def get_nfl_props_odds():
    """Fetch NFL Player Props from Odds API"""
    if not API_KEY:
        print(f"{Colors.RED}✗ No API Key found{Colors.END}")
        return []
        
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events"
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'h2h', 
        'oddsFormat': 'american'
    }
    
    try:
        # 1. Get Events (Games)
        r = requests.get(url, params=params)
        r.raise_for_status()
        r.raise_for_status()
        raw_events = r.json()

        # Filter past games
        events = []
        current_time_utc = datetime.now(pytz.utc)
        for event in raw_events:
            try:
                ct = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
                if ct > current_time_utc:
                    events.append(event)
            except: 
                continue
                
        print(f"  Found {len(events)} upcoming games (filtered from {len(raw_events)})")
        
        all_props = []
        
        print(f"{Colors.CYAN}Found {len(events)} upcoming games. Fetching passing props...{Colors.END}")
        
        # 2. For each even, get passing props
        for event in events:
            game_id = event['id']
            home_team = event['home_team']
            away_team = event['away_team']
            commence_time = event['commence_time']
            
            props_url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/{game_id}/odds"
            props_params = {
                'apiKey': API_KEY,
                'regions': 'us',
                'markets': 'player_pass_yds',
                'oddsFormat': 'american'
            }
            
            pr = requests.get(props_url, params=props_params)
            
            if pr.status_code != 200:
                print(f"  Game {game_id}: Failed {pr.status_code} - {pr.text}")
                
            if pr.status_code == 200:
                game_odds = pr.json()
                b_count = len(game_odds.get('bookmakers', []))
                if b_count > 0:
                    print(f"  Game {game_id}: Found {b_count} bookmakers")
                else:
                    print(f"  Game {game_id}: 0 bookmakers found")
                
                for bookmaker in game_odds.get('bookmakers', []):
                    # Prefer major books
                    bk_key = bookmaker['key']
                    
                    for market in bookmaker.get('markets', []):
                        if market['key'] == 'player_pass_yds':
                            for outcome in market['outcomes']:
                                p_name = outcome['description']
                                # Determine opponent
                                # If we can't perfectly map player to team here without roster, we guess?
                                # Actually, just store home/away options, we'll refine in analysis if needed.
                                # For now, assume if not listed in 'stats' we skip.
                                # But we need to know player's team to know opponent.
                                # We'll fill opponent in 'analyze_props'
                                
                                all_props.append({
                                    'player': p_name,
                                    'team': 'UNK', # Will resolve later
                                    'opponent': 'UNK', # Will resolve later
                                    'home_team': home_team,
                                    'away_team': away_team,
                                    'game_id': game_id,
                                    'matchup': f"{away_team} @ {home_team}",
                                    'commence_time': commence_time,
                                    'line': outcome.get('point'),
                                    'type': 'OVER',  # Analysis determines logic
                                    'side': outcome['name'], # Over/Under 
                                    'price': outcome.get('price'),
                                    'bookmaker': bk_key
                                })
                                
        return all_props
        
    except Exception as e:
        print(f"{Colors.RED}Error fetching odds: {e}{Colors.END}")
        return []

# =============================================================================
# ANALYSIS LOGIC
# =============================================================================

def analyze_props(props, stats_cache):
    recommendations = []
    
    # Group by player
    player_props = {}
    for p in props:
        name = p['player']
        if name not in player_props:
            player_props[name] = []
        player_props[name].append(p)
        
    print(f"\nAnalyzing {len(player_props)} players...")
    
    for player_name, entries in player_props.items():
        stats = stats_cache.get(player_name)
        if not stats:
            continue
            
        # Extract stats
        season_avg = stats.get('season_pass_yds_avg', 0)
        recent_avg = stats.get('recent_pass_yds_avg', 0)
        consistency = stats.get('consistency_score', 0)
        team = stats.get('team', 'UNK')
        
        # Determine opponent info from the prop entry + team
        # If player team is home_team, opp is away_team, etc.
        # stats['team'] usually is abbreviation like 'KC'
        # prop['home_team'] is full name 'Kansas City Chiefs'
        
        # Calculate Projected Yards
        projected = (season_avg * 0.4) + (recent_avg * 0.6)
        
        for entry in entries:
            side = entry.get('side') 
            line = entry.get('line')
            price = entry.get('price')
            
            # Resolve opponent
            home = entry['home_team']
            away = entry['away_team']
            # Simple heuristic
            opponent = 'UNK'
            if team in home or home in team: opponent = away
            elif team in away or away in team: opponent = home
            else: opponent = "Opponent" # Fallback
            
            if not side or not line:
                continue
                
            edge = 0
            ai_score = 0
            is_play = False
            
            if side == 'Over':
                edge = projected - line
                if edge >= MIN_EDGE_OVER:
                    # Positive check
                    if consistency >= MIN_CONSISTENCY:
                        ai_score = (edge / 15.0) * 5.0 + (consistency * 5.0)
                        if ai_score >= MIN_AI_SCORE:
                            is_play = True
            elif side == 'Under':
                edge = line - projected
                if edge >= MIN_EDGE_UNDER:
                    if consistency >= MIN_CONSISTENCY:
                        ai_score = (edge / 15.0) * 5.0 + (consistency * 5.0)
                        if ai_score >= MIN_AI_SCORE:
                            is_play = True
            
            if is_play:
                rec = {
                    'player': player_name,
                    'team': team,
                    'opponent': opponent,
                    'home_team': home,
                    'away_team': away,
                    'matchup': entry['matchup'],
                    'commence_time': entry['commence_time'],
                    'type': side.upper(),
                    'line': line,
                    'odds': price,
                    'model_proj': round(projected, 1),
                    'edge': round(edge, 1),
                    'ai_score': round(min(10.0, ai_score), 1),
                    'bookmaker': entry['bookmaker'],
                    'stats': stats,
                    'season_avg': season_avg,
                    'recent_avg': recent_avg
                }
                recommendations.append(rec)
                
    # Deduplicate: Keep highest AI score per player
    best_plays = {}
    for r in recommendations:
        p = r['player']
        if p not in best_plays or r['ai_score'] > best_plays[p]['ai_score']:
            best_plays[p] = r
            
    return list(best_plays.values())

# =============================================================================
# HTML GENERATION (Matching NBA Rebounds Style)
# =============================================================================

def get_team_abbreviation(team_name):
    """Map full team names to valid ESPN logo abbreviations."""
    """Map full team names & abbrs to valid ESPN logo abbreviations."""
    # Common NFL Map
    m = {
        'Arizona Cardinals': 'ari', 'ARI': 'ari',
        'Atlanta Falcons': 'atl', 'ATL': 'atl',
        'Baltimore Ravens': 'bal', 'BAL': 'bal',
        'Buffalo Bills': 'buf', 'BUF': 'buf',
        'Carolina Panthers': 'car', 'CAR': 'car', 
        'Chicago Bears': 'chi', 'CHI': 'chi',
        'Cincinnati Bengals': 'cin', 'CIN': 'cin',
        'Cleveland Browns': 'cle', 'CLE': 'cle',
        'Dallas Cowboys': 'dal', 'DAL': 'dal',
        'Denver Broncos': 'den', 'DEN': 'den',
        'Detroit Lions': 'det', 'DET': 'det',
        'Green Bay Packers': 'gb', 'GB': 'gb',
        'Houston Texans': 'hou', 'HOU': 'hou',
        'Indianapolis Colts': 'ind', 'IND': 'ind',
        'Jacksonville Jaguars': 'jax', 'JAX': 'jax', 'JAC': 'jax',
        'Kansas City Chiefs': 'kc', 'KC': 'kc',
        'Las Vegas Raiders': 'lv', 'LV': 'lv',
        'Los Angeles Chargers': 'lac', 'LAC': 'lac',
        'Los Angeles Rams': 'lar', 'LAR': 'lar', 'LA': 'lar',
        'Miami Dolphins': 'mia', 'MIA': 'mia',
        'Minnesota Vikings': 'min', 'MIN': 'min',
        'New England Patriots': 'ne', 'NE': 'ne',
        'New Orleans Saints': 'no', 'NO': 'no',
        'New York Giants': 'nyg', 'NYG': 'nyg',
        'New York Jets': 'nyj', 'NYJ': 'nyj',
        'Philadelphia Eagles': 'phi', 'PHI': 'phi',
        'Pittsburgh Steelers': 'pit', 'PIT': 'pit',
        'San Francisco 49ers': 'sf', 'SF': 'sf',
        'Seattle Seahawks': 'sea', 'SEA': 'sea',
        'Tampa Bay Buccaneers': 'tb', 'TB': 'tb',
        'Tennessee Titans': 'ten', 'TEN': 'ten',
        'Washington Commanders': 'was', 'WAS': 'was', 'WSH': 'was'
    }
    return m.get(team_name, 'nfl').lower()

def format_game_datetime(game_time_str):
    try:
        if not game_time_str: return 'TBD'
        dt_obj = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        et_tz = pytz.timezone('US/Eastern')
        dt_et = dt_obj.astimezone(et_tz)
        return dt_et.strftime('%a, %b %d • %-I:%M %p ET')
    except:
        return game_time_str

def calculate_player_stats(player_name, tracking_data):
    """ROI stats for specific player"""
    if not tracking_data: return None
    player_picks = [p for p in tracking_data['picks'] 
                   if p.get('player') == player_name and p.get('status') in ['win', 'loss']]
    if not player_picks: return None
    
    wins = sum(1 for p in player_picks if p['status'] == 'win')
    losses = sum(1 for p in player_picks if p['status'] == 'loss')
    
    total_profit_cents = 0
    for p in player_picks:
        total_profit_cents += p.get('profit_loss', 0)
        
    roi = (total_profit_cents/100.0) / len(player_picks) * 100
    
    return {
        'season_record': f"{wins}-{losses}",
        'player_roi': round(roi, 1)
    }

def generate_reasoning_tags(play):
    tags = []
    
    # Recent Form
    recent = play.get('recent_avg', 0)
    season = play.get('season_avg', 0)
    
    if recent > season + 20:
        tags.append({"text": f"Avg {recent:.1f} L5 Games (Hot)", "color": "green"})
    elif recent < season - 20:
        tags.append({"text": f"Avg {recent:.1f} L5 Games (Cold)", "color": "red"})
        
    # Edge
    edge = play.get('edge', 0)
    if abs(edge) >= 25:
        txt = f"Massive Edge {edge:+.1f}"
        tags.append({"text": txt, "color": "green" if edge > 0 else "red"})
    elif abs(edge) >= 15:
        txt = f"Strong Edge {edge:+.1f}"
        tags.append({"text": txt, "color": "green" if edge > 0 else "blue"})
        
    return tags

def generate_html_output(plays, stats, tracking_data):
    # Sort plays by AI Score
    plays.sort(key=lambda x: x['ai_score'], reverse=True)
    
    # Separate Over/Under
    over_plays = [p for p in plays if p['type'] == 'OVER']
    under_plays = [p for p in plays if p['type'] == 'UNDER']
    
    # Recent Tracking Stats
    completed_picks = [p for p in tracking_data['picks'] if p.get('status') in ['win', 'loss']]
    completed_picks.sort(key=lambda x: x.get('game_time', ''), reverse=True)
    
    last_10 = calculate_recent_performance(completed_picks, 10)
    last_20 = calculate_recent_performance(completed_picks, 20)
    last_50 = calculate_recent_performance(completed_picks, 50)
    
    # -------------------------------------------------------------------------
    # HTML TEMPLATES (Ported from NBA Rebounds Model)
    # -------------------------------------------------------------------------
    
    html_header = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics - NFL Passing</title>
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
        body {{ margin: 0; padding: 20px; font-family: 'Inter', sans-serif; background-color: var(--bg-main); color: var(--text-primary); -webkit-font-smoothing: antialiased; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        
        /* HEADER */
        header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; }}
        h1 {{ margin: 0; font-size: 24px; font-weight: 700; margin-bottom: 5px; }}
        .subheader {{ font-size: 18px; font-weight: 600; color: var(--text-primary); margin-bottom: 5px; }}
        .date-sub {{ color: var(--text-secondary); font-size: 14px; margin-top: 5px; }}
        .header-stats {{ text-align: right; }}
        
        /* SUMMARY GRID */
        .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 30px; }}
        .stat-box {{ background-color: var(--bg-card); border-radius: 12px; padding: 15px; text-align: center; border: 1px solid var(--border-color); }}
        .stat-label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 5px; }}
        .stat-value {{ font-size: 20px; font-weight: 700; }}
        
        /* CARDS */
        .section-title {{ font-size: 18px; margin-bottom: 15px; display: flex; align-items: center; }}
        .section-title span.highlight {{ color: var(--accent-green); margin-left: 8px; font-size: 14px; }}
        
        .prop-card {{ background-color: var(--bg-card); border-radius: 16px; overflow: hidden; margin-bottom: 20px; border: 1px solid var(--border-color); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); }}
        .card-header {{ padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-card-secondary); border-bottom: 1px solid var(--border-color); }}
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
        .tag-green {{ background-color: rgba(74, 222, 128, 0.15); color: var(--accent-green); }}
        .tag-red {{ background-color: rgba(248, 113, 113, 0.15); color: var(--accent-red); }}
        .tag-blue {{ background-color: rgba(96, 165, 250, 0.15); color: var(--accent-blue); }}
        
        .txt-green {{ color: var(--accent-green); }}
        .txt-red {{ color: var(--accent-red); }}
        
        /* TRACKING SECTION */
        .metric-value.good {{ color: var(--accent-green); }}
        
        @media (max-width: 600px) {{
            .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .stat-box:last-child {{ grid-column: span 2; }}
            .card-header {{ padding: 12px 15px; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">NFL Passing Props</div>
            <div class="date-sub">Sharp +EV Model • Season {CURRENT_SEASON}</div>
        </div>
        <div class="header-stats">
            <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 4px; font-weight: 600;">SEASON RECORD</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                {stats['wins']}-{stats['losses']} ({stats['win_rate']}%)
            </div>
            <div style="font-size: 0.9rem; color: {'var(--accent-green)' if stats['profit'] > 0 else 'var(--accent-red)'};">
                 {stats['profit']:+.2f}u
            </div>
            <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 4px;">CLV: {stats.get('clv_rate', 0)}%</div>
        </div>
    </header>
"""
    
    # Helper to generate play cards
    def generate_cards(play_list, is_over):
        c_html = ""
        type_class = "txt-green" if is_over else "txt-red"
        
        for play in play_list:
            # Use player team first, verify it's not UNK
            team_key = play.get('team', 'UNK')
            if team_key == 'UNK': team_key = play['home_team']
            
            team_abbr = get_team_abbreviation(team_key)
            logo_url = f"https://a.espncdn.com/i/teamlogos/nfl/500/{team_abbr}.png"
            
            p_stats = calculate_player_stats(play['player'], tracking_data)
            p_stats_html = ""
            if p_stats:
                roi_sign = '+' if p_stats['player_roi'] > 0 else ''
                p_stats_html = f'''
                <div class="player-stats">
                    <div class="player-stats-item">
                        <div class="player-stats-label">This Season</div>
                        <div class="player-stats-value">{p_stats['season_record']}</div>
                    </div>
                    <div class="player-stats-divider"></div>
                    <div class="player-stats-item">
                        <div class="player-stats-label">Player ROI</div>
                        <div class="player-stats-value txt-green">{roi_sign}{p_stats['player_roi']:.1f}%</div>
                    </div>
                </div>'''
            
            tags = generate_reasoning_tags(play)
            tags_html = "".join([f'<span class="tag tag-{tag["color"]}">{tag["text"]}</span>' for tag in tags])
            
            c_html += f'''
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                    <img src="{logo_url}" alt="Logo" class="team-logo">
                    <div class="player-info">
                        <h2>{play['player']}</h2>
                        <div class="matchup-info">{play['matchup']}</div>
                    </div>
                </div>
                <div class="game-meta">
                    <div class="game-date-time">{format_game_datetime(play['commence_time'])}</div>
                </div>
            </div>
            <div class="card-body">
                <div class="bet-main-row">
                    <div class="bet-selection">
                        <span class="{type_class}">{play['type']}</span> 
                        <span class="line">{play['line']} YDS</span> 
                        <span class="bet-odds">{(str(play['odds']))}</span>
                    </div>
                </div>
                <div class="model-subtext">
                    Model Predicts: <strong>{play['model_proj']} YDS</strong> (Edge: {play['edge']:+.1f})
                </div>
                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="metric-lbl">AI SCORE</span>
                        <span class="metric-val txt-green">{play['ai_score']}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">SEASON AVG</span>
                        <span class="metric-val">{play['season_avg']}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">RECENT AVG</span>
                        <span class="metric-val">{play['recent_avg']}</span>
                    </div>
                </div>
                {p_stats_html}
                <div class="tags-container">
                    {tags_html}
                </div>
            </div>
        </div>'''
        return c_html

    over_html = generate_cards(over_plays, True)
    under_html = generate_cards(under_plays, False)
    
    # Tracking Section
    def get_track_class(val): return 'good' if val > 0 else 'txt-red'
    
    # --- Daily Performance Tracking HTML ---
    daily_tracking_html = ""
    if stats and 'today' in stats:
        t_stats = stats['today']
        y_stats = stats.get('yesterday', {'record':'0-0', 'profit':0, 'roi':0})
        
        daily_tracking_html = f"""
        <section style="margin-top: 2rem;">
            <div class="section-title">📅 Daily Performance</div>
            <div class="metrics-grid" style="grid-template-columns: repeat(2, 1fr);">
                <!-- Today -->
                <div class="prop-card" style="padding: 1rem; margin:0;">
                    <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">TODAY</div>
                    <div style="text-align:center;">
                        <div style="font-weight:700; font-size:1.1rem;">{t_stats['record']}</div>
                        <div class="{get_track_class(t_stats['profit'])}">{t_stats['profit']:+.1f}u</div>
                        <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">{t_stats['roi']:.1f}% ROI</div>
                    </div>
                </div>
                <!-- Yesterday -->
                <div class="prop-card" style="padding: 1rem; margin:0;">
                    <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">YESTERDAY</div>
                    <div style="text-align:center;">
                        <div style="font-weight:700; font-size:1.1rem;">{y_stats['record']}</div>
                        <div class="{get_track_class(y_stats['profit'])}">{y_stats['profit']:+.1f}u</div>
                         <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">{y_stats['roi']:.1f}% ROI</div>
                    </div>
                </div>
            </div>
        </section>
        """

    tracking_html = f'''
    <section style="margin-top: 3rem;">
        <div class="section-title">🔥 Recent Form</div>
        <div class="metrics-grid" style="grid-template-columns: repeat(3, 1fr);">
            <!-- Last 10 -->
            <div class="prop-card" style="padding: 1rem; margin:0;">
                <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">LAST 10</div>
                <div style="text-align:center;">
                    <div style="font-weight:700;">{last_10['record']}</div>
                    <div class="{get_track_class(last_10['profit'])}">{last_10['profit']:+.1f}u</div>
                </div>
            </div>
            <!-- Last 20 -->
            <div class="prop-card" style="padding: 1rem; margin:0;">
                <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">LAST 20</div>
                <div style="text-align:center;">
                    <div style="font-weight:700;">{last_20['record']}</div>
                    <div class="{get_track_class(last_20['profit'])}">{last_20['profit']:+.1f}u</div>
                </div>
            </div>
            <!-- Last 50 -->
            <div class="prop-card" style="padding: 1rem; margin:0;">
                <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">LAST 50</div>
                <div style="text-align:center;">
                    <div style="font-weight:700;">{last_50['record']}</div>
                    <div class="{get_track_class(last_50['profit'])}">{last_50['profit']:+.1f}u</div>
                </div>
            </div>
        </div>
    </section>
    '''
    
    full_html = html_header
    if over_html: full_html += f'<section><div class="section-title">Top OVERS <span class="highlight">Min Edge {MIN_EDGE_OVER}</span></div>{over_html}</section>'
    if under_html: full_html += f'<section><div class="section-title">Top UNDERS <span class="highlight">Min Edge {MIN_EDGE_UNDER}</span></div>{under_html}</section>'
    full_html += daily_tracking_html
    full_html += tracking_html
    full_html += "</div></body></html>"
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(full_html)
    print(f"\n✅ HTML saved: {OUTPUT_HTML}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"{Colors.BOLD}🏈 NFL Passing Props Model - Sharp +EV{Colors.END}")
    
    # 1. Grade pending picks
    print(f"\n{Colors.CYAN}--- Grading Pending Picks ---{Colors.END}")
    try:
        updated = grade_props_tracking_file(TRACKING_FILE, stat_kind='passing_yards')
        print(f"Graded {updated} picks.")
    except Exception as e:
        print(f"{Colors.YELLOW}Grading failed: {e}{Colors.END}")
        
    backfill_profit_loss()
    
    stats = load_player_stats()
    if not stats: return
    
    odds = get_nfl_props_odds()
    plays = []
    
    if odds:
        plays = analyze_props(odds, stats)
        print(f"\nFound {len(plays)} sharp plays:")
        for p in plays:
            print(f"  ⭐ {p['player']} {p['type']} {p['line']} (Proj: {p['model_proj']}) | Edge: {p['edge']} | AI: {p['ai_score']}")
        track_new_picks(plays, odds)
    else:
        print(f"No odds found. Generating HTML with tracking data only.")
    
    # Calc stats for dashboard
    t_data = load_tracking_data()
    ts = calculate_tracking_stats(t_data)
    
    # Gen HTML
    generate_html_output(plays, ts, t_data)

if __name__ == "__main__":
    main()
