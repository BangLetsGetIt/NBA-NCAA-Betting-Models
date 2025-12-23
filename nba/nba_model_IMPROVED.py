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

# Import for the NBA's official stats API
from nba_api.stats.endpoints import leaguedashteamstats, scoreboardv2
from nba_api.stats.static import teams as nba_teams
import time

# =========================
# CONFIG
# =========================

load_dotenv()
API_KEY = os.getenv("ODDS_API_KEY")
if not API_KEY:
    print("FATAL: ODDS_API_KEY not found in .env file.")
    exit()

BASE_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
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
CSV_FILE = os.path.join(SCRIPT_DIR, "nba_model_output.csv")
HTML_FILE = os.path.join(SCRIPT_DIR, "nba_model_output.html")
STATS_FILE = os.path.join(SCRIPT_DIR, "nba_stats_cache.json")
SPLITS_CACHE_FILE = os.path.join(SCRIPT_DIR, "nba_home_away_splits_cache.json")
SCHEDULE_CACHE_FILE = os.path.join(SCRIPT_DIR, "nba_schedule_cache.json")

# Tracking files
PICKS_TRACKING_FILE = os.path.join(SCRIPT_DIR, "nba_picks_tracking.json")
TRACKING_HTML_FILE = os.path.join(SCRIPT_DIR, "nba_tracking_dashboard.html")

# IMPORTANT: Update this to the current NBA season (e.g., '2024-25')
CURRENT_SEASON = '2024-25'

# --- IMPROVED Model Parameters ---
HOME_COURT_ADVANTAGE = 3.0  # Reduced from 3.5 - modern NBA HCA trending lower
SPREAD_THRESHOLD = 5.0      # Tightened from 3.0 - only show higher confidence plays
TOTAL_THRESHOLD = 6.0       # Tightened from 4.0 - only show higher confidence plays

# Stricter thresholds for LOGGING picks (these are the bets we actually track)
CONFIDENT_SPREAD_EDGE = 8.0  # Keep at 8 - spreads performing well
CONFIDENT_TOTAL_EDGE = 15.0  # Increased from 12.0 - totals underperforming

# CALIBRATION: Model projects ~18 points lower than market (98% UNDER bias)
# Adding calibration to balance OVER/UNDER betting
TOTAL_CALIBRATION = 12.0    # Add to model total to reduce UNDER bias
UNIT_SIZE = 100

# Date filtering
DAYS_AHEAD_TO_FETCH = 2  # Only fetch games within next 2 days (today + tomorrow)

# --- Parameters for Team Form/Momentum ---
LAST_N_GAMES = 10
SEASON_WEIGHT = 0.55    # Slightly less emphasis on full season
FORM_WEIGHT = 0.45      # More emphasis on recent form

# --- Parameters for Home/Away Splits ---
USE_HOME_AWAY_SPLITS = True
SPLITS_WEIGHT = 0.60         # More weight on splits
COMPOSITE_WEIGHT = 0.40      # Less weight on composite

# --- NEW: Rest Day Adjustments ---
BACK_TO_BACK_PENALTY = -2.5  # Penalize teams on back-to-back
REST_ADVANTAGE_BONUS = 1.5   # Bonus if opponent is on B2B

# --- NEW: Injury Impact ---
STAR_INJURY_IMPACT = -3.5    # Impact when star player is out
ROLE_INJURY_IMPACT = -1.0    # Impact when role player is out

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
# TEAM NAME NORMALIZATION
# =========================

def normalize_team_name(team_name):
    """Normalize team names for consistent matching across APIs"""
    name = team_name.strip()

    # Comprehensive mapping
    name_map = {
        # LA teams - handle variations
        "LA Clippers": "Los Angeles Clippers",
        "L.A. Clippers": "Los Angeles Clippers",
        "LAC": "Los Angeles Clippers",
        "LA Lakers": "Los Angeles Lakers",
        "L.A. Lakers": "Los Angeles Lakers",
        "LAL": "Los Angeles Lakers",
        # All 30 NBA teams
        "Atlanta Hawks": "Atlanta Hawks",
        "Boston Celtics": "Boston Celtics",
        "Brooklyn Nets": "Brooklyn Nets",
        "Charlotte Hornets": "Charlotte Hornets",
        "Chicago Bulls": "Chicago Bulls",
        "Cleveland Cavaliers": "Cleveland Cavaliers",
        "Dallas Mavericks": "Dallas Mavericks",
        "Denver Nuggets": "Denver Nuggets",
        "Detroit Pistons": "Detroit Pistons",
        "Golden State Warriors": "Golden State Warriors",
        "Houston Rockets": "Houston Rockets",
        "Indiana Pacers": "Indiana Pacers",
        "Los Angeles Clippers": "Los Angeles Clippers",
        "Los Angeles Lakers": "Los Angeles Lakers",
        "Memphis Grizzlies": "Memphis Grizzlies",
        "Miami Heat": "Miami Heat",
        "Milwaukee Bucks": "Milwaukee Bucks",
        "Minnesota Timberwolves": "Minnesota Timberwolves",
        "New Orleans Pelicans": "New Orleans Pelicans",
        "New York Knicks": "New York Knicks",
        "Oklahoma City Thunder": "Oklahoma City Thunder",
        "Orlando Magic": "Orlando Magic",
        "Philadelphia 76ers": "Philadelphia 76ers",
        "Phoenix Suns": "Phoenix Suns",
        "Portland Trail Blazers": "Portland Trail Blazers",
        "Sacramento Kings": "Sacramento Kings",
        "San Antonio Spurs": "San Antonio Spurs",
        "Toronto Raptors": "Toronto Raptors",
        "Utah Jazz": "Utah Jazz",
        "Washington Wizards": "Washington Wizards",
    }

    return name_map.get(name, name)

def get_team_name(api_name):
    """Normalize team name for consistent lookups"""
    return normalize_team_name(api_name)

# =========================
# TRACKING FUNCTIONS
# =========================

def load_picks_tracking():
    """Load existing picks tracking data"""
    if os.path.exists(PICKS_TRACKING_FILE):
        with open(PICKS_TRACKING_FILE, 'r') as f:
            return json.load(f)
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

    with open(PICKS_TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)
    print(f"{Colors.GREEN}✓ Tracking data saved to {PICKS_TRACKING_FILE}{Colors.END}")

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
        # NBA uses 'pick' field, NCAA uses 'pick_text' field
        pick_text = pick.get('pick', pick.get('pick_text', '')).upper()
        profit = pick.get('profit_loss', pick.get('profit', 0))

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

def log_confident_pick(game_data, pick_type, edge, model_line, market_line):
    """Log a confident pick to the tracking file"""
    tracking_data = load_picks_tracking()

    pick_id = f"{game_data['home_team']}_{game_data['away_team']}_{game_data['commence_time']}_{pick_type}"

    # Check if this pick already exists
    existing_pick = next((p for p in tracking_data['picks'] if p['pick_id'] == pick_id), None)
    if existing_pick:
        return

    if pick_type == 'spread':
        pick_text = game_data.get('ATS Pick', '')
    else:
        pick_text = game_data.get('Total Pick', '')

    pick_entry = {
        "pick_id": pick_id,
        "date_logged": datetime.now().isoformat(),
        "game_date": game_data['commence_time'],
        "home_team": game_data['home_team'],
        "away_team": game_data['away_team'],
        "matchup": f"{game_data['away_team']} @ {game_data['home_team']}",
        "pick_type": pick_type.capitalize(),
        "model_line": model_line,
        "market_line": market_line,
        "opening_line": market_line,  # Store opening line when first logged
        "closing_line": market_line,   # Initially same as opening, will be updated on subsequent runs
        "edge": round(edge, 1),
        "pick": pick_text,
        "units": 1,
        "status": "Pending",
        "result": None,
        "profit_loss": 0,
        "actual_home_score": None,
        "actual_away_score": None,
        "clv_status": None  # Will be calculated when closing line is updated
    }

    tracking_data['picks'].append(pick_entry)
    tracking_data['summary']['total_picks'] += 1
    tracking_data['summary']['pending'] += 1

    save_picks_tracking(tracking_data)

    print(f"{Colors.GREEN}📝 LOGGED PICK: {pick_text} (Edge: {edge:+.1f}){Colors.END}")

def calculate_clv_status(opening_line, closing_line, pick_type, pick_text):
    """
    Calculate if a pick beat the closing line (positive CLV).
    
    Args:
        opening_line: The line when the pick was first logged
        closing_line: The line at game time (or latest available)
        pick_type: 'Spread' or 'Total'
        pick_text: The pick text (e.g., "New York Knicks -2.5" or "OVER 234.5")
    
    Returns:
        "positive" if beat closing line, "negative" if worse, "neutral" if same
    """
    try:
        # If lines are the same, no CLV advantage
        if abs(opening_line - closing_line) < 0.1:
            return "neutral"
        
        if pick_type.lower() == 'spread':
            # For spreads, determine if we're betting favorite or underdog
            # Extract the spread value from pick text
            if 'BET:' in pick_text:
                # Format: "✅ BET: Team Name -2.5" or "✅ BET: Team Name +5.0"
                parts = pick_text.split('BET:')
                if len(parts) > 1:
                    spread_str = parts[1].strip().split()[-1]  # Get the last part (the spread)
                    try:
                        bet_spread = float(spread_str)
                    except:
                        # Fallback: use opening_line sign to determine
                        bet_spread = opening_line
                else:
                    bet_spread = opening_line
            else:
                bet_spread = opening_line
            
            # If betting favorite (negative spread): Better line = smaller absolute value
            # If betting underdog (positive spread): Better line = larger value
            if bet_spread < 0:
                # Betting favorite: -2.5 is better than -3.5 (smaller absolute value)
                if abs(opening_line) < abs(closing_line):
                    return "positive"
                else:
                    return "negative"
            else:
                # Betting underdog: +5.5 is better than +4.5 (larger value)
                if opening_line > closing_line:
                    return "positive"
                else:
                    return "negative"
        
        elif pick_type.lower() == 'total':
            # For totals, determine if we're betting OVER or UNDER
            pick_upper = pick_text.upper()
            
            if 'OVER' in pick_upper:
                # Betting OVER: Lower total is better (e.g., OVER 234.5 beats OVER 235.5)
                if opening_line < closing_line:
                    return "positive"
                else:
                    return "negative"
            elif 'UNDER' in pick_upper:
                # Betting UNDER: Higher total is better (e.g., UNDER 235.5 beats UNDER 234.5)
                if opening_line > closing_line:
                    return "positive"
                else:
                    return "negative"
            else:
                # Can't determine, return neutral
                return "neutral"
        
        return "neutral"
    
    except Exception as e:
        # If calculation fails, return neutral (fail gracefully)
        print(f"{Colors.YELLOW}⚠ Error calculating CLV status: {e}{Colors.END}")
        return "neutral"

