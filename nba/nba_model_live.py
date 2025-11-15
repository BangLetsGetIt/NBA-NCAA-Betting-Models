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
CSV_FILE = "nba_model_output.csv"
HTML_FILE = "nba_model_output.html"
STATS_FILE = "nba_stats_cache.json"
SPLITS_CACHE_FILE = "nba_home_away_splits_cache.json"

# NEW: Tracking files
PICKS_TRACKING_FILE = "nba_picks_tracking.json"
TRACKING_HTML_FILE = "nba_tracking_dashboard.html"

# IMPORTANT: Update this to the current NBA season (e.g., '2025-26')
CURRENT_SEASON = '2025-26' 

# --- Model Parameters ---
HOME_COURT_ADVANTAGE = 2.5
SPREAD_THRESHOLD = 2.0  # Minimum edge to show as a pick
TOTAL_THRESHOLD = 3.0   # Minimum edge to show as a pick

# NEW: Tracking Parameters
CONFIDENT_SPREAD_EDGE = 3.0  # Edge needed to LOG and TRACK a spread pick
CONFIDENT_TOTAL_EDGE = 4.0   # Edge needed to LOG and TRACK a total pick
UNIT_SIZE = 100  # Standard bet size in dollars (for tracking)

# NEW: Date filtering parameter
DAYS_AHEAD_TO_FETCH = 7  # Only fetch games within next 7 days

# --- Parameters for Team Form/Momentum ---
LAST_N_GAMES = 10       
SEASON_WEIGHT = 0.70    
FORM_WEIGHT = 0.30      

# --- Parameters for Home/Away Splits ---
USE_HOME_AWAY_SPLITS = True  
SPLITS_WEIGHT = 0.50         
COMPOSITE_WEIGHT = 0.50      

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

# Map API names to nba_api names
TEAM_NAME_MAP = {
    "LA Clippers": "Los Angeles Clippers",
}

# =========================
# TRACKING FUNCTIONS
# =========================

def normalize_team_name(team_name):
    """Normalize team names for consistent matching across APIs"""
    name = team_name.strip()
    
    # Comprehensive mapping - handles variations from different APIs
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
    # Create backup before saving
    if os.path.exists(PICKS_TRACKING_FILE):
        backup_file = f"{PICKS_TRACKING_FILE}.backup"
        shutil.copy2(PICKS_TRACKING_FILE, backup_file)
        print(f"{Colors.CYAN}✓ Backup created: {backup_file}{Colors.END}")
    
    with open(PICKS_TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)
    print(f"{Colors.GREEN}✓ Tracking data saved to {PICKS_TRACKING_FILE}{Colors.END}")
    print(f"{Colors.GREEN}  Total picks in file: {len(tracking_data['picks'])}{Colors.END}")

def log_confident_pick(game_data, pick_type, edge, model_line, market_line):
    """
    Log a confident pick to the tracking file
    
    Args:
        game_data: Dictionary with game information
        pick_type: 'spread' or 'total'
        edge: The calculated edge value
        model_line: Model's predicted line
        market_line: Market's current line
    """
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
    
    print(f"{Colors.GREEN}📝 LOGGED CONFIDENT PICK: {pick_text} (Edge: {edge:+.1f}){Colors.END}")

