import csv
import json
import os
import re
import traceback
import shutil
from datetime import datetime, timedelta
from jinja2 import Template
import requests
from dotenv import load_dotenv
import pytz
import pandas as pd
from collections import defaultdict

# =========================
# CONFIG
# =========================

load_dotenv()
API_KEY = os.getenv("ODDS_API_KEY")
if not API_KEY:
    print("FATAL: ODDS_API_KEY not found in .env file.")
    print("Get your free API key at: https://the-odds-api.com/")
    exit()

BASE_URL = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/odds/"
PARAMS = {
    "apiKey": API_KEY,
    "regions": "us,us2",
    "markets": "h2h,spreads,totals",
    "oddsFormat": "american",
    "dateFormat": "iso"
}

# --- File & Model Config ---
# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Use absolute paths to ensure files are created in the correct location
CSV_FILE = os.path.join(SCRIPT_DIR, "ncaab_model_output.csv")
HTML_FILE = os.path.join(SCRIPT_DIR, "ncaab_model_output.html")
STATS_FILE = os.path.join(SCRIPT_DIR, "ncaab_stats_cache.json")
KENPOM_CACHE_FILE = os.path.join(SCRIPT_DIR, "ncaab_kenpom_cache.json")

# Tracking files
PICKS_TRACKING_FILE = os.path.join(SCRIPT_DIR, "ncaab_picks_tracking.json")
TRACKING_HTML_FILE = os.path.join(SCRIPT_DIR, "ncaab_tracking_dashboard.html")

# --- Model Parameters (ALIGNED WITH PROFITABLE NBA MODEL) ---
# CHANGES MADE TO IMPROVE PROFITABILITY:
# 1. Lowered thresholds to match NBA model (3.0 spread, 4.0 total)
# 2. Removed MAX edge caps (were cutting off potentially good plays)
# 3. Adjusted season/form weights to 70/30 (was 60/40)
# 4. Increased recent games window to 10 (was 8) for better sample size
# 
# NBA Model Performance: 97-64 (60.2% win rate) with these settings
# Previous NCAAB: 778-699 (52.6% win rate) - too conservative

HOME_COURT_ADVANTAGE = 3.2  # College home court advantage
SPREAD_THRESHOLD = 2.0  # Lowered from 5.0 - match NBA model (display threshold)
TOTAL_THRESHOLD = 3.0   # Lowered from 6.0 - match NBA model (display threshold)

# Tracking Parameters (ALIGNED WITH NBA MODEL FOR PROFITABILITY)
# NBA model: 3.0 spread, 4.0 total = 60.2% win rate
# Strategy: Trust the model's edge calculation, don't artificially cap edges
CONFIDENT_SPREAD_EDGE = 3.0  # Lowered from 5.5 - match NBA model success
CONFIDENT_TOTAL_EDGE = 4.0   # Lowered from 7.0 - match NBA model success
# REMOVED MAX edge caps - NBA model doesn't cap and performs better
# If model calculates a large edge, trust it (may indicate real value)
UNIT_SIZE = 100  # Standard bet size in dollars

# Date filtering
DAYS_AHEAD_TO_FETCH = 2  # Only fetch games within next 2 days

# --- Parameters for Team Form/Momentum (ALIGNED WITH NBA MODEL) ---
LAST_N_GAMES = 10      # Increased from 8 - match NBA model (better sample size)
SEASON_WEIGHT = 0.70   # Increased from 0.60 - match NBA model (more trust in season stats)
FORM_WEIGHT = 0.30     # Decreased from 0.40 - match NBA model (less reactive to noise)

# --- Parameters for Home/Away Splits ---
USE_HOME_AWAY_SPLITS = True  
SPLITS_WEIGHT = 0.55        # Home court matters more in college
COMPOSITE_WEIGHT = 0.45      

# --- College-Specific Parameters ---
PACE_ADJUSTMENT_WEIGHT = 0.15  # Factor in tempo differences
CONFERENCE_STRENGTH_WEIGHT = 0.10  # Factor in conference quality
EXPERIENCE_WEIGHT = 0.05  # Senior-heavy teams get boost

# Conference strength tiers (based on historical performance)
CONFERENCE_TIERS = {
    # Tier 1: Elite conferences
    "Big Ten": 1.0,
    "SEC": 1.0,
    "Big 12": 1.0,
    "ACC": 0.95,
    "Big East": 0.95,
    
    # Tier 2: Strong conferences
    "Pac-12": 0.85,
    "Mountain West": 0.80,
    "West Coast": 0.80,
    "American": 0.75,
    "Atlantic 10": 0.75,
    
    # Tier 3: Mid-major conferences
    "Missouri Valley": 0.70,
    "Conference USA": 0.65,
    "Sun Belt": 0.65,
    "MAC": 0.60,
    "WAC": 0.60,
    
    # Tier 4: Lower conferences
    "Default": 0.50  # For conferences not listed
}

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    PURPLE = '\033[35m'
    ORANGE = '\033[38;5;208m'

# =========================
# TRACKING FUNCTIONS
# =========================

def normalize_team_name(team_name):
    """Normalize team names for consistent matching across APIs"""
    name = str(team_name).strip()

    # Remove mascot/nickname suffixes (e.g., "Baylor Bears" -> "Baylor")
    # Common mascots to remove
    mascots = [
        ' Bears', ' Bulldogs', ' Tigers', ' Eagles', ' Wildcats', ' Huskies',
        ' Cardinals', ' Spartans', ' Wolverines', ' Tar Heels', ' Blue Devils',
        ' Jayhawks', ' Longhorns', ' Sooners', ' Volunteers', ' Crimson Tide',
        ' Gators', ' Hoosiers', ' Buckeyes', ' Hawkeyes', ' Nittany Lions',
        ' Badgers', ' Golden Gophers', ' Terrapins', ' Scarlet Knights',
        ' Fighting Irish', ' Seminoles', ' Hurricanes', ' Orange', ' Yellow Jackets',
        ' Demon Deacons', ' Pirates', ' Wolfpack', ' Gamecocks', ' Razorbacks',
        ' Aggies', ' Red Raiders', ' Mountaineers', ' Cyclones', ' Horned Frogs',
        ' Bruins', ' Trojans', ' Sun Devils', ' Utes', ' Cougars', ' Ducks',
        ' Beavers', ' Huskies', ' Golden Bears', ' Cardinal', ' Warriors',
        ' Gaels', ' Bulldogs', ' Broncos', ' Rebels', ' Runnin Rebels',
        ' Rainbow Warriors', ' Aztecs', ' Lobos', ' Cowboys', ' Red Storm',
        ' Hoyas', ' Musketeers', ' Friars', ' Pirates', ' Seton Hall Pirates',
        ' Golden Eagles', ' Blue Jays', ' Shockers', ' Billikens', ' Explorers',
        ' Minutemen', ' Rams', ' Spiders', ' Colonials', ' Revolutionaries',
        ' Dukes', ' Dragons', ' Bearcats', ' Golden Hurricane', ' Knights',
        ' Black Knights', ' Midshipmen', ' Falcons', ' Owls', ' Flames',
        ' Lions', ' Leopards', ' Raiders', ' Chanticleers', ' Penguins',
        ' Great Danes', ' Statesmen', ' Engineers', ' Retrievers', ' Seahawks',
        ' Seawolves', ' Bison', ' Thundering Herd', ' Golden Lions', ' Colonels',
        ' Panthers', ' Golden Panthers'
    ]

    for mascot in mascots:
        if name.endswith(mascot):
            name = name[:-len(mascot)].strip()
            break

    # Common abbreviations and variations
    name_map = {
        # State abbreviations
        "Norfolk St": "Norfolk State",
        "UNC Asheville": "UNC Asheville",
        "Miami (OH)": "Miami (OH)",
        "Miami (FL)": "Miami (FL)",
        "UConn": "Connecticut",
        "UCF": "UCF",
        "UNLV": "UNLV",
        "USC": "USC",
        "UCLA": "UCLA",
        "LSU": "LSU",
        "TCU": "TCU",
        "SMU": "SMU",
        "BYU": "BYU",
        "VCU": "VCU",
        "UTEP": "UTEP",
        "UTSA": "UTSA",
        "UNC": "North Carolina",
        "GW": "George Washington",
        "CSU Northridge": "Cal State Northridge",
        "NC State": "North Carolina State",
        "San Diego St": "San Diego State",
        "Arkansas-Pine Bluff": "Arkansas-Pine Bluff",
        "San Diego State": "San Diego State",
    }

    # Check direct mapping
    if name in name_map:
        return name_map[name]

    return name

def load_picks_tracking():
    """Load existing picks tracking data"""
    if os.path.exists(PICKS_TRACKING_FILE):
        try:
            with open(PICKS_TRACKING_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"{Colors.RED}Error reading tracking file! Creating a new one.{Colors.END}")
            return {"picks": [], "summary": {}}
    return {
        "picks": [],
        "summary": {
            "total_picks": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "pending": 0
        }
    }

def get_team_historical_performance():
    """Calculate historical win rates for all teams"""
    tracking_data = load_picks_tracking()
    team_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'profit': 0})

    for pick in tracking_data.get('picks', []):
        status = pick.get('status', '')
        if status not in ['win', 'loss']:
            continue

        home_team = normalize_team_name(pick.get('home_team', ''))
        away_team = normalize_team_name(pick.get('away_team', ''))
        pick_text = pick.get('pick_text', '').upper()
        profit = pick.get('profit', 0)

        # Determine which team we bet on
        bet_team = None
        if 'BET:' in pick_text:
            if home_team.upper() in pick_text:
                bet_team = home_team
            elif away_team.upper() in pick_text:
                bet_team = away_team

        if not bet_team:
            continue

        if status == 'win':
            team_stats[bet_team]['wins'] += 1
        elif status == 'loss':
            team_stats[bet_team]['losses'] += 1

        team_stats[bet_team]['profit'] += profit if profit else 0

    # Calculate win rates
    team_performance = {}
    for team, stats in team_stats.items():
        total = stats['wins'] + stats['losses']
        if total >= 1:  # Show performance for any team with historical data
            win_rate = (stats['wins'] / total * 100) if total > 0 else 0
            team_performance[team] = {
                'record': f"{stats['wins']}-{stats['losses']}",
                'win_rate': win_rate,
                'total_picks': total,
                'profit': stats['profit'] / 100
            }

    return team_performance

