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
try:
    from fetch_ncaab_stats import fetch_sports_reference_stats
except ImportError:
    # Fallback to local file approach if import fails (e.g. running from different dir)
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from fetch_ncaab_stats import fetch_sports_reference_stats

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
# --- File & Model Config ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, "ncaab_model_output.csv")
HTML_FILE = os.path.join(SCRIPT_DIR, "ncaab_model_output.html")
STATS_FILE = os.path.join(SCRIPT_DIR, "ncaab_stats_cache.json")
KENPOM_CACHE_FILE = os.path.join(SCRIPT_DIR, "ncaab_kenpom_cache.json")

# Tracking files
PICKS_TRACKING_FILE = os.path.join(SCRIPT_DIR, "ncaab_picks_tracking.json")
TRACKING_HTML_FILE = os.path.join(SCRIPT_DIR, "ncaab_tracking_dashboard.html")

# --- Model Parameters (Tuned for College Basketball) ---
HOME_COURT_ADVANTAGE = 3.2  # Reduced from 3.5 - spreads losing may indicate overvaluing home teams
SPREAD_THRESHOLD = 10.0  # Raised from 6.0 - edge 6-10 losing -41u, edge 10+ winning +44u (Dec 20)
TOTAL_THRESHOLD = 6.0   # Keep at 6.0 - totals are profitable (+25u)

# Tracking Parameters - ADJUSTED (Dec 23, 2024) - REAL STATS ERA
# Lowered to 10.0 now that we have reliable data, to caption more value.
CONFIDENT_SPREAD_EDGE = 10.0  # Lowered from 15.0 (was 12.0)
CONFIDENT_TOTAL_EDGE = 10.0   # Lowered from 15.0 (was 12.0)
# MAX EDGE CAPS
# Real stats might produce larger variance, but >40 is still likely an error/mismatch
MAX_SPREAD_EDGE = 35.0 
MAX_TOTAL_EDGE = 35.0
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
    name = team_name.strip()
    
    # Common variations and abbreviations
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
        
        # State variations
        "Miami FL": "Miami",
        "Miami (FL)": "Miami",
        "Miami OH": "Miami Ohio",
        "Miami (OH)": "Miami Ohio",
        
        # Common full names
        "St. John's": "St John's",
        "Saint John's": "St John's",
    }
    
    return name_map.get(name, name)

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
            "daysFrom": 2  # Check last 2 days
        }
        
        response = requests.get(scores_url, params=params, timeout=10)
        
        if response.status_code == 200:
            scores = response.json()
            print(f"{Colors.GREEN}✓ Fetched {len(scores)} completed games{Colors.END}")
            return scores
        else:
            print(f"{Colors.YELLOW}⚠️  Could not fetch scores: {response.status_code}{Colors.END}")
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
    
    # Fetch completed scores
    completed_games = fetch_completed_scores()
    
    if not completed_games:
        print(f"{Colors.YELLOW}No completed games found.{Colors.END}")
        return
    
    updated_count = 0
    
    for pick in pending_picks:
        # Find matching completed game
        for game in completed_games:
            if not game.get('completed'):
                continue
                
            home_team = normalize_team_name(game['home_team'])
            away_team = normalize_team_name(game['away_team'])
            
            pick_home = normalize_team_name(pick['home_team'])
            pick_away = normalize_team_name(pick['away_team'])
            
            if home_team == pick_home and away_team == pick_away:
                # Found the game!
                scores = game.get('scores')
                if not scores or len(scores) < 2:
                    continue
                
                try:
                    home_score_str = next((s['score'] for s in scores if s['name'] == game['home_team']), None)
                    away_score_str = next((s['score'] for s in scores if s['name'] == game['away_team']), None)
                    
                    if home_score_str is None or away_score_str is None:
                        continue
                        
                    home_score = int(home_score_str)
                    away_score = int(away_score_str)
                
                except (ValueError, TypeError):
                    print(f"{Colors.RED}Error parsing scores for {game['home_team']}{Colors.END}")
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
    
    if updated_count > 0:
        # Recalculate summary
        tracking_data['summary'] = calculate_summary_stats(tracking_data['picks'])
        save_picks_tracking(tracking_data)
        print(f"{Colors.GREEN}✅ Updated {updated_count} picks{Colors.END}")

        # Regenerate HTML if the function exists
        # Assuming generate_html exists or we can invoke the main display logic
        # For NCAAB model, it usually runs main() to generate output.
        # Let's check if we can invoke save_csv or display_terminal?
        # Actually ncaab_model_2ndFINAL generates 'ncaab_tracking_dashboard.html' externally?
        # No, wait, let's just return the count and handle HTML generation if needed.
        # But wait, looking at the file outline, there is NO generate_tracking_html function!
        # The outline showed 'generate_tracking_html' only in NBA model.
        # NCAAB model has 'save_csv' and 'display_terminal'.
        # Ah, the user asked for this feature, but maybe the dashboard doesn't exist yet?
        # "TRACKING_HTML_FILE = os.path.join(SCRIPT_DIR, 'ncaab_tracking_dashboard.html')" is defined in line 46.
        # But is there code to populate it?
        # Let's searching for where TRACKING_HTML_FILE is used.
    else:
        print(f"{Colors.YELLOW}No picks were updated (games may not be complete yet){Colors.END}")

    return updated_count