def update_pick_results():
    """
    Check for completed games and update pick results
    This should be run after games complete
    """
    tracking_data = load_picks_tracking()
    updated = False
    
    print(f"\n{Colors.CYAN}{'='*90}{Colors.END}")
    print(f"{Colors.CYAN}🔄 UPDATING RESULTS FOR COMPLETED GAMES{Colors.END}")
    print(f"{Colors.CYAN}{'='*90}{Colors.END}")
    
    # Show current tracking status
    pending_picks = [p for p in tracking_data['picks'] if p['status'] == 'Pending']
    completed_picks = [p for p in tracking_data['picks'] if p['status'] == 'Completed']
    
    print(f"\n{Colors.YELLOW}📊 CURRENT STATUS:{Colors.END}")
    print(f"  Total Picks: {len(tracking_data['picks'])}")
    print(f"  Completed: {len(completed_picks)}")
    print(f"  Pending: {len(pending_picks)}")
    
    if not pending_picks:
        print(f"\n{Colors.GREEN}✓ No pending picks to update{Colors.END}")
        return
    
    print(f"\n{Colors.YELLOW}📋 PENDING PICKS WAITING FOR RESULTS:{Colors.END}")
    for i, pick in enumerate(pending_picks, 1):
        pick_home = normalize_team_name(pick['home_team'])
        pick_away = normalize_team_name(pick['away_team'])
        game_date = pick.get('game_date', 'Unknown')[:10]  # Just the date part
        print(f"  {i}. {pick_away} @ {pick_home} ({pick['pick_type']}) - Game Date: {game_date}")
    
    # Get recent game results from NBA API
    print(f"\n{Colors.CYAN}🔍 SEARCHING NBA API FOR COMPLETED GAMES...{Colors.END}\n")
    
    try:
        today = datetime.now()
        # Check last 7 days for completed games
        for days_ago in range(7):
            check_date = (today - timedelta(days=days_ago)).strftime('%m/%d/%Y')
            
            print(f"{Colors.BOLD}Checking {check_date}...{Colors.END}")
            
            try:
                scoreboard = scoreboardv2.ScoreboardV2(game_date=check_date)
                all_dfs = scoreboard.get_data_frames()
                
                # DataFrame 0 has game info, DataFrame 1 has team line scores
                games_df = all_dfs[0]
                line_scores_df = all_dfs[1]
                
                if games_df.empty:
                    print(f"  No games on this date")
                    continue
                
                games_found = 0
                for _, game in games_df.iterrows():
                    game_id = game['GAME_ID']
                    game_status = str(game.get('GAME_STATUS_TEXT', ''))
                    
                    # Only process Final games
                    if 'Final' not in game_status:
                        continue
                    
                    games_found += 1
                    
                    # Get team names from the line scores dataframe
                    game_lines = line_scores_df[line_scores_df['GAME_ID'] == game_id]
                    
                    if len(game_lines) < 2:
                        continue
                    
                    # Find home and away teams
                    home_team = None
                    away_team = None
                    home_score = 0
                    away_score = 0
                    
                    for _, team_line in game_lines.iterrows():
                        team_name = normalize_team_name(team_line['TEAM_NAME'])
                        team_id = team_line['TEAM_ID']
                        # Calculate total points
                        pts = sum([
                            team_line.get('PTS_QTR1', 0) or 0,
                            team_line.get('PTS_QTR2', 0) or 0,
                            team_line.get('PTS_QTR3', 0) or 0,
                            team_line.get('PTS_QTR4', 0) or 0,
                            team_line.get('PTS_OT1', 0) or 0,
                            team_line.get('PTS_OT2', 0) or 0,
                            team_line.get('PTS_OT3', 0) or 0,
                        ])
                        
                        # Determine if home or away
                        if team_id == game['HOME_TEAM_ID']:
                            home_team = team_name
                            home_score = int(pts)
                        else:
                            away_team = team_name
                            away_score = int(pts)
                    
                    if not home_team or not away_team:
                        continue
                    
                    actual_total = home_score + away_score
                    actual_spread = home_score - away_score  # Positive means home won
                    
                    print(f"  ✓ Found: {away_team} {away_score} @ {home_team} {home_score}")
                    
                    # Find pending picks for this game
                    matches_found = 0
                    for pick in tracking_data['picks']:
                        if pick['status'] != 'Pending':
                            continue
                        
                        # Match by team names using normalization
                        pick_home = normalize_team_name(pick['home_team'])
                        pick_away = normalize_team_name(pick['away_team'])
                        
                        # Exact matching after normalization
                        if pick_home == home_team and pick_away == away_team:
                            matches_found += 1
                            print(f"    🎯 MATCH! Updating {pick['pick_type']}: {pick['pick']}")
                            
                            # Update the pick result
                            pick['actual_home_score'] = home_score
                            pick['actual_away_score'] = away_score
                            
                            # Determine result based on pick type
                            if pick['pick_type'] == 'Spread':
                                market_spread = float(pick['market_line'])
                                pick_text = pick['pick']
                                
                                # Determine which team was picked
                                if pick_home in pick_text:
                                    # Betting on home team: (actual_spread) + (spread) > 0 to win
                                    cover_margin = actual_spread + market_spread
                                else:
                                    # Betting on away team: (-actual_spread) + (-spread) > 0 to win  
                                    cover_margin = -actual_spread - market_spread
                                
                                print(f"      Spread Check: actual={actual_spread:+d}, line={market_spread:+.1f}, margin={cover_margin:+.1f}")
                                
                                if abs(cover_margin) < 0.01:  # Push
                                    pick['result'] = 'Push'
                                    pick['profit_loss'] = 0
                                    print(f"      ➖ PUSH")
                                elif cover_margin > 0:  # Win
                                    pick['result'] = 'Win'
                                    pick['profit_loss'] = 100
                                    print(f"      ✅ WIN (+1.00 units)")
                                else:  # Loss
                                    pick['result'] = 'Loss'
                                    pick['profit_loss'] = -110
                                    print(f"      ❌ LOSS (-1.10 units)")
                            
                            elif pick['pick_type'] == 'Total':
                                market_total = float(pick['market_line'])
                                pick_text = pick['pick']
                                total_diff = actual_total - market_total
                                
                                print(f"      Total Check: actual={actual_total}, line={market_total:.1f}, diff={total_diff:+.1f}")
                                
                                if abs(total_diff) < 0.01:  # Push
                                    pick['result'] = 'Push'
                                    pick['profit_loss'] = 0
                                    print(f"      ➖ PUSH")
                                elif 'OVER' in pick_text and total_diff > 0:  # Over wins
                                    pick['result'] = 'Win'
                                    pick['profit_loss'] = 100
                                    print(f"      ✅ WIN (+1.00 units)")
                                elif 'UNDER' in pick_text and total_diff < 0:  # Under wins
                                    pick['result'] = 'Win'
                                    pick['profit_loss'] = 100
                                    print(f"      ✅ WIN (+1.00 units)")
                                else:  # Loss
                                    pick['result'] = 'Loss'
                                    pick['profit_loss'] = -110
                                    print(f"      ❌ LOSS (-1.10 units)")
                            
                            pick['status'] = 'Completed'
                            updated = True
                    
                    if matches_found == 0:
                        print(f"    ⚠️  No pending picks matched this game")
                
                if games_found == 0:
                    print(f"  No completed games on this date")
                
                time.sleep(0.6)  # Rate limiting
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
    
    except Exception as e:
        print(f"\n{Colors.RED}✗ Error updating results: {e}{Colors.END}")
        traceback.print_exc()
    
    # Recalculate summary from actual pick data
    tracking_data['summary'] = {
        'total_picks': len(tracking_data['picks']),
        'wins': sum(1 for p in tracking_data['picks'] if p.get('result') == 'Win'),
        'losses': sum(1 for p in tracking_data['picks'] if p.get('result') == 'Loss'),
        'pushes': sum(1 for p in tracking_data['picks'] if p.get('result') == 'Push'),
        'pending': sum(1 for p in tracking_data['picks'] if p.get('status') == 'Pending')
    }
    
    save_picks_tracking(tracking_data)
    
    if updated:
        wins = tracking_data['summary']['wins']
        losses = tracking_data['summary']['losses']
        pushes = tracking_data['summary']['pushes']
        print(f"\n{Colors.GREEN}{'='*90}{Colors.END}")
        print(f"{Colors.GREEN}✅ RESULTS UPDATED! Record: {wins}-{losses}-{pushes}{Colors.END}")
        print(f"{Colors.GREEN}{'='*90}{Colors.END}")
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
    
    # Calculate win rate (excluding pushes)
    decided = stats['wins'] + stats['losses']
    if decided > 0:
        stats['win_rate'] = (stats['wins'] / decided) * 100
    
    # Calculate profit
    stats['total_profit'] = sum(p['profit_loss'] for p in tracking_data['picks'])
    
    # Calculate ROI
    total_risked = decided * 110  # Risk 110 to win 100
    if total_risked > 0:
        stats['roi'] = (stats['total_profit'] / total_risked) * 100
    
    return stats