def get_team_performance_indicator(team_name, team_performance):
    """Get performance indicator for a team - now shows data for ALL teams with history"""
    normalized_name = normalize_team_name(team_name)

    if normalized_name not in team_performance:
        return None

    perf = team_performance[normalized_name]
    win_rate = perf['win_rate']
    record = perf['record']
    profit = perf['profit']
    total = perf['total_picks']

    # Special handling for limited data (1-2 picks)
    if total <= 2:
        return {
            'emoji': 'ℹ️',
            'label': 'LIMITED',
            'color': Colors.CYAN,
            'message': f"{team_name} - Limited data: {record} ({win_rate:.0f}%) | {profit:+.2f}u ({total} pick{'s' if total > 1 else ''})"
        }

    # Hot performers (66.7%+)
    if win_rate >= 66.7:
        return {
            'emoji': '🔥',
            'label': 'HOT',
            'color': Colors.GREEN,
            'message': f"{team_name} - Strong performer: {record} ({win_rate:.0f}%) | +{profit:.2f}u over {total} picks"
        }
    # Good performers (60-66.6%)
    elif win_rate >= 60.0:
        return {
            'emoji': '✅',
            'label': 'GOOD',
            'color': Colors.GREEN,
            'message': f"{team_name} - Good record: {record} ({win_rate:.0f}%) | +{profit:.2f}u over {total} picks"
        }
    # Neutral-positive (52-59.9%)
    elif win_rate >= 52.0:
        return {
            'emoji': '📊',
            'label': 'NEUTRAL+',
            'color': Colors.CYAN,
            'message': f"{team_name} - Slightly above average: {record} ({win_rate:.0f}%) | {profit:+.2f}u over {total} picks"
        }
    # Neutral range (48-51.9%)
    elif win_rate >= 48.0:
        return {
            'emoji': '➖',
            'label': 'NEUTRAL',
            'color': Colors.END,
            'message': f"{team_name} - Average performance: {record} ({win_rate:.0f}%) | {profit:+.2f}u over {total} picks"
        }
    # Neutral-negative (40.1-47.9%)
    elif win_rate > 40.0:
        return {
            'emoji': '📉',
            'label': 'NEUTRAL-',
            'color': Colors.YELLOW,
            'message': f"{team_name} - Slightly below average: {record} ({win_rate:.0f}%) | {profit:+.2f}u over {total} picks"
        }
    # Caution zone (33.4-40%)
    elif win_rate > 33.3:
        return {
            'emoji': '⚠️',
            'label': 'CAUTION',
            'color': Colors.YELLOW,
            'message': f"{team_name} - Below average: {record} ({win_rate:.0f}%) | {profit:+.2f}u over {total} picks"
        }
    # Cold performers (≤33.3%)
    else:
        return {
            'emoji': '🚫',
            'label': 'COLD',
            'color': Colors.RED,
            'message': f"{team_name} - Poor performer: {record} ({win_rate:.0f}%) | {profit:+.2f}u over {total} picks"
        }

def save_picks_tracking(tracking_data):
    """Save picks tracking data with automatic backup"""
    if os.path.exists(PICKS_TRACKING_FILE):
        backup_file = f"{PICKS_TRACKING_FILE}.backup"
        shutil.copy2(PICKS_TRACKING_FILE, backup_file)
        # print(f"{Colors.CYAN}✓ Backup created: {backup_file}{Colors.END}") # Optional: can be noisy
    
    with open(PICKS_TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)
    print(f"{Colors.GREEN}✓ Tracking data saved to {PICKS_TRACKING_FILE}{Colors.END}")
    print(f"{Colors.GREEN}  Total picks in file: {len(tracking_data['picks'])}{Colors.END}")

def log_confident_pick(game_data, pick_type, edge, model_line, market_line):
    """Log or update a confident pick in the tracking file"""
    tracking_data = load_picks_tracking()

    # Create unique pick ID
    pick_id = f"{game_data['home_team']}_{game_data['away_team']}_{game_data['commence_time']}_{pick_type}"

    # Determine the actual pick
    if pick_type == 'spread':
        pick_text = game_data.get('ATS Pick', '')
    else:  # total
        pick_text = game_data.get('Total Pick', '')

    if not pick_text or '✅' not in pick_text:
        return  # Not a bet, skip

    # Check if this pick already exists
    existing_pick = next((p for p in tracking_data['picks'] if p['pick_id'] == pick_id), None)

    if existing_pick:
        # Update existing pick with current lines/edge
        existing_pick['model_line'] = model_line
        existing_pick['market_line'] = market_line
        existing_pick['edge'] = edge
        existing_pick['pick_text'] = pick_text
        save_picks_tracking(tracking_data)
        # Silently update without printing
        return

    # Create new pick entry
    pick_entry = {
        "pick_id": pick_id,
        "game_date": game_data['commence_time'],
        "home_team": game_data['home_team'],
        "away_team": game_data['away_team'],
        "pick_type": pick_type,
        "pick_text": pick_text,
        "model_line": model_line,
        "market_line": market_line,
        "edge": edge,
        "status": "pending",
        "result": None,
        "profit": None,
        "logged_at": datetime.now(pytz.timezone('US/Eastern')).isoformat()
    }

    tracking_data['picks'].append(pick_entry)
    tracking_data['summary']['total_picks'] = tracking_data['summary'].get('total_picks', 0) + 1
    tracking_data['summary']['pending'] = tracking_data['summary'].get('pending', 0) + 1

    save_picks_tracking(tracking_data)

    print(f"{Colors.PURPLE}📝 LOGGED: {pick_type.upper()} - {pick_text} (Edge: {edge:+.1f}){Colors.END}")

def fetch_completed_scores():
    """Fetch scores for recently completed games"""
    print(f"{Colors.CYAN}Fetching completed game scores...{Colors.END}")

    try:
        # Fetch scores from The Odds API
        scores_url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/scores/"
        params = {
            "apiKey": API_KEY,
            "daysFrom": 3  # Check last 3 days (API maximum)
        }

        response = requests.get(scores_url, params=params, timeout=10)

        if response.status_code == 200:
            scores = response.json()
            print(f"{Colors.GREEN}✓ Fetched {len(scores)} completed games{Colors.END}")
            return scores
        else:
            print(f"{Colors.YELLOW}⚠️  Could not fetch scores: {response.status_code}{Colors.END}")
            if response.status_code == 422:
                print(f"{Colors.YELLOW}   API Response: {response.text[:200]}{Colors.END}")
                print(f"{Colors.YELLOW}   This may be a temporary API issue. Results will update on next run.{Colors.END}")
            return []

    except Exception as e:
        print(f"{Colors.RED}Error fetching scores: {e}{Colors.END}")
        return []

def clear_stale_picks(days_old=7):
    """Remove or mark picks that are too old to verify (older than API window)"""
    tracking_data = load_picks_tracking()
    et = pytz.timezone('US/Eastern')
    current_time = datetime.now(et)
    cutoff_date = current_time - timedelta(days=days_old)

    stale_count = 0
    for pick in tracking_data['picks']:
        if pick.get('status') != 'pending':
            continue

        try:
            game_dt = datetime.fromisoformat(str(pick.get('game_date', '')).replace('Z', '+00:00'))
            game_dt_et = game_dt.astimezone(et)

            # If game is older than cutoff, remove it
            if game_dt_et < cutoff_date:
                tracking_data['picks'].remove(pick)
                stale_count += 1
                print(f"{Colors.YELLOW}Removed stale pick (too old to verify): {pick['away_team']} @ {pick['home_team']} ({game_dt_et.strftime('%Y-%m-%d')}){Colors.END}")
        except:
            pass

    if stale_count > 0:
        tracking_data['summary'] = calculate_summary_stats(tracking_data['picks'])
        save_picks_tracking(tracking_data)
        print(f"{Colors.GREEN}✓ Removed {stale_count} stale picks{Colors.END}")

    return stale_count

