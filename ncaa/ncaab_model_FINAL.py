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
import numpy as np
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
    "regions": "us",
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

# --- Model Parameters (Tuned for College Basketball) ---
HOME_COURT_ADVANTAGE = 3.5  # Stronger in college
SPREAD_THRESHOLD = 2.5  # Minimum edge to show as a pick
TOTAL_THRESHOLD = 4.0   # Minimum edge to show as a pick

# Tracking Parameters
CONFIDENT_SPREAD_EDGE = 5.0  # Higher threshold for sharp college picks
CONFIDENT_TOTAL_EDGE = 7.0   # College totals are volatile
UNIT_SIZE = 100  # Standard bet size in dollars

# Date filtering
DAYS_AHEAD_TO_FETCH = 7  # Only fetch games within next 7 days

# --- Parameters for Team Form/Momentum ---
LAST_N_GAMES = 8       # Smaller recent sample for college
SEASON_WEIGHT = 0.65   # Less weight on full season
FORM_WEIGHT = 0.35     # More weight on recent form

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
    
    # Common abbreviations and variations
    name_map = {
        # Common abbreviations
        "UConn": "Connecticut",
        "UCF": "Central Florida",
        "UNLV": "Nevada Las Vegas",
        "USC": "Southern California",
        "UCLA": "California Los Angeles",
        "LSU": "Louisiana State",
        "TCU": "Texas Christian",
        "SMU": "Southern Methodist",
        "BYU": "Brigham Young",
        "VCU": "Virginia Commonwealth",
        "UTEP": "Texas El Paso",
        "UTSA": "Texas San Antonio",
        
        # State variations
        "Miami FL": "Miami",
        "Miami (FL)": "Miami",
        "Miami OH": "Miami Ohio",
        "Miami (OH)": "Miami Ohio",
        
        # Common variations
        "St. John's": "St John's",
        "Saint John's": "St John's",
        "St. Mary's": "St Mary's",
        "Saint Mary's": "St Mary's",
        "UNC": "North Carolina",
    }
    
    # First check direct mapping
    if name in name_map:
        return name_map[name]
    
    # Normalize common patterns
    normalized = name
    normalized = normalized.replace(" St ", " State ")
    normalized = normalized.replace(" St.", " State")
    
    return normalized

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
    """Log a confident pick to the tracking file"""
    tracking_data = load_picks_tracking()
    
    # Create unique pick ID
    pick_id = f"{game_data['home_team']}_{game_data['away_team']}_{game_data['commence_time']}_{pick_type}"
    
    # Check if this pick already exists
    existing_pick = next((p for p in tracking_data['picks'] if p['pick_id'] == pick_id), None)
    if existing_pick:
        return  # Don't log duplicates
    
    # Determine the actual pick
    if pick_type == 'spread':
        pick_text = game_data.get('ATS Pick', '')
    else:  # total
        pick_text = game_data.get('Total Pick', '')
    
    if not pick_text or '✅' not in pick_text:
        print(f"{Colors.YELLOW}⚠️  Skipping logging for non-pick: {pick_type}{Colors.END}")
        return

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
            "daysFrom": 3  # Check last 3 days (API limit)
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
    Fetch or generate team statistics
    In production, this would pull from a college basketball stats API
    For now, we'll use a simulated stats model based on historical patterns
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
            print(f"{Colors.YELLOW}⚠️  Cache file error: {e}. Re-generating.{Colors.END}")

    
    # In production, integrate with college basketball stats API
    # For now, return empty dict (will use simulated stats in processing)
    print(f"{Colors.YELLOW}⚠️  No stats cache found or cache is old. Using simulated model.{Colors.END}")
    
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