def generate_tracking_html():
    """Generate HTML dashboard for tracking picks"""
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)
    
    # Separate pending and completed picks
    pending_picks = [p for p in tracking_data['picks'] if p['status'] == 'Pending']
    completed_picks = [p for p in tracking_data['picks'] if p['status'] in ['Win', 'Loss', 'Push']]
    
    # Sort by date (most recent first)
    pending_picks.sort(key=lambda x: x['game_date'], reverse=False)
    completed_picks.sort(key=lambda x: x['game_date'], reverse=True)
    
    def format_profit(profit):
        """Format profit with color class"""
        if profit > 0:
            return 'text-green-400'
        elif profit < 0:
            return 'text-red-400'
        return 'text-gray-400'
    
    def format_game_date(date_str):
        """Format game date in EST timezone"""
        # Parse UTC time
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Convert to EST
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
# TEAM NAME NORMALIZATION
# =========================

def get_team_name(api_name):
    """Converts API team name to stats team name using the map."""
    return TEAM_NAME_MAP.get(api_name, api_name)

# =========================
# MODEL CALCULATIONS
# =========================

def calculate_model_spread(home_team, away_team, stats, splits_data=None):
    """Calculate predicted spread using composite stats and optionally home/away splits."""
    try:
        home_team_name = get_team_name(home_team)
        away_team_name = get_team_name(away_team)
        
        # Use splits for spread calculation when available
        if USE_HOME_AWAY_SPLITS and splits_data and splits_data.get('Home') and splits_data.get('Road'):
            if home_team_name in splits_data['Home'] and away_team_name in splits_data['Road']:
                home_rating = splits_data['Home'][home_team_name]['NET_RATING']
                away_rating = splits_data['Road'][away_team_name]['NET_RATING']
                
                spread = (home_rating - away_rating) + HOME_COURT_ADVANTAGE
                return round(spread, 1)
        
        # Fallback to composite only
        home_stats = stats[home_team_name]['NET_RATING']
        away_stats = stats[away_team_name]['NET_RATING']
        
        spread = (home_stats - away_stats) + HOME_COURT_ADVANTAGE
        return round(spread, 1)
    
    except KeyError as e:
        print(f"{Colors.RED}Missing stats for team: {e}{Colors.END}")
        return 0.0

