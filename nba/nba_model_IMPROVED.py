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
    "regions": "us",
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
HOME_COURT_ADVANTAGE = 3.5  # Increased from 2.5 to 3.5
SPREAD_THRESHOLD = 3.0      # Increased from 2.0 - minimum to show
TOTAL_THRESHOLD = 4.0       # Increased from 3.0 - minimum to show

# Stricter thresholds for LOGGING picks (these are the bets we actually track)
CONFIDENT_SPREAD_EDGE = 5.0  # Increased from 3.0 - need 5+ points edge
CONFIDENT_TOTAL_EDGE = 7.0   # Increased from 4.0 - need 7+ points edge
UNIT_SIZE = 100

# Date filtering
DAYS_AHEAD_TO_FETCH = 7

# --- Parameters for Team Form/Momentum ---
LAST_N_GAMES = 10
SEASON_WEIGHT = 0.65    # Slightly less emphasis on full season
FORM_WEIGHT = 0.35      # More emphasis on recent form

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
        "edge": round(edge, 1),
        "pick": pick_text,
        "units": 1,
        "status": "Pending",
        "result": None,
        "profit_loss": 0,
        "actual_home_score": None,
        "actual_away_score": None
    }

    tracking_data['picks'].append(pick_entry)
    tracking_data['summary']['total_picks'] += 1
    tracking_data['summary']['pending'] += 1

    save_picks_tracking(tracking_data)

    print(f"{Colors.GREEN}📝 LOGGED PICK: {pick_text} (Edge: {edge:+.1f}){Colors.END}")

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
        wins = tracking_data['summary']['wins']
        losses = tracking_data['summary']['losses']
        pushes = tracking_data['summary']['pushes']
        print(f"\n{Colors.GREEN}✅ Updated {updated_count} picks! Record: {wins}-{losses}-{pushes}{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}⚠️  No new results found{Colors.END}")

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