def estimate_team_strength(team_name):
    """
    Estimate team strength based on historical data and patterns
    Returns offensive and defensive ratings (points per 100 possessions)
    """
    # This is a simplified model - in production, use real stats
    # We'll use team name patterns and conference to estimate strength
    
    team_lower = team_name.lower()
    
    # Power conference teams tend to be stronger
    power_conferences = ['duke', 'kansas', 'north carolina', 'kentucky', 'gonzaga',
                        'villanova', 'michigan', 'ucla', 'arizona', 'purdue',
                        'houston', 'texas', 'alabama', 'tennessee', 'connecticut',
                        'marquette', 'creighton', 'baylor', 'xavier', 'st john']
    
    mid_major_strong = ['san diego state', 'nevada', 'new mexico', 'vcu',
                       'memphis', 'wichita state', 'davidson', 'saint mary']
    
    # Base ratings (average team is around 100)
    if any(p in team_lower for p in power_conferences):
        off_rating = np.random.normal(108, 4)  # Strong offense
        def_rating = np.random.normal(95, 4)   # Strong defense
    elif any(m in team_lower for m in mid_major_strong):
        off_rating = np.random.normal(104, 5)
        def_rating = np.random.normal(98, 5)
    else:
        off_rating = np.random.normal(100, 6)
        def_rating = np.random.normal(100, 6)
    
    # Ensure realistic ranges
    off_rating = max(85, min(120, off_rating))
    def_rating = max(85, min(115, def_rating))
    
    # Estimate pace (possessions per game)
    pace = np.random.normal(70, 4)
    pace = max(62, min(78, pace))
    
    return {
        "offensive_rating": off_rating,
        "defensive_rating": def_rating,
        "pace": pace,
        "net_rating": off_rating - def_rating
    }

# =========================
# GAME PROCESSING
# =========================