def calculate_model_total(home_team, away_team, stats, splits_data=None):
    """Calculate predicted total based on Pace and Offensive/Defensive Ratings."""
    try:
        home_team_name = get_team_name(home_team)
        away_team_name = get_team_name(away_team)
        
        # Use composite stats for totals
        home_stats = stats[home_team_name]
        away_stats = stats[away_team_name]
        
        avg_pace = (home_stats['Pace'] + away_stats['Pace']) / 2
        avg_efficiency = (home_stats['OffRtg'] + away_stats['OffRtg']) / 2
        
        total = (avg_pace / 100) * avg_efficiency * 2
        
        # Sanity check
        if total < 190 or total > 250:
            print(f"{Colors.YELLOW}WARNING: Unusual total {total:.1f} for {home_team} vs {away_team}{Colors.END}")
            total = max(190, min(250, total))
        
        return round(total, 1)
    
    except KeyError as e:
        print(f"{Colors.RED}Missing stats for team: {e}{Colors.END}")
        return 0.0

def predicted_score(model_spread, model_total):
    """Calculate predicted final scores"""
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

        # Check what columns are actually available (NBA API column names can vary)
        print(f"{Colors.CYAN}Available columns: {list(season_df.columns)[:10]}...{Colors.END}")
        
        # Determine correct column names
        team_name_col = None
        team_abbr_col = None
        
        for col in season_df.columns:
            if 'TEAM' in col.upper() and 'NAME' in col.upper() and 'ABBREVIATION' not in col.upper():
                team_name_col = col
            if 'TEAM' in col.upper() and ('ABBR' in col.upper() or 'ABBREVIATION' in col.upper()):
                team_abbr_col = col
        
        if not team_name_col:
            # Fallback: use TEAM_ID and get name another way
            team_name_col = 'TEAM_ID'
        
        # Blend season and form stats
        stats_dict = {}
        for _, row in season_df.iterrows():
            # Get team identifiers
            team_name = row.get(team_name_col, row.get('TEAM_NAME', 'Unknown'))
            team_id = row.get('TEAM_ID', None)
            
            # Get season stats
            season_net_rating = row.get('NET_RATING', 0)
            season_pace = row.get('PACE', 100)
            season_off_rtg = row.get('OFF_RATING', 110)
            season_def_rtg = row.get('DEF_RATING', 110)
            
            # Get form stats for this team using TEAM_ID (most reliable)
            form_row = form_df[form_df['TEAM_ID'] == team_id] if team_id else pd.DataFrame()
            if not form_row.empty:
                form_net_rating = form_row.iloc[0].get('NET_RATING', season_net_rating)
                form_pace = form_row.iloc[0].get('PACE', season_pace)
                form_off_rtg = form_row.iloc[0].get('OFF_RATING', season_off_rtg)
                form_def_rtg = form_row.iloc[0].get('DEF_RATING', season_def_rtg)
            else:
                form_net_rating, form_pace, form_off_rtg, form_def_rtg = season_net_rating, season_pace, season_off_rtg, season_def_rtg
            
            # Blend (70% season, 30% form)
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
            team_name = row.get('TEAM_NAME', row.get('TEAM_ID', 'Unknown'))
            splits_dict["Home"][team_name] = {
                "NET_RATING": row.get('NET_RATING', 0),
                "Pace": row.get('PACE', 100),
                "OffRtg": row.get('OFF_RATING', 110),
                "DefRtg": row.get('DEF_RATING', 110)
            }
        
        # Process road stats
        for _, row in road_df.iterrows():
            team_name = row.get('TEAM_NAME', row.get('TEAM_ID', 'Unknown'))
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
                
                # Only include games within the next N days
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
# PROCESS GAMES
# =========================