def update_pick_results():
    """Update tracking data with results from completed games"""
    tracking_data = load_picks_tracking()

    if not tracking_data['picks']:
        print(f"{Colors.YELLOW}No picks to update.{Colors.END}")
        return

    # Get pending picks
    pending_picks = [p for p in tracking_data['picks'] if p.get('status') == 'pending']

    if not pending_picks:
        print(f"{Colors.GREEN}No pending picks to update.{Colors.END}")
        return
    
    print(f"{Colors.CYAN}Checking {len(pending_picks)} pending picks...{Colors.END}")
    print(f"{Colors.CYAN}Pending pick date range:{Colors.END}")
    dates = sorted([p.get('game_date', '')[:10] for p in pending_picks])
    if dates:
        print(f"  Oldest: {dates[0]}")
        print(f"  Newest: {dates[-1]}")
    
    # Fetch completed scores
    completed_games = fetch_completed_scores()
    
    if not completed_games:
        print(f"{Colors.YELLOW}No completed games found.{Colors.END}")
        return
    
    print(f"{Colors.CYAN}Found {len(completed_games)} completed games from API{Colors.END}")
    
    updated_count = 0
    matched_games = set()
    
    for pick in pending_picks:
        # Find matching completed game
        matched = False
        for game in completed_games:
            if not game.get('completed'):
                continue
                
            home_team = normalize_team_name(game['home_team'])
            away_team = normalize_team_name(game['away_team'])
            
            pick_home = normalize_team_name(pick['home_team'])
            pick_away = normalize_team_name(pick['away_team'])
            
            if home_team == pick_home and away_team == pick_away:
                # Found the game!
                matched = True
                matched_games.add(f"{away_team} @ {home_team}")
                
                scores = game.get('scores')
                if not scores or len(scores) < 2:
                    print(f"{Colors.RED}⚠️  Found match but missing scores: {away_team} @ {home_team}{Colors.END}")
                    continue
                
                try:
                    home_score_str = next((s['score'] for s in scores if s['name'] == game['home_team']), None)
                    away_score_str = next((s['score'] for s in scores if s['name'] == game['away_team']), None)
                    
                    if home_score_str is None or away_score_str is None:
                        print(f"{Colors.RED}⚠️  Could not parse scores for: {away_team} @ {home_team}{Colors.END}")
                        continue
                        
                    home_score = int(home_score_str)
                    away_score = int(away_score_str)
                
                except (ValueError, TypeError) as e:
                    print(f"{Colors.RED}Error parsing scores for {game['home_team']}: {e}{Colors.END}")
                    continue
                
                # Calculate result based on pick type
                if pick['pick_type'] == 'spread':
                    result = evaluate_spread_pick(pick, home_score, away_score)
                else:  # total
                    result = evaluate_total_pick(pick, home_score, away_score)
                
                # Update pick
                pick['status'] = result['status']
                pick['result'] = result['result']
                pick['profit'] = result['profit']
                pick['actual_score'] = f"{away_team} {away_score}, {home_team} {home_score}"
                
                updated_count += 1
                
                print(f"{Colors.GREEN}✓ Updated: {pick['pick_text']} -> {result['status'].upper()}{Colors.END}")
                
                break
        
        if not matched:
            pick_game_date = pick.get('game_date', '')[:10]
            print(f"{Colors.YELLOW}⚠️  No match found: {pick['away_team']} @ {pick['home_team']} ({pick_game_date}){Colors.END}")
    
    if updated_count > 0:
        # Recalculate summary
        tracking_data['summary'] = calculate_summary_stats(tracking_data['picks'])
        save_picks_tracking(tracking_data)
        print(f"\n{Colors.GREEN}✅ Updated {updated_count} picks{Colors.END}")
        print(f"{Colors.CYAN}Matched games: {len(matched_games)}{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}No picks were updated{Colors.END}")
        print(f"{Colors.YELLOW}This could mean:{Colors.END}")
        print(f"  1. Games haven't completed yet")
        print(f"  2. Team name mismatches between pick and API")
        print(f"  3. Games are outside the daysFrom window")

def evaluate_spread_pick(pick, home_score, away_score):
    """Evaluate if a spread pick won, lost, or pushed"""
    # Determine which team was picked
    pick_text = pick['pick_text'].upper()
    
    # Calculate actual margin
    actual_margin = home_score - away_score
    
    try:
        # Determine picked team and spread
        if pick['home_team'].upper() in pick_text:
            # Picked home team
            picked_home = True
            spread = float(pick['market_line'])
        else:
            # Picked away team
            picked_home = False
            spread = -float(pick['market_line'])
    except (ValueError, TypeError):
        print(f"{Colors.RED}Error parsing market line: {pick['market_line']}{Colors.END}")
        return {"status": "error", "result": "Parse Error", "profit": 0}

    # Calculate covered margin
    if picked_home:
        covered_margin = actual_margin + spread
    else:
        covered_margin = -actual_margin + spread
    
    # Determine result
    if abs(covered_margin) < 0.1:  # Push
        return {
            "status": "push",
            "result": "Push",
            "profit": 0
        }
    elif covered_margin > 0:  # Win
        return {
            "status": "win",
            "result": f"Won by {abs(covered_margin):.1f}",
            "profit": UNIT_SIZE * 0.91  # Standard -110 odds
        }
    else:  # Loss
        return {
            "status": "loss",
            "result": f"Lost by {abs(covered_margin):.1f}",
            "profit": -UNIT_SIZE
        }

def evaluate_total_pick(pick, home_score, away_score):
    """Evaluate if a total pick won, lost, or pushed"""
    pick_text = pick['pick_text'].upper()
    total_score = home_score + away_score
    
    try:
        line = float(pick['market_line'])
    except (ValueError, TypeError):
        print(f"{Colors.RED}Error parsing market line: {pick['market_line']}{Colors.END}")
        return {"status": "error", "result": "Parse Error", "profit": 0}
        
    # Determine if picked over or under
    picked_over = "OVER" in pick_text
    
    # Calculate difference
    difference = total_score - line
    
    # Determine result
    if abs(difference) < 0.1:  # Push
        return {
            "status": "push",
            "result": "Push",
            "profit": 0
        }
    elif (picked_over and difference > 0) or (not picked_over and difference < 0):
        # Win
        return {
            "status": "win",
            "result": f"Won by {abs(difference):.1f}",
            "profit": UNIT_SIZE * 0.91
        }
    else:
        # Loss
        return {
            "status": "loss",
            "result": f"Lost by {abs(difference):.1f}",
            "profit": -UNIT_SIZE
        }

def calculate_summary_stats(picks):
    """Calculate summary statistics from picks"""
    total = len(picks)
    wins = sum(1 for p in picks if p.get('status') == 'win')
    losses = sum(1 for p in picks if p.get('status') == 'loss')
    pushes = sum(1 for p in picks if p.get('status') == 'push')
    pending = sum(1 for p in picks if p.get('status') == 'pending')
    
    return {
        "total_picks": total,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending
    }

def calculate_tracking_stats(tracking_data):
    """Calculate detailed tracking statistics"""
    picks = tracking_data.get('picks', [])
    
    total_picks = len(picks)
    wins = sum(1 for p in picks if p.get('status') == 'win')
    losses = sum(1 for p in picks if p.get('status') == 'loss')
    pushes = sum(1 for p in picks if p.get('status') == 'push')
    pending = sum(1 for p in picks if p.get('status') == 'pending')
    
    # Calculate profit
    total_profit = sum(p.get('profit', 0) for p in picks if p.get('profit') is not None)
    
    # Calculate win rate (excluding pushes and pending)
    decided_picks = wins + losses
    win_rate = (wins / decided_picks * 100) if decided_picks > 0 else 0.0
    
    # Calculate ROI
    total_risked = (wins + losses) * UNIT_SIZE
    roi = (total_profit / total_risked * 100) if total_risked > 0 else 0.0
    
    return {
        "total_picks": total_picks,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending,
        "win_rate": win_rate,
        "total_profit": total_profit,
        "roi": roi
    }

def get_historical_performance_by_edge(tracking_data):
    """Calculate win rates by edge magnitude for A.I. Rating system"""
    picks = tracking_data.get('picks', [])
    completed_picks = [p for p in picks if p.get('status') in ['win', 'loss']]
    
    # Group picks by edge range
    edge_ranges = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for pick in completed_picks:
        edge = abs(float(pick.get('edge', 0)))
        status = pick.get('status', '')
        
        # Create edge range buckets
        if edge >= 10:
            range_key = "10+"
        elif edge >= 8:
            range_key = "8-9.9"
        elif edge >= 6:
            range_key = "6-7.9"
        elif edge >= 4:
            range_key = "4-5.9"
        elif edge >= 3:
            range_key = "3-3.9"
        else:
            range_key = "0-2.9"
        
        if status == 'win':
            edge_ranges[range_key]['wins'] += 1
        elif status == 'loss':
            edge_ranges[range_key]['losses'] += 1
    
    # Calculate win rates
    performance_by_edge = {}
    for range_key, stats in edge_ranges.items():
        total = stats['wins'] + stats['losses']
        if total >= 5:  # Only use ranges with sufficient data
            win_rate = stats['wins'] / total if total > 0 else 0.5
            performance_by_edge[range_key] = win_rate
    
    return performance_by_edge

def calculate_ai_rating(game_data, team_performance, historical_edge_performance):
    """
    Calculate A.I. Rating that supplements edge-based approach
    
    Rating considers:
    1. Normalized edge (0-5 scale)
    2. Data quality indicators
    3. Historical performance on similar games
    4. Model confidence indicators
    5. Team performance indicators
    
    Returns rating in 2.3-4.9 range (matching reference model)
    """
    # 1. BASE: Normalized edge score
    max_edge = max(abs(game_data.get('spread_edge', 0)), abs(game_data.get('total_edge', 0)))
    
    # Normalize edge to 0-5 scale (15 edge = 5.0 rating)
    if max_edge >= 15:
        normalized_edge = 5.0
    else:
        normalized_edge = max_edge / 3.0
        normalized_edge = min(5.0, max(0.0, normalized_edge))
    
    # 2. DATA QUALITY FACTOR (0.85-1.0)
    # Assume high quality if we have predicted scores (stats available)
    has_predicted_score = 'Predicted Score' in game_data and game_data['Predicted Score']
    data_quality = 1.0 if has_predicted_score else 0.85
    
    # 3. HISTORICAL PERFORMANCE FACTOR (0.9-1.1)
    # How has model performed on similar edge ranges?
    historical_factor = 1.0  # Default neutral
    
    if historical_edge_performance:
        # Find appropriate edge range
        if max_edge >= 10:
            range_key = "10+"
        elif max_edge >= 8:
            range_key = "8-9.9"
        elif max_edge >= 6:
            range_key = "6-7.9"
        elif max_edge >= 4:
            range_key = "4-5.9"
        elif max_edge >= 3:
            range_key = "3-3.9"
        else:
            range_key = "0-2.9"
        
        if range_key in historical_edge_performance:
            hist_win_rate = historical_edge_performance[range_key]
            # Convert win rate to multiplier: 60% = 1.0, 55% = 0.95, 65% = 1.05
            historical_factor = 0.9 + (hist_win_rate - 0.55) * 2.0
            historical_factor = max(0.9, min(1.1, historical_factor))
    
    # 4. MODEL CONFIDENCE FACTOR (0.9-1.15)
    # Based on edge magnitude and consistency
    confidence = 1.0
    
    # Larger edges suggest stronger model confidence
    if max_edge >= 12:
        confidence = 1.10  # Very large edges
    elif max_edge >= 8:
        confidence = 1.05  # Large edges
    elif max_edge >= 6:
        confidence = 1.0   # Medium edges
    elif max_edge >= 4:
        confidence = 0.98  # Smaller edges
    else:
        confidence = 0.95  # Small edges
    
    # Boost confidence if both spread and total have edges
    has_spread_bet = '✅' in game_data.get('ATS Pick', '')
    has_total_bet = '✅' in game_data.get('Total Pick', '')
    if has_spread_bet and has_total_bet:
        confidence *= 1.03  # Small boost for multiple edges
    
    confidence = max(0.9, min(1.15, confidence))
    
    # 5. TEAM PERFORMANCE INDICATOR FACTOR (0.9-1.1)
    # Boost rating if betting on historically profitable team
    team_factor = 1.0
    team_indicator = game_data.get('team_indicator')
    if team_indicator:
        label = team_indicator.get('label', '').upper()
        if label in ['HOT', 'GOOD']:
            team_factor = 1.05  # Small boost for proven teams
        elif label in ['NEUTRAL+']:
            team_factor = 1.02  # Tiny boost
        elif label in ['COLD']:
            team_factor = 0.95  # Small penalty for cold teams
    
    # 6. CALCULATE COMPOSITE RATING
    base_rating = normalized_edge
    
    # Apply factors (multiplicative)
    composite_rating = (
        base_rating * 
        data_quality * 
        historical_factor * 
        confidence * 
        team_factor
    )
    
    # 7. SCALE TO 2.3-4.9 RANGE (matching reference model)
    # Maps 0-5 range to 2.3-4.9 range
    ai_rating = 2.3 + (composite_rating / 5.0) * 2.6
    ai_rating = max(2.3, min(4.9, ai_rating))  # Clamp to range
    
    return round(ai_rating, 1)