def fetch_completed_scores_nba():
    """Fetch NBA scores for recently completed games from The Odds API"""
    print(f"{Colors.CYAN}Fetching completed NBA game scores...{Colors.END}")

    try:
        scores_url = "https://api.the-odds-api.com/v4/sports/basketball_nba/scores/"
        params = {
            "apiKey": API_KEY,
            "daysFrom": 3  # Check last 3 days
        }

        response = requests.get(scores_url, params=params, timeout=10)

        if response.status_code == 200:
            scores = response.json()
            print(f"{Colors.GREEN}✓ Fetched {len(scores)} games from API{Colors.END}")
            completed = [g for g in scores if g.get('completed')]
            print(f"{Colors.GREEN}✓ Found {len(completed)} completed games{Colors.END}")
            return completed
        else:
            print(f"{Colors.YELLOW}⚠️  Could not fetch scores: {response.status_code}{Colors.END}")
            if response.status_code == 422:
                print(f"{Colors.YELLOW}   API Response: {response.text[:200]}{Colors.END}")
                print(f"{Colors.YELLOW}   This may be a temporary API issue. Results will update on next run.{Colors.END}")
            return []

    except Exception as e:
        print(f"{Colors.RED}Error fetching NBA scores: {e}{Colors.END}")
        return []