def process_games(games, stats, splits_data=None):
    """Process each game and generate predictions"""
    results = []
    
    for game in games:
        try:
            home_team = game['home_team']
            away_team = game['away_team']
            commence_time = game['commence_time']
            
            # Convert to Eastern Time
            dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            eastern = pytz.timezone('US/Eastern')
            dt_eastern = dt.astimezone(eastern)
            game_time = dt_eastern.strftime('%m/%d/%y %I:%M %p %Z')
            
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
            home_spread = next((o['point'] for o in spread_market['outcomes'] if o['name'] == home_team), None)
            market_total = total_market['outcomes'][0]['point'] if total_market['outcomes'] else None
            
            if home_spread is None or market_total is None:
                continue
            
            # Calculate model predictions
            model_spread = calculate_model_spread(home_team, away_team, stats, splits_data)
            model_total = calculate_model_total(home_team, away_team, stats, splits_data)
            
            # Calculate edges
            # This is the "value" calculation.
            # A positive edge means the model is *higher* on the home team than the market.
            # e.g. Model +10.6, Market -3.0. Edge = (+10.6) - (-3.0) = +13.6. Bet HOME.
            # e.g. Model +3.4, Market -20.5. Edge = (+3.4) - (-20.5) = +23.9. Bet HOME.
            spread_edge = model_spread - home_spread
            total_edge = model_total - market_total
            
            # Predicted scores
            pred_home, pred_away = predicted_score(model_spread, model_total)
            
            # Determine picks with explanations
            ats_pick = ""
            ats_explanation = ""
            
            # *** NEW LOGIC ***
            if spread_edge > SPREAD_THRESHOLD:
                # Value is on the HOME team.
                ats_pick = f"✅ BET: {home_team} {home_spread:+.1f}"
                ats_explanation = f"Model projects {home_team} to win by {model_spread:+.1f}."

            elif spread_edge < -SPREAD_THRESHOLD:
                # Value is on the AWAY team.
                away_spread = -home_spread
                ats_pick = f"✅ BET: {away_team} {away_spread:+.1f}"
                ats_explanation = f"Model projects {home_team} to win by only {model_spread:+.1f}."
                
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
            
            # Log confident picks for tracking
            if '✅' in ats_pick and abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
                log_confident_pick(result, 'spread', spread_edge, model_spread, home_spread)
            
            if '✅' in total_pick and abs(total_edge) >= CONFIDENT_TOTAL_EDGE:
                log_confident_pick(result, 'total', total_edge, model_total, market_total)
            
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Error processing game: {e}{Colors.END}")
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
    """Save results to HTML with confidence bars and mobile optimization"""
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
                <p style="font-size: 1.25rem; opacity: 0.9;">Real-time odds from The Odds API</p>
                <div>
                    <div class="badge">● TEAM MOMENTUM (Last {{ last_n }} Games)</div>
                    <div class="badge">● HOME/AWAY SPLITS</div>
                    <div class="badge">● DYNAMIC STATS MODEL</div>
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
    print(f"{Colors.BOLD}{Colors.CYAN}🎲 NBA BETTING MODEL WITH TRACKING 🎲{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}⚡ Team Momentum + Home/Away Splits + Auto Tracking ⚡{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}📅 Filtering games within next {DAYS_AHEAD_TO_FETCH} days{Colors.END}")
    print(f"{Colors.BOLD}{'='*90}{Colors.END}\n")
    
    # CRITICAL: Update old picks FIRST before adding new ones
    print(f"{Colors.BOLD}{Colors.CYAN}STEP 1: Checking for Completed Games & Updating Past Picks{Colors.END}")
    update_pick_results()
    generate_tracking_html()
    
    # Fetch composite stats
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 2: Fetching Composite Stats (Season + Form){Colors.END}")
    composite_stats = fetch_advanced_stats()
    if not composite_stats:
        print(f"\n{Colors.RED}⚠️  Could not fetch advanced stats. Exiting.{Colors.END}")
        return
    
    # Fetch home/away splits
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 3: Fetching Home/Away Splits{Colors.END}")
    splits_data = fetch_home_away_splits()
    
    # Fetch current odds
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 4: Fetching Live Odds (Next {DAYS_AHEAD_TO_FETCH} Days){Colors.END}")
    games = fetch_odds()
    
    if not games:
        print(f"\n{Colors.YELLOW}⚠️  No games found from The Odds API in next {DAYS_AHEAD_TO_FETCH} days.{Colors.END}\n")
        return
    
    # Process and analyze
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 5: Processing Games & Generating New Picks{Colors.END}\n")
    results = process_games(games, composite_stats, splits_data)
    
    if results:
        print(f"\n{Colors.BOLD}{Colors.GREEN}✅ Analyzed {len(results)} games with complete odds{Colors.END}\n")
        display_terminal(results)
        save_csv(results)
        save_html(results)
    else:
        print(f"\n{Colors.YELLOW}⚠️  No games with complete betting lines found.{Colors.END}\n")
    
    # Generate final tracking dashboard with both old and new picks
    print(f"\n{Colors.BOLD}{Colors.CYAN}STEP 6: Generating Final Tracking Dashboard{Colors.END}")
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