# =========================
# DATA FETCHING FUNCTIONS
# =========================

def fetch_odds():
    """Fetch current odds from The Odds API"""
    try:
        response = requests.get(BASE_URL, params=PARAMS, timeout=15)
        
        if response.status_code != 200:
            print(f"{Colors.RED}ERROR: The Odds API returned status {response.status_code}{Colors.END}")
            print(f"Response: {response.text}")
            return []
        
        games = response.json()
        print(f"{Colors.GREEN}✓ Fetched {len(games)} games from The Odds API{Colors.END}")
        
        # Filter games by date
        et = pytz.timezone('US/Eastern')
        now = datetime.now(et)
        cutoff = now + timedelta(days=DAYS_AHEAD_TO_FETCH)
        
        filtered_games = []
        for game in games:
            game_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            if now <= game_time <= cutoff:
                filtered_games.append(game)
        
        print(f"{Colors.GREEN}✓ {len(filtered_games)} games in the next {DAYS_AHEAD_TO_FETCH} days{Colors.END}")
        
        return filtered_games
        
    except Exception as e:
        print(f"{Colors.RED}Error fetching odds: {e}{Colors.END}")
        traceback.print_exc()
        return []

def fetch_team_stats():
    """
    Fetch real NCAA basketball team statistics from Sports-Reference
    """
    print(f"{Colors.CYAN}Loading team statistics...{Colors.END}")

    # Check cache first
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                stats = json.load(f)
                cache_time = datetime.fromisoformat(stats.get('cached_at', '2000-01-01'))

                # Use cache if less than 6 hours old
                if datetime.now() - cache_time < timedelta(hours=6):
                    print(f"{Colors.GREEN}✓ Using cached stats (age: {int((datetime.now() - cache_time).total_seconds() / 3600)}h){Colors.END}")
                    return stats.get('teams', {})
        except (json.JSONDecodeError, IOError) as e:
            print(f"{Colors.YELLOW}⚠️  Cache file error: {e}. Re-fetching.{Colors.END}")

    # Fetch fresh stats from Sports-Reference
    print(f"{Colors.CYAN}🔄 Fetching fresh stats from Sports-Reference...{Colors.END}")

    try:
        import subprocess
        result = subprocess.run(
            ['python3', os.path.join(SCRIPT_DIR, 'fetch_ncaab_stats.py')],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ Stats fetch successful{Colors.END}")

            # Load the newly created cache
            with open(STATS_FILE, 'r') as f:
                stats = json.load(f)
                return stats.get('teams', {})
        else:
            print(f"{Colors.RED}✗ Stats fetch failed: {result.stderr}{Colors.END}")
            return {}

    except Exception as e:
        print(f"{Colors.RED}✗ Error fetching stats: {e}{Colors.END}")
        return {}

def save_stats_cache(stats_data):
    """Save team statistics to cache"""
    cache_data = {
        "cached_at": datetime.now().isoformat(),
        "teams": stats_data
    }
    
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        print(f"{Colors.GREEN}✓ Stats cached to {STATS_FILE}{Colors.END}")
    except IOError as e:
        print(f"{Colors.RED}Error saving stats cache: {e}{Colors.END}")


# estimate_team_strength() function removed - now using real stats from Sports-Reference

# =========================
# GAME PROCESSING
# =========================

def extract_best_odds(bookmakers, market_type):
    """Extract best available odds for a given market, prioritizing Hard Rock Bet"""
    best_odds = {}
    
    # Sort bookmakers to put Hard Rock first
    sorted_books = sorted(bookmakers, key=lambda b: 0 if b['key'] == 'hardrockbet' else (1 if b['key'] == 'fanduel' else 2))
    
    for book in sorted_books:
        for market in book.get('markets', []):
            if market['key'] != market_type:
                continue
            
            for outcome in market['outcomes']:
                team = outcome['name']
                
                if market_type == 'h2h':
                    price = outcome['price']
                    if team not in best_odds or price > best_odds[team]:
                        best_odds[team] = price
                
                elif market_type == 'spreads':
                    point = outcome['point']
                    price = outcome['price']
                    # We can add logic to prefer lower vig (e.g., -105 vs -110)
                    if team not in best_odds:
                        best_odds[team] = {'point': point, 'price': price}
                
                elif market_type == 'totals':
                    name = outcome['name']  # 'Over' or 'Under'
                    point = outcome['point']
                    price = outcome['price']
                    if name not in best_odds:
                        best_odds[name] = {'point': point, 'price': price}
    
    return best_odds

def process_games(games, team_stats):
    """Process games and generate predictions"""
    results = []

    # Load historical team performance
    team_performance = get_team_historical_performance()
    
    # Load historical edge performance for A.I. Rating calculation
    tracking_data = load_picks_tracking()
    historical_edge_performance = get_historical_performance_by_edge(tracking_data)

    for game in games:
        try:
            home_team = normalize_team_name(game['home_team'])
            away_team = normalize_team_name(game['away_team'])
            
            # Get team statistics
            # Skip games if we don't have stats for both teams
            home_stats = team_stats.get(home_team)
            away_stats = team_stats.get(away_team)

            if not home_stats or not away_stats:
                # print(f"Skipping {away_team} @ {home_team}: Missing team stats")
                continue
            
            # Extract odds
            spreads = extract_best_odds(game['bookmakers'], 'spreads')
            totals = extract_best_odds(game['bookmakers'], 'totals')
            
            if not spreads or not totals:
                # print(f"Skipping {away_team} @ {home_team}: Missing odds data")
                continue  # Skip if missing odds
            
            # Get market lines
            home_spread = spreads.get(game['home_team'], {}).get('point')
            # away_spread = spreads.get(game['away_team'], {}).get('point') # Redundant if home_spread exists
            
            if home_spread is None:
                # print(f"Skipping {away_team} @ {home_team}: Missing home spread")
                continue
            
            market_spread = home_spread
            market_total = totals.get('Over', {}).get('point')
            
            if market_total is None:
                # print(f"Skipping {away_team} @ {home_team}: Missing total")
                continue
            
            # Calculate predictions
            prediction = predict_game(home_team, away_team, home_stats, away_stats)
            
            model_spread = prediction['spread']
            model_total = prediction['total']
            
            # --- START: CORRECTED SPREAD LOGIC ---
            ats_pick = ""
            ats_explanation = ""
            spread_edge = 0.0 # This will be our display edge

            # This is the "cover margin" for the HOME team.
            # A positive value means the model predicts the home team will cover.
            # Example (Arizona): model +10.1, market +3.5. Margin = 10.1 + 3.5 = +13.6. Bet Home.
            home_cover_margin = model_spread + market_spread

            # This is the "cover margin" for the AWAY team.
            # A positive value means the model predicts the away team will cover.
            away_cover_margin = (-model_spread) + (-market_spread)
            
            if home_cover_margin > SPREAD_THRESHOLD:
                # Value is on the HOME team
                spread_edge = home_cover_margin
                ats_pick = f"✅ BET: {home_team} {market_spread:+.1f}"
                # Adjusted confidence levels based on historical performance
                if spread_edge >= 12:
                    confidence = "VERY HIGH"
                elif spread_edge >= 8:
                    confidence = "HIGH"
                elif spread_edge >= 6:
                    confidence = "MEDIUM"
                else:
                    confidence = "LOW"

                if model_spread > 0 and market_spread > 0:
                    # Model predicts outright win for home underdog.
                    ats_explanation = f"MODEL PREDICTS OUTRIGHT WIN: {home_team} by {model_spread:+.1f} (Market: {market_spread:+.1f})"
                else:
                    ats_explanation = f"{confidence} confidence. Model predicts {home_team} covers by {home_cover_margin:+.1f} points."

            elif away_cover_margin > SPREAD_THRESHOLD:
                # Value is on the AWAY team
                spread_edge = away_cover_margin
                away_spread = -market_spread
                ats_pick = f"✅ BET: {away_team} {away_spread:+.1f}"
                # Adjusted confidence levels based on historical performance
                if spread_edge >= 12:
                    confidence = "VERY HIGH"
                elif spread_edge >= 8:
                    confidence = "HIGH"
                elif spread_edge >= 6:
                    confidence = "MEDIUM"
                else:
                    confidence = "LOW"

                if (-model_spread) > 0 and away_spread > 0:
                    # Model predicts outright win for away underdog.
                    ats_explanation = f"MODEL PREDICTS OUTRIGHT WIN: {away_team} by {-model_spread:+.1f} (Market: {away_spread:+.1f})"
                else:
                    ats_explanation = f"{confidence} confidence. Model predicts {away_team} covers by {away_cover_margin:+.1f} points."

            else:
                ats_pick = "❌ NO BET"
                # Use the larger margin (as a negative number) to show how close it was
                spread_edge = max(home_cover_margin, away_cover_margin)
                ats_explanation = f"Edge ({spread_edge:+.1f}) not significant."

            
            total_edge = model_total - market_total
            # --- END: CORRECTED SPREAD LOGIC ---

            total_pick, total_explanation = determine_total_pick(
                total_edge, market_total
            )
            
            # Format game time
            game_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            et_time = game_time.astimezone(pytz.timezone('US/Eastern'))

            # Check for team performance indicators
            picked_team = None
            if '✅ BET:' in ats_pick:
                # Extract team from pick text
                if home_team in ats_pick:
                    picked_team = home_team
                elif away_team in ats_pick:
                    picked_team = away_team

            team_indicator = None
            if picked_team:
                team_indicator = get_team_performance_indicator(picked_team, team_performance)

            game_data = {
                "commence_time": game['commence_time'],
                "GameTime": et_time.strftime("%m/%d %I:%M %p"),
                "Matchup": f"{away_team} @ {home_team}",
                "home_team": home_team,
                "away_team": away_team,
                "Market Spread": f"{market_spread:+.1f}",
                "Model Spread": f"{model_spread:+.1f}",
                "spread_edge": spread_edge, # This is now the cover margin
                "ATS Pick": ats_pick,
                "ATS Explanation": ats_explanation,
                "Market Total": f"{market_total:.1f}",
                "Model Total": f"{model_total:.1f}",
                "total_edge": total_edge,
                "Total Pick": total_pick,
                "Total Explanation": total_explanation,
                "Predicted Score": f"{away_team} {prediction['away_score']:.1f}, {home_team} {prediction['home_score']:.1f}",
                "team_indicator": team_indicator
            }
            
            # Calculate A.I. Rating (supplements edge-based approach)
            ai_rating = calculate_ai_rating(game_data, team_performance, historical_edge_performance)
            game_data["ai_rating"] = ai_rating

            # Always show all games with picks or no-bets
            results.append(game_data)

            # Log/update confident picks (will update existing or create new)
            # Trust the model's edge calculation - no artificial caps (aligned with NBA model)
            if '✅' in ats_pick and abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
                log_confident_pick(game_data, 'spread', spread_edge, model_spread, market_spread)

            if '✅' in total_pick and abs(total_edge) >= CONFIDENT_TOTAL_EDGE:
                log_confident_pick(game_data, 'total', total_edge, model_total, market_total)
        
        except Exception as e:
            print(f"{Colors.RED}Error processing game {game.get('home_team')}: {e}{Colors.END}")
            traceback.print_exc()
            continue
    
    return results

def predict_game(home_team, away_team, home_stats, away_stats):
    """
    Predict game outcome using advanced college basketball model

    Key factors:
    1. Offensive/Defensive efficiency ratings (properly weighted)
    2. Pace of play
    3. Home court advantage (reduced, more realistic)
    4. Regression to mean for extreme predictions
    """
    # Get team ratings
    home_off = home_stats['offensive_rating']
    home_def = home_stats['defensive_rating']
    away_off = away_stats['offensive_rating']
    away_def = away_stats['defensive_rating']

    # Average pace - slightly regressed to league average (~70)
    team_pace = (home_stats['pace'] + away_stats['pace']) / 2
    avg_pace = team_pace * 0.85 + 70 * 0.15  # Regress 15% to mean

    # NCAA average is approximately 100 points per 100 possessions
    ncaa_avg_efficiency = 100.0

    # Predict points per 100 possessions using Four Factors approach
    # Weight: 60% offensive strength, 40% opponent defensive weakness
    # This prevents overvaluing mismatches
    home_points_per_100 = (home_off * 0.60) + ((2 * ncaa_avg_efficiency - away_def) * 0.40)
    away_points_per_100 = (away_off * 0.60) + ((2 * ncaa_avg_efficiency - home_def) * 0.40)

    # Adjust for pace
    home_points = home_points_per_100 * (avg_pace / 100)
    away_points = away_points_per_100 * (avg_pace / 100)

    # Apply home court advantage (reduced and more realistic)
    home_points += HOME_COURT_ADVANTAGE / 2
    away_points -= HOME_COURT_ADVANTAGE / 2

    # Calculate spread and total
    spread = home_points - away_points
    total = home_points + away_points

    # Regress extreme predictions toward market efficiency
    # If predicted spread is very large, regress it 10% toward 0
    if abs(spread) > 15:
        spread = spread * 0.90
        # Recalculate points based on regressed spread
        margin_diff = (home_points - away_points) - spread
        home_points -= margin_diff / 2
        away_points += margin_diff / 2

    # Regress extreme totals toward league average (~145)
    league_avg_total = 145.0
    if total > 160 or total < 130:
        total = total * 0.85 + league_avg_total * 0.15

    return {
        'home_score': home_points,
        'away_score': away_points,
        'spread': spread,
        'total': total
    }

# Removed the broken determine_spread_pick function

def determine_total_pick(edge, market_line):
    """Determine if there's value on the total"""
    abs_edge = abs(edge)

    if abs_edge < TOTAL_THRESHOLD:
        return "❌ NO BET", f"Edge too small ({edge:+.1f})"

    # Determine over/under
    if edge > 0:
        # Model projects higher, bet over
        direction = "OVER"
    else:
        # Model projects lower, bet under
        direction = "UNDER"

    # Adjusted confidence levels based on historical performance
    if abs_edge >= 14:
        confidence = "VERY HIGH"
    elif abs_edge >= 10:
        confidence = "HIGH"
    elif abs_edge >= 7:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return (
        f"✅ BET: {direction} {market_line}",
        f"{confidence} confidence ({abs_edge:.1f} edge)"
    )

# =========================
# OUTPUT FUNCTIONS
# =========================

def display_terminal(results):
    """Display results in terminal with color formatting"""
    print(f"\n{Colors.BOLD}{'='*120}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}🏀 COLLEGE BASKETBALL MODEL PREDICTIONS 🏀{Colors.END}")
    print(f"{Colors.BOLD}{'='*120}{Colors.END}\n")

    # Results are already sorted by edge in main(), don't re-sort

    for i, game in enumerate(results, 1):
        print(f"{Colors.BOLD}{Colors.CYAN}━━━ GAME {i}: {game['Matchup']} ━━━{Colors.END}")
        print(f"{Colors.CYAN}🕐 {game['GameTime']}{Colors.END}")
        
        # Display A.I. Rating prominently
        ai_rating = game.get('ai_rating', 2.3)
        rating_stars = '⭐' * (int(ai_rating) - 2) if ai_rating >= 3.0 else ''
        
        # Color code rating
        if ai_rating >= 4.5:
            rating_color = Colors.GREEN
            rating_label = "PREMIUM PLAY"
        elif ai_rating >= 4.0:
            rating_color = Colors.GREEN
            rating_label = "STRONG PLAY"
        elif ai_rating >= 3.5:
            rating_color = Colors.CYAN
            rating_label = "GOOD PLAY"
        elif ai_rating >= 3.0:
            rating_color = Colors.YELLOW
            rating_label = "STANDARD PLAY"
        else:
            rating_color = Colors.YELLOW
            rating_label = "MARGINAL PLAY"
        
        print(f"{rating_color}{Colors.BOLD}🎯 A.I. Rating: {ai_rating:.1f} {rating_stars} ({rating_label}){Colors.END}")

        # Display team performance indicator if available
        if game.get('team_indicator'):
            indicator = game['team_indicator']
            print(f"{indicator['color']}{indicator['emoji']} {indicator['label']}: {indicator['message']}{Colors.END}")

        print(f"\n{Colors.YELLOW}📊 SPREAD:{Colors.END}")
        print(f"  Market: {game['Market Spread']} | Model: {game['Model Spread']} | Edge: {game['spread_edge']:+.1f}")

        pick_color = Colors.GREEN if '✅' in game['ATS Pick'] else Colors.RED
        print(f"  {pick_color}{game['ATS Pick']}{Colors.END}")
        if game.get('ATS Explanation'):
            print(f"  {Colors.CYAN}{game['ATS Explanation']}{Colors.END}")
        
        print(f"\n{Colors.YELLOW}🎯 TOTAL:{Colors.END}")
        print(f"  Market: {game['Market Total']} | Model: {game['Model Total']} | Edge: {game['total_edge']:+.1f}")
        
        pick_color = Colors.GREEN if '✅' in game['Total Pick'] else Colors.RED
        print(f"  {pick_color}{game['Total Pick']}{Colors.END}")
        if game.get('Total Explanation'):
            print(f"  {Colors.CYAN}{game['Total Explanation']}{Colors.END}")
        
        print(f"\n{Colors.PURPLE}📈 {game['Predicted Score']}{Colors.END}")
        print()
    
    print(f"{Colors.BOLD}{'='*120}{Colors.END}\n")

def save_csv(results):
    """Save results to CSV file"""
    if not results:
        return

    # Results are already sorted by edge in main(), don't re-sort

    fieldnames = [
        'GameTime', 'Matchup', 'home_team', 'away_team', 'A.I. Rating',
        'Market Spread', 'Model Spread', 'spread_edge', 'ATS Pick', 'ATS Explanation',
        'Market Total', 'Model Total', 'total_edge', 
        'Total Pick', 'Total Explanation', 'Predicted Score', 'commence_time'
    ]
    
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(results)
        
        print(f"{Colors.GREEN}✓ CSV saved: {CSV_FILE}{Colors.END}")
    except IOError as e:
        print(f"{Colors.RED}Error saving CSV: {e}{Colors.END}")

def save_html(results):
    """Generate HTML output with PROPS_HTML_STYLING_GUIDE aesthetic - REVISED COPY"""
    et = pytz.timezone('US/Eastern')
    timestamp_str = datetime.now(et).strftime('%Y-%m-%d %I:%M %p ET')
    
    # CSS/HTML Template matches the new revised aesthetic
    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCAAB Model Picks</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #121212;
            --bg-card: #1c1c1e;
            --bg-metric: #2c2c2e;
            --text-primary: #ffffff;
            --text-secondary: #8e8e93;
            --accent-green: #34c759;
            --accent-red: #ff3b30;
            --border-color: #333333;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 2rem;
        }

        .container {
            max-width: 850px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }

        header h1 {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }

        .date-sub {
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 500;
        }

        .prop-card {
            background-color: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255,255,255,0.05);
        }

        /* Header Section */
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .matchup-info h2 {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .matchup-sub {
            font-size: 0.85rem;
            color: var(--text-secondary);
            text-transform: uppercase;
        }

        .game-time-badge {
            background-color: var(--bg-metric);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        /* Bet Section */
        .bet-row {
            margin-bottom: 1.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .bet-row:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }

        .main-pick {
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
            letter-spacing: -0.01em;
        }
        
        .main-pick.green { color: var(--accent-green); }
        .main-pick.red { color: var(--accent-red); }

        .model-context {
            color: var(--text-secondary);
            font-size: 0.95rem;
            font-weight: 500;
        }

        .edge-val {
            color: var(--accent-green);
            font-weight: 600;
            margin-left: 6px;
        }

        /* Metrics Row */
        .metrics-row {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
        }

        .metric-box {
            background-color: var(--bg-metric);
            border-radius: 8px;
            padding: 0.8rem 1.5rem;
            text-align: center;
            flex: 1;
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

        /* Tags */
        .tags-row {
            display: flex;
            gap: 0.75rem;
            margin-top: 1.5rem;
            flex-wrap: wrap;
        }

        .tag {
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .tag-red { background: rgba(255, 59, 48, 0.15); color: #ff453a; }
        .tag-blue { background: rgba(10, 132, 255, 0.15); color: #5ac8fa; }
        .tag-green { background: rgba(48, 209, 88, 0.15); color: #32d74b; }

        @media (max-width: 600px) {
            body { padding: 1rem; }
            .metrics-row { gap: 0.5rem; }
            .metric-box { padding: 0.8rem 0.5rem; }
            .main-pick { font-size: 1.5rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🏀 NCAAB MODEL</h1>
                <div class="date-sub">{{ timestamp }}</div>
            </div>
            <div>
                 <span style="font-size: 1.5rem;">🎓</span>
            </div>
        </header>

        {% for game in results %}
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                     <div class="matchup-info">
                        <h2>{{ game.Matchup }}</h2>
                        <div class="matchup-sub">NCAAB</div>
                    </div>
                </div>
                <div class="game-time-badge">{{ game.GameTime }}</div>
            </div>

            <!-- SPREAD BET BLOCK -->
            <div class="bet-row">
                {% if '✅' in game['ATS Pick'] %}
                <div class="main-pick green">{{ game['ATS Pick'] }}</div>
                {% else %}
                <div class="main-pick">{{ game['Market Spread'] }}</div>
                {% endif %}
                
                <div class="model-context">
                    Model: {{ game['Model Spread'] }}
                    <span class="edge-val">Edge: {{ "%+.1f"|format(game.spread_edge) }}</span>
                </div>
            </div>

            <!-- TOTAL BET BLOCK -->
            <div class="bet-row" style="border-bottom: none;">
                {% if '✅' in game['Total Pick'] %}
                    <div class="main-pick green">{{ game['Total Pick'] }}</div>
                {% else %}
                <div class="main-pick">O/U {{ game['Market Total'] }}</div>
                {% endif %}
                
                <div class="model-context">
                    Model: {{ game['Model Total'] }}
                    <span class="edge-val">Edge: {{ "%+.1f"|format(game.total_edge) }}</span>
                </div>
            </div>

            <!-- METRICS ROW -->
            <div class="metrics-row">
                {% set ai_rating = game.ai_rating if game.ai_rating else 2.3 %}
                <div class="metric-box">
                    <div class="metric-title">AI RATING</div>
                    <div class="metric-value {{ 'good' if ai_rating >= 4.0 else '' }}">{{ "%.1f"|format(ai_rating) }}</div>
                </div>
                <!-- Calculate Max EV/Confidence -->
                {% set spread_confidence = (game.spread_edge|abs / 10.0 * 100)|int %}
                {% set total_confidence = (game.total_edge|abs / 12.0 * 100)|int %}
                {% set max_conf = spread_confidence if spread_confidence > total_confidence else total_confidence %}
                {% if max_conf > 99 %}{% set max_conf = 99 %}{% endif %}
                
                <div class="metric-box">
                    <div class="metric-title">WIN % (EST)</div>
                    <div class="metric-value {{ 'good' if max_conf >= 55 else '' }}">{{ 50 + (max_conf * 0.25)|int }}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">PREDICTED</div>
                    <div class="metric-value" style="font-size: 1rem;">{{ game['Predicted Score'] }}</div>
                </div>
            </div>

            <!-- TAGS -->
            <div class="tags-row">
                {% if game.team_indicator %}
                <div class="tag tag-blue">{{ game.team_indicator.emoji }} {{ game.team_indicator.message }}</div>
                {% endif %}
                
                {% if game['ATS Explanation'] %}
                <div class="tag tag-green">ATS: {{ game['ATS Explanation'] }}</div>
                {% endif %}
                
                {% if game['Total Explanation'] %}
                <div class="tag tag-green">Total: {{ game['Total Explanation'] }}</div>
                {% endif %}
            </div>

        </div>
        {% endfor %}
    </div>
</body>
</html>"""

    template = Template(template_str)
    html_output = template.render(
        results=results, 
        timestamp=timestamp_str
    )
    
    try:
        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html_output)
        print(f"{Colors.GREEN}✓ HTML saved: {HTML_FILE}{Colors.END}")
    except IOError as e:
        print(f"{Colors.RED}Error saving HTML: {e}{Colors.END}")



# Custom filter for date formatting (MOVED TO GLOBAL SCOPE)
def format_date(date_str):
    try:
        dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        et_dt = dt.astimezone(pytz.timezone('US/Eastern'))
        return et_dt.strftime("%m/%d %I:%M %p")
    except Exception:
        return str(date_str)


def generate_tracking_html():
    """Generate tracking dashboard HTML"""
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)

    et = pytz.timezone('US/Eastern')
    timestamp_str = datetime.now(et).strftime('%Y-%m-%d %I:%M %p')
    current_time = datetime.now(et)

    # Calculate today's and yesterday's records
    today = current_time.date()
    yesterday = (current_time - timedelta(days=1)).date()

    completed_picks = [p for p in tracking_data['picks'] if p.get('status', '').lower() in ['win', 'loss', 'push']]

    # Today's record
    today_wins = 0
    today_losses = 0
    today_pushes = 0

    # Yesterday's record
    yesterday_wins = 0
    yesterday_losses = 0
    yesterday_pushes = 0

    for pick in completed_picks:
        try:
            game_dt = datetime.fromisoformat(str(pick.get('game_date', '')).replace('Z', '+00:00'))
            game_dt_et = game_dt.astimezone(et)
            game_date = game_dt_et.date()

            if game_date == today:
                if pick.get('status', '').lower() == 'win':
                    today_wins += 1
                elif pick.get('status', '').lower() == 'loss':
                    today_losses += 1
                elif pick.get('status', '').lower() == 'push':
                    today_pushes += 1
            elif game_date == yesterday:
                if pick.get('status', '').lower() == 'win':
                    yesterday_wins += 1
                elif pick.get('status', '').lower() == 'loss':
                    yesterday_losses += 1
                elif pick.get('status', '').lower() == 'push':
                    yesterday_pushes += 1
        except:
            pass

    # Always show both today's and yesterday's records
    today_total = today_wins + today_losses + today_pushes
    yesterday_total = yesterday_wins + yesterday_losses + yesterday_pushes

    # Calculate spread and total records (overall, today, and yesterday)
    all_completed = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() in ['win', 'loss', 'push']]

    # Overall records by type
    spread_wins = spread_losses = spread_pushes = 0
    total_wins = total_losses = total_pushes = 0

    # Today's records by type
    today_spread_wins = today_spread_losses = today_spread_pushes = 0
    today_total_wins = today_total_losses = today_total_pushes = 0

    # Yesterday records by type
    yesterday_spread_wins = yesterday_spread_losses = yesterday_spread_pushes = 0
    yesterday_total_wins = yesterday_total_losses = yesterday_total_pushes = 0

    for pick in all_completed:
        pick_type = pick.get('pick_type', '').lower()
        status = pick.get('status', '').lower()

        # Check if from today or yesterday
        is_today = False
        is_yesterday = False
        try:
            game_dt = datetime.fromisoformat(str(pick.get('game_date', '')).replace('Z', '+00:00'))
            game_dt_et = game_dt.astimezone(et)
            game_date = game_dt_et.date()
            is_today = (game_date == today)
            is_yesterday = (game_date == yesterday)
        except:
            pass

        # Count overall records
        if pick_type == 'spread':
            if status == 'win':
                spread_wins += 1
                if is_today:
                    today_spread_wins += 1
                if is_yesterday:
                    yesterday_spread_wins += 1
            elif status == 'loss':
                spread_losses += 1
                if is_today:
                    today_spread_losses += 1
                if is_yesterday:
                    yesterday_spread_losses += 1
            elif status == 'push':
                spread_pushes += 1
                if is_today:
                    today_spread_pushes += 1
                if is_yesterday:
                    yesterday_spread_pushes += 1
        elif pick_type == 'total':
            if status == 'win':
                total_wins += 1
                if is_today:
                    today_total_wins += 1
                if is_yesterday:
                    yesterday_total_wins += 1
            elif status == 'loss':
                total_losses += 1
                if is_today:
                    today_total_losses += 1
                if is_yesterday:
                    yesterday_total_losses += 1
            elif status == 'push':
                total_pushes += 1
                if is_today:
                    today_total_pushes += 1
                if is_yesterday:
                    yesterday_total_pushes += 1

    # We'll pass both today's and yesterday's records to the template
    # No need to determine which one to display - we'll show both

    # Separate picks into categories
    all_pending = [p for p in tracking_data.get('picks', []) if p.get('status') == 'pending']
    
    # UPCOMING: Pending picks where game date is in the future
    upcoming_picks = []
    # STALE: Pending picks where game date is in the past (need updating)
    stale_picks = []
    
    for pick in all_pending:
        try:
            game_dt = datetime.fromisoformat(str(pick.get('game_date', '')).replace('Z', '+00:00'))
            game_dt_et = game_dt.astimezone(et)
            
            if game_dt_et > current_time:
                upcoming_picks.append(pick)
            else:
                stale_picks.append(pick)
        except:
            # If we can't parse the date, assume it's stale
            stale_picks.append(pick)
    
    completed_picks = [p for p in tracking_data.get('picks', []) if p.get('status') != 'pending']
    
    # Sort by game date
    upcoming_picks.sort(key=lambda x: x.get('game_date', ''))
    completed_picks.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    stale_picks.sort(key=lambda x: x.get('game_date', ''))
    
    template_str = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCAAB Bet Tracking Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
            background: #000000;
            color: #ffffff;
            padding: 1.5rem;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .card {
            background: #1a1a1a;
            border-radius: 1.25rem;
            border: none;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .stat-card {
            background: #262626;
            border: none;
            border-radius: 1rem;
            padding: 1.5rem;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #4ade80;
        }
        .stat-value.positive { color: #4ade80; }
        .stat-value.negative { color: #f87171; }
        .stat-label {
            color: #94a3b8;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.5rem;
            font-weight: 500;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: #ffffff;
            text-align: center;
        }
        h2 {
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: #ffffff;
        }
        h3 {
            font-size: 1.5rem;
            font-weight: 700;
            color: #ffffff;
        }
        h4 {
            font-size: 1.125rem;
            font-weight: 600;
            color: #94a3b8;
        }
        table { width: 100%; border-collapse: collapse; }
        thead { background: #262626; }
        th { padding: 0.875rem 1rem; text-align: left; color: #94a3b8; font-weight: 600; font-size: 0.875rem; }
        td { padding: 0.875rem 1rem; border-bottom: 1px solid #2a3441; font-size: 0.9375rem; }
        tr:hover { background: #262626; }
        .text-center { text-align: center; }
        .text-green-400 { color: #4ade80; }
        .text-blue-400 { color: #60a5fa; }
        .text-pink-400 { color: #f472b6; }
        .text-red-400 { color: #f87171; }
        .text-yellow-400 { color: #fbbf24; }
        .text-gray-400 { color: #94a3b8; }
        .font-bold { font-weight: 700; }
        .text-sm { font-size: 0.875rem; }
        .badge {
            display: inline-block;
            padding: 0.375rem 0.875rem;
            border-radius: 0.5rem;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-pending { background: rgba(96, 165, 250, 0.2); color: #60a5fa; }
        .badge-win { background: rgba(74, 222, 128, 0.2); color: #4ade80; }
        .badge-loss { background: rgba(248, 113, 113, 0.2); color: #f87171; }
        .badge-push { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
        .badge-error { background: rgba(248, 113, 113, 0.2); color: #f87171; }
        .subtitle { color: #94a3b8; font-size: 1rem; font-weight: 400; }

        /* Mobile Responsiveness */
        @media (max-width: 1024px) {
            .container { max-width: 100%; }
            h1 { font-size: 2rem; }
            h2 { font-size: 1.5rem; }
            h3 { font-size: 1.25rem; }
        }

        @media (max-width: 768px) {
            body { padding: 1rem; }
            .card { padding: 1.25rem; }

            h1 { font-size: 1.75rem; }
            h2 { font-size: 1.25rem; }
            h3 { font-size: 1.125rem; }
            h4 { font-size: 1rem; }

            /* Make all inline 5-column grids responsive */
            div[style*="grid-template-columns: repeat(5, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            /* Make all inline 4-column grids responsive */
            div[style*="grid-template-columns: repeat(4, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            /* Make all inline 2-column grids single column on mobile */
            div[style*="grid-template-columns: repeat(2, 1fr)"] {
                grid-template-columns: 1fr !important;
            }

            /* Make all inline 3-column grids responsive */
            div[style*="grid-template-columns: repeat(3, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            /* Make auto-fit grids smaller on mobile */
            .grid {
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 0.75rem;
            }

            /* Stat cards */
            .stat-card {
                padding: 1rem;
            }
            .stat-value {
                font-size: 1.75rem;
            }
            .stat-label {
                font-size: 0.6875rem;
            }

            /* Tables - enable horizontal scroll and reduce font */
            table {
                font-size: 0.8125rem;
                display: block;
                overflow-x: auto;
                white-space: nowrap;
                -webkit-overflow-scrolling: touch;
            }
            thead, tbody, tr {
                display: table;
                width: 100%;
                table-layout: fixed;
            }
            th, td {
                padding: 0.625rem 0.5rem;
                font-size: 0.8125rem;
            }
            th {
                font-size: 0.75rem;
            }

            /* Badges */
            .badge {
                padding: 0.3125rem 0.625rem;
                font-size: 0.6875rem;
                margin: 0.1875rem;
            }

            /* Reduce spacing */
            div[style*="padding: 2rem"] {
                padding: 1.25rem !important;
            }
            div[style*="padding: 1.5rem"] {
                padding: 1rem !important;
            }
            div[style*="gap: 1.5rem"] {
                gap: 1rem !important;
            }
            div[style*="margin-bottom: 2rem"] {
                margin-bottom: 1.25rem !important;
            }
            div[style*="font-size: 1.75rem"] {
                font-size: 1.5rem !important;
            }
        }

        @media (max-width: 480px) {
            body { padding: 0.75rem; }
            .card { padding: 1rem; margin-bottom: 1rem; }

            h1 { font-size: 1.5rem; }
            h2 { font-size: 1.125rem; }
            h3 { font-size: 1rem; }

            .stat-value { font-size: 1.5rem; }
            .stat-label { font-size: 0.625rem; }
            .stat-card { padding: 0.75rem; }

            /* Force all multi-column grids to single column on small phones */
            div[style*="grid-template-columns"] {
                grid-template-columns: 1fr !important;
            }

            .grid {
                grid-template-columns: 1fr;
            }

            table { font-size: 0.75rem; }
            th, td { padding: 0.5rem 0.375rem; font-size: 0.75rem; }
            th { font-size: 0.6875rem; }

            .badge {
                display: block;
                margin: 0.25rem 0;
                text-align: center;
            }

            div[style*="font-size: 1.75rem"] {
                font-size: 1.25rem !important;
            }
            div[style*="font-size: 1.5rem"] {
                font-size: 1.125rem !important;
            }
            div[style*="font-size: 1.125rem"] {
                font-size: 1rem !important;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="text-center">Model Performance</h1>
            <p class="text-center subtitle" style="margin-bottom: 2rem;">CourtSide Analytics - NCAAB</p>

            <!-- Overall Performance Card -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #4ade80; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    📊 Overall Performance
                </h3>
                <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.total_picks }}</div>
                        <div class="stat-label">Total Bets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.wins }}-{{ stats.losses }}{% if stats.pushes > 0 %}-{{ stats.pushes }}{% endif %}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ "%.1f"|format(stats.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if stats.total_profit > 0 %}text-green-400{% elif stats.total_profit < 0 %}text-red-400{% endif %}">
                            {% if stats.total_profit > 0 %}+{% endif %}{{ "%.2f"|format(stats.total_profit/100) }}u
                        </div>
                        <div class="stat-label">Total Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if stats.roi > 0 %}text-green-400{% elif stats.roi < 0 %}text-red-400{% endif %}">
                            {% if stats.roi > 0 %}+{% endif %}{{ "%.1f"|format(stats.roi) }}%
                        </div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ spread_wins + spread_losses + spread_pushes }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.5rem;">{{ spread_wins }}-{{ spread_losses }}{% if spread_pushes > 0 %}-{{ spread_pushes }}{% endif %}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-blue-400 font-bold">{% if spread_wins + spread_losses > 0 %}{{ "%.1f"|format(spread_wins / (spread_wins + spread_losses) * 100) }}%{% else %}0.0%{% endif %}</span></div>
                            <div><span class="text-gray-400">Profit:</span> <span class="text-green-400 font-bold">{{ "%.2f"|format((spread_wins * 100 - spread_losses * 110) / 100) }}u</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Totals ({{ total_wins + total_losses + total_pushes }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #f472b6; margin-bottom: 0.5rem;">{{ total_wins }}-{{ total_losses }}{% if total_pushes > 0 %}-{{ total_pushes }}{% endif %}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-pink-400 font-bold">{% if total_wins + total_losses > 0 %}{{ "%.1f"|format(total_wins / (total_wins + total_losses) * 100) }}%{% else %}0.0%{% endif %}</span></div>
                            <div><span class="text-gray-400">Profit:</span> <span class="text-green-400 font-bold">{{ "%.2f"|format((total_wins * 100 - total_losses * 110) / 100) }}u</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Today's/Yesterday's Record -->
            {% if today_total > 0 or yesterday_total > 0 %}
            <div style="background: #262626; border-radius: 1rem; padding: 1.5rem;">
                <h3 style="font-size: 1.25rem; margin-bottom: 1rem; text-align: center; color: #fbbf24;">Recent Records</h3>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 2rem;">
                    {% if today_total > 0 %}
                    <div style="text-align: center;">
                        <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">Today</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #4ade80;">{{ today_wins }}-{{ today_losses }}{% if today_pushes > 0 %}-{{ today_pushes }}{% endif %}</div>
                    </div>
                    {% endif %}
                    {% if yesterday_total > 0 %}
                    <div style="text-align: center;">
                        <div style="font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem;">{{ yesterday.strftime('%b %d') }}</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #4ade80;">{{ yesterday_wins }}-{{ yesterday_losses }}{% if yesterday_pushes > 0 %}-{{ yesterday_pushes }}{% endif %}</div>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endif %}
        </div>
        
        {% if upcoming_picks %}
        <div class="card">
            <h2>🎯 Upcoming Bets</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Game Date</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Pick</th>
                            <th>Line</th>
                            <th>Edge</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pick in upcoming_picks %}
                        <tr>
                            <td class="text-sm font-bold">{{ format_date(pick.game_date) }}</td>
                            <td class="font-bold">{{ pick.away_team }} @ {{ pick.home_team }}</td>
                            <td>{{ pick.pick_type|title }}</td>
                            <td class="text-yellow-400">{{ pick.pick_text }}</td>
                            <td>{{ pick.market_line }}</td>
                            <td>{{ "%+.1f"|format(pick.edge) }}</td>
                            <td><span class="badge badge-pending">Pending</span></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}
        
        {% if stale_picks %}
        <div class="card">
            <h2>⚠️ Past Pending Bets (Need Update)</h2>
            <p style="color: #f59e0b; margin-bottom: 1rem; font-size: 0.875rem;">
                ⚠️ These picks are from past games but haven't been updated yet. Run the model to update them.
            </p>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Game Date</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Pick</th>
                            <th>Line</th>
                            <th>Edge</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pick in stale_picks %}
                        <tr style="opacity: 0.7;">
                            <td class="text-sm font-bold">{{ format_date(pick.game_date) }}</td>
                            <td class="font-bold">{{ pick.away_team }} @ {{ pick.home_team }}</td>
                            <td>{{ pick.pick_type|title }}</td>
                            <td class="text-gray-400">{{ pick.pick_text }}</td>
                            <td>{{ pick.market_line }}</td>
                            <td>{{ "%+.1f"|format(pick.edge) }}</td>
                            <td><span class="badge badge-error">Needs Update</span></td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
        {% endif %}
        
        <div class="text-center text-gray-400 text-sm" style="margin-top: 2rem;">
            <p>Last updated: {{ timestamp }}</p>
        </div>
    </div>
</body>
</html>'''
    
    # Custom filter for date formatting
    # (This function has been moved to the global scope, outside generate_tracking_html)
    
    template = Template(template_str)
    # *** THIS IS THE FIX: ***
    # We no longer register it as a filter
    # template.filters['format_date'] = format_date
    
    html_output = template.render(
        stats=stats,
        upcoming_picks=upcoming_picks,
        stale_picks=stale_picks,
        completed_picks=completed_picks,
        timestamp=timestamp_str,
        format_date=format_date,
        # Overall records
        spread_wins=spread_wins,
        spread_losses=spread_losses,
        spread_pushes=spread_pushes,
        total_wins=total_wins,
        total_losses=total_losses,
        total_pushes=total_pushes,
        # Today's records
        today_wins=today_wins,
        today_losses=today_losses,
        today_pushes=today_pushes,
        today_total=today_total,
        today_spread_wins=today_spread_wins,
        today_spread_losses=today_spread_losses,
        today_spread_pushes=today_spread_pushes,
        today_total_wins=today_total_wins,
        today_total_losses=today_total_losses,
        today_total_pushes=today_total_pushes,
        # Yesterday's records
        yesterday=yesterday,
        yesterday_wins=yesterday_wins,
        yesterday_losses=yesterday_losses,
        yesterday_pushes=yesterday_pushes,
        yesterday_total=yesterday_total,
        yesterday_spread_wins=yesterday_spread_wins,
        yesterday_spread_losses=yesterday_spread_losses,
        yesterday_spread_pushes=yesterday_spread_pushes,
        yesterday_total_wins=yesterday_total_wins,
        yesterday_total_losses=yesterday_total_losses,
        yesterday_total_pushes=yesterday_total_pushes
    )
    
    try:
        with open(TRACKING_HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        print(f"{Colors.GREEN}✓ Tracking dashboard saved: {TRACKING_HTML_FILE}{Colors.END}")
    except IOError as e:
        print(f"{Colors.RED}Error saving tracking HTML: {e}{Colors.END}")

# =========================
# MAIN EXECUTION
# =========================

def main():
    """Main execution function"""
    print(f"\n{Colors.BOLD}{'='*100}{Colors.END}") 
    print(f"{Colors.BOLD}{Colors.CYAN}🏀 COLLEGE BASKETBALL SHARP MODEL 🏀{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}⚡ Targeting 56%+ Win Rate with Advanced Analytics ⚡{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}📅 Filtering games within next {DAYS_AHEAD_TO_FETCH} days{Colors.END}")
    print(f"{Colors.BOLD}{'='*100}{Colors.END}\n")
    
    try:
        # STEP 1: Clean up stale picks that are too old to verify
        print(f"{Colors.BOLD}{Colors.CYAN}STEP 1: Cleaning Up Stale Picks (>7 days old){Colors.END}")
        clear_stale_picks(days_old=7)

        # STEP 2: Update old picks with completed game results
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 2: Checking for Completed Games & Updating Past Picks{Colors.END}")
        update_pick_results()
        generate_tracking_html()

        # STEP 3: Fetch team statistics
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 3: Loading Team Statistics{Colors.END}")
        team_stats = fetch_team_stats()

        # STEP 4: Fetch current odds
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 4: Fetching Live Odds (Next {DAYS_AHEAD_TO_FETCH} Days){Colors.END}")
        games = fetch_odds()

        if not games:
            print(f"\n{Colors.YELLOW}⚠️  No games found from The Odds API in next {DAYS_AHEAD_TO_FETCH} days.{Colors.END}\n")
            return

        # STEP 5: Process and analyze
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 5: Processing Games & Generating Sharp Picks{Colors.END}\n")
        results = process_games(games, team_stats)

        if results:
            print(f"\n{Colors.BOLD}{Colors.GREEN}✅ Analyzed {len(results)} games with complete odds{Colors.END}\n")

            # Sort all results by A.I. Rating (primary), with edge as tiebreaker
            # This prioritizes quality/trustworthiness while considering edge magnitude
            def get_sort_score(game):
                # Primary: A.I. Rating (2.3-4.9 range)
                rating = game.get('ai_rating', 2.3)
                # Secondary: Maximum edge (for tiebreaking)
                spread_edge = abs(game.get('spread_edge', 0))
                total_edge = abs(game.get('total_edge', 0))
                max_edge = max(spread_edge, total_edge)
                # Return tuple: (rating, edge) for sorting
                return (rating, max_edge)

            sorted_results = sorted(results, key=get_sort_score, reverse=True)

            print(f"{Colors.YELLOW}📊 All picks sorted by A.I. Rating (quality/confidence first){Colors.END}\n")

            display_terminal(sorted_results)
            save_csv(sorted_results)
            save_html(sorted_results)
        else:
            print(f"\n{Colors.YELLOW}⚠️  No games with complete betting lines found.{Colors.END}\n")

        # STEP 6: Generate final tracking dashboard
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 6: Generating Final Tracking Dashboard{Colors.END}")
        generate_tracking_html()
        
        # Display tracking summary
        tracking_data = load_picks_tracking()
        stats = calculate_tracking_stats(tracking_data)
        
        print(f"\n{Colors.BOLD}{'='*100}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.YELLOW}📊 TRACKING SUMMARY 📊{Colors.END}")
        print(f"{Colors.BOLD}{'='*100}{Colors.END}")
        print(f"{Colors.GREEN}Total Tracked Bets: {stats['total_picks']}{Colors.END}")
        print(f"{Colors.GREEN}Record: {stats['wins']}-{stats['losses']}-{stats['pushes']}{Colors.END}")
        print(f"{Colors.GREEN}Win Rate: {stats['win_rate']:.1f}%{Colors.END}")
        profit = stats.get('total_profit', 0)
        profit_color = Colors.GREEN if profit > 0 else (Colors.RED if profit < 0 else Colors.YELLOW)
        print(f"{profit_color}Profit: {profit/100:+.2f} units{Colors.END}")
        roi = stats.get('roi', 0)
        roi_color = Colors.GREEN if roi > 0 else (Colors.RED if roi < 0 else Colors.YELLOW)
        print(f"{roi_color}ROI: {roi:+.1f}%{Colors.END}")
        print(f"{Colors.BOLD}{'='*100}{Colors.END}\n")

        # Update unified dashboard
        print(f"{Colors.CYAN}Updating unified dashboard...{Colors.END}")
        try:
            import subprocess
            subprocess.run(
                ['python3', os.path.join(SCRIPT_DIR, '..', 'unified_dashboard_interactive.py')],
                timeout=30,
                capture_output=True
            )
            print(f"{Colors.GREEN}✓ Dashboard updated{Colors.END}\n")
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Dashboard update failed: {e}{Colors.END}\n")

    except Exception as e:
        print(f"{Colors.RED}{'='*30} FATAL ERROR {'='*30}{Colors.END}")
        print(f"{Colors.RED}An unhandled exception occurred: {e}{Colors.END}")
        traceback.print_exc()
        print(f"{Colors.RED}{'='*73}{Colors.END}")


if __name__ == "__main__":
    main()