def update_pick_results():
    """Check for completed games and update pick results"""
    tracking_data = load_picks_tracking()

    print(f"\n{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"{Colors.CYAN}🔄 UPDATING RESULTS FOR COMPLETED GAMES{Colors.END}")
    print(f"{Colors.CYAN}{'='*90}{Colors.END}")

    pending_picks = [p for p in tracking_data['picks'] if p.get('status', '').lower() == 'pending']

    if not pending_picks:
        print(f"\n{Colors.GREEN}✓ No pending picks to update{Colors.END}")
        return

    print(f"\n{Colors.YELLOW}📋 Checking {len(pending_picks)} pending picks...{Colors.END}")

    # Fetch completed scores from The Odds API
    completed_games = fetch_completed_scores_nba()

    if not completed_games:
        print(f"{Colors.YELLOW}⚠️  No completed games found.{Colors.END}")
        save_picks_tracking(tracking_data)
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

                print(f"  ✓ Updating: {away_team} {away_score} @ {home_team} {home_score}")

                pick['actual_home_score'] = home_score
                pick['actual_away_score'] = away_score

                actual_total = home_score + away_score
                actual_spread = home_score - away_score

                if pick['pick_type'] == 'Spread':
                    market_spread = float(pick['market_line'])
                    pick_text = pick['pick']

                    if pick_home in pick_text:
                        cover_margin = actual_spread + market_spread
                    else:
                        cover_margin = -actual_spread - market_spread

                    if abs(cover_margin) < 0.01:
                        pick['status'] = 'push'
                        pick['result'] = 'Push'
                        pick['profit_loss'] = 0
                    elif cover_margin > 0:
                        pick['status'] = 'win'
                        pick['result'] = 'Win'
                        pick['profit_loss'] = 100
                    else:
                        pick['status'] = 'loss'
                        pick['result'] = 'Loss'
                        pick['profit_loss'] = -110

                elif pick['pick_type'] == 'Total':
                    market_total = float(pick['market_line'])
                    pick_text = pick['pick']
                    total_diff = actual_total - market_total

                    if abs(total_diff) < 0.01:
                        pick['status'] = 'push'
                        pick['result'] = 'Push'
                        pick['profit_loss'] = 0
                    elif 'OVER' in pick_text and total_diff > 0:
                        pick['status'] = 'win'
                        pick['result'] = 'Win'
                        pick['profit_loss'] = 100
                    elif 'UNDER' in pick_text and total_diff < 0:
                        pick['status'] = 'win'
                        pick['result'] = 'Win'
                        pick['profit_loss'] = 100
                    else:
                        pick['status'] = 'loss'
                        pick['result'] = 'Loss'
                        pick['profit_loss'] = -110

                updated_count += 1
                print(f"    Result: {pick['result']}")
                break

    # Recalculate summary using status field to match NCAA model
    tracking_data['summary'] = {
        'total_picks': len(tracking_data['picks']),
        'wins': sum(1 for p in tracking_data['picks'] if p.get('status', '').lower() == 'win'),
        'losses': sum(1 for p in tracking_data['picks'] if p.get('status', '').lower() == 'loss'),
        'pushes': sum(1 for p in tracking_data['picks'] if p.get('status', '').lower() == 'push'),
        'pending': sum(1 for p in tracking_data['picks'] if p.get('status', '').lower() == 'pending')
    }

    save_picks_tracking(tracking_data)

    if updated_count > 0:
        # Recalculate summary
        tracking_data['summary'] = calculate_summary_stats(tracking_data['picks'])
        save_picks_tracking(tracking_data)
        print(f"{Colors.GREEN}✅ Updated {updated_count} picks{Colors.END}")
        
        # Regenerate HTML
        generate_tracking_html()
    else:
        print(f"{Colors.YELLOW}No picks were updated (games may not be complete yet){Colors.END}")

    return updated_count

def calculate_tracking_stats(tracking_data):
    """Calculate tracking statistics"""
    stats = {
        'total_picks': tracking_data['summary']['total_picks'],
        'wins': tracking_data['summary']['wins'],
        'losses': tracking_data['summary']['losses'],
        'pushes': tracking_data['summary']['pushes'],
        'pending': tracking_data['summary']['pending'],
        'win_rate': 0.0,
        'total_profit': 0,
        'roi': 0.0
    }

    decided = stats['wins'] + stats['losses']
    if decided > 0:
        stats['win_rate'] = (stats['wins'] / decided) * 100

    stats['total_profit'] = sum(p.get('profit_loss', 0) for p in tracking_data['picks'])

    total_risked = decided * 110
    if total_risked > 0:
        stats['roi'] = (stats['total_profit'] / total_risked) * 100

    return stats

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

def calculate_stats_for_picks(picks):
    """Calculate detailed stats for a subset of picks"""
    wins = sum(1 for p in picks if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in picks if p.get('status', '').lower() == 'loss')
    pushes = sum(1 for p in picks if p.get('status', '').lower() == 'push')
    total = wins + losses + pushes
    
    profit = sum(p.get('profit_loss', 0) for p in picks)
    risked = total * 110  # Approximation
    
    win_rate = (wins / total * 100) if total > 0 else 0.0
    roi = (profit / risked * 100) if risked > 0 else 0.0
    
    # Spreads
    spread_picks = [p for p in picks if p.get('pick_type', '').lower() == 'spread']
    s_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
    s_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
    s_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
    s_total = s_wins + s_losses + s_pushes
    s_win_rate = (s_wins / s_total * 100) if s_total > 0 else 0.0
    s_profit = sum(p.get('profit_loss', 0) for p in spread_picks)
    s_risked = s_total * 110
    s_roi = (s_profit / s_risked * 100) if s_risked > 0 else 0.0
    
    # Totals
    total_picks_subset = [p for p in picks if p.get('pick_type', '').lower() == 'total']
    t_wins = sum(1 for p in total_picks_subset if p.get('status', '').lower() == 'win')
    t_losses = sum(1 for p in total_picks_subset if p.get('status', '').lower() == 'loss')
    t_pushes = sum(1 for p in total_picks_subset if p.get('status', '').lower() == 'push')
    t_total = t_wins + t_losses + t_pushes
    t_win_rate = (t_wins / t_total * 100) if t_total > 0 else 0.0
    t_profit = sum(p.get('profit_loss', 0) for p in total_picks_subset)
    t_risked = t_total * 110
    t_roi = (t_profit / t_risked * 100) if t_risked > 0 else 0.0
    
    return {
        'record': f"{wins}-{losses}{f'-{pushes}' if pushes > 0 else ''}",
        'win_rate': win_rate,
        'profit': profit / 100,  # Convert cents to units if needed, but assuming input is already correct scale? Wait, profit_loss in json is likely units*100 or something. 
                                 # Checking calculate_tracking_stats: stats['total_profit'] / 100 in template. 
                                 # So profit here is comparable to stats['total_profit']. 
                                 # The template divides stats.total_profit by 100.
                                 # But for last_100, the template uses: {{ "%.2f"|format(last_100.profit) }}u
                                 # So I should return UNITS directly or handle the division.
                                 # Let's check calculate_tracking_stats again. 
                                 # stats['total_profit'] = sum(p.get('profit_loss', 0) ...)
                                 # In template: {{ "%.2f"|format(stats.total_profit/100) }}u
                                 # In template for last_100: {{ "%.2f"|format(last_100.profit) }}u
                                 # So last_100.profit should be in UNITS (i.e. already divided by 100).
        'roi': roi,
        'spreads': {
            'count': s_total,
            'record': f"{s_wins}-{s_losses}{f'-{s_pushes}' if s_pushes > 0 else ''}",
            'win_rate': s_win_rate,
            'roi': s_roi
        },
        'totals': {
            'count': t_total,
            'record': f"{t_wins}-{t_losses}{f'-{t_pushes}' if t_pushes > 0 else ''}",
            'win_rate': t_win_rate,
            'roi': t_roi
        }
    }

def generate_tracking_html():
    """Generate HTML dashboard for tracking picks"""
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)

    # Get current time in Eastern timezone
    est_tz = pytz.timezone('America/New_York')
    current_time = datetime.now(est_tz)

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
            game_dt_est = game_dt.astimezone(est_tz)
            game_date = game_dt_est.date()

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

    # Determine which record to display (prefer today if there are completed games)
    today_total = today_wins + today_losses + today_pushes
    if today_total > 0:
        # Show today's record
        display_label = "Today's Record"
        display_wins = today_wins
        display_losses = today_losses
        display_pushes = today_pushes
    else:
        # Show yesterday's record with date
        display_label = yesterday.strftime('%b %d') + " Record"
        display_wins = yesterday_wins
        display_losses = yesterday_losses
        display_pushes = yesterday_pushes

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
            game_dt_est = game_dt.astimezone(est_tz)
            game_date = game_dt_est.date()
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

    # Calculate Last 100/50/20 Stats
    # Sort picks by date descending
    sorted_picks = sorted(all_completed, key=lambda x: x.get('game_date', ''), reverse=True)
    
    # Adjust profit calculation for helper (convert cents to units)
    # The helper expects raw profit_loss (cents?) and returns units
    # Actually, let's look at calculate_stats_for_picks implementation above. 
    # I wrote: 'profit': profit / 100. 
    # So if profit_loss is in cents (100 = 1 unit), then dividing by 100 gives units.
    # Logic seems consistent with template usage.
    
    last_100 = calculate_stats_for_picks(sorted_picks[:100])
    last_50 = calculate_stats_for_picks(sorted_picks[:50])
    last_20 = calculate_stats_for_picks(sorted_picks[:20])

    # Determine which breakdown to display
    if today_total > 0:
        # Show today's breakdown
        display_spread_wins = today_spread_wins
        display_spread_losses = today_spread_losses
        display_spread_pushes = today_spread_pushes
        display_total_wins = today_total_wins
        display_total_losses = today_total_losses
        display_total_pushes = today_total_pushes
    else:
        # Show yesterday's breakdown
        display_spread_wins = yesterday_spread_wins
        display_spread_losses = yesterday_spread_losses
        display_spread_pushes = yesterday_spread_pushes
        display_total_wins = yesterday_total_wins
        display_total_losses = yesterday_total_losses
        display_total_pushes = yesterday_total_pushes

    # ========== PERFORMANCE BREAKDOWN (SELLING POINT) ==========
    # Calculate Last 100, Last 50, and Last 20 picks performance
    def calculate_recent_performance(picks_list, count):
        """Calculate performance stats for last N picks (most recent first)"""
        # Since picks_list is sorted with most recent first (reverse=True), 
        # we take the first N picks, not the last N
        recent = picks_list[:count] if len(picks_list) >= count else picks_list
        wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
        losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
        pushes = sum(1 for p in recent if p.get('status', '').lower() == 'push')
        total = wins + losses + pushes
        profit = sum(p.get('profit_loss', 0) for p in recent if p.get('status', '').lower() in ['win', 'loss', 'push'])

        win_rate = (wins / total * 100) if total > 0 else 0
        roi = (profit / (total * 100) * 100) if total > 0 else 0

        # Breakdown by type
        spread_picks = [p for p in recent if p.get('pick_type') == 'Spread']
        total_picks = [p for p in recent if p.get('pick_type') == 'Total']

        spread_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
        spread_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
        spread_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
        spread_total = spread_wins + spread_losses + spread_pushes
        spread_profit = sum(p.get('profit_loss', 0) for p in spread_picks if p.get('status', '').lower() in ['win', 'loss', 'push'])
        spread_wr = (spread_wins / spread_total * 100) if spread_total > 0 else 0
        spread_roi = (spread_profit / (spread_total * 100) * 100) if spread_total > 0 else 0

        total_wins = sum(1 for p in total_picks if p.get('status', '').lower() == 'win')
        total_losses = sum(1 for p in total_picks if p.get('status', '').lower() == 'loss')
        total_pushes = sum(1 for p in total_picks if p.get('status', '').lower() == 'push')
        total_total = total_wins + total_losses + total_pushes
        total_profit = sum(p.get('profit_loss', 0) for p in total_picks if p.get('status', '').lower() in ['win', 'loss', 'push'])
        total_wr = (total_wins / total_total * 100) if total_total > 0 else 0
        total_roi = (total_profit / (total_total * 100) * 100) if total_total > 0 else 0

        return {
            'record': f"{wins}-{losses}" + (f"-{pushes}" if pushes > 0 else ""),
            'win_rate': win_rate,
            'profit': profit / 100,
            'roi': roi,
            'count': len(recent),
            'spreads': {
                'record': f"{spread_wins}-{spread_losses}" + (f"-{spread_pushes}" if spread_pushes > 0 else ""),
                'win_rate': spread_wr,
                'profit': spread_profit / 100,
                'roi': spread_roi,
                'count': len(spread_picks)
            },
            'totals': {
                'record': f"{total_wins}-{total_losses}" + (f"-{total_pushes}" if total_pushes > 0 else ""),
                'win_rate': total_wr,
                'profit': total_profit / 100,
                'roi': total_roi,
                'count': len(total_picks)
            }
        }

    # Get all pending picks
    all_pending = [p for p in tracking_data['picks'] if p.get('status', '').lower() == 'pending']

    # Separate pending picks by whether game is in future (upcoming) or past (stale)
    pending_picks = []
    for pick in all_pending:
        try:
            game_dt = datetime.fromisoformat(str(pick.get('game_date', '')).replace('Z', '+00:00'))
            game_dt_est = game_dt.astimezone(est_tz)

            # Only include if game hasn't started yet
            if game_dt_est > current_time:
                pending_picks.append(pick)
        except:
            # If we can't parse the date, skip it
            pass

    # Get completed picks (redefine to ensure we have the latest)
    completed_picks = [p for p in tracking_data['picks'] if
                       p.get('status', '').lower() in ['win', 'loss', 'push']]

    # Sort completed picks by date (most recent first) BEFORE calculating recent performance
    pending_picks.sort(key=lambda x: x['game_date'], reverse=False)
    completed_picks.sort(key=lambda x: x['game_date'], reverse=True)

    # Calculate Last 10, Last 20, and Last 50 picks performance (AFTER sorting)
    last_10 = calculate_recent_performance(completed_picks, 10)
    last_20 = calculate_recent_performance(completed_picks, 20)
    last_50 = calculate_recent_performance(completed_picks, 50)

    def format_profit(profit):
        if profit > 0:
            return 'text-green-400'
        elif profit < 0:
            return 'text-red-400'
        return 'text-gray-400'

    def format_game_date(date_str):
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        est_tz = pytz.timezone('America/New_York')
        dt_est = dt.astimezone(est_tz)
        return dt_est.strftime('%m/%d %I:%M %p')

    timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    template_str = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics - Performance Dashboard</title>
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
            color: #10b981;
        }
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
        .text-green-400 { color: #10b981; }
        .text-blue-400 { color: #3b82f6; }
        .text-pink-400 { color: #f472b6; }
        .text-red-400 { color: #ef4444; }
        .text-yellow-400 { color: #f59e0b; }
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
        .badge-win { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .badge-loss { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        .badge-push { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
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
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="text-center">Model Performance</h1>
            <p class="text-center subtitle" style="margin-bottom: 2rem;">CourtSide Analytics</p>

            <!-- Overall Performance Card -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #10b981; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
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
            <div style="background: #262626; border-radius: 1rem; padding: 1.5rem;">
                <h3 style="font-size: 1.25rem; margin-bottom: 1rem; text-align: center; color: #f59e0b;">{{ display_label }}</h3>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem;">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem; font-weight: 700; color: #10b981;">{{ display_wins }}-{{ display_losses }}{% if display_pushes > 0 %}-{{ display_pushes }}{% endif %}</div>
                        <div style="color: #94a3b8; font-size: 0.875rem; margin-top: 0.5rem;">Overall</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2rem; font-weight: 700; color: #60a5fa;">{{ display_spread_wins }}-{{ display_spread_losses }}{% if display_spread_pushes > 0 %}-{{ display_spread_pushes }}{% endif %}</div>
                        <div style="color: #94a3b8; font-size: 0.875rem; margin-top: 0.5rem;">Spreads</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 2rem; font-weight: 700; color: #f472b6;">{{ display_total_wins }}-{{ display_total_losses }}{% if display_total_pushes > 0 %}-{{ display_total_pushes }}{% endif %}</div>
                        <div style="color: #94a3b8; font-size: 0.875rem; margin-top: 0.5rem;">Totals</div>
                    </div>
                </div>
            </div>
        </div>

        {% if pending_picks %}
        <div class="card">
            <h2>🎯 Today's Projections</h2>
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
                        {% for pick in pending_picks %}
                        <tr>
                            <td class="text-sm font-bold">{{ format_game_date(pick.game_date) }}</td>
                            <td class="font-bold">{{ pick.matchup }}</td>
                            <td>{{ pick.pick_type }}</td>
                            <td class="text-yellow-400">{{ pick.pick }}</td>
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

        <!-- PERFORMANCE BREAKDOWN - SELLING POINT -->
        <div class="card">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h2 style="font-size: 2rem; margin-bottom: 0.5rem;">🔥 Recent Performance Breakdown</h2>
                <p class="subtitle">Verified Track Record</p>
            </div>

            <!-- Last 100 Picks -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #10b981; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
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
                        <div class="stat-value {% if last_100.profit > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_100.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_100.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_100.roi > 0 %}text-green-400{% else %}text-red-400{% endif %}">
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
                <h3 style="color: #10b981; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    🚀 Last 50 Picks
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value text-green-400">{{ last_50.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value text-green-400">{{ "%.1f"|format(last_50.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.profit > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_50.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_50.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.roi > 0 %}text-green-400{% else %}text-red-400{% endif %}">
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
                            <div><span class="text-gray-400">Win%:</span> <span class="text-green-400 font-bold">{{ "%.1f"|format(last_50.spreads.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_50.spreads.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_50.spreads.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_50.spreads.roi) }}%</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Totals ({{ last_50.totals.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_50.totals.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-green-400 font-bold">{{ "%.1f"|format(last_50.totals.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_50.totals.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_50.totals.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_50.totals.roi) }}%</span></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Last 20 Picks -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem;">
                <h3 style="color: #10b981; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    ⚡ Last 20 Picks (Hot Streak)
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value text-green-400">{{ last_20.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value text-green-400">{{ "%.1f"|format(last_20.win_rate) }}%</div>
                        <div class="stat-label">Win Rate</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.profit > 0 %}text-green-400{% else %}text-red-400{% endif %}">
                            {% if last_20.profit > 0 %}+{% endif %}{{ "%.2f"|format(last_20.profit) }}u
                        </div>
                        <div class="stat-label">Profit</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.roi > 0 %}text-green-400{% else %}text-red-400{% endif %}">
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
                            <div><span class="text-gray-400">Win%:</span> <span class="text-green-400 font-bold">{{ "%.1f"|format(last_20.spreads.win_rate) }}%</span></div>
                            <div><span class="text-gray-400">ROI:</span> <span class="{% if last_20.spreads.roi > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{% if last_20.spreads.roi > 0 %}+{% endif %}{{ "%.1f"|format(last_20.spreads.roi) }}%</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #60a5fa; font-size: 1.25rem; margin-bottom: 1rem; text-align: center;">Totals ({{ last_20.totals.count }} picks)</h4>
                        <div style="text-align: center; font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ last_20.totals.record }}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-green-400 font-bold">{{ "%.1f"|format(last_20.totals.win_rate) }}%</span></div>
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

    template = Template(template_str)
    html_output = template.render(
        stats=stats,
        pending_picks=pending_picks,
        completed_picks=completed_picks,
        timestamp=timestamp,
        format_profit=format_profit,
        format_game_date=format_game_date,
        display_label=display_label,
        display_wins=display_wins,
        display_losses=display_losses,
        display_pushes=display_pushes,
        spread_wins=spread_wins,
        spread_losses=spread_losses,
        spread_pushes=spread_pushes,
        total_wins=total_wins,
        total_losses=total_losses,
        total_pushes=total_pushes,
        display_spread_wins=display_spread_wins,
        display_spread_losses=display_spread_losses,
        display_spread_pushes=display_spread_pushes,
        display_total_wins=display_total_wins,
        display_total_losses=display_total_losses,
        display_total_pushes=display_total_pushes,
        last_100=last_100,
        last_50=last_50,
        last_20=last_20
    )

    with open(TRACKING_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"{Colors.GREEN}✓ Tracking dashboard saved: {TRACKING_HTML_FILE}{Colors.END}")

# =========================
# SCHEDULE & REST DAY TRACKING
# =========================

def fetch_team_schedule():
    """Fetch team schedules to determine rest days"""

    # Check cache
    if os.path.exists(SCHEDULE_CACHE_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(SCHEDULE_CACHE_FILE))
        if (datetime.now() - file_mod_time) < timedelta(hours=12):
            with open(SCHEDULE_CACHE_FILE, 'r') as f:
                return json.load(f)

    print(f"{Colors.CYAN}🔄 Fetching team schedules...{Colors.END}")

    schedule_data = {}

    try:
        # Fetch scoreboard for last 7 days and next 7 days
        for days_offset in range(-7, 8):
            check_date = (datetime.now() + timedelta(days=days_offset)).strftime('%m/%d/%Y')

            try:
                scoreboard = scoreboardv2.ScoreboardV2(game_date=check_date)
                games_df = scoreboard.get_data_frames()[0]

                if games_df.empty:
                    continue

                for _, game in games_df.iterrows():
                    home_team = normalize_team_name(game.get('HOME_TEAM_NAME', ''))
                    visitor_team = normalize_team_name(game.get('VISITOR_TEAM_NAME', ''))
                    game_date_str = check_date

                    if home_team not in schedule_data:
                        schedule_data[home_team] = []
                    if visitor_team not in schedule_data:
                        schedule_data[visitor_team] = []

                    schedule_data[home_team].append(game_date_str)
                    schedule_data[visitor_team].append(game_date_str)

                time.sleep(0.6)

            except Exception as e:
                continue

        # Cache the schedule
        with open(SCHEDULE_CACHE_FILE, 'w') as f:
            json.dump(schedule_data, f, indent=2)

        print(f"{Colors.GREEN}✓ Fetched schedules for {len(schedule_data)} teams{Colors.END}")
        return schedule_data

    except Exception as e:
        print(f"{Colors.YELLOW}⚠ Could not fetch schedules: {e}{Colors.END}")
        return {}

def is_back_to_back(team_name, game_date_str, schedule_data):
    """Check if a team is playing on back-to-back days"""
    if team_name not in schedule_data:
        return False

    try:
        game_date = datetime.strptime(game_date_str, '%m/%d/%Y')
        prev_date = (game_date - timedelta(days=1)).strftime('%m/%d/%Y')

        return prev_date in schedule_data[team_name]
    except:
        return False

def get_rest_days(team_name, game_date_str, schedule_data):
    """Calculate days of rest before a game"""
    if team_name not in schedule_data:
        return 2  # Default assumption

    try:
        game_date = datetime.strptime(game_date_str, '%m/%d/%Y')
        team_games = sorted([datetime.strptime(d, '%m/%d/%Y') for d in schedule_data[team_name]])

        for i, date in enumerate(team_games):
            if date == game_date and i > 0:
                prev_game = team_games[i-1]
                return (game_date - prev_game).days - 1

        return 2
    except:
        return 2

# =========================
# IMPROVED MODEL CALCULATIONS
# =========================

def calculate_model_spread(home_team, away_team, stats, splits_data=None, schedule_data=None, game_date_str=None):
    """
    IMPROVED: Calculate predicted spread with rest day adjustments
    """
    try:
        home_team_name = get_team_name(home_team)
        away_team_name = get_team_name(away_team)

        # Validate teams exist in stats
        if home_team_name not in stats or away_team_name not in stats:
            print(f"{Colors.RED}❌ Missing stats for {home_team_name} or {away_team_name}{Colors.END}")
            return None

        # Use splits for spread calculation when available
        if USE_HOME_AWAY_SPLITS and splits_data and splits_data.get('Home') and splits_data.get('Road'):
            if home_team_name in splits_data['Home'] and away_team_name in splits_data['Road']:
                home_rating = splits_data['Home'][home_team_name]['NET_RATING']
                away_rating = splits_data['Road'][away_team_name]['NET_RATING']

                spread = (home_rating - away_rating) + HOME_COURT_ADVANTAGE
            else:
                # Fallback to composite
                home_stats = stats[home_team_name]['NET_RATING']
                away_stats = stats[away_team_name]['NET_RATING']
                spread = (home_stats - away_stats) + HOME_COURT_ADVANTAGE
        else:
            # Fallback to composite only
            home_stats = stats[home_team_name]['NET_RATING']
            away_stats = stats[away_team_name]['NET_RATING']
            spread = (home_stats - away_stats) + HOME_COURT_ADVANTAGE

        # NEW: Adjust for rest days / back-to-backs
        if schedule_data and game_date_str:
            home_b2b = is_back_to_back(home_team_name, game_date_str, schedule_data)
            away_b2b = is_back_to_back(away_team_name, game_date_str, schedule_data)

            if home_b2b:
                spread += BACK_TO_BACK_PENALTY
                print(f"{Colors.YELLOW}  ⚠️  {home_team_name} on back-to-back ({BACK_TO_BACK_PENALTY:+.1f}){Colors.END}")

            if away_b2b:
                spread -= BACK_TO_BACK_PENALTY  # Benefits home team
                print(f"{Colors.YELLOW}  ⚠️  {away_team_name} on back-to-back ({-BACK_TO_BACK_PENALTY:+.1f}){Colors.END}")

            # Rest advantage
            if away_b2b and not home_b2b:
                spread += REST_ADVANTAGE_BONUS
                print(f"{Colors.GREEN}  ✓ {home_team_name} has rest advantage ({REST_ADVANTAGE_BONUS:+.1f}){Colors.END}")
            elif home_b2b and not away_b2b:
                spread -= REST_ADVANTAGE_BONUS
                print(f"{Colors.GREEN}  ✓ {away_team_name} has rest advantage ({-REST_ADVANTAGE_BONUS:+.1f}){Colors.END}")

        return round(spread, 1)

    except KeyError as e:
        print(f"{Colors.RED}❌ Missing stats in calculate_model_spread for team: {e}{Colors.END}")
        return None
    except Exception as e:
        print(f"{Colors.RED}❌ Error in calculate_model_spread: {e}{Colors.END}")
        return None

def calculate_model_total(home_team, away_team, stats, splits_data=None):
    """
    IMPROVED: Calculate predicted total with better formula including defense
    """
    try:
        home_team_name = get_team_name(home_team)
        away_team_name = get_team_name(away_team)

        # Validate teams exist
        if home_team_name not in stats or away_team_name not in stats:
            print(f"{Colors.RED}❌ Missing stats for {home_team_name} or {away_team_name}{Colors.END}")
            return None

        # Use composite stats for totals
        home_stats = stats[home_team_name]
        away_stats = stats[away_team_name]

        # IMPROVED FORMULA: Account for both offense AND defense
        # Expected home team points = (Home OffRtg + Away DefRtg) / 2
        # Expected away team points = (Away OffRtg + Home DefRtg) / 2

        home_expected = (home_stats['OffRtg'] + away_stats['DefRtg']) / 2
        away_expected = (away_stats['OffRtg'] + home_stats['DefRtg']) / 2

        # Adjust for pace
        avg_pace = (home_stats['Pace'] + away_stats['Pace']) / 2
        pace_factor = avg_pace / 100.0  # NBA average pace ~100

        total = (home_expected + away_expected) * pace_factor

        # Apply calibration to reduce UNDER bias
        # Model historically projects ~18 points below market
        total += TOTAL_CALIBRATION

        # Sanity check with wider bounds
        if total < 180 or total > 260:
            print(f"{Colors.YELLOW}⚠️  Unusual total {total:.1f} for {home_team} vs {away_team}{Colors.END}")
            total = max(190, min(250, total))

        return round(total, 1)

    except KeyError as e:
        print(f"{Colors.RED}❌ Missing stats in calculate_model_total for team: {e}{Colors.END}")
        return None
    except Exception as e:
        print(f"{Colors.RED}❌ Error in calculate_model_total: {e}{Colors.END}")
        return None

def predicted_score(model_spread, model_total):
    """Calculate predicted final scores"""
    if model_spread is None or model_total is None:
        return None, None

    home_score = round(model_total / 2 + model_spread / 2)
    away_score = round(model_total / 2 - model_spread / 2)
    return home_score, away_score

# =========================
# FETCH ADVANCED STATS
# =========================

def fetch_advanced_stats():
    """Fetch and cache advanced team stats from stats.nba.com API with retry logic."""

    # Check cache first
    if os.path.exists(STATS_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(STATS_FILE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached composite stats (less than 6 hours old){Colors.END}")
            with open(STATS_FILE, 'r') as f:
                return json.load(f)

    print(f"{Colors.CYAN}🔄 Fetching new team stats from stats.nba.com...{Colors.END}")
    
    # Retry logic with exponential backoff
    max_retries = 3
    retry_delays = [2, 5, 10]  # seconds to wait between retries
    
    for attempt in range(max_retries):
        try:
            # Fetch full-season stats with increased timeout
            season_stats_data = leaguedashteamstats.LeagueDashTeamStats(
                measure_type_detailed_defense='Advanced',
                season=CURRENT_SEASON,
                timeout=60  # Increased from 30 to 60 seconds
            )
            season_df = season_stats_data.get_data_frames()[0]
            time.sleep(0.6)

            # Fetch last N games stats with increased timeout
            form_stats_data = leaguedashteamstats.LeagueDashTeamStats(
                measure_type_detailed_defense='Advanced',
                season=CURRENT_SEASON,
                last_n_games=LAST_N_GAMES,
                timeout=60  # Increased from 30 to 60 seconds
            )
            form_df = form_stats_data.get_data_frames()[0]
            time.sleep(0.6)

            # Blend season and form stats
            stats_dict = {}
            for _, row in season_df.iterrows():
                team_name = row.get('TEAM_NAME', 'Unknown')
                team_id = row.get('TEAM_ID', None)

                season_net_rating = row.get('NET_RATING', 0)
                season_pace = row.get('PACE', 100)
                season_off_rtg = row.get('OFF_RATING', 110)
                season_def_rtg = row.get('DEF_RATING', 110)

                # Get form stats for this team
                form_row = form_df[form_df['TEAM_ID'] == team_id] if team_id else pd.DataFrame()
                if not form_row.empty:
                    form_net_rating = form_row.iloc[0].get('NET_RATING', season_net_rating)
                    form_pace = form_row.iloc[0].get('PACE', season_pace)
                    form_off_rtg = form_row.iloc[0].get('OFF_RATING', season_off_rtg)
                    form_def_rtg = form_row.iloc[0].get('DEF_RATING', season_def_rtg)
                else:
                    form_net_rating, form_pace, form_off_rtg, form_def_rtg = season_net_rating, season_pace, season_off_rtg, season_def_rtg

                # Blend (65% season, 35% form)
                stats_dict[team_name] = {
                    "NET_RATING": round(SEASON_WEIGHT * season_net_rating + FORM_WEIGHT * form_net_rating, 1),
                    "Pace": round(SEASON_WEIGHT * season_pace + FORM_WEIGHT * form_pace, 2),
                    "OffRtg": round(SEASON_WEIGHT * season_off_rtg + FORM_WEIGHT * form_off_rtg, 1),
                    "DefRtg": round(SEASON_WEIGHT * season_def_rtg + FORM_WEIGHT * form_def_rtg, 1)
                }

            # Cache the results
            with open(STATS_FILE, 'w') as f:
                json.dump(stats_dict, f, indent=2)

            print(f"{Colors.GREEN}✓ Fetched and cached stats for {len(stats_dict)} teams{Colors.END}")
            return stats_dict

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delays[attempt]
                print(f"{Colors.YELLOW}⚠ Attempt {attempt + 1}/{max_retries} failed: {e}{Colors.END}")
                print(f"{Colors.YELLOW}   Retrying in {wait_time} seconds...{Colors.END}")
                time.sleep(wait_time)
            else:
                print(f"{Colors.RED}✗ Error fetching stats after {max_retries} attempts: {e}{Colors.END}")
                # Fall back to cached data even if it's older than 6 hours
                if os.path.exists(STATS_FILE):
                    print(f"{Colors.YELLOW}⚠ Falling back to cached stats (may be stale){Colors.END}")
                    try:
                        with open(STATS_FILE, 'r') as f:
                            cached_stats = json.load(f)
                            if cached_stats:
                                print(f"{Colors.GREEN}✓ Using cached stats for {len(cached_stats)} teams{Colors.END}")
                                return cached_stats
                    except Exception as cache_error:
                        print(f"{Colors.RED}✗ Could not load cached stats: {cache_error}{Colors.END}")
                traceback.print_exc()
                return {}

def fetch_home_away_splits():
    """Fetch and cache home/away split stats with retry logic."""

    # Check cache
    if os.path.exists(SPLITS_CACHE_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(SPLITS_CACHE_FILE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached home/away splits (less than 6 hours old){Colors.END}")
            with open(SPLITS_CACHE_FILE, 'r') as f:
                return json.load(f)

    print(f"{Colors.CYAN}🔄 Fetching home/away splits from stats.nba.com...{Colors.END}")

    # Retry logic with exponential backoff
    max_retries = 3
    retry_delays = [2, 5, 10]  # seconds to wait between retries
    
    for attempt in range(max_retries):
        try:
            # Fetch home stats with increased timeout
            home_stats = leaguedashteamstats.LeagueDashTeamStats(
                measure_type_detailed_defense='Advanced',
                season=CURRENT_SEASON,
                location_nullable='Home',
                timeout=60  # Increased from 30 to 60 seconds
            )
            home_df = home_stats.get_data_frames()[0]
            time.sleep(0.6)

            # Fetch road stats with increased timeout
            road_stats = leaguedashteamstats.LeagueDashTeamStats(
                measure_type_detailed_defense='Advanced',
                season=CURRENT_SEASON,
                location_nullable='Road',
                timeout=60  # Increased from 30 to 60 seconds
            )
            road_df = road_stats.get_data_frames()[0]
            time.sleep(0.6)

            splits_dict = {"Home": {}, "Road": {}}

            # Process home stats
            for _, row in home_df.iterrows():
                team_name = row.get('TEAM_NAME', 'Unknown')
                splits_dict["Home"][team_name] = {
                    "NET_RATING": row.get('NET_RATING', 0),
                    "Pace": row.get('PACE', 100),
                    "OffRtg": row.get('OFF_RATING', 110),
                    "DefRtg": row.get('DEF_RATING', 110)
                }

            # Process road stats
            for _, row in road_df.iterrows():
                team_name = row.get('TEAM_NAME', 'Unknown')
                splits_dict["Road"][team_name] = {
                    "NET_RATING": row.get('NET_RATING', 0),
                    "Pace": row.get('PACE', 100),
                    "OffRtg": row.get('OFF_RATING', 110),
                    "DefRtg": row.get('DEF_RATING', 110)
                }

            # Cache
            with open(SPLITS_CACHE_FILE, 'w') as f:
                json.dump(splits_dict, f, indent=2)

            print(f"{Colors.GREEN}✓ Fetched and cached home/away splits{Colors.END}")
            return splits_dict

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = retry_delays[attempt]
                print(f"{Colors.YELLOW}⚠ Attempt {attempt + 1}/{max_retries} failed: {e}{Colors.END}")
                print(f"{Colors.YELLOW}   Retrying in {wait_time} seconds...{Colors.END}")
                time.sleep(wait_time)
            else:
                print(f"{Colors.YELLOW}⚠ Could not fetch splits after {max_retries} attempts: {e}{Colors.END}")
                # Fall back to cached data even if it's older than 6 hours
                if os.path.exists(SPLITS_CACHE_FILE):
                    print(f"{Colors.YELLOW}⚠ Falling back to cached splits (may be stale){Colors.END}")
                    try:
                        with open(SPLITS_CACHE_FILE, 'r') as f:
                            cached_splits = json.load(f)
                            if cached_splits:
                                print(f"{Colors.GREEN}✓ Using cached splits{Colors.END}")
                                return cached_splits
                    except Exception as cache_error:
                        print(f"{Colors.YELLOW}⚠ Could not load cached splits: {cache_error}{Colors.END}")
                return None

# =========================
# FETCH ODDS
# =========================

def fetch_odds():
    """Fetch current NBA odds from The Odds API, filtered by date"""
    try:
        response = requests.get(BASE_URL, params=PARAMS, timeout=10)
        response.raise_for_status()
        all_games = response.json()

        # Filter games by date
        now = datetime.now()
        cutoff_date = now + timedelta(days=DAYS_AHEAD_TO_FETCH)

        filtered_games = []
        for game in all_games:
            commence_time_str = game.get('commence_time', '')
            try:
                dt = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                dt_naive = dt.replace(tzinfo=None)

                if dt_naive <= cutoff_date:
                    # NEW: Filter out games that have already started
                    # API returns UTC time string like '2023-10-25T23:00:00Z'
                    # We compare with current UTC time
                    game_time_utc = pytz.utc.localize(dt_naive)
                    current_time_utc = datetime.now(pytz.utc)
                    
                    if game_time_utc > current_time_utc:
                        filtered_games.append(game)
            except:
                continue

        print(f"{Colors.GREEN}✓ Fetched odds for {len(all_games)} total games{Colors.END}")
        print(f"{Colors.GREEN}✓ Filtered to {len(filtered_games)} games in next {DAYS_AHEAD_TO_FETCH} days{Colors.END}")

        return filtered_games

    except Exception as e:
        print(f"{Colors.RED}✗ Error fetching odds: {e}{Colors.END}")
        return []

# =========================
# PROCESS GAMES WITH VALIDATION
# =========================

def validate_market_line(spread, total, home_team, away_team):
    """Validate that market lines are reasonable"""
    issues = []

    # Check spread
    if abs(spread) > 25:
        issues.append(f"Unusual spread: {spread:+.1f}")

    # Check total
    if total < 180 or total > 260:
        issues.append(f"Unusual total: {total:.1f}")

    if issues:
        print(f"{Colors.YELLOW}⚠️  Market line validation warnings for {away_team} @ {home_team}:{Colors.END}")
        for issue in issues:
            print(f"{Colors.YELLOW}    - {issue}{Colors.END}")

    # Return True if lines are reasonable, False if they're too extreme
    return len(issues) == 0 or (abs(spread) < 30 and 170 < total < 270)

def process_games(games, stats, splits_data=None, schedule_data=None):
    """Process each game and generate predictions with improved validation"""
    results = []

    # Load historical team performance
    team_performance = get_team_historical_performance()
    
    # Load historical edge performance for A.I. Rating calculation
    tracking_data = load_picks_tracking()
    historical_edge_performance = get_historical_performance_by_edge(tracking_data)
    
    # Track if we need to save updated CLV data
    clv_updated = False

    for game in games:
        try:
            # Normalize team names from The Odds API
            home_team = normalize_team_name(game['home_team'])
            away_team = normalize_team_name(game['away_team'])
            commence_time = game['commence_time']

            # Convert to Eastern Time
            dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            eastern = pytz.timezone('US/Eastern')
            dt_eastern = dt.astimezone(eastern)
            game_time = dt_eastern.strftime('%m/%d/%y %I:%M %p %Z')
            game_date_str = dt_eastern.strftime('%m/%d/%Y')

            # Get bookmaker data
            if not game.get('bookmakers'):
                continue

            # Prioritize Hard Rock Bet, then FanDuel, then first available
            bookmaker = next((b for b in game['bookmakers'] if b['key'] == 'hardrockbet'),
                        next((b for b in game['bookmakers'] if b['key'] == 'fanduel'), 
                             game['bookmakers'][0]))
            markets = {m['key']: m for m in bookmaker.get('markets', [])}

            # Extract lines
            spread_market = markets.get('spreads')
            total_market = markets.get('totals')

            if not spread_market or not total_market:
                continue

            # Get market lines
            home_spread = next((o['point'] for o in spread_market['outcomes']
                               if normalize_team_name(o['name']) == home_team), None)
            market_total = total_market['outcomes'][0]['point'] if total_market['outcomes'] else None

            if home_spread is None or market_total is None:
                continue

            # Validate market lines
            if not validate_market_line(home_spread, market_total, home_team, away_team):
                print(f"{Colors.RED}❌ Skipping {away_team} @ {home_team} - extreme market lines{Colors.END}")
                continue

            # Calculate model predictions
            model_spread = calculate_model_spread(home_team, away_team, stats, splits_data, schedule_data, game_date_str)
            model_total = calculate_model_total(home_team, away_team, stats, splits_data)

            # CRITICAL: Skip if model returns None (missing data)
            if model_spread is None or model_total is None:
                print(f"{Colors.RED}❌ Skipping {away_team} @ {home_team} - missing model data{Colors.END}")
                continue

            # Calculate edges
            spread_edge = model_spread + home_spread
            total_edge = model_total - market_total

            # Predicted scores
            pred_home, pred_away = predicted_score(model_spread, model_total)

            if pred_home is None or pred_away is None:
                continue

            # Determine picks with explanations
            ats_pick = ""
            ats_explanation = ""

            if spread_edge > SPREAD_THRESHOLD:
                # Home team COVERS
                ats_pick = f"✅ BET: {home_team} {home_spread:+.1f}"

                if home_spread < 0:
                    ats_explanation = f"Model projects {home_team} to win by {abs(model_spread):.1f}, covering {home_spread}."
                else:
                    if model_spread > 0:
                        ats_explanation = f"Model projects {home_team} to win outright, easily covering {home_spread:+.1f}."
                    else:
                        ats_explanation = f"Model projects {home_team} to lose by only {abs(model_spread):.1f}, covering {home_spread:+.1f}."

            elif spread_edge < -SPREAD_THRESHOLD:
                # Home team DOESN'T COVER
                away_spread = -home_spread
                ats_pick = f"✅ BET: {away_team} {away_spread:+.1f}"

                if home_spread < 0:
                    ats_explanation = f"Model projects {home_team} to win by only {abs(model_spread):.1f}, not enough to cover {home_spread}."
                else:
                    ats_explanation = f"Model projects {home_team} to lose by {abs(model_spread):.1f}, {away_team} covers {away_spread:+.1f}."

            else:
                ats_pick = "⚠️ NO BET - Too close to call"
                ats_explanation = f"Edge too small ({spread_edge:+.1f})"

            total_pick = ""
            total_explanation = ""
            if abs(total_edge) >= TOTAL_THRESHOLD:
                if total_edge > 0:
                    total_pick = f"✅ BET: OVER {market_total}"
                    total_explanation = f"Model projects {model_total:.0f} total points, bet the OVER"
                else:
                    total_pick = f"✅ BET: UNDER {market_total}"
                    total_explanation = f"Model projects {model_total:.0f} total points, bet the UNDER"
            else:
                total_pick = "⚠️ NO BET - Too close to call"
                total_explanation = ""

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

            result = {
                "Matchup": f"{away_team} @ {home_team}",
                "GameTime": game_time,
                "Market Spread": f"{home_spread:+.1f}",
                "Model Spread": f"{model_spread:+.1f}",
                "Market Total": market_total,
                "Model Total": model_total,
                "ATS Pick": ats_pick,
                "ATS Explanation": ats_explanation,
                "Total Pick": total_pick,
                "Total Explanation": total_explanation,
                "Predicted Score": f"{away_team} {pred_away}, {home_team} {pred_home}",
                "home_team": home_team,
                "away_team": away_team,
                "commence_time": commence_time,
                "spread_edge": spread_edge,
                "total_edge": total_edge,
                "team_indicator": team_indicator
            }
            
            # Calculate A.I. Rating (supplements edge-based approach)
            ai_rating = calculate_ai_rating(result, team_performance, historical_edge_performance)
            result["ai_rating"] = ai_rating

            # Check for existing picks and update CLV if game hasn't started
            try:
                # Check if game has started
                game_dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                if game_dt.tzinfo is None:
                    game_dt = game_dt.replace(tzinfo=pytz.timezone('UTC'))
                now_utc = datetime.now(pytz.timezone('UTC'))
                game_has_started = game_dt <= now_utc
                
                if not game_has_started:
                    # Update closing line for existing spread picks
                    if '✅' in ats_pick and abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
                        spread_pick_id = f"{home_team}_{away_team}_{commence_time}_spread"
                        existing_spread_pick = next((p for p in tracking_data['picks'] if p.get('pick_id') == spread_pick_id), None)
                        
                        if existing_spread_pick:
                            # Update closing line if it has changed
                            if existing_spread_pick.get('closing_line') != home_spread:
                                existing_spread_pick['closing_line'] = home_spread
                                # Calculate CLV status
                                existing_spread_pick['clv_status'] = calculate_clv_status(
                                    existing_spread_pick.get('opening_line', home_spread),
                                    home_spread,
                                    'Spread',
                                    ats_pick
                                )
                                clv_updated = True
                    
                    # Update closing line for existing total picks
                    if '✅' in total_pick and abs(total_edge) >= CONFIDENT_TOTAL_EDGE:
                        total_pick_id = f"{home_team}_{away_team}_{commence_time}_total"
                        existing_total_pick = next((p for p in tracking_data['picks'] if p.get('pick_id') == total_pick_id), None)
                        
                        if existing_total_pick:
                            # Update closing line if it has changed
                            if existing_total_pick.get('closing_line') != market_total:
                                existing_total_pick['closing_line'] = market_total
                                # Calculate CLV status
                                existing_total_pick['clv_status'] = calculate_clv_status(
                                    existing_total_pick.get('opening_line', market_total),
                                    market_total,
                                    'Total',
                                    total_pick
                                )
                                clv_updated = True
            except Exception as e:
                # Fail gracefully - don't break the model if CLV update fails
                print(f"{Colors.YELLOW}⚠ Error updating CLV: {e}{Colors.END}")

            results.append(result)

            # Log ONLY confident picks with higher thresholds
            if '✅' in ats_pick and abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
                log_confident_pick(result, 'spread', spread_edge, model_spread, home_spread)

            if '✅' in total_pick and abs(total_edge) >= CONFIDENT_TOTAL_EDGE:
                log_confident_pick(result, 'total', total_edge, model_total, market_total)

        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Error processing game: {e}{Colors.END}")
            traceback.print_exc()
            continue

    # Save updated CLV data if any picks were updated
    if clv_updated:
        save_picks_tracking(tracking_data)
        print(f"{Colors.GREEN}✓ Updated CLV data for existing picks{Colors.END}")

    return results

# =========================
# DISPLAY & SAVE
# =========================

def display_terminal(results):
    """Display results in terminal"""
    print(f"\n{Colors.BOLD}{'='*90}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}🏀 NBA MODEL PREDICTIONS 🏀{Colors.END}")
    print(f"{Colors.BOLD}{'='*90}{Colors.END}\n")

    for r in results:
        print(f"{Colors.BOLD}{Colors.CYAN}{r['Matchup']}{Colors.END}")
        print(f"  🕐 {r['GameTime']}")
        
        # Display A.I. Rating prominently
        ai_rating = r.get('ai_rating', 2.3)
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
        
        print(f"  {rating_color}{Colors.BOLD}🎯 A.I. Rating: {ai_rating:.1f} {rating_stars} ({rating_label}){Colors.END}")

        # Display team performance indicator if available
        if r.get('team_indicator'):
            indicator = r['team_indicator']
            print(f"  {indicator['color']}{indicator['emoji']} {indicator['label']}: {indicator['message']}{Colors.END}")

        print(f"  📊 Spread: Market {r['Market Spread']} | Model {r['Model Spread']}")
        print(f"  🎯 Total: Market {r['Market Total']} | Model {r['Model Total']}")
        print(f"  {Colors.GREEN if '✅' in r['ATS Pick'] else Colors.YELLOW}{r['ATS Pick']}{Colors.END}")
        if r['ATS Explanation']:
            print(f"     {Colors.CYAN}{r['ATS Explanation']}{Colors.END}")
        print(f"  {Colors.GREEN if '✅' in r['Total Pick'] else Colors.YELLOW}{r['Total Pick']}{Colors.END}")
        if r['Total Explanation']:
            print(f"     {Colors.CYAN}{r['Total Explanation']}{Colors.END}")
        print(f"  📈 Predicted: {r['Predicted Score']}")
        print()

def save_csv(results):
    """Save results to CSV"""
    if not results:
        return

    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"{Colors.GREEN}✓ CSV saved: {CSV_FILE}{Colors.END}")

def save_html(results):
    # Load tracking data for display
    tracking_data = load_picks_tracking()
    
    # Get pending picks - ensure pending picks only show upcoming games (not past ones waiting for update)
    # We can filter out stale pending picks if needed, but usually we want to see everything marked as pending
    pending_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() == 'pending']
    
    # Get recent completed picks
    completed_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    # Sort
    pending_picks.sort(key=lambda x: x.get('game_date', ''))
    completed_picks.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    
    # --- STATISTICS CALCULATION ---
    
    def calculate_stats(picks):
        if not picks:
            return {
                'record': '0-0-0', 'win_rate': 0, 'profit': 0, 'roi': 0, 'count': 0,
                'spreads': {'record': '0-0-0', 'win_rate': 0, 'roi': 0},
                'totals': {'record': '0-0-0', 'win_rate': 0, 'roi': 0}
            }
            
        wins = sum(1 for p in picks if p.get('status', '').lower() == 'win')
        losses = sum(1 for p in picks if p.get('status', '').lower() == 'loss')
        pushes = sum(1 for p in picks if p.get('status', '').lower() == 'push')
        count = wins + losses + pushes
        
        # Profit (cents)
        profit_cents = sum(p.get('profit_loss', 0) for p in picks)
        profit_units = profit_cents / 100.0
        
        # Win Rate & ROI
        win_rate = (wins / count * 100) if count > 0 else 0
        roi = (profit_cents / (count * 100) * 100) if count > 0 else 0
        
        # Breakdowns
        spread_picks = [p for p in picks if 'spread' in p.get('pick_type', '').lower()]
        total_picks = [p for p in picks if 'total' in p.get('pick_type', '').lower()]
        
        # Spread Stats
        s_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
        s_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
        s_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
        s_profit = sum(p.get('profit_loss', 0) for p in spread_picks)
        s_count = len(spread_picks)
        s_wr = (s_wins / s_count * 100) if s_count > 0 else 0
        s_roi = (s_profit / (s_count * 100) * 100) if s_count > 0 else 0
        
        # Total Stats
        t_wins = sum(1 for p in total_picks if p.get('status', '').lower() == 'win')
        t_losses = sum(1 for p in total_picks if p.get('status', '').lower() == 'loss')
        t_pushes = sum(1 for p in total_picks if p.get('status', '').lower() == 'push')
        t_profit = sum(p.get('profit_loss', 0) for p in total_picks)
        t_count = len(total_picks)
        t_wr = (t_wins / t_count * 100) if t_count > 0 else 0
        t_roi = (t_profit / (t_count * 100) * 100) if t_count > 0 else 0

        return {
            'record': f"{wins}-{losses}" + (f"-{pushes}" if pushes > 0 else ""),
            'wins': wins, 'losses': losses, 'pushes': pushes,
            'win_rate': win_rate,
            'profit': profit_units,
            'roi': roi,
            'count': count,
            'spreads': {
                'record': f"{s_wins}-{s_losses}" + (f"-{s_pushes}" if s_pushes > 0 else ""),
                'win_rate': s_wr,
                'roi': s_roi,
                'count': s_count
            },
            'totals': {
                'record': f"{t_wins}-{t_losses}" + (f"-{t_pushes}" if t_pushes > 0 else ""),
                'win_rate': t_wr,
                'roi': t_roi,
                'count': t_count
            }
        }

    season_stats = calculate_stats(completed_picks)
    
    # Calculate Last 10, Last 20, and Last 50 picks performance (standardized tracking)
    def calculate_recent_performance(picks_list, count):
        """Calculate performance stats for last N picks (most recent first)"""
        recent = picks_list[:count] if len(picks_list) >= count else picks_list
        wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
        losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
        pushes = sum(1 for p in recent if p.get('status', '').lower() == 'push')
        total = wins + losses + pushes
        
        # Profit (cents to units)
        profit_cents = sum(p.get('profit_loss', 0) for p in recent)
        profit_units = profit_cents / 100.0
        
        # Win Rate (excluding pushes) & ROI
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        roi = (profit_cents / (total * 100) * 100) if total > 0 else 0
        
        return {
            'record': f"{wins}-{losses}" + (f"-{pushes}" if pushes > 0 else ""),
            'win_rate': win_rate,
            'profit': profit_units,
            'roi': roi
        }
    
    last_10 = calculate_recent_performance(completed_picks, 10)
    last_20 = calculate_recent_performance(completed_picks, 20)
    last_50 = calculate_recent_performance(completed_picks, 50)
    
    # --- Daily Performance Tracking ---
    from datetime import datetime, timedelta
    import pytz
    
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    today_str = now_et.strftime('%Y-%m-%d')
    yesterday_str = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def get_daily_picks(target_date_str):
        d_picks = []
        for p in completed_picks:
            gd = p.get('game_date', '')
            if not gd: continue
            try:
                dt_utc = datetime.fromisoformat(gd.replace('Z', '+00:00'))
                dt_et = dt_utc.astimezone(et_tz)
                if dt_et.strftime('%Y-%m-%d') == target_date_str:
                    d_picks.append(p)
            except:
                continue
        return d_picks

    today_picks = get_daily_picks(today_str)
    yesterday_picks = get_daily_picks(yesterday_str)
    
    today_stats = calculate_stats(today_picks)
    yesterday_stats = calculate_stats(yesterday_picks)
    
    # Helper for formatting dates in the template
    def format_date_helper(date_str):
        try:
            dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
            est_tz = pytz.timezone('US/Eastern')
            dt_est = dt.astimezone(est_tz)
            return dt_est.strftime('%m/%d %I:%M %p')
        except:
            return date_str

    # Create timestamp string for the report
    et = pytz.timezone('US/Eastern')
    timestamp_str = datetime.now(et).strftime('%Y-%m-%d %I:%M %p ET')

    # Add CLV status to each result
    for result in results:
        result['clv_status_spread'] = None
        result['clv_status_total'] = None
        
        try:
            # Check for matching spread pick
            if '✅' in result.get('ATS Pick', ''):
                spread_pick_id = f"{result['home_team']}_{result['away_team']}_{result['commence_time']}_spread"
                spread_pick = next((p for p in tracking_data.get('picks', []) if p.get('pick_id') == spread_pick_id), None)
                
                if spread_pick:
                    result['clv_status_spread'] = spread_pick.get('clv_status')
            
            # Check for matching total pick
            if '✅' in result.get('Total Pick', ''):
                total_pick_id = f"{result['home_team']}_{result['away_team']}_{result['commence_time']}_total"
                total_pick = next((p for p in tracking_data.get('picks', []) if p.get('pick_id') == total_pick_id), None)
                
                if total_pick:
                    result['clv_status_total'] = total_pick.get('clv_status')
        except Exception as e:
            # Fail gracefully - don't break HTML generation if CLV check fails
            pass

    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics NBA Picks</title>
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

        .team-logos-container {
            display: flex;
            align-items: center;
            gap: 8px;
            position: relative;
        }

        .team-logo {
            width: 44px;
            height: 44px;
            object-fit: contain;
        }

        .away-logo {
            opacity: 0.85; /* Slightly dimmed to show home team prominence */
        }

        .home-logo {
            /* Home team logo is more prominent */
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

        /* Table Styles */
        .tracking-section { margin-top: 3rem; }
        .tracking-header { 
            font-size: 1.5rem; 
            font-weight: 700; 
            color: var(--text-primary); 
            margin-bottom: 1.5rem; 
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        thead { background: var(--bg-metric); }
        th { padding: 0.75rem 1rem; text-align: left; color: var(--text-secondary); font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
        td { padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-color); color: var(--text-primary); font-size: 0.9rem; text-align: left; }
        tr:hover { background: rgba(255,255,255,0.03); }
        
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
        .badge-pending { background: rgba(255, 149, 0, 0.15); color: #ff9f0a; }
        .badge-win { background: rgba(50, 215, 75, 0.15); color: #32d74b; }
        .badge-loss { background: rgba(255, 69, 58, 0.15); color: #ff453a; }
        .badge-push { background: rgba(142, 142, 147, 0.15); color: #8e8e93; }

        .text-green { color: var(--accent-green); }
        .text-red { color: var(--accent-red); }
        .text-gray { color: var(--text-secondary); }
        .font-bold { font-weight: 700; }

        @media (max-width: 768px) {
            body { padding: 1rem; }
            .metrics-row { flex-direction: column; gap: 0.5rem; }
            .metric-box { padding: 0.8rem 0.5rem; }
            .main-pick { font-size: 1.5rem; }
            .header-left { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
            .card-header { align-items: flex-start; }
            
            table { display: block; overflow-x: auto; white-space: nowrap; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>CourtSide Analytics NBA Picks</h1>
                <div class="date-sub">Generated: {{ timestamp }}</div>
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
        {% set home_team_key = r.home_team %}
        {% set away_team_key = r.away_team %}
        {% set home_abbr = team_abbr_map.get(home_team_key, 'nba')|lower %}
        {% set away_abbr = team_abbr_map.get(away_team_key, 'nba')|lower %}
        
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                    <div class="team-logos-container">
                        <img src="https://a.espncdn.com/i/teamlogos/nba/500/{{ away_abbr }}.png" 
                             alt="{{ r.away_team }}" 
                             class="team-logo away-logo"
                             onerror="this.src='https://a.espncdn.com/i/teamlogos/nba/500/nba.png'">
                        <img src="https://a.espncdn.com/i/teamlogos/nba/500/{{ home_abbr }}.png" 
                             alt="{{ r.home_team }}" 
                             class="team-logo home-logo"
                             onerror="this.src='https://a.espncdn.com/i/teamlogos/nba/500/nba.png'">
                    </div>
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
                <div class="metric-box">
                    <div class="metric-title">AI SCORE</div>
                    {% set ai = r.ai_rating if r.ai_rating else 2.5 %}
                    <div class="metric-value {{ 'good' if ai >= 4.0 else '' }}">{{ "%.1f"|format(ai) }}</div>
                </div>
                <!-- Calculate Max EV/Confidence -->
                {% set conf_spread = (r.spread_edge|abs / 10 * 100)|int %}
                {% set conf_total = (r.total_edge|abs / 12 * 100)|int %}
                {% set max_conf = conf_spread if conf_spread > conf_total else conf_total %}
                {% if max_conf > 99 %}{% set max_conf = 99 %}{% endif %}
                
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
                {% if r.team_indicator %}
                <div class="tag tag-blue">{{ r.team_indicator.emoji }} {{ r.team_indicator.message }}</div>
                {% endif %}
                
                {% if r.clv_status_spread %}
                    {% if r.clv_status_spread == 'positive' %}
                        <div class="tag tag-green">✅ CLV: Beat spread</div>
                    {% elif r.clv_status_spread == 'negative' %}
                        <div class="tag tag-red">⚠️ CLV: Missed spread</div>
                    {% else %}
                         <div class="tag tag-blue">➖ CLV: Neutral</div>
                    {% endif %}
                {% elif '✅' in r['ATS Pick'] %}
                     <div class="tag tag-blue">⏳ CLV: Tracking</div>
                {% endif %}

                {% if r.clv_status_total %}
                    {% if r.clv_status_total == 'positive' %}
                        <div class="tag tag-green">✅ CLV: Beat total</div>
                    {% elif r.clv_status_total == 'negative' %}
                        <div class="tag tag-red">⚠️ CLV: Missed total</div>
                    {% else %}
                         <div class="tag tag-blue">➖ CLV: Neutral</div>
                    {% endif %}
                {% elif '✅' in r['Total Pick'] %}
                     <div class="tag tag-blue">⏳ CLV: Tracking</div>
                {% endif %}
                
                {% if r['ATS Explanation'] %}
                <div class="tag tag-green">{{ r['ATS Explanation'][:60] }}...</div>
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
                        <div style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ today_stats.record }}</div>
                        <div style="font-size: 1.2rem; margin-bottom: 0.2rem;" class="{{ 'good' if today_stats.profit > 0 else ('text-red' if today_stats.profit < 0 else '') }}">
                            {{ "%+.1f"|format(today_stats.profit) }}u
                        </div>
                        <div style="font-size: 0.9rem;" class="{{ 'good' if today_stats.roi > 0 else ('text-red' if today_stats.roi < 0 else '') }}">
                            {{ "%.1f"|format(today_stats.roi) }}% ROI
                        </div>
                    </div>
                </div>

                <!-- Yesterday -->
                <div class="prop-card" style="flex: 1; padding: 1.5rem; margin-bottom: 0;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">YESTERDAY</div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem; font-weight: 700; margin-bottom: 0.5rem;">{{ yesterday_stats.record }}</div>
                        <div style="font-size: 1.2rem; margin-bottom: 0.2rem;" class="{{ 'good' if yesterday_stats.profit > 0 else ('text-red' if yesterday_stats.profit < 0 else '') }}">
                            {{ "%+.1f"|format(yesterday_stats.profit) }}u
                        </div>
                        <div style="font-size: 0.9rem;" class="{{ 'good' if yesterday_stats.roi > 0 else ('text-red' if yesterday_stats.roi < 0 else '') }}">
                            {{ "%.1f"|format(yesterday_stats.roi) }}% ROI
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

    # Define team abbreviation map for logos
    team_abbr_map = {
        'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 
        'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 
        'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET', 
        'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND', 
        'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 
        'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 
        'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 
        'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 
        'Phoenix Suns': 'PHX', 'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 
        'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
    }

    template = Template(template_str)
    html_output = template.render(
        results=results,
        timestamp=timestamp_str,
        team_abbr_map=team_abbr_map,
        season_stats=season_stats,
        today_stats=today_stats,
        yesterday_stats=yesterday_stats,
        last_10=last_10,
        last_20=last_20,
        last_50=last_50,
        pending_picks=pending_picks,
        completed_picks=completed_picks,
        format_date=format_date_helper
    )

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"{Colors.GREEN}✓ HTML saved: {HTML_FILE}{Colors.END}")


# =========================
# MAIN EXECUTION
# =========================

def main():
    """Main execution function"""
    print(f"\n{Colors.BOLD}{'='*90}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🎲 IMPROVED NBA BETTING MODEL 🎲{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}⚡ Enhanced Stats + Rest Days + Stricter Filters ⚡{Colors.END}")
    print(f"{Colors.BOLD}{'='*90}{Colors.END}\n")

    # STEP 1: Update old picks
    print(f"{Colors.BOLD}{Colors.CYAN}STEP 1: Checking for Completed Games{Colors.END}")
    update_pick_results()
    generate_tracking_html()

    # STEP 2: Fetch composite stats
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 2: Fetching Composite Stats (Season + Form){Colors.END}")
    composite_stats = fetch_advanced_stats()
    if not composite_stats:
        print(f"\n{Colors.YELLOW}⚠️  Could not fetch advanced stats. Continuing with available data...{Colors.END}")
        # Continue anyway - the model can work with limited data

    # STEP 3: Fetch home/away splits
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 3: Fetching Home/Away Splits{Colors.END}")
    splits_data = fetch_home_away_splits()

    # STEP 4: Fetch team schedules
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 4: Fetching Team Schedules (Rest Days){Colors.END}")
    schedule_data = fetch_team_schedule()

    # STEP 5: Fetch current odds
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 5: Fetching Live Odds (Next {DAYS_AHEAD_TO_FETCH} Days){Colors.END}")
    games = fetch_odds()

    if not games:
        print(f"\n{Colors.YELLOW}⚠️  No games found from The Odds API.{Colors.END}\n")
        return

    # STEP 6: Process and analyze
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 6: Processing Games & Generating Picks{Colors.END}\n")
    results = process_games(games, composite_stats, splits_data, schedule_data)

    if results:
        print(f"\n{Colors.BOLD}{Colors.GREEN}✅ Analyzed {len(results)} games with complete odds{Colors.END}\n")

        # Sort all results by highest edge (spread or total)
        # This puts the most confident plays first
        # Sort by A.I. Rating (primary), with edge as tiebreaker
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

    # STEP 7: Generate final tracking dashboard
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 7: Generating Final Tracking Dashboard{Colors.END}")
    generate_tracking_html()

    # Display tracking summary
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)

    print(f"\n{Colors.BOLD}{'='*90}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}📊 TRACKING SUMMARY 📊{Colors.END}")
    print(f"{Colors.BOLD}{'='*90}{Colors.END}")
    print(f"{Colors.GREEN}Total Tracked Bets: {stats['total_picks']}{Colors.END}")
    print(f"{Colors.GREEN}Record: {stats['wins']}-{stats['losses']}-{stats['pushes']}{Colors.END}")
    print(f"{Colors.GREEN}Win Rate: {stats['win_rate']:.1f}%{Colors.END}")
    profit_color = Colors.GREEN if stats['total_profit'] > 0 else Colors.RED
    print(f"{profit_color}Profit: {stats['total_profit']/100:+.2f} units{Colors.END}")
    print(f"{profit_color}ROI: {stats['roi']:+.1f}%{Colors.END}")
    print(f"{Colors.BOLD}{'='*90}{Colors.END}\n")

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

if __name__ == "__main__":
    main()