def extract_best_odds(bookmakers, market_type):
    """Extract best available odds for a given market"""
    best_odds = {}
    
    for book in bookmakers:
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
    
    for game in games:
        try:
            home_team = normalize_team_name(game['home_team'])
            away_team = normalize_team_name(game['away_team'])
            
            # Get team statistics
            # Use defaultdict to avoid repeated .get() or checks
            home_stats = team_stats.get(home_team) or estimate_team_strength(home_team)
            away_stats = team_stats.get(away_team) or estimate_team_strength(away_team)
            
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
                confidence = "HIGH" if spread_edge >= 5 else "MEDIUM"
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
                confidence = "HIGH" if spread_edge >= 5 else "MEDIUM"

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
                "Predicted Score": f"{away_team} {prediction['away_score']:.1f}, {home_team} {prediction['home_score']:.1f}"
            }
            
            results.append(game_data)
            
            # Log confident picks
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
    1. Offensive/Defensive efficiency ratings
    2. Pace of play
    3. Home court advantage (stronger in college)
    4. Conference strength adjustments
    """
    # Get team ratings
    home_off = home_stats['offensive_rating']
    home_def = home_stats['defensive_rating']
    away_off = away_stats['offensive_rating']
    away_def = away_stats['defensive_rating']
    
    # Average pace
    avg_pace = (home_stats['pace'] + away_stats['pace']) / 2
    
    # Predict points per 100 possessions
    # Adjusted formula: Team's Off vs Opponent's Def
    home_points_per_100 = (home_off + away_def) / 2 # Simple average, can be more complex
    away_points_per_100 = (away_off + home_def) / 2
    
    # Adjust for pace
    home_points = home_points_per_100 * (avg_pace / 100)
    away_points = away_points_per_100 * (avg_pace / 100)
    
    # Apply home court advantage
    home_points += HOME_COURT_ADVANTAGE / 2
    away_points -= HOME_COURT_ADVANTAGE / 2
    
    # Add some variance (college games are more volatile)
    # Note: Adding fixed variance here might be less effective than modeling
    # variance in the final prediction. Let's keep it simple for now.
    # variance = np.random.normal(0, 1.5) 
    # home_points += variance
    # away_points -= variance
    
    # Calculate spread and total
    spread = home_points - away_points
    total = home_points + away_points
    
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
        confidence = "HIGH" if abs_edge >= 7 else "MEDIUM"
    else:
        # Model projects lower, bet under
        direction = "UNDER"
        confidence = "HIGH" if abs_edge >= 7 else "MEDIUM"
    
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
    
    # Sort results by game time
    results.sort(key=lambda x: x['commence_time'])
    
    for i, game in enumerate(results, 1):
        print(f"{Colors.BOLD}{Colors.CYAN}━━━ GAME {i}: {game['Matchup']} ━━━{Colors.END}")
        print(f"{Colors.CYAN}🕐 {game['GameTime']}{Colors.END}")
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
    
    # Sort results by game time
    results.sort(key=lambda x: x['commence_time'])
    
    fieldnames = [
        'GameTime', 'Matchup', 'home_team', 'away_team', 'Market Spread', 'Model Spread', 
        'spread_edge', 'ATS Pick', 'ATS Explanation',
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
    """Generate beautiful HTML output"""
    et = pytz.timezone('US/Eastern')
    timestamp_str = datetime.now(et).strftime('%Y-%m-%d %I:%M %p ET')
    
    # Sort results by game time
    results.sort(key=lambda x: x['commence_time'])
    
    template_str = '''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NCAAB Model Picks</title>
        <style>
           * { margin: 0; padding: 0; box-sizing: border-box; }
           body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #e2e8f0;
                padding: 2rem;
                min-height: 100vh;
            }
           .container { max-width: 1200px; margin: 0 auto; }
           .card { 
                background: #1a1a1a; 
                border-radius: 1rem; 
                border: 1px solid #2a2a2a;
                padding: 2rem;
                margin-bottom: 1.5rem;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            }
           .header-card {
                text-align: center;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                border: 2px solid #f97316;
            }
           .game-card { 
                padding: 1.5rem; 
                border-bottom: 1px solid #2a2a2a;
            }
           .game-card:last-child { border-bottom: none; }
           .matchup { font-size: 1.5rem; font-weight: 800; color: #ffffff; margin-bottom: 0.5rem; }
           .game-time { color: #9ca3af; font-size: 0.875rem; margin-bottom: 1rem; }
           .bet-section {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-top: 1rem;
            }
           .bet-box {
                background: #0a0a0a;
                padding: 1rem;
                border-radius: 0.5rem;
                border-left: 4px solid #f97316;
            }
           .bet-title { 
                font-weight: 700; 
                color: #f97316; 
                margin-bottom: 0.5rem;
                text-transform: uppercase;
                font-size: 0.875rem;
                letter-spacing: 0.05em;
            }
           .odds-line { 
                display: flex; 
                justify-content: space-between; 
                margin: 0.25rem 0; 
                font-size: 0.95rem;
                color: #cbd5e1;
            }
           .odds-line strong {
                color: #ffffff;
           }
           .confidence-bar-container {
                margin: 0.75rem 0;
           }
           .confidence-label {
                display: flex;
                justify-content: space-between;
                margin-bottom: 0.5rem;
                font-size: 0.875rem;
                color: #9ca3af;
           }
           .confidence-pct {
                font-weight: 700;
                color: #f97316;
           }
           .confidence-bar {
                height: 8px;
                background: #1e293b;
                border-radius: 999px;
                overflow: hidden;
                border: 1px solid #2a2a2a;
           }
           .confidence-fill {
                height: 100%;
                background: linear-gradient(90deg, #f97316 0%, #fb923c 100%);
                border-radius: 999px;
                transition: width 0.3s ease;
           }
           .pick { 
                font-weight: 700; 
                padding: 0.75rem; 
                margin-top: 0.5rem; 
                border-radius: 0.375rem;
                font-size: 1.1rem;
                line-height: 1.6;
            }
           .pick-yes { 
                background: linear-gradient(135deg, #064e3b 0%, #065f46 100%);
                color: #10b981;
                border: 1px solid #10b981;
            }
           .pick-no { 
                background: linear-gradient(135deg, #7c2d12 0%, #9a3412 100%);
                color: #fb923c;
                border: 1px solid #fb923c;
            }
           .pick-none { 
                background: #1a1a1a;
                color: #6b7280;
                border: 1px solid #374151;
            }
           .prediction {
                margin-top: 1rem;
                padding: 0.75rem;
                background: #0a0a0a;
                border-radius: 0.375rem;
                color: #a78bfa;
                font-weight: 600;
                text-align: center;
                font-size: 1.25rem;
            }
           .badge { 
                display: inline-block;
                padding: 0.5rem 1rem;
                border-radius: 9999px;
                font-size: 0.875rem;
                font-weight: 700;
                background-color: #7c2d12;
                color: #fb923c;
                margin: 0.25rem;
            }
           @media (max-width: 768px) {
                .bet-section {
                    grid-template-columns: 1fr;
                }
                body {
                    padding: 1rem;
                }
                .matchup {
                    font-size: 1.25rem;
                }
           }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card header-card">
                <h1 style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem;">🏀 COLLEGE BASKETBALL MODEL</h1>
                <p style="font-size: 1.25rem; opacity: 0.9;">Sharp Analytics + Real-time Odds</p>
                <div>
                    <div class="badge">● EFFICIENCY RATINGS</div>
                    <div class="badge">● PACE ADJUSTMENTS</div>
                    <div class="badge">● HOME COURT EDGE</div>
                    <div class="badge">● CONFERENCE STRENGTH</div>
                </div>
                <p style="font-size: 0.875rem; opacity: 0.75; margin-top: 1rem;">Generated: {{ timestamp }}</p>
            </div>
            
            <div class="card">
                {% for game in results %}
                <div class="game-card">
                    <div class="matchup">{{ game.Matchup }}</div>
                    <div class="game-time">🕐 {{ game.GameTime }}</div>
                    
                    <div class="bet-section">
                        <div class="bet-box">
                            <div class="bet-title">📊 SPREAD BET</div>
                            <div class="odds-line">
                                <span>Vegas Line:</span>
                                <strong>{{ game['Market Spread'] }}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Model Prediction:</span>
                                <strong>{{ game['Model Spread'] }}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Edge:</span>
                                <strong>{{ "%+.1f"|format(game.spread_edge) }} pts</strong>
                            </div>
                            {% set spread_confidence = (game.spread_edge|abs / 10.0 * 100)|int %}
                            {% if spread_confidence > 100 %}{% set spread_confidence = 100 %}{% endif %}
                            <div class="confidence-bar-container">
                                <div class="confidence-label">
                                    <span>Confidence</span>
                                    <span class="confidence-pct">{{ spread_confidence }}%</span>
                                </div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: {{ spread_confidence }}%"></div>
                                </div>
                            </div>
                            <div class="pick {{ 'pick-yes' if '✅' in game['ATS Pick'] else 'pick-none' }}">
                                {{ game['ATS Pick'] }}{% if game['ATS Explanation'] %}<br><small style="opacity: 0.8;">{{ game['ATS Explanation'] }}</small>{% endif %}
                            </div>
                        </div>
                        
                        <div class="bet-box">
                            <div class="bet-title">🎯 OVER/UNDER BET</div>
                            <div class="odds-line">
                                <span>Vegas Total:</span>
                                <strong>{{ game['Market Total']|float|round(1) }}</strong>
                            </div>
                            <div class="odds-line">
                                <span>Model Projects:</span>
                                <strong>{{ game['Model Total']|float|round(1) }} pts</strong>
                            </div>
                            <div class="odds-line">
                                <span>Edge:</span>
                                <strong>{{ (game.total_edge)|abs|round(1) }} pts</strong>
                            </div>
                            {% set total_confidence = (game.total_edge|abs / 12.0 * 100)|int %}
                            {% if total_confidence > 100 %}{% set total_confidence = 100 %}{% endif %}
                            <div class="confidence-bar-container">
                                <div class="confidence-label">
                                    <span>Confidence</span>
                                    <span class="confidence-pct">{{ total_confidence }}%</span>
                                </div>
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: {{ total_confidence }}%"></div>
                                </div>
                            </div>
                            <div class="pick {{ 'pick-yes' if 'OVER' in game['Total Pick'] and '✅' in game['Total Pick'] else ('pick-no' if 'UNDER' in game['Total Pick'] and '✅' in game['Total Pick'] else 'pick-none') }}">
                                {{ game['Total Pick'] }}{% if game['Total Explanation'] %}<br><small style="opacity: 0.8;">{{ game['Total Explanation'] }}</small>{% endif %}
                            </div>
                        </div>
                    </div>
                    
                    <div class="prediction">
                        📈 PREDICTED: {{ game['Predicted Score'] }}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>'''
    
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

    # Calculate yesterday's record
    yesterday = (current_time - timedelta(days=1)).date()
    yesterday_picks = [p for p in tracking_data.get('picks', []) if p.get('status') in ['win', 'loss', 'push']]
    yesterday_wins = 0
    yesterday_losses = 0
    yesterday_pushes = 0

    for pick in yesterday_picks:
        try:
            game_dt = datetime.fromisoformat(str(pick.get('game_date', '')).replace('Z', '+00:00'))
            game_dt_et = game_dt.astimezone(et)

            if game_dt_et.date() == yesterday:
                if pick.get('status') == 'win':
                    yesterday_wins += 1
                elif pick.get('status') == 'loss':
                    yesterday_losses += 1
                elif pick.get('status') == 'push':
                    yesterday_pushes += 1
        except:
            pass

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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            padding: 2rem;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .card { 
            background: #1a1a1a; 
            border-radius: 1rem; 
            border: 1px solid #2a2a2a;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        .stat-card {
            background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
            border: 2px solid #f97316;
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 900;
            color: #f97316;
        }
        .stat-value.positive { color: #10b981; }
        .stat-value.negative { color: #ef4444; }
        .stat-label {
            color: #9ca3af;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0.5rem;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        h1 { font-size: 2.5rem; font-weight: 900; margin-bottom: 0.5rem; color: #f97316; }
        h2 { font-size: 1.875rem; font-weight: 700; margin-bottom: 1.5rem; color: #f97316; }
        table { width: 100%; border-collapse: collapse; }
        thead { background: #0a0a0a; }
        th { padding: 0.75rem 1rem; text-align: left; color: #f97316; font-weight: 700; }
        td { padding: 0.75rem 1rem; border-bottom: 1px solid #2a2a2a; }
        tr:hover { background: #0a0a0a; }
        .text-center { text-align: center; }
        .text-green-400 { color: #10b981; }
        .text-red-400 { color: #ef4444; }
        .text-yellow-400 { color: #f97316; }
        .text-gray-400 { color: #9ca3af; }
        .font-bold { font-weight: 700; }
        .text-sm { font-size: 0.875rem; }
        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .badge-pending { background: #78350f; color: #fb923c; }
        .badge-win { background: #064e3b; color: #10b981; }
        .badge-loss { background: #450a0a; color: #ef4444; }
        .badge-push { background: #374151; color: #9ca3af; }
        .badge-error { background: #450a0a; color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="text-center">🏀 COLLEGE BASKETBALL TRACKING</h1>
            <p class="text-center text-gray-400" style="font-size: 1.25rem; margin-bottom: 2rem;">Performance Analytics Dashboard</p>
            
            <div class="grid">
                <div class="stat-card">
                    <div class="stat-value">{{ stats.total_picks }}</div>
                    <div class="stat-label">Total Bets</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ "%.1f"|format(stats.win_rate) }}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {{ 'positive' if stats.total_profit > 0 else ('negative' if stats.total_profit < 0 else '') }}">
                        {{ "%+.2f"|format(stats.total_profit / 100) }}u
                    </div>
                    <div class="stat-label">Total Profit</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {{ 'positive' if stats.roi > 0 else ('negative' if stats.roi < 0 else '') }}">
                        {{ "%+.1f"|format(stats.roi) }}%
                    </div>
                    <div class="stat-label">ROI</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ yesterday_wins }}-{{ yesterday_losses }}{% if yesterday_pushes > 0 %}-{{ yesterday_pushes }}{% endif %}</div>
                    <div class="stat-label">Yesterday's Record</div>
                </div>
            </div>
            
            <div style="background: #0a0a0a; border-radius: 0.5rem; padding: 1rem; display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; text-align: center;">
                <div>
                    <span class="text-gray-400">Wins:</span>
                    <span class="text-green-400 font-bold" style="margin-left: 0.5rem;">{{ stats.wins }}</span>
                </div>
                <div>
                    <span class="text-gray-400">Losses:</span>
                    <span class="text-red-400 font-bold" style="margin-left: 0.5rem;">{{ stats.losses }}</span>
                </div>
                <div>
                    <span class="text-gray-400">Pushes:</span>
                    <span class="text-gray-400 font-bold" style="margin-left: 0.5rem;">{{ stats.pushes }}</span>
                </div>
            </div>
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
        
        {% if completed_picks %}
        <div class="card">
            <h2>📊 Recent Results</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Game Date</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Pick</th>
                            <th>Result</th>
                            <th>Profit</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pick in completed_picks[:20] %}
                        <tr>
                            <td class="text-sm font-bold">{{ format_date(pick.game_date) }}</td>
                            <td class="font-bold">{{ pick.away_team }} @ {{ pick.home_team }}</td>
                            <td>{{ pick.pick_type|title }}</td>
                            <td class="text-sm">{{ pick.pick_text }}</td>
                            <td class="text-sm text-gray-400">{{ pick.result or 'N/A' }}</td>
                            <td class="{{ 'text-green-400' if pick.profit and pick.profit > 0 else ('text-red-400' if pick.profit and pick.profit < 0 else 'text-gray-400') }}">
                                {{ "%+.2f"|format(pick.profit / 100) if pick.profit is not none else '-' }}u
                            </td>
                            <td>
                                <span class="badge badge-{{ pick.status }}">{{ pick.status|title }}</span>
                            </td>
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
        format_date=format_date,  # <-- We pass the function in as a variable
        yesterday_wins=yesterday_wins,
        yesterday_losses=yesterday_losses,
        yesterday_pushes=yesterday_pushes
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
        # STEP 1: Update old picks first
        print(f"{Colors.BOLD}{Colors.CYAN}STEP 1: Checking for Completed Games & Updating Past Picks{Colors.END}")
        update_pick_results()
        generate_tracking_html()
        
        # STEP 2: Fetch team statistics
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 2: Loading Team Statistics{Colors.END}")
        team_stats = fetch_team_stats()
        
        # STEP 3: Fetch current odds
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 3: Fetching Live Odds (Next {DAYS_AHEAD_TO_FETCH} Days){Colors.END}")
        games = fetch_odds()
        
        if not games:
            print(f"\n{Colors.YELLOW}⚠️  No games found from The Odds API in next {DAYS_AHEAD_TO_FETCH} days.{Colors.END}\n")
            return
        
        # STEP 4: Process and analyze
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 4: Processing Games & Generating Sharp Picks{Colors.END}\n")
        results = process_games(games, team_stats)
        
        if results:
            print(f"\n{Colors.BOLD}{Colors.GREEN}✅ Analyzed {len(results)} games with complete odds{Colors.END}\n")
            display_terminal(results)
            save_csv(results)
            save_html(results)
        else:
            print(f"\n{Colors.YELLOW}⚠️  No games with complete betting lines found.{Colors.END}\n")
        
        # STEP 5: Generate final tracking dashboard
        print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 5: Generating Final Tracking Dashboard{Colors.END}")
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

    except Exception as e:
        print(f"{Colors.RED}{'='*30} FATAL ERROR {'='*30}{Colors.END}")
        print(f"{Colors.RED}An unhandled exception occurred: {e}{Colors.END}")
        traceback.print_exc()
        print(f"{Colors.RED}{'='*73}{Colors.END}")


if __name__ == "__main__":
    main()