def evaluate_spread_pick(pick, home_score, away_score):
    """Evaluate if a spread pick won, lost, or pushed"""
    # Determine which team was picked
    pick_text = pick['pick_text'].upper()
    
    # Calculate actual margin
    actual_margin = home_score - away_score
    
    try:
        # Determine picked team and spread
        if pick['home_team'].upper() in pick_text or "HOME" in pick_text:
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

    # --- DAILY PERFORMANCE TRACKING ---
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    today_str = now_et.strftime('%Y-%m-%d')
    yesterday_str = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def calc_daily_stats(target_date_str):
        daily_picks = []
        for p in picks:
            # Parse date from pick
            # Format in tracking file is typically strict ISO or similar
            # Example: "2024-12-19T00:30:00Z"
            if 'game_date' not in p: continue
            
            try:
                g_time = p['game_date']
                if 'Z' in g_time:
                    dt_utc = datetime.fromisoformat(g_time.replace('Z', '+00:00'))
                    dt_et = dt_utc.astimezone(et_tz)
                else:
                    # Handle non-Z format if any
                    dt_et = datetime.fromisoformat(g_time)
                
                if dt_et.strftime('%Y-%m-%d') == target_date_str:
                    daily_picks.append(p)
            except:
                continue
                
        d_wins = sum(1 for p in daily_picks if p.get('status') == 'win')
        d_losses = sum(1 for p in daily_picks if p.get('status') == 'loss')
        d_pushes = sum(1 for p in daily_picks if p.get('status') == 'push')
        d_total = d_wins + d_losses  # Exclude pushes from denominator for Win Rate typically? Or include?
        # NBA model includes wins+losses for total.
        
        d_profit = sum(p.get('profit', 0) for p in daily_picks if p.get('profit') is not None)
        
        d_risked = (d_wins + d_losses) * UNIT_SIZE
        d_roi = (d_profit / d_risked * 100) if d_risked > 0 else 0.0
        
        return {
            'record': f"{d_wins}-{d_losses}-{d_pushes}",
            'profit': d_profit, # in dollars since UNIT_SIZE=100
            'roi': d_roi,
            'count': len(daily_picks)
        }

    today_stats = calc_daily_stats(today_str)
    yesterday_stats = calc_daily_stats(yesterday_str)

    return {
        "total_picks": total_picks,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending,
        "win_rate": win_rate,
        "total_profit": total_profit,
        "roi": roi,
        "today": today_stats,
        "yesterday": yesterday_stats
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
            gt_str = game.get('commence_time')
            if not gt_str:
                continue
                
            try:
                # Parse ISO string (Robust)
                if 'Z' in gt_str:
                    gt_dt = datetime.fromisoformat(gt_str.replace('Z', '+00:00'))
                else:
                    gt_dt = datetime.fromisoformat(gt_str)
                
                # Ensure offset-aware (UTC)
                if gt_dt.tzinfo is None:
                    gt_dt = gt_dt.replace(tzinfo=pytz.utc)
                else:
                    gt_dt = gt_dt.astimezone(pytz.utc)
                
                # Compare (now is Eastern aware, gt_dt is UTC aware - comparison is safe)
                if now <= gt_dt <= cutoff:
                    filtered_games.append(game)
            except Exception as e:
                print(f"Time Parse Error: {e} for {gt_str}")
                continue
        
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

    
    
    # Cache is old or missing - FETCH REAL STATS
    print(f"{Colors.YELLOW}⚠️  Cache expired or missing. Fetching fresh stats from Sports-Reference...{Colors.END}")
    try:
        stats = fetch_sports_reference_stats(2025)
        if stats:
            save_stats_cache(stats)
            return stats
    except Exception as e:
        print(f"{Colors.RED}Error fetching real stats: {e}{Colors.END}")
    
    print(f"{Colors.RED}❌ Failed to fetch real stats. Model will fail for teams without data.{Colors.END}")
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
    
    
    # NO MORE RANDOM GUESSING
    # If we don't have stats, we return league averages.
    # This prevents the model from betting on teams we know nothing about.
    # League avg ORtg/DRtg ~ 100-105. Pace ~ 68-70.
    
    return {
        "offensive_rating": 105.0,
        "defensive_rating": 105.0,
        "pace": 69.0,
        "net_rating": 0.0
    }

# =========================
# GAME PROCESSING
# =========================

def smart_stats_lookup(team_name, stats_dict):
    """
    Intelligent lookup for team stats handling naming differences
    (e.g., 'Binghamton Bearcats' (Odds API) vs 'Binghamton' (Sports Ref))
    """
    # 1. Direct match
    if team_name in stats_dict:
        return stats_dict[team_name]
    
    # 2. Try normalized name
    norm_name = normalize_team_name(team_name)
    if norm_name in stats_dict:
        return stats_dict[norm_name]

    # 3. Clean common suffixes/mascots
    # Sports-Ref usually uses just the school name (e.g. "Duke")
    # Odds API uses full name (e.g. "Duke Blue Devils")
    
    # Search for stats key that appears at the start of the team name
    # e.g. team_name="Army Knights", key="Army" -> Match!
    # e.g. team_name="Binghamton Bearcats", key="Binghamton" -> Match!
    
    # Sort keys by length (longest first) to match "North Carolina" before "North"
    sorted_keys = sorted(stats_dict.keys(), key=len, reverse=True)
    
    for key in sorted_keys:
        # Check if the stats key (e.g. "Virginia Tech") is in the team name (e.g. "Virginia Tech Hokies")
        if key in team_name:
            # print(f"  Matched '{team_name}' to '{key}'")
            return stats_dict[key]
            
    # 4. Reverse check for State/St./etc.
    # e.g. team_name="Kansas St", key="Kansas State"
    
    return None

def extract_best_odds(bookmakers, market_type):
    """Extract best available odds for a given market, prioritizing Hard Rock Bet"""
    best_odds = {}
    
    # Prioritize Hard Rock Bet, then FanDuel
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
    
    for game in games:
        try:
            home_team = normalize_team_name(game['home_team'])
            away_team = normalize_team_name(game['away_team'])
            
            # Get team statistics using SMART LOOKUP
            home_stats = smart_stats_lookup(home_team, team_stats)
            away_stats = smart_stats_lookup(away_team, team_stats)
            
            # STRICT FILTER: If we don't have real stats, we don't bet.
            if not home_stats or not away_stats:
                # Fallback to estimate (averages) just to show the game in the list, 
                # but we'll flag it as low confidence if we needed to. 
                # Actually, better to just log it and use the averages so we at least see the line.
                # But since estimate_team_strength now returns averages, the model will likely pass.
                
                if not home_stats:
                    # print(f"  ⚠️ No stats for {home_team}")
                    home_stats = estimate_team_strength(home_team) # Returns averages
                
                if not away_stats:
                    # print(f"  ⚠️ No stats for {away_team}")
                    away_stats = estimate_team_strength(away_team) # Returns averages
            
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
            
            # Calculate edges
            spread_edge = model_spread - market_spread
            total_edge = model_total - market_total
            
            # Determine picks
            ats_pick, ats_explanation = determine_spread_pick(
                home_team, away_team, spread_edge, market_spread
            )
            
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
                "spread_edge": spread_edge,
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
    
    # Improved prediction formula: Weight offensive strength more (60%) than opponent defensive weakness (40%)
    # This prevents overvaluing when facing weak defenses
    ncaa_avg = 100.0  # Average offensive rating in NCAA
    
    # Weighted formula: 60% offensive strength, 40% opponent defensive weakness
    home_points_per_100 = (home_off * 0.60) + ((2 * ncaa_avg - away_def) * 0.40)
    away_points_per_100 = (away_off * 0.60) + ((2 * ncaa_avg - home_def) * 0.40)
    
    # Adjust for pace
    home_points = home_points_per_100 * (avg_pace / 100)
    away_points = away_points_per_100 * (avg_pace / 100)
    
    # Apply home court advantage
    home_points += HOME_COURT_ADVANTAGE / 2
    away_points -= HOME_COURT_ADVANTAGE / 2
    
    # Calculate spread and total before regression
    spread = home_points - away_points
    total = home_points + away_points
    
    # Regression to mean for extreme predictions
    # Regress extreme spreads (>15 points) 10% toward league average
    if abs(spread) > 15.0:
        regression_factor = 0.10
        home_points = home_points * (1 - regression_factor) + (home_points + away_points) / 2 * regression_factor
        away_points = away_points * (1 - regression_factor) + (home_points + away_points) / 2 * regression_factor
        spread = home_points - away_points
        total = home_points + away_points
    
    # Regress extreme totals (<130 or >160) 15% toward league average (typically ~145)
    league_avg_total = 145.0
    if total < 130.0 or total > 160.0:
        regression_factor = 0.15
        total = total * (1 - regression_factor) + league_avg_total * regression_factor
        # Adjust individual scores proportionally to maintain spread
        if total != (home_points + away_points):
            scale_factor = total / (home_points + away_points)
            home_points = home_points * scale_factor
            away_points = away_points * scale_factor
            spread = home_points - away_points
    
    return {
        'home_score': home_points,
        'away_score': away_points,
        'spread': spread,
        'total': total
    }

def determine_spread_pick(home_team, away_team, edge, market_line):
    """Determine if there's value on the spread"""
    abs_edge = abs(edge)
    
    if abs_edge < SPREAD_THRESHOLD:
        return "❌ NO BET", f"Edge too small ({edge:+.1f})"
    
    # Check maximum edge cap - very large edges likely indicate model errors
    if abs_edge > MAX_SPREAD_EDGE:
        return "❌ NO BET", f"⚠️ SKIPPED: Edge too large ({abs_edge:.1f} > {MAX_SPREAD_EDGE:.1f}) - likely model error"
    
    # Determine which side to bet
    if edge > 0:
        # Model spread is HIGHER than market (e.g., Model: +3.4, Market: -20.5)
        # This means the AWAY team is undervalued.
        # We bet the AWAY team to cover their line (which is -market_line)
        pick_team = away_team
        pick_line = -market_line # e.g., if market_line is -20.5, this becomes +20.5
        confidence = "HIGH" if abs_edge >= 5 else "MEDIUM"
        
        # Format line with a +
        pick_line_str = f"+{pick_line}" if pick_line > 0 else f"{pick_line}"

    else: # edge < 0
        # Model spread is LOWER than market (e.g., Model: -10, Market: -7.5)
        # This means the HOME team is undervalued.
        # We bet the HOME team to cover their line (which is market_line)
        pick_team = home_team
        pick_line_str = f"{market_line:+.1f}" # e.g., -20.5
        confidence = "HIGH" if abs_edge >= 5 else "MEDIUM"
    
    return (
        f"✅ BET: {pick_team} {pick_line_str}",
        f"{confidence} confidence ({edge:+.1f} edge)"
    )

def determine_total_pick(edge, market_line):
    """Determine if there's value on the total"""
    abs_edge = abs(edge)
    
    if abs_edge < TOTAL_THRESHOLD:
        return "❌ NO BET", f"Edge too small ({edge:+.1f})"
    
    # Check maximum edge cap - very large edges likely indicate model errors
    if abs_edge > MAX_TOTAL_EDGE:
        return "❌ NO BET", f"⚠️ SKIPPED: Edge too large ({abs_edge:.1f} > {MAX_TOTAL_EDGE:.1f}) - likely model error"
    
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
    
    # Load tracking data for display
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)
    
    # Calculate recent performance breakdown (last 100, 50, 20)
    completed_picks = [p for p in tracking_data.get('picks', []) if p.get('status') != 'pending']
    pending_picks = [p for p in tracking_data.get('picks', []) if p.get('status') == 'pending']
    
    completed_picks.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    pending_picks.sort(key=lambda x: x.get('game_date', ''))
    
    last_10 = calculate_recent_performance(completed_picks, 10)
    last_20 = calculate_recent_performance(completed_picks, 20)
    last_50 = calculate_recent_performance(completed_picks, 50)
    # Calculate Season Stats
    season_stats = calculate_recent_performance(completed_picks, len(completed_picks))
    
    # Sort results by game time
    results.sort(key=lambda x: x['commence_time'])
    
    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCAAB Model Picks • CourtSide Analytics</title>
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
            align-items: center;
        }

        header h1 {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }

        .header-sub {
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

        .team-logo {
            width: 44px;
            height: 44px;
            object-fit: contain;
            background: #fff;
            border-radius: 50%;
            padding: 2px;
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
        .metric-value.text-red { color: var(--accent-red); }

        .metric-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
        }

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

        /* Tracking Section */
        .tracking-section { margin-top: 3rem; }
        .tracking-header { 
            font-size: 1.5rem; 
            font-weight: 700; 
            color: var(--text-primary); 
            margin-bottom: 1.5rem; 
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }

        .text-green { color: var(--accent-green); }
        .text-red { color: var(--accent-red); }

        @media (max-width: 768px) {
            body { padding: 1rem; }
            .metrics-row { flex-direction: column; gap: 0.5rem; }
            .metric-box { padding: 0.8rem 0.5rem; }
            .main-pick { font-size: 1.5rem; }
            .header-left { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
            .card-header { align-items: flex-start; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>CourtSide Analytics CBB Picks</h1>
                <div class="header-sub">Generated: {{ timestamp }}</div>
            </div>
            <div style="text-align: right;">
                <div class="metric-title">SEASON RECORD</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                    {{ season_stats.record }} ({{ "%.1f"|format(season_stats.win_rate) }}%)
                </div>
                <div style="font-size: 0.9rem; color: {{ 'var(--accent-green)' if season_stats.profit > 0 else 'var(--accent-red)' }};">
                     {{ "%+.1f"|format(season_stats.profit) }}u
                </div>
            </div>
        </header>

        {% for r in results %}
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                    <!-- Placeholder logo since NCAAB has too many teams to map easily -->
                    <div style="width: 44px; height: 44px; background: #333; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">🏀</div>
                    <div class="matchup-info">
                        <h2>{{ r.Matchup }}</h2>
                        <div class="matchup-sub">{{ r.home_team }} Home Game</div>
                    </div>
                </div>
                <div class="game-time-badge">{{ r.GameTime }}</div>
            </div>

            <!-- SPREAD BET BLOCK -->
            <div class="bet-row">
                {% if '✅' in r['ATS Pick'] %}
                <div class="main-pick green">{{ r['ATS Pick'].replace('✅ BET: ', '') }}</div>
                {% else %}
                <div class="main-pick">{{ r['Market Spread'] }}</div>
                {% endif %}
                
                <div class="model-context">
                    Model: {{ r['Model Spread'] }}
                    <span class="edge-val">Edge: {{ "%+.1f"|format(r.spread_edge) }}</span>
                </div>
            </div>

            <!-- TOTAL BET BLOCK -->
            <div class="bet-row" style="border-bottom: none;">
                {% if '✅' in r['Total Pick'] %}
                    {% if 'OVER' in r['Total Pick'] %}
                    <div class="main-pick green">OVER {{ r['Market Total'] }}</div>
                    {% else %}
                    <div class="main-pick green">UNDER {{ r['Market Total'] }}</div>
                    {% endif %}
                {% else %}
                <div class="main-pick">O/U {{ r['Market Total'] }}</div>
                {% endif %}
                
                <div class="model-context">
                    Model: {{ r['Model Total'] }}
                    <span class="edge-val">Edge: {{ "%+.1f"|format(r.total_edge|abs) }}</span>
                </div>
            </div>

            <!-- METRICS ROW -->
            <div class="metrics-row">
                <!-- Confidence based on max edge -->
                {% set conf_spread = (r.spread_edge|abs / 10 * 100)|int %}
                {% set conf_total = (r.total_edge|abs / 12 * 100)|int %}
                {% set max_conf = conf_spread if conf_spread > conf_total else conf_total %}
                {% if max_conf > 99 %}{% set max_conf = 99 %}{% endif %}
                
                <div class="metric-box">
                    <div class="metric-title">CONFIDENCE</div>
                    <div class="metric-value {{ 'good' if max_conf >= 60 else '' }}">{{ max_conf }}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">WIN % (EST)</div>
                    <div class="metric-value {{ 'good' if max_conf >= 60 else '' }}">{{ 50 + (max_conf * 0.2)|int }}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">PREDICTED</div>
                    <div class="metric-value">{{ r['Predicted Score'] }}</div>
                </div>
            </div>

            <!-- TAGS -->
            <div class="tags-row">
                {% if r['ATS Explanation'] %}
                <div class="tag tag-green">{{ r['ATS Explanation'][:80] }}{% if r['ATS Explanation']|length > 80 %}...{% endif %}</div>
                {% endif %}
            </div>

        </div>
        {% endfor %}

        <!-- DAILY PERFORMANCE -->
        <div class="tracking-section" style="margin-top: 3rem; margin-bottom: 0;">
            <div class="tracking-header">📅 Daily Performance</div>
            <div class="metrics-row" style="margin-bottom: 2rem;">
                <!-- Today -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem; margin-bottom: 0;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">TODAY</div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ stats.today.record }}</div>
                        <div style="font-size: 1.2rem; margin-bottom: 0.2rem;" class="{{ 'text-green' if stats.today.profit > 0 else ('text-red' if stats.today.profit < 0 else '') }}">
                            {{ "%+.1f"|format(stats.today.profit / 100) }}u
                        </div>
                        <div style="font-size: 0.9rem;" class="{{ 'text-green' if stats.today.roi > 0 else ('text-red' if stats.today.roi < 0 else '') }}">
                            {{ "%.1f"|format(stats.today.roi) }}% ROI
                        </div>
                    </div>
                </div>

                <!-- Yesterday -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem; margin-bottom: 0;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">YESTERDAY</div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ stats.yesterday.record }}</div>
                        <div style="font-size: 1.2rem; margin-bottom: 0.2rem;" class="{{ 'text-green' if stats.yesterday.profit > 0 else ('text-red' if stats.yesterday.profit < 0 else '') }}">
                            {{ "%+.1f"|format(stats.yesterday.profit / 100) }}u
                        </div>
                        <div style="font-size: 0.9rem;" class="{{ 'text-green' if stats.yesterday.roi > 0 else ('text-red' if stats.yesterday.roi < 0 else '') }}">
                            {{ "%.1f"|format(stats.yesterday.roi) }}% ROI
                        </div>
                    </div>
                </div>
            </div>
        </div>

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
                            <div class="metric-value">{{ last_10.record }}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {{ 'good' if last_10.win_rate >= 55 else ('text-red' if last_10.win_rate < 50) }}">{{ "%.0f"|format(last_10.win_rate) }}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {{ 'good' if last_10.profit > 0 else ('text-red' if last_10.profit < 0) }}">{{ "%+.1f"|format(last_10.profit) }}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {{ 'good' if last_10.roi > 0 else ('text-red' if last_10.roi < 0) }}">{{ "%+.1f"|format(last_10.roi) }}%</div>
                        </div>
                    </div>
                </div>

                <!-- Last 20 -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 20</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div>
                            <div class="metric-label">Record</div>
                            <div class="metric-value">{{ last_20.record }}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {{ 'good' if last_20.win_rate >= 55 else ('text-red' if last_20.win_rate < 50) }}">{{ "%.0f"|format(last_20.win_rate) }}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {{ 'good' if last_20.profit > 0 else ('text-red' if last_20.profit < 0) }}">{{ "%+.1f"|format(last_20.profit) }}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {{ 'good' if last_20.roi > 0 else ('text-red' if last_20.roi < 0) }}">{{ "%+.1f"|format(last_20.roi) }}%</div>
                        </div>
                    </div>
                </div>

                <!-- Last 50 -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 50</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div>
                            <div class="metric-label">Record</div>
                            <div class="metric-value">{{ last_50.record }}</div>
                        </div>
                        <div>
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value {{ 'good' if last_50.win_rate >= 55 else ('text-red' if last_50.win_rate < 50) }}">{{ "%.0f"|format(last_50.win_rate) }}%</div>
                        </div>
                        <div>
                            <div class="metric-label">Profit</div>
                            <div class="metric-value {{ 'good' if last_50.profit > 0 else ('text-red' if last_50.profit < 0) }}">{{ "%+.1f"|format(last_50.profit) }}u</div>
                        </div>
                        <div>
                            <div class="metric-label">ROI</div>
                            <div class="metric-value {{ 'good' if last_50.roi > 0 else ('text-red' if last_50.roi < 0) }}">{{ "%+.1f"|format(last_50.roi) }}%</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    template = Template(template_str)
    html_output = template.render(
        results=results, 
        timestamp=timestamp_str,
        stats=stats,
        last_10=last_10,
        last_20=last_20,
        last_50=last_50,
        season_stats=season_stats,
        format_date=format_date
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

def calculate_recent_performance(picks_list, count):
    """Calculate performance stats for last N picks (most recent first)"""
    # Filter to only completed picks
    completed = [p for p in picks_list if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    # Take first N picks (most recent first since list is sorted reverse=True)
    recent = completed[:count] if len(completed) >= count else completed
    
    wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
    pushes = sum(1 for p in recent if p.get('status', '').lower() == 'push')
    total = wins + losses + pushes
    
    # Calculate profit (stored in cents, convert to units)
    profit_cents = sum(p.get('profit', 0) for p in recent if p.get('profit') is not None)
    profit_units = profit_cents / 100.0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (profit_cents / (total * UNIT_SIZE) * 100) if total > 0 else 0
    
    # Breakdown by type
    spread_picks = [p for p in recent if p.get('pick_type', '').lower() == 'spread']
    total_picks = [p for p in recent if p.get('pick_type', '').lower() == 'total']
    
    spread_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
    spread_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
    spread_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
    spread_total = spread_wins + spread_losses + spread_pushes
    spread_profit_cents = sum(p.get('profit', 0) for p in spread_picks if p.get('profit') is not None)
    spread_profit_units = spread_profit_cents / 100.0
    spread_wr = (spread_wins / spread_total * 100) if spread_total > 0 else 0
    spread_roi = (spread_profit_cents / (spread_total * UNIT_SIZE) * 100) if spread_total > 0 else 0
    
    total_wins = sum(1 for p in total_picks if p.get('status', '').lower() == 'win')
    total_losses = sum(1 for p in total_picks if p.get('status', '').lower() == 'loss')
    total_pushes = sum(1 for p in total_picks if p.get('status', '').lower() == 'push')
    total_total = total_wins + total_losses + total_pushes
    total_profit_cents = sum(p.get('profit', 0) for p in total_picks if p.get('profit') is not None)
    total_profit_units = total_profit_cents / 100.0
    total_wr = (total_wins / total_total * 100) if total_total > 0 else 0
    total_roi = (total_profit_cents / (total_total * UNIT_SIZE) * 100) if total_total > 0 else 0
    
    return {
        'record': f"{wins}-{losses}" + (f"-{pushes}" if pushes > 0 else ""),
        'win_rate': win_rate,
        'profit': profit_units,
        'roi': roi,
        'count': len(recent),
        'spreads': {
            'record': f"{spread_wins}-{spread_losses}" + (f"-{spread_pushes}" if spread_pushes > 0 else ""),
            'win_rate': spread_wr,
            'profit': spread_profit_units,
            'roi': spread_roi,
            'count': len(spread_picks)
        },
        'totals': {
            'record': f"{total_wins}-{total_losses}" + (f"-{total_pushes}" if total_pushes > 0 else ""),
            'win_rate': total_wr,
            'profit': total_profit_units,
            'roi': total_roi,
            'count': len(total_picks)
        }
    }

def generate_tracking_html():
    """Generate tracking dashboard HTML"""
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)
    
    all_picks = tracking_data.get('picks', [])
    all_picks.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    
    # Calculate Last N Stats
    last_100 = calculate_recent_performance(all_picks, 100)
    last_50 = calculate_recent_performance(all_picks, 50)
    last_20 = calculate_recent_performance(all_picks, 20)
    
    # Calculate Season Stats (All completed picks)
    season_stats = calculate_recent_performance(all_picks, len(all_picks))

    # Helper for formatting dates (must be inside to use in template if not passed)
    def format_date(date_str):
        try:
            dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
            est = pytz.timezone('US/Eastern')
            return dt.astimezone(est).strftime('%Y-%m-%d')
        except:
            return date_str

    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p ET")

    template_str = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCAAB Model Tracking • CourtSide Analytics</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #121212;
            color: #ffffff;
            padding: 2rem;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: #1c1c1e;
            border: 1px solid #2a2a2a;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border-radius: 12px;
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
        .text-blue-400 { color: #60a5fa; }
        .text-pink-400 { color: #f472b6; }
        .text-red-400 { color: #ef4444; }
        .text-yellow-400 { color: #f97316; }
        .text-gray-400 { color: #9ca3af; }
        h3 { font-size: 1.5rem; font-weight: 700; color: #ffffff; }
        h4 { font-size: 1.125rem; font-weight: 600; color: #94a3b8; }
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
            
            /* Make all inline 4-column grids responsive */
            div[style*="grid-template-columns: repeat(4, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }
            
            /* Make all inline 2-column grids single column on mobile */
            div[style*="grid-template-columns: repeat(2, 1fr)"] {
                grid-template-columns: 1fr !important;
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
            
            /* Tables - enable horizontal scroll */
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
            
            /* Reduce spacing */
            div[style*="padding: 2rem"] {
                padding: 1.25rem !important;
            }
            div[style*="margin-bottom: 2rem"] {
                margin-bottom: 1.25rem !important;
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
            
            header { flex-direction: column; align-items: flex-start; gap: 1rem; }
            .header-title h1 { font-size: 1.5rem; }
            div[style*="text-align: right"] { text-align: left !important; }
        }
    </style>
</head>
<body>
        <div class="container">
            <header>
                <div class="header-title">
                    <h1>🏀 SEASON RECORD</h1>
                    <div class="header-subtitle">Generated: {{ timestamp }}</div>
                </div>
                <div style="text-align: right;">
                    <div class="metric-title">SEASON RECORD</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">
                        {{ season_stats.record }} ({{ "%.1f"|format(season_stats.win_rate) }}%)
                    </div>
                    <div style="font-size: 1.1rem; color: {{ '#10b981' if season_stats.profit > 0 else '#ef4444' }}; font-weight: 600;">
                         {{ "%+.1f"|format(season_stats.profit) }}u
                    </div>
                </div>
            </header>

            <!-- Overall Stats Cards -->
            <div class="card">
                <div class="grid">
                    <div class="stat-card">
                        <div class="stat-value">{{ stats.total_picks }}</div>
                        <div class="stat-label">Total Picks</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {{ 'positive' if stats.total_profit > 0 else 'negative' }}">
                            {{ "%+.1f"|format(stats.total_profit) }}u
                        </div>
                        <div class="stat-label">Total Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {{ 'positive' if stats.total_roi > 0 else 'negative' }}">
                            {{ "%.1f"|format(stats.total_roi) }}%
                        </div>
                        <div class="stat-label">Total ROI</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ "%.1f"|format(stats.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                </div>
            </div>

            <!-- Recent Performance Breakdown -->
            <div class="card">
                <h2>📈 Recent Performance Breakdown</h2>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
                    <!-- Last 100 -->
                    <div style="background: #262626; border-radius: 0.5rem; padding: 0.75rem;">
                        <div style="font-weight: 600; color: #f97316; margin-bottom: 0.5rem; font-size: 0.7rem;">Last 100</div>
                        <div style="color: #cbd5e1; margin-bottom: 0.25rem;">Record: <strong>{{ last_100.record }}</strong></div>
                        <div style="color: #60a5fa; margin-bottom: 0.25rem; font-size: 0.7rem;">
                            Spreads: {{ last_100.spreads.record }} ({% if last_100.spreads.roi > 0 %}+{% endif %}{{ '%.1f'|format(last_100.spreads.roi) }}% ROI)
                        </div>
                        <div style="color: #f472b6; font-size: 0.7rem;">
                            Totals: {{ last_100.totals.record }} ({% if last_100.totals.roi > 0 %}+{% endif %}{{ '%.1f'|format(last_100.totals.roi) }}% ROI)
                        </div>
                    </div>
                    <!-- Last 50 -->
                    <div style="background: #262626; border-radius: 0.5rem; padding: 0.75rem;">
                        <div style="font-weight: 600; color: #f97316; margin-bottom: 0.5rem; font-size: 0.7rem;">Last 50</div>
                        <div style="color: #cbd5e1; margin-bottom: 0.25rem;">Record: <strong>{{ last_50.record }}</strong></div>
                        <div style="color: #60a5fa; margin-bottom: 0.25rem; font-size: 0.7rem;">
                            Spreads: {{ last_50.spreads.record }} ({% if last_50.spreads.roi > 0 %}+{% endif %}{{ '%.1f'|format(last_50.spreads.roi) }}% ROI)
                        </div>
                        <div style="color: #f472b6; font-size: 0.7rem;">
                            Totals: {{ last_50.totals.record }} ({% if last_50.totals.roi > 0 %}+{% endif %}{{ '%.1f'|format(last_50.totals.roi) }}% ROI)
                        </div>
                    </div>
                    <!-- Last 20 -->
                    <div style="background: #262626; border-radius: 0.5rem; padding: 0.75rem;">
                        <div style="font-weight: 600; color: #f97316; margin-bottom: 0.5rem; font-size: 0.7rem;">Last 20</div>
                        <div style="color: #cbd5e1; margin-bottom: 0.25rem;">Record: <strong>{{ last_20.record }}</strong></div>
                        <div style="color: #60a5fa; margin-bottom: 0.25rem; font-size: 0.7rem;">
                            Spreads: {{ last_20.spreads.record }} ({% if last_20.spreads.roi > 0 %}+{% endif %}{{ '%.1f'|format(last_20.spreads.roi) }}% ROI)
                        </div>
                        <div style="color: #f472b6; font-size: 0.7rem;">
                            Totals: {{ last_20.totals.record }} ({% if last_20.totals.roi > 0 %}+{% endif %}{{ '%.1f'|format(last_20.totals.roi) }}% ROI)
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>'''
    
    template = Template(template_str)
    html_output = template.render(
        stats=stats,  # Add stats to template context
        timestamp=timestamp,
        season_stats=season_stats, # Pass season_stats to template
        last_100=last_100,  # Add recent performance data
        last_50=last_50,
        last_20=last_20,
        format_date=format_date
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

def calculate_recent_performance(picks_list, count):
    """Calculate performance stats for last N picks (most recent first)"""
    # Filter to only completed picks
    completed = [p for p in picks_list if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    # Take first N picks (most recent first since list is sorted reverse=True)
    recent = completed[:count] if len(completed) >= count else completed
    
    wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
    pushes = sum(1 for p in recent if p.get('status', '').lower() == 'push')
    total = wins + losses + pushes
    
    # Calculate profit (stored in cents, convert to units)
    profit_cents = sum(p.get('profit', 0) for p in recent if p.get('profit') is not None)
    profit_units = profit_cents / 100.0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (profit_cents / (total * UNIT_SIZE) * 100) if total > 0 else 0
    
    # Breakdown by type
    spread_picks = [p for p in recent if p.get('pick_type', '').lower() == 'spread']
    total_picks = [p for p in recent if p.get('pick_type', '').lower() == 'total']
    
    spread_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
    spread_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
    spread_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
    spread_total = spread_wins + spread_losses + spread_pushes
    spread_profit_cents = sum(p.get('profit', 0) for p in spread_picks if p.get('profit') is not None)
    spread_profit_units = spread_profit_cents / 100.0
    spread_wr = (spread_wins / spread_total * 100) if spread_total > 0 else 0
    spread_roi = (spread_profit_cents / (spread_total * UNIT_SIZE) * 100) if spread_total > 0 else 0
    
    total_wins = sum(1 for p in total_picks if p.get('status', '').lower() == 'win')
    total_losses = sum(1 for p in total_picks if p.get('status', '').lower() == 'loss')
    total_pushes = sum(1 for p in total_picks if p.get('status', '').lower() == 'push')
    total_total = total_wins + total_losses + total_pushes
    total_profit_cents = sum(p.get('profit', 0) for p in total_picks if p.get('profit') is not None)
    total_profit_units = total_profit_cents / 100.0
    total_wr = (total_wins / total_total * 100) if total_total > 0 else 0
    total_roi = (total_profit_cents / (total_total * UNIT_SIZE) * 100) if total_total > 0 else 0
    
    return {
        'record': f"{wins}-{losses}" + (f"-{pushes}" if pushes > 0 else ""),
        'win_rate': win_rate,
        'profit': profit_units,
        'roi': roi,
        'count': len(recent),
        'spreads': {
            'record': f"{spread_wins}-{spread_losses}" + (f"-{spread_pushes}" if spread_pushes > 0 else ""),
            'win_rate': spread_wr,
            'profit': spread_profit_units,
            'roi': spread_roi,
            'count': len(spread_picks)
        },
        'totals': {
            'record': f"{total_wins}-{total_losses}" + (f"-{total_pushes}" if total_pushes > 0 else ""),
            'win_rate': total_wr,
            'profit': total_profit_units,
            'roi': total_roi,
            'count': len(total_picks)
        }
    }

def generate_tracking_html():
    """Generate tracking dashboard HTML"""
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)
    
    all_picks = tracking_data.get('picks', [])
    all_picks.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    
    # Calculate Last N Stats
    last_100 = calculate_recent_performance(all_picks, 100)
    last_50 = calculate_recent_performance(all_picks, 50)
    last_20 = calculate_recent_performance(all_picks, 20)
    
    # Calculate Season Stats (All completed picks)
    season_stats = calculate_recent_performance(all_picks, len(all_picks))

    # Helper for formatting dates (must be inside to use in template if not passed)
    def format_date(date_str):
        try:
            dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
            est = pytz.timezone('US/Eastern')
            return dt.astimezone(est).strftime('%Y-%m-%d')
        except:
            return date_str

    timestamp = datetime.now().strftime("%Y-%m-%d %I:%M %p ET")

    template_str = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCAAB Model Tracking • CourtSide Analytics</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #121212;
            color: #ffffff;
            padding: 2rem;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: #1c1c1e;
            border: 1px solid #2a2a2a;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            border-radius: 12px;
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
        .text-blue-400 { color: #60a5fa; }
        .text-pink-400 { color: #f472b6; }
        .text-red-400 { color: #ef4444; }
        .text-yellow-400 { color: #f97316; }
        .text-gray-400 { color: #9ca3af; }
        h3 { font-size: 1.5rem; font-weight: 700; color: #ffffff; }
        h4 { font-size: 1.125rem; font-weight: 600; color: #94a3b8; }
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
            
            /* Make all inline 4-column grids responsive */
            div[style*="grid-template-columns: repeat(4, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }
            
            /* Make all inline 2-column grids single column on mobile */
            div[style*="grid-template-columns: repeat(2, 1fr)"] {
                grid-template-columns: 1fr !important;
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
            
            /* Tables - enable horizontal scroll */
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
            
            /* Reduce spacing */
            div[style*="padding: 2rem"] {
                padding: 1.25rem !important;
            }
            div[style*="margin-bottom: 2rem"] {
                margin-bottom: 1.25rem !important;
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
            
            header { flex-direction: column; align-items: flex-start; gap: 1rem; }
            .header-title h1 { font-size: 1.5rem; }
            div[style*="text-align: right"] { text-align: left !important; }
        }
        
        /* Header Section */
        header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin-bottom: 2rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #333;
        }
        .header-title h1 { margin: 0; font-size: 2rem; color: #f97316; }
        .header-subtitle { color: #9ca3af; font-size: 0.9rem; margin-top: 0.5rem; }
        .metric-title { font-size: 0.75rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; font-weight: 600; }
    </style>
</head>
<body>
        <div class="container">

            <header>
                <div class="header-title">
                    <h1>🏀 COLLEGE BASKETBALL TRACKING</h1>
                    <div class="header-subtitle">Generated: {{ timestamp }}</div>
                </div>
                <div style="text-align: right;">
                    <div class="metric-title">SEASON RECORD</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #10b981;">
                        {{ season_stats.record }} ({{ "%.1f"|format(season_stats.win_rate) }}%)
                    </div>
                    <div style="font-size: 1.1rem; color: {{ '#10b981' if season_stats.profit > 0 else '#ef4444' }}; font-weight: 600;">
                         {{ "%+.1f"|format(season_stats.profit) }}u
                    </div>
                </div>
            </header>

            <!-- Overall Stats Cards -->
            <div class="card">
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
                </div>
            </div>

            <!-- Daily Performance -->
            <div style="background: #1c1c1e; border: 1px solid #2a2a2a; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;">
                <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.25rem; border-bottom: 1px solid #333; padding-bottom: 1rem;">
                    <span style="font-size: 1.5rem;">📅</span>
                    <h2 style="margin: 0; font-size: 1.5rem; color: #f3f4f6;">Daily Performance</h2>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <!-- TODAY -->
                    <div style="background: #121212; border-radius: 0.75rem; padding: 1.5rem; text-align: center; border: 1px solid #333;">
                        <div style="color: #9ca3af; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.75rem; letter-spacing: 0.05em;">Today</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem;">{{ stats.today.record }}</div>
                        <div style="font-size: 1.25rem; font-weight: 600; color: {{ '#10b981' if stats.today.profit > 0 else ('#ef4444' if stats.today.profit < 0 else '#e5e7eb') }}; margin-bottom: 0.25rem;">
                            {{ "%+.1f"|format(stats.today.profit) }}u
                        </div>
                        <div style="font-size: 0.875rem; color: #9ca3af;">{{ "%.1f"|format(stats.today.roi) }}% ROI</div>
                    </div>
                    
                    <!-- YESTERDAY -->
                    <div style="background: #121212; border-radius: 0.75rem; padding: 1.5rem; text-align: center; border: 1px solid #333;">
                        <div style="color: #9ca3af; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 0.75rem; letter-spacing: 0.05em;">Yesterday</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #fff; margin-bottom: 0.5rem;">{{ stats.yesterday.record }}</div>
                        <div style="font-size: 1.25rem; font-weight: 600; color: {{ '#10b981' if stats.yesterday.profit > 0 else ('#ef4444' if stats.yesterday.profit < 0 else '#e5e7eb') }}; margin-bottom: 0.25rem;">
                            {{ "%+.1f"|format(stats.yesterday.profit) }}u
                        </div>
                        <div style="font-size: 0.875rem; color: #9ca3af;">{{ "%.1f"|format(stats.yesterday.roi) }}% ROI</div>
                    </div>
                </div>
            </div>
        
        <!-- PERFORMANCE BREAKDOWN - SELLING POINT -->
        <div class="card">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h2 style="font-size: 2rem; margin-bottom: 0.5rem;">🔥 Recent Performance Breakdown</h2>
                <p class="text-gray-400" style="font-size: 1rem; font-weight: 400;">Verified Track Record</p>
            </div>

            <!-- Last 100 Picks -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #4ade80; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    📊 Last 100 Picks
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value">{{ last_100.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ "%.1f"|format(last_100.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_100.profit > 0 %}positive{% elif last_100.profit < 0 %}negative{% endif %}">
                            {% if last_100.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_100.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_100.roi > 0 %}positive{% elif last_100.roi < 0 %}negative{% endif %}">
                            {% if last_100.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_100.roi) }}%
                        </div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ last_100.spreads.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.5rem;">{{ last_100.spreads.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-blue-400 font-bold">{{ "%.1f"|format(last_100.spreads.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_100.spreads.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_100.spreads.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_100.spreads.roi) }}%</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Totals ({{ last_100.totals.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #f472b6; margin-bottom: 0.5rem;">{{ last_100.totals.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-pink-400 font-bold">{{ "%.1f"|format(last_100.totals.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_100.totals.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_100.totals.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_100.totals.roi) }}%</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Last 50 Picks -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #4ade80; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    🚀 Last 50 Picks
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.win_rate >= 50 %}positive{% else %}negative{% endif %}">{{ last_50.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.win_rate >= 50 %}positive{% else %}negative{% endif %}">{{ "%.1f"|format(last_50.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.profit > 0 %}positive{% elif last_50.profit < 0 %}negative{% endif %}">
                            {% if last_50.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_50.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.roi > 0 %}positive{% elif last_50.roi < 0 %}negative{% endif %}">
                            {% if last_50.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_50.roi) }}%
                        </div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ last_50.spreads.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_50.spreads.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="{% if last_50.spreads.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.1f"|format(last_50.spreads.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_50.spreads.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_50.spreads.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_50.spreads.roi) }}%</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Totals ({{ last_50.totals.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_50.totals.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="{% if last_50.totals.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.1f"|format(last_50.totals.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_50.totals.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_50.totals.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_50.totals.roi) }}%</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Last 20 Picks -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem;">
                <h3 style="color: #4ade80; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    ⚡ Last 20 Picks (Hot Streak)
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.win_rate >= 50 %}positive{% else %}negative{% endif %}">{{ last_20.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.win_rate >= 50 %}positive{% else %}negative{% endif %}">{{ "%.1f"|format(last_20.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.profit > 0 %}positive{% elif last_20.profit < 0 %}negative{% endif %}">
                            {% if last_20.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_20.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.roi > 0 %}positive{% elif last_20.roi < 0 %}negative{% endif %}">
                            {% if last_20.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_20.roi) }}%
                        </div>
                        <div class="stat-label">ROI</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem;">
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ last_20.spreads.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_20.spreads.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="{% if last_20.spreads.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.1f"|format(last_20.spreads.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_20.spreads.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_20.spreads.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_20.spreads.roi) }}%</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Totals ({{ last_20.totals.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_20.totals.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="{% if last_20.totals.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.1f"|format(last_20.totals.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_20.totals.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_20.totals.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_20.totals.roi) }}%</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
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
        last_100=last_100,
        last_50=last_50,
        last_20=last_20,
        season_stats=season_stats,
        timestamp=timestamp,
        format_date=format_date
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