def generate_tracking_html():
    """Generate HTML dashboard for tracking picks"""
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)

    # Get current time in Eastern timezone
    est_tz = pytz.timezone('America/New_York')
    current_time = datetime.now(est_tz)

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

    # Get completed picks
    completed_picks = [p for p in tracking_data['picks'] if
                       p.get('status', '').lower() in ['win', 'loss', 'push']]

    pending_picks.sort(key=lambda x: x['game_date'], reverse=False)
    completed_picks.sort(key=lambda x: x['game_date'], reverse=True)

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
    <title>NBA Bet Tracking Dashboard</title>
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
        }
        .stat-card {
            background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
            border: 2px solid #fbbf24;
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 900;
            color: #fbbf24;
        }
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
        h1 { font-size: 2.5rem; font-weight: 900; margin-bottom: 0.5rem; color: #fbbf24; }
        h2 { font-size: 1.875rem; font-weight: 700; margin-bottom: 1.5rem; color: #fbbf24; }
        table { width: 100%; border-collapse: collapse; }
        thead { background: #0a0a0a; }
        th { padding: 0.75rem 1rem; text-align: left; color: #fbbf24; font-weight: 700; }
        td { padding: 0.75rem 1rem; border-bottom: 1px solid #2a2a2a; }
        tr:hover { background: #0a0a0a; }
        .text-center { text-align: center; }
        .text-green-400 { color: #10b981; }
        .text-red-400 { color: #ef4444; }
        .text-yellow-400 { color: #fbbf24; }
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
        .badge-pending { background: #78350f; color: #fbbf24; }
        .badge-win { background: #064e3b; color: #10b981; }
        .badge-loss { background: #450a0a; color: #ef4444; }
        .badge-push { background: #374151; color: #9ca3af; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="text-center">🏀 NBA BET TRACKING</h1>
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

        {% if pending_picks %}
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

        {% if completed_picks %}
        <div class="card">
            <h2>📊 Completed Bets</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Game Date</th>
                            <th>Game</th>
                            <th>Type</th>
                            <th>Pick</th>
                            <th>Line</th>
                            <th>Score</th>
                            <th>Result</th>
                            <th>Profit</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pick in completed_picks %}
                        <tr>
                            <td class="text-sm font-bold">{{ format_game_date(pick.game_date) }}</td>
                            <td class="font-bold">{{ pick.matchup }}</td>
                            <td>{{ pick.pick_type }}</td>
                            <td>{{ pick.pick }}</td>
                            <td>{{ pick.market_line }}</td>
                            <td class="text-sm">{{ pick.actual_away_score }}-{{ pick.actual_home_score }}</td>
                            <td>
                                {% if pick.result == 'Win' %}
                                <span class="badge badge-win">✅ Win</span>
                                {% elif pick.result == 'Loss' %}
                                <span class="badge badge-loss">❌ Loss</span>
                                {% else %}
                                <span class="badge badge-push">➖ Push</span>
                                {% endif %}
                            </td>
                            <td class="font-bold {{ format_profit(pick.profit_loss) }}">
                                {{ "%+.2f"|format(pick.profit_loss/100) }}u
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

    template = Template(template_str)
    html_output = template.render(
        stats=stats,
        pending_picks=pending_picks,
        completed_picks=completed_picks,
        timestamp=timestamp,
        format_profit=format_profit,
        format_game_date=format_game_date
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
    """Fetch and cache advanced team stats from stats.nba.com API."""

    # Check cache first
    if os.path.exists(STATS_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(STATS_FILE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached composite stats (less than 6 hours old){Colors.END}")
            with open(STATS_FILE, 'r') as f:
                return json.load(f)

    print(f"{Colors.CYAN}🔄 Fetching new team stats from stats.nba.com...{Colors.END}")
    try:
        # Fetch full-season stats
        season_stats_data = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Advanced',
            season=CURRENT_SEASON,
            timeout=30
        )
        season_df = season_stats_data.get_data_frames()[0]
        time.sleep(0.6)

        # Fetch last N games stats
        form_stats_data = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Advanced',
            season=CURRENT_SEASON,
            last_n_games=LAST_N_GAMES,
            timeout=30
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
        print(f"{Colors.RED}✗ Error fetching stats: {e}{Colors.END}")
        traceback.print_exc()
        return {}

def fetch_home_away_splits():
    """Fetch and cache home/away split stats."""

    # Check cache
    if os.path.exists(SPLITS_CACHE_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(SPLITS_CACHE_FILE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached home/away splits (less than 6 hours old){Colors.END}")
            with open(SPLITS_CACHE_FILE, 'r') as f:
                return json.load(f)

    print(f"{Colors.CYAN}🔄 Fetching home/away splits from stats.nba.com...{Colors.END}")

    try:
        # Fetch home stats
        home_stats = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Advanced',
            season=CURRENT_SEASON,
            location_nullable='Home',
            timeout=30
        )
        home_df = home_stats.get_data_frames()[0]
        time.sleep(0.6)

        # Fetch road stats
        road_stats = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Advanced',
            season=CURRENT_SEASON,
            location_nullable='Road',
            timeout=30
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
        print(f"{Colors.YELLOW}⚠ Could not fetch splits: {e}{Colors.END}")
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

            bookmaker = game['bookmakers'][0]
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
                "total_edge": total_edge
            }

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
    """Save results to HTML"""
    timestamp_str = datetime.now().strftime('%Y-%m-%d %I:%M %p %Z')

    template_str = '''<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NBA Model Picks</title>
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
            }
           .header-card {
                text-align: center;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                border: 2px solid #fbbf24;
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
                border-left: 4px solid #fbbf24;
            }
           .bet-title {
                font-weight: 700;
                color: #fbbf24;
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
                color: #fbbf24;
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
                background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
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
           .pick small {
                display: block;
                font-size: 0.85rem;
                font-weight: 400;
                margin-top: 0.5rem;
                opacity: 0.9;
                line-height: 1.4;
            }
           .pick-yes { background-color: #064e3b; color: #10b981; border: 2px solid #10b981; }
           .pick-no { background-color: #450a0a; color: #ef4444; border: 2px solid #ef4444; }
           .pick-none { background-color: #1e293b; color: #94a3b8; border: 2px solid #475569; }
           .prediction {
                background: linear-gradient(135deg, #422006 0%, #78350f 100%);
                color: #fbbf24;
                padding: 1rem;
                border-radius: 0.5rem;
                text-align: center;
                font-weight: 800;
                font-size: 1.25rem;
                margin-top: 1rem;
            }
           .badge {
                display: inline-block;
                padding: 0.5rem 1rem;
                border-radius: 9999px;
                font-size: 0.875rem;
                font-weight: 700;
                background-color: #064e3b;
                color: #10b981;
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
                <h1 style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem;">🏀 NBA MODEL PICKS</h1>
                <p style="font-size: 1.25rem; opacity: 0.9;">IMPROVED Model - Stricter Filters</p>
                <div>
                    <div class="badge">● REST DAY TRACKING</div>
                    <div class="badge">● HOME/AWAY SPLITS</div>
                    <div class="badge">● MOMENTUM (Last {{ last_n }} Games)</div>
                    <div class="badge">● 5+ SPREAD | 7+ TOTAL EDGES</div>
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
                                {{ game['ATS Pick'] }}{% if game['ATS Explanation'] %}<br><small>{{ game['ATS Explanation'] }}</small>{% endif %}
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
                                <strong>{{ "%+.1f"|format(game.total_edge|abs) }} pts</strong>
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
                                {{ game['Total Pick'] }}{% if game['Total Explanation'] %}<br><small>{{ game['Total Explanation'] }}</small>{% endif %}
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
        timestamp=timestamp_str,
        last_n=LAST_N_GAMES
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
        print(f"\n{Colors.RED}⚠️  Could not fetch advanced stats. Exiting.{Colors.END}")
        return

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
        display_terminal(results)
        save_csv(results)
        save_html(results)
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

if __name__ == "__main__":
    main()
