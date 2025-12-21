#!/usr/bin/env python3
"""
Soccer Model - Full Matchup Analysis (NBA Style)
=================================================
Complete soccer betting model with spreads and totals, focusing on unders value.

Key Features:
- Full matchup analysis (like NBA model)
- Spreads and totals for each game
- Game cards showing both markets
- Sharp +EV thresholds
- Unders value focus
- NBA-style dark theme with mobile optimization
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Template
import pytz

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

ODDS_API_KEY = os.getenv('ODDS_API_KEY')
if not ODDS_API_KEY:
    print("FATAL: ODDS_API_KEY not found in .env file.")
    exit()

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
SCRIPT_DIR = Path(__file__).parent
OUTPUT_HTML = SCRIPT_DIR / "soccer_totals_output.html"  # Keep same filename for GitHub Pages
TRACKING_FILE = SCRIPT_DIR / "soccer_picks_tracking.json"

# Sharp +EV thresholds
SPREAD_THRESHOLD = 0.25  # 0.25 goal spread edge to display
TOTAL_THRESHOLD = 0.30   # 0.30 goal total edge to display
CONFIDENT_SPREAD_EDGE = 0.50  # 0.50+ goal edge to log (sharp)
CONFIDENT_TOTAL_EDGE = 0.40   # 0.40+ goal edge to log (sharp) - unders focus

# Home advantage in soccer (typically ~0.3-0.4 goals)
HOME_ADVANTAGE = 0.35

# League averages
LEAGUE_AVG_GOALS = {
    'soccer_epl': 2.65,
    'soccer_spain_la_liga': 2.55,
    'soccer_italy_serie_a': 2.60,
    'soccer_germany_bundesliga': 2.85,
    'soccer_france_ligue_one': 2.55,
    'soccer_usa_mls': 2.80,
}

# Team power ratings (higher = better team)
# Based on recent form and quality
TEAM_RATINGS = {
    # Premier League
    'Arsenal': 72, 'Manchester City': 78, 'Liverpool': 75,
    'Chelsea': 65, 'Tottenham': 68, 'Manchester United': 62,
    'Newcastle': 66, 'Brighton': 64, 'West Ham': 60,
    'Aston Villa': 63, 'Crystal Palace': 58, 'Wolves': 57,
    'Fulham': 56, 'Brentford': 55, 'Everton': 59,
    'Nottingham Forest': 53, 'Burnley': 48, 'Sheffield United': 45,
    
    # La Liga
    'Real Madrid': 80, 'Barcelona': 77, 'Atletico Madrid': 73,
    'Real Sociedad': 68, 'Villarreal': 66, 'Real Betis': 64,
    'Sevilla': 65, 'Valencia': 61, 'Athletic Bilbao': 67,
    'CA Osasuna': 58, 'Getafe': 57, 'Girona': 63,
    
    # Serie A
    'Inter Milan': 76, 'Juventus': 74, 'AC Milan': 72,
    'Napoli': 70, 'Atalanta': 69, 'Roma': 67,
    'Lazio': 68, 'Fiorentina': 64, 'Bologna': 63,
    
    # Bundesliga
    'Bayern Munich': 79, 'Borussia Dortmund': 73,
    'RB Leipzig': 71, 'Bayer Leverkusen': 70,
}

# ============================================================================
# PREDICTION FUNCTIONS
# ============================================================================

def get_league_from_sport_key(sport_key):
    """Extract league name"""
    if 'epl' in sport_key:
        return 'Premier League'
    elif 'la_liga' in sport_key:
        return 'La Liga'
    elif 'serie_a' in sport_key:
        return 'Serie A'
    elif 'bundesliga' in sport_key:
        return 'Bundesliga'
    elif 'ligue_one' in sport_key:
        return 'Ligue 1'
    elif 'mls' in sport_key:
        return 'MLS'
    return sport_key.replace('soccer_', '').replace('_', ' ').title()

def calculate_spread_prediction(home_team, away_team):
    """Calculate predicted goal spread (home - away)"""
    home_rating = TEAM_RATINGS.get(home_team, 60.0)
    away_rating = TEAM_RATINGS.get(away_team, 60.0)
    
    raw_diff = (home_rating - away_rating) / 20.0  # Convert rating to goals
    predicted_spread = raw_diff + HOME_ADVANTAGE
    
    return round(predicted_spread, 2)

def calculate_total_prediction(home_team, away_team, league_avg):
    """Calculate predicted total goals"""
    home_rating = TEAM_RATINGS.get(home_team, 60.0)
    away_rating = TEAM_RATINGS.get(away_team, 60.0)
    
    # Offensive strength (higher rating = more goals scored)
    home_off = (home_rating / 80.0) * 2.0  # Scale to goals
    away_off = (away_rating / 80.0) * 2.0
    
    # Defensive strength (inverse - higher rating = fewer goals allowed)
    home_def_factor = 1.0 - ((home_rating - 50) / 100.0) * 0.3
    away_def_factor = 1.0 - ((away_rating - 50) / 100.0) * 0.3
    
    # Calculate predicted goals
    home_goals = home_off * away_def_factor
    away_goals = away_off * home_def_factor
    
    predicted_total = (home_goals + away_goals) * (league_avg / 2.65)
    
    # Regression to league mean
    predicted_total = (predicted_total * 0.7) + (league_avg * 0.3)
    
    return round(predicted_total, 2)

def calculate_predicted_scores(home_team, away_team, league_avg):
    """Calculate individual team scores"""
    predicted_spread = calculate_spread_prediction(home_team, away_team)
    predicted_total = calculate_total_prediction(home_team, away_team, league_avg)
    
    home_score = (predicted_total + predicted_spread) / 2
    away_score = (predicted_total - predicted_spread) / 2
    
    return round(home_score, 2), round(away_score, 2)

# ============================================================================
# API FUNCTIONS
# ============================================================================

def fetch_soccer_odds(api_key):
    """Fetch soccer odds with spreads and totals"""
    print("\n⚽ Fetching soccer odds (spreads & totals)...")
    
    sports = [
        'soccer_epl',
        'soccer_spain_la_liga',
        'soccer_italy_serie_a',
        'soccer_germany_bundesliga',
        'soccer_france_ligue_one',
        'soccer_usa_mls',
    ]
    
    all_games = []
    
    for sport in sports:
        url = f"{ODDS_API_BASE}/sports/{sport}/odds"
        params = {
            'apiKey': api_key,
            'regions': 'us,us2',
            'markets': 'spreads,totals',
            'oddsFormat': 'american'
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            games = response.json()
            
            for game in games:
                game['sport_key'] = sport
                game['league'] = get_league_from_sport_key(sport)
                all_games.append(game)
            
            if games:
                print(f"   ✅ {get_league_from_sport_key(sport)}: {len(games)} games")
        
        except Exception as e:
            print(f"   ⚠️  {get_league_from_sport_key(sport)}: Error - {e}")
            continue
    
    print(f"\n📊 Total: {len(all_games)} games found")
    return all_games

# ============================================================================
# A.I. RATING SYSTEM
# ============================================================================

def get_historical_performance_by_edge(tracking_data):
    """Calculate win rates by edge magnitude for A.I. Rating system (soccer - goals)"""
    picks = tracking_data.get('picks', [])
    completed_picks = [p for p in picks if p.get('status') in ['win', 'loss']]
    
    from collections import defaultdict
    edge_ranges = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for pick in completed_picks:
        edge = abs(float(pick.get('edge', 0)))
        status = pick.get('status', '')
        
        # Soccer edge ranges (smaller than basketball - goals not points)
        if edge >= 0.8:
            range_key = "0.8+"
        elif edge >= 0.6:
            range_key = "0.6-0.79"
        elif edge >= 0.4:
            range_key = "0.4-0.59"
        elif edge >= 0.3:
            range_key = "0.3-0.39"
        else:
            range_key = "0-0.29"
        
        if status == 'win':
            edge_ranges[range_key]['wins'] += 1
        elif status == 'loss':
            edge_ranges[range_key]['losses'] += 1
    
    performance_by_edge = {}
    for range_key, stats in edge_ranges.items():
        total = stats['wins'] + stats['losses']
        if total >= 5:
            win_rate = stats['wins'] / total if total > 0 else 0.5
            performance_by_edge[range_key] = win_rate
    
    return performance_by_edge

def calculate_ai_rating(analysis, historical_edge_performance):
    """
    Calculate A.I. Rating for soccer (adapted for goal-based edges)
    Returns rating in 2.3-4.9 range
    """
    # Get max edge from bets (in goals)
    max_edge = 0.0
    has_spread_bet = False
    has_total_bet = False
    
    for bet in analysis.get('bets', []):
        edge = abs(bet.get('edge', 0))
        max_edge = max(max_edge, edge)
        if bet.get('type') == 'SPREAD':
            has_spread_bet = True
        elif bet.get('type') == 'TOTAL':
            has_total_bet = True
    
    # Normalize soccer edge to 0-5 scale (0.9 goal edge = 5.0 rating for soccer)
    if max_edge >= 0.9:
        normalized_edge = 5.0
    else:
        normalized_edge = (max_edge / 0.18)  # 0.9 goals = 5.0
        normalized_edge = min(5.0, max(0.0, normalized_edge))
    
    # Data quality
    data_quality = 1.0 if analysis.get('home_score') else 0.85
    
    # Historical performance
    historical_factor = 1.0
    if historical_edge_performance:
        if max_edge >= 0.8:
            range_key = "0.8+"
        elif max_edge >= 0.6:
            range_key = "0.6-0.79"
        elif max_edge >= 0.4:
            range_key = "0.4-0.59"
        elif max_edge >= 0.3:
            range_key = "0.3-0.39"
        else:
            range_key = "0-0.29"
        
        if range_key in historical_edge_performance:
            hist_win_rate = historical_edge_performance[range_key]
            historical_factor = 0.9 + (hist_win_rate - 0.55) * 2.0
            historical_factor = max(0.9, min(1.1, historical_factor))
    
    # Model confidence
    confidence = 1.0
    if max_edge >= 0.7:
        confidence = 1.10
    elif max_edge >= 0.5:
        confidence = 1.05
    elif max_edge >= 0.4:
        confidence = 1.0
    elif max_edge >= 0.3:
        confidence = 0.98
    else:
        confidence = 0.95
    
    if has_spread_bet and has_total_bet:
        confidence *= 1.03
    confidence = max(0.9, min(1.15, confidence))
    
    # Calculate composite rating
    composite_rating = normalized_edge * data_quality * historical_factor * confidence
    
    # Scale to 2.3-4.9 range
    ai_rating = 2.3 + (composite_rating / 5.0) * 2.6
    ai_rating = max(2.3, min(4.9, ai_rating))
    
    return round(ai_rating, 1)

# ============================================================================
# GAME ANALYSIS
# ============================================================================

def analyze_game(game):
    """Analyze a single game for spreads and totals"""
    home_team = game.get('home_team', '')
    away_team = game.get('away_team', '')
    commence_time = game.get('commence_time', '')
    league = game.get('league', 'Unknown')
    sport_key = game.get('sport_key', '')
    
    # Filter out past games (keep games starting within next 7 days)
    if commence_time:
        try:
            from datetime import datetime
            import pytz
            
            # Robust Parse
            if 'Z' in commence_time:
                dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(commence_time)
                
            # Ensure offset-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.utc)
            else:
                dt = dt.astimezone(pytz.utc)
                
            now = datetime.now(pytz.utc)
            
            # Check if game already started
            if dt < now:
                return None
                
            # Check if game is too far in future (> 7 days)
            if (dt - now).total_seconds() > (7 * 24 * 3600):
                return None
        except:
            pass
    
    if not home_team or not away_team:
        return None
    
    league_avg = LEAGUE_AVG_GOALS.get(sport_key, 2.65)
    
    # Get market lines from prioritized bookmakers
    bookmakers = game.get('bookmakers', [])
    if not bookmakers:
        return None
    
    # Prioritize Hard Rock Bet, then FanDuel, then first available
    bookmaker = next((b for b in bookmakers if b['key'] == 'hardrockbet'),
                next((b for b in bookmakers if b['key'] == 'fanduel'), 
                     bookmakers[0]))
    markets = bookmaker.get('markets', [])
    
    spread_market = next((m for m in markets if m['key'] == 'spreads'), None)
    total_market = next((m for m in markets if m['key'] == 'totals'), None)
    
    # Calculate predictions
    predicted_spread = calculate_spread_prediction(home_team, away_team)
    predicted_total = calculate_total_prediction(home_team, away_team, league_avg)
    home_score, away_score = calculate_predicted_scores(home_team, away_team, league_avg)
    
    # Confidence based on data availability
    home_known = home_team in TEAM_RATINGS
    away_known = away_team in TEAM_RATINGS
    if home_known and away_known:
        confidence = 0.85
    elif home_known or away_known:
        confidence = 0.70
    else:
        confidence = 0.55
    
    bets = []
    
    # Analyze spread
    if spread_market:
        home_outcome = next((o for o in spread_market['outcomes'] if o['name'] == home_team), None)
        if home_outcome:
            market_spread = float(home_outcome['point'])
            spread_edge = predicted_spread - market_spread
            
            if abs(spread_edge) >= SPREAD_THRESHOLD:
                if spread_edge > 0:
                    rec_text = f"{home_team} {market_spread:+.2f}"
                else:
                    rec_text = f"{away_team} {-market_spread:+.2f}"
                
                # Determine recommendation string (LEAN vs BET)
                if abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
                    recommendation = rec_text
                else:
                    recommendation = f"(LEAN) {rec_text}"

                bet_data = {
                    'type': 'SPREAD',
                    'market_line': market_spread,
                    'model_prediction': predicted_spread,
                    'edge': spread_edge,
                    'recommendation': recommendation,
                }
                bets.append(bet_data)
                
                # Log confident picks
                if abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
                    log_confident_pick(game, 'SPREAD', spread_edge, predicted_spread, market_spread, rec_text)
    
    # Analyze total (focus on unders)
    if total_market:
        over_outcome = next((o for o in total_market['outcomes'] if o['name'] == 'Over'), None)
        if over_outcome:
            market_total = float(over_outcome['point'])
            total_edge = predicted_total - market_total  # Negative = under value
            
            # Focus on unders (negative edge = under value)
            if total_edge < 0:  # Model predicts lower than market (UNDER value)
                under_edge = abs(total_edge)
                
                if under_edge >= TOTAL_THRESHOLD:
                    rec_text = f"Under {market_total}"
                    
                    if under_edge >= CONFIDENT_TOTAL_EDGE:
                        recommendation = rec_text
                    else:
                        recommendation = f"(LEAN) {rec_text}"
                    
                    bet_data = {
                        'type': 'TOTAL',
                        'market_line': market_total,
                        'model_prediction': predicted_total,
                        'edge': -under_edge,  # Negative = under value
                        'recommendation': recommendation,
                        'direction': 'UNDER',
                    }
                    bets.append(bet_data)
                    
                    # Log confident picks
                    if under_edge >= CONFIDENT_TOTAL_EDGE:
                        log_confident_pick(game, 'TOTAL', -under_edge, predicted_total, market_total, rec_text)

            elif total_edge >= TOTAL_THRESHOLD:  # Over value
                rec_text = f"Over {market_total}"
                
                if total_edge >= CONFIDENT_TOTAL_EDGE:
                    recommendation = rec_text
                else:
                    recommendation = f"(LEAN) {rec_text}"

                bet_data = {
                    'type': 'TOTAL',
                    'market_line': market_total,
                    'model_prediction': predicted_total,
                    'edge': total_edge,
                    'recommendation': recommendation,
                    'direction': 'OVER',
                }
                bets.append(bet_data)
                
                # Log confident picks
                if total_edge >= CONFIDENT_TOTAL_EDGE:
                    log_confident_pick(game, 'TOTAL', total_edge, predicted_total, market_total, rec_text)
    


    # Format game time
    game_time_formatted = commence_time[:10] if commence_time else 'TBD'  # Default to date only
    if commence_time:
        try:
            from datetime import datetime
            import pytz
            dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
            et = pytz.timezone('US/Eastern')
            dt_et = dt.astimezone(et)
            game_time_formatted = dt_et.strftime('%m/%d %I:%M %p ET')
        except:
            pass
    
    analysis_dict = {
        'home_team': home_team,
        'away_team': away_team,
        'league': league,
        'commence_time': commence_time,
        'game_time_formatted': game_time_formatted,
        'predicted_spread': predicted_spread,
        'predicted_total': predicted_total,
        'home_score': home_score,
        'away_score': away_score,
        'confidence': confidence,
        'bets': bets,
    }
    
    return analysis_dict

# ============================================================================
# HTML GENERATION (NBA Style)
# ============================================================================

def generate_html(analyses, tracking_data=None):
    """Generate HTML page with PROPS_HTML_STYLING_GUIDE aesthetic - REVISED COPY"""
    
    # Show all games - display "No edge" for markets without value
    # Only filter out None values, keep games even if they don't have bets meeting thresholds
    analyses = [a for a in analyses if a]

    # Helper for formatting dates in the template
    def format_date_helper(date_str):
        try:
            dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
            est_tz = pytz.timezone('US/Eastern')
            dt_est = dt.astimezone(est_tz)
            return dt_est.strftime('%m/%d %I:%M %p')
        except:
            return date_str
            
    # Load tracking data for header stats if not provided
    if not tracking_data:
        tracking_data = load_picks_tracking()
    
    # Calculate season stats for header
    season_stats = calculate_tracking_stats(tracking_data)
    
    # Add team stats to each analysis (Dec 20, 2024)
    for analysis in analyses:
        analysis['home_team_stats'] = calculate_team_stats(analysis.get('home_team'), tracking_data)
        analysis['away_team_stats'] = calculate_team_stats(analysis.get('away_team'), tracking_data)
    
    # Get completed picks and calculate recent performance
    completed_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() in ['win', 'loss', 'push']]
    # Sort by game_date (most recent first)
    completed_picks.sort(key=lambda x: x.get('game_date', ''), reverse=True)
    
    # Calculate Last 10, Last 20, and Last 50 picks performance
    last_10 = calculate_recent_performance(completed_picks, 10)
    last_20 = calculate_recent_performance(completed_picks, 20)
    last_50 = calculate_recent_performance(completed_picks, 50)
    
    # CSS/HTML Template matches the new revised aesthetic
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soccer Model - Matchup Analysis</title>
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
        
        .metric-title {
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
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
        
        .text-red { color: var(--accent-red); }
        
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
        
        /* Stats Table for Tracking */
        .stats-table {
            width: 100%;
            border-collapse: collapse;
            color: #fff;
            margin-top: 1rem;
        }
        .stats-table th, .stats-table td {
            padding: 10px;
            text-align: center;
            border: 1px solid #333;
        }
        .stats-table th {
            background: #2a2a2a;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }
        .stats-table td {
            background: #1e1e1e;
        }

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
                <h1>⚽ SOCCER MODEL</h1>
                <div class="date-sub">{{ timestamp }}</div>
            </div>
            <div style="text-align: right;">
                <div class="metric-title">SEASON RECORD</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                    {{ season_stats.wins }}-{{ season_stats.losses }}{% if season_stats.pushes > 0 %}-{{ season_stats.pushes }}{% endif %} ({{ "%.1f"|format(season_stats.win_rate) }}%)
                </div>
                <div style="font-size: 0.9rem; color: {{ 'var(--accent-green)' if season_stats.total_profit > 0 else 'var(--accent-red)' }};">
                     {{ "%+.1f"|format(season_stats.total_profit/100) }}u
                </div>
            </div>
        </header>

        {% if analyses|length == 0 %}
        <div class="prop-card" style="text-align: center; padding: 3rem;">
            <p style="color: var(--text-secondary); font-size: 1.1rem;">No upcoming games found matching model criteria.</p>
        </div>
        {% endif %}

        {% for game in analyses %}
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                    <span style="font-size: 2rem; margin-right: 0.5rem;">⚽</span>
                     <div class="matchup-info">
                        <h2>{{ game.away_team }} @ {{ game.home_team }}</h2>
                        <div class="matchup-sub">{{ game.league }}</div>
                    </div>
                </div>
                <div class="game-time-badge">{{ game.game_time_formatted }}</div>
            </div>

            <div class="card-body">
                {# Fix: Use selectattr to find SPREAD/TOTAL bets directly #}
                {% set spread_bet = game.bets|selectattr('type', 'equalto', 'SPREAD')|first %}
                {% set total_bet = game.bets|selectattr('type', 'equalto', 'TOTAL')|first %}

                <!-- SPREAD BET BLOCK -->
                <div class="bet-row">
                    {% if spread_bet and spread_bet.recommendation %}
                    <div class="main-pick {{ 'green' if spread_bet.edge|abs >= CONFIDENT_SPREAD_EDGE else '' }}">{{ spread_bet.recommendation }}</div>
                    {% else %}
                    <div class="main-pick">SPREAD {{ spread_bet.market_line if spread_bet else '--' }}</div>
                    {% endif %}
                    
                    <div class="model-context">
                        Model: {% if spread_bet %}{{ "%.2f"|format(spread_bet.model_prediction) }}{% else %}--{% endif %}
                        <span class="edge-val">Edge: {% if spread_bet %}{{ "%+.2f"|format(spread_bet.edge) }}{% else %}--{% endif %}</span>
                    </div>
                </div>

                <!-- TOTAL BET BLOCK -->
                <div class="bet-row" style="border-bottom: none;">
                    {% if total_bet and total_bet.recommendation %}
                        <div class="main-pick {{ 'green' if total_bet.edge|abs >= CONFIDENT_TOTAL_EDGE else '' }}">{{ total_bet.recommendation }}</div>
                    {% else %}
                        <div class="main-pick">TOTAL {{ total_bet.market_line if total_bet else '--' }}</div>
                    {% endif %}
                    
                    <div class="model-context">
                        Model: {% if total_bet %}{{ "%.2f"|format(total_bet.model_prediction) }}{% else %}--{% endif %}
                        <span class="edge-val">Edge: {% if total_bet %}{{ "%+.2f"|format(total_bet.edge|abs) }}{% else %}--{% endif %}</span>
                    </div>
                </div>

                <!-- METRICS ROW -->
                <div class="metrics-row">
                    <div class="metric-box">
                        <div class="metric-title">PREDICTED SCORE</div>
                        <div class="metric-value">{{ "%.1f"|format(game.away_score) }} - {{ "%.1f"|format(game.home_score) }}</div>
                    </div>
                    
                    <div class="metric-box">
                        <div class="metric-title">CONFIDENCE</div>
                        {% set conf_score = game.confidence * 100 %}
                        <div class="metric-value {{ 'good' if conf_score >= 80 else '' }}">{{ "%.0f"|format(conf_score) }}%</div>
                    </div>
                </div>

                <!-- TEAM BET HISTORY (Dec 20, 2024) -->
                {% if game.home_team_stats or game.away_team_stats %}
                <div class="metrics-row" style="margin-top: 0.75rem;">
                    <div class="metric-box">
                        <div class="metric-title">{{ game.home_team[:12] }} RECORD</div>
                        <div class="metric-value">{{ game.home_team_stats.record if game.home_team_stats else '--' }}</div>
                        {% if game.home_team_stats %}
                        <div style="font-size: 0.75rem; color: {{ 'var(--accent-green)' if game.home_team_stats.roi > 0 else 'var(--accent-red)' }};">{{ "%+.0f"|format(game.home_team_stats.roi) }}% ROI</div>
                        {% endif %}
                    </div>
                    <div class="metric-box">
                        <div class="metric-title">{{ game.away_team[:12] }} RECORD</div>
                        <div class="metric-value">{{ game.away_team_stats.record if game.away_team_stats else '--' }}</div>
                        {% if game.away_team_stats %}
                        <div style="font-size: 0.75rem; color: {{ 'var(--accent-green)' if game.away_team_stats.roi > 0 else 'var(--accent-red)' }};">{{ "%+.0f"|format(game.away_team_stats.roi) }}% ROI</div>
                        {% endif %}
                    </div>
                </div>
                {% endif %}

            </div>
        </div>
        {% endfor %}

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
    
    template = Template(HTML_TEMPLATE)
    html = template.render(
        analyses=analyses,
        timestamp=datetime.now().strftime('%B %d, %Y at %I:%M %p ET'),
        CONFIDENT_SPREAD_EDGE=CONFIDENT_SPREAD_EDGE,
        CONFIDENT_TOTAL_EDGE=CONFIDENT_TOTAL_EDGE,
        TOTAL_THRESHOLD=TOTAL_THRESHOLD,
        last_10=last_10,
        last_20=last_20,
        last_50=last_50,
        season_stats=season_stats # Pass season stats to template
    )
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ HTML saved: {OUTPUT_HTML}")

# ============================================================================
# TRACKING FUNCTIONS
# ============================================================================

def calculate_tracking_summary(picks):
    """Calculate summary statistics from picks"""
    total = len(picks)
    wins = len([p for p in picks if p.get('status', '').lower() == 'win'])
    losses = len([p for p in picks if p.get('status', '').lower() == 'loss'])
    pushes = len([p for p in picks if p.get('status', '').lower() == 'push'])
    pending = len([p for p in picks if p.get('status', '').lower() == 'pending'])

    completed = wins + losses + pushes
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
    
    # Calculate ROI (assuming -110 odds standard)
    roi = (wins * 0.91) - (losses * 1.0)
    roi_pct = (roi / total * 100) if total > 0 else 0.0

    # Calculate CLV
    clv_picks = [p for p in picks if p.get('opening_odds') and p.get('latest_odds')]
    positive_clv = len([p for p in clv_picks if p.get('latest_odds', 0) < p.get('opening_odds', 0)])
    clv_rate = (positive_clv / len(clv_picks) * 100) if clv_picks else 0.0

    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'pending': pending,
        'win_rate': win_rate,
        'roi': roi,
        'roi_pct': roi_pct,
        'clv_rate': clv_rate,
        'clv_count': f"{positive_clv}/{len(clv_picks)}"
    }

def load_tracking():
    """Load tracking data from JSON file"""
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, 'r') as f:
            data = json.load(f)
            # Recalculate summary to ensure it's up to date
            if 'picks' in data:
                data['summary'] = calculate_tracking_summary(data['picks'])
            return data
    return {
        'picks': [],
        'summary': calculate_tracking_summary([])
    }

def save_tracking(tracking_data):
    """Save tracking data to JSON file"""
    with open(TRACKING_FILE, 'w') as f:
        json.dump(tracking_data, f, indent=2)

def log_confident_pick(game_data, pick_type, edge, model_line, market_line, recommendation):
    """Log a confident pick to tracking file"""
    tracking_data = load_tracking()
    
    home_team = game_data.get('home_team', '')
    away_team = game_data.get('away_team', '')
    commence_time = game_data.get('commence_time', '')
    sport_key = game_data.get('sport_key', '')
    league = game_data.get('league', 'Unknown')
    
    # Create pick ID
    pick_id = f"{home_team}_{away_team}_{commence_time}_{pick_type.lower()}"
    
    # Check if already logged - update odds if exists
    existing_pick = next((p for p in tracking_data['picks'] if p.get('pick_id') == pick_id), None)
    if existing_pick:
        # Update odds if they've changed
        odds = extract_odds_from_game(game_data, pick_type, recommendation)
        if odds is not None:
            if existing_pick.get('opening_odds') is None:
                existing_pick['opening_odds'] = odds
            existing_pick['latest_odds'] = odds
            existing_pick['last_updated'] = datetime.now().isoformat()
            save_tracking(tracking_data)
        return
    
    # Extract odds from game data
    odds = extract_odds_from_game(game_data, pick_type, recommendation)
    
    # Determine direction
    if pick_type == 'SPREAD':
        if 'home' in recommendation.lower() or home_team in recommendation:
            direction = 'HOME'
            pick_text = f"{home_team} {market_line}"
        else:
            direction = 'AWAY'
            pick_text = f"{away_team} {abs(market_line)}"
    else:  # TOTAL
        if 'under' in recommendation.lower():
            direction = 'UNDER'
            pick_text = f"UNDER {market_line}"
        else:
            direction = 'OVER'
            pick_text = f"OVER {market_line}"
    
    pick = {
        'pick_id': pick_id,
        'date_logged': datetime.now().isoformat(),
        'game_time': commence_time,
        'home_team': home_team,
        'away_team': away_team,
        'matchup': f"{away_team} @ {home_team}",
        'league': league,
        'sport_key': sport_key,
        'pick_type': pick_type,
        'direction': direction,
        'pick': pick_text,
        'model_line': model_line,
        'market_line': market_line,
        'edge': edge,
        'odds': odds,
        'opening_odds': odds,
        'latest_odds': odds,
        'status': 'pending',
        'result': None,
        'actual_home_score': None,
        'actual_away_score': None,
        'profit_loss': None
    }
    
    tracking_data['picks'].append(pick)
    tracking_data['summary'] = calculate_tracking_summary(tracking_data['picks'])
    
    save_tracking(tracking_data)
    print(f"📝 LOGGED: {pick_type} - {pick_text} (Edge: {edge:+.2f})")

def extract_odds_from_game(game_data, pick_type, recommendation):
    """Extract odds from game data for a specific pick"""
    try:
        bookmakers = game_data.get('bookmakers', [])
        if not bookmakers:
            return None
        
        bookmaker = bookmakers[0]  # Use first bookmaker
        markets = bookmaker.get('markets', [])
        
        if pick_type == 'SPREAD':
            spread_market = next((m for m in markets if m['key'] == 'spreads'), None)
            if not spread_market:
                return None
            
            # Find the outcome matching the recommendation
            home_team = game_data.get('home_team', '')
            away_team = game_data.get('away_team', '')
            
            if home_team in recommendation:
                outcome = next((o for o in spread_market['outcomes'] if o['name'] == home_team), None)
            else:
                outcome = next((o for o in spread_market['outcomes'] if o['name'] == away_team), None)
            
            if outcome:
                return outcome.get('price', -110)
        
        elif pick_type == 'TOTAL':
            total_market = next((m for m in markets if m['key'] == 'totals'), None)
            if not total_market:
                return None
            
            # Find the outcome matching the recommendation
            if 'under' in recommendation.lower():
                outcome = next((o for o in total_market['outcomes'] if o['name'] == 'Under'), None)
            else:
                outcome = next((o for o in total_market['outcomes'] if o['name'] == 'Over'), None)
            
            if outcome:
                return outcome.get('price', -110)
        
        return None
    except Exception as e:
        return None

def fetch_completed_soccer_scores():
    """Fetch completed soccer scores from The Odds API"""
    print("\n⚽ Fetching completed soccer scores...")
    
    sports = [
        'soccer_epl',
        'soccer_spain_la_liga',
        'soccer_italy_serie_a',
        'soccer_germany_bundesliga',
        'soccer_france_ligue_one',
        'soccer_usa_mls',
    ]
    
    all_scores = []
    
    for sport in sports:
        try:
            scores_url = f"{ODDS_API_BASE}/sports/{sport}/scores/"
            params = {
                'apiKey': ODDS_API_KEY,
                'daysFrom': 3  # Check last 3 days
            }
            
            response = requests.get(scores_url, params=params, timeout=10)
            
            if response.status_code == 200:
                scores = response.json()
                completed = [s for s in scores if s.get('completed')]
                all_scores.extend(completed)
                if completed:
                    print(f"   ✅ {get_league_from_sport_key(sport)}: {len(completed)} completed games")
            else:
                print(f"   ⚠️  {get_league_from_sport_key(sport)}: API returned {response.status_code}")
        
        except Exception as e:
            print(f"   ⚠️  {get_league_from_sport_key(sport)}: Error - {e}")
            continue
    
    print(f"\n📊 Total: {len(all_scores)} completed games found")
    return all_scores

def calculate_pick_result(pick, home_score, away_score):
    """Calculate win/loss/push for a pick given actual scores"""
    pick_type = pick.get('pick_type', '')
    direction = pick.get('direction', '')
    market_line = pick.get('market_line', 0)
    
    # Ensure numeric types
    try:
        market_line = float(market_line)
        home_score = float(home_score)
        away_score = float(away_score)
    except (ValueError, TypeError):
        return None, 0
    
    if pick_type == 'SPREAD':
        actual_spread = home_score - away_score
        
        if direction == 'HOME':
            # We bet home team with the spread
            cover_margin = actual_spread - market_line
        else:  # AWAY
            # We bet away team with the spread
            cover_margin = -actual_spread - market_line
        
        if abs(cover_margin) < 0.1:
            return 'Push', 0
        elif cover_margin > 0:
            return 'Win', 91  # Standard -110 payout
        else:
            return 'Loss', -100
    
    elif pick_type == 'TOTAL':
        actual_total = home_score + away_score
        
        if direction == 'UNDER':
            diff = market_line - actual_total
            if abs(diff) < 0.1:
                return 'Push', 0
            elif diff > 0:
                return 'Win', 91
            else:
                return 'Loss', -100
        else:  # OVER
            diff = actual_total - market_line
            if abs(diff) < 0.1:
                return 'Push', 0
            elif diff > 0:
                return 'Win', 91
            else:
                return 'Loss', -100
    
    return None, 0

def update_pick_results():
    """Check for completed games and update pick results using real scores"""
    tracking_data = load_tracking()
    pending_picks = [p for p in tracking_data['picks'] if p.get('status') == 'pending']
    
    if not pending_picks:
        print("\n✅ No pending picks to update")
        return 0
    
    print(f"\n🔍 Checking {len(pending_picks)} pending picks...")
    
    # Fetch completed scores
    completed_scores = fetch_completed_soccer_scores()
    
    if not completed_scores:
        print("⚠️  No completed scores found")
        return 0
    
    # Create lookup dict: (home_team, away_team, sport_key) -> (home_score, away_score)
    scores_dict = {}
    for score in completed_scores:
        home_team = score.get('home_team', '')
        away_team = score.get('away_team', '')
        sport_key = score.get('sport_key', '')
        scores = score.get('scores', [])
        
        if len(scores) >= 2:
            try:
                home_score = float(scores[0].get('score', 0))
                away_score = float(scores[1].get('score', 0))
                key = (home_team, away_team, sport_key)
                scores_dict[key] = (home_score, away_score)
            except (ValueError, TypeError):
                continue
    
    updated_count = 0
    et = pytz.timezone('US/Eastern')
    
    for pick in pending_picks:
        try:
            home_team = pick.get('home_team', '')
            away_team = pick.get('away_team', '')
            sport_key = pick.get('sport_key', '')
            
            # Try to find score
            key = (home_team, away_team, sport_key)
            if key not in scores_dict:
                # Try without sport_key (some APIs may not include it)
                key_alt = (home_team, away_team, '')
                if key_alt in scores_dict:
                    home_score, away_score = scores_dict[key_alt]
                else:
                    continue
            else:
                home_score, away_score = scores_dict[key]
            
            # Calculate result
            result, profit = calculate_pick_result(pick, home_score, away_score)
            
            if result is None:
                continue
            
            # Update pick
            pick['status'] = result.lower()
            pick['result'] = result
            pick['actual_home_score'] = home_score
            pick['actual_away_score'] = away_score
            pick['profit_loss'] = profit
            pick['updated_at'] = datetime.now().isoformat()
            
            updated_count += 1
            
            result_symbol = "✅" if result == 'Win' else "❌" if result == 'Loss' else "➖"
            print(f"  {result_symbol} {pick['matchup']}: {home_score}-{away_score} - {pick['pick']} ({result})")
        
        except Exception as e:
            print(f"  ⚠️  Error updating pick: {e}")
            continue
    
    # Recalculate summary
    tracking_data['summary'] = calculate_tracking_summary(tracking_data['picks'])
    
    save_tracking(tracking_data)
    
    if updated_count > 0:
        wins = tracking_data['summary']['wins']
        losses = tracking_data['summary']['losses']
        pushes = tracking_data['summary']['pushes']
        print(f"\n✅ Updated {updated_count} picks! Record: {wins}-{losses}-{pushes}")
    else:
        print("\n⚠️  No picks were updated")
    
    return updated_count

# ============================================================================
# TRACKING DASHBOARD FUNCTIONS
# ============================================================================

UNIT_SIZE = 100  # Standard bet size for ROI calculations

def load_picks_tracking():
    """Load tracking data from JSON file (compatible with dashboard)"""
    return load_tracking()

def calculate_tracking_stats(tracking_data):
    """Calculate detailed tracking statistics for dashboard"""
    picks = tracking_data.get('picks', [])
    
    total_picks = len(picks)
    wins = sum(1 for p in picks if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in picks if p.get('status', '').lower() == 'loss')
    pushes = sum(1 for p in picks if p.get('status', '').lower() == 'push')
    pending = sum(1 for p in picks if p.get('status', '').lower() == 'pending')
    
    # Calculate profit (profit_loss is in cents)
    total_profit_cents = sum(p.get('profit_loss', 0) for p in picks if p.get('profit_loss') is not None)
    total_profit_units = total_profit_cents / 100.0
    
    # Calculate win rate (excluding pushes and pending)
    decided_picks = wins + losses
    win_rate = (wins / decided_picks * 100) if decided_picks > 0 else 0.0
    
    # Calculate ROI
    total_risked = (wins + losses) * UNIT_SIZE
    roi = (total_profit_cents / total_risked * 100) if total_risked > 0 else 0.0
    
    # Breakdown by type
    spread_picks = [p for p in picks if p.get('pick_type', '').upper() == 'SPREAD']
    total_picks_list = [p for p in picks if p.get('pick_type', '').upper() == 'TOTAL']
    
    spread_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
    spread_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
    spread_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
    
    total_wins = sum(1 for p in total_picks_list if p.get('status', '').lower() == 'win')
    total_losses = sum(1 for p in total_picks_list if p.get('status', '').lower() == 'loss')
    total_pushes = sum(1 for p in total_picks_list if p.get('status', '').lower() == 'push')
    
    return {
        "total_picks": total_picks,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "pending": pending,
        "win_rate": win_rate,
        "total_profit": total_profit_units * 100,  # Return in cents for consistency
        "roi": roi,
        "spread_wins": spread_wins,
        "spread_losses": spread_losses,
        "spread_pushes": spread_pushes,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "total_pushes": total_pushes,
    }

def calculate_team_stats(team_name, tracking_data):
    """Calculate bet history for a specific team (Dec 20, 2024)"""
    if not tracking_data:
        return None
    
    picks = tracking_data.get('picks', [])
    team_picks = [p for p in picks if 
                  p.get('home_team') == team_name or p.get('away_team') == team_name]
    
    completed = [p for p in team_picks if p.get('status', '').lower() in ['win', 'loss']]
    if not completed:
        return None
    
    wins = sum(1 for p in completed if p.get('status', '').lower() == 'win')
    losses = len(completed) - wins
    
    # Calculate profit
    profit_cents = 0
    for p in completed:
        if p.get('profit_loss') is not None:
            profit_cents += p['profit_loss']
        else:
            profit_cents += 91 if p.get('status', '').lower() == 'win' else -100
    
    roi = (profit_cents / 100) / len(completed) * 100 if completed else 0
    
    return {
        'record': f"{wins}-{losses}",
        'profit': profit_cents / 100,
        'roi': roi
    }

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
    
    # Calculate profit (profit_loss is in cents, convert to units)
    profit_cents = sum(p.get('profit_loss', 0) for p in recent if p.get('profit_loss') is not None)
    profit_units = profit_cents / 100.0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (profit_cents / (total * UNIT_SIZE) * 100) if total > 0 else 0
    
    # Breakdown by type (soccer uses uppercase SPREAD/TOTAL)
    spread_picks = [p for p in recent if p.get('pick_type', '').upper() == 'SPREAD']
    total_picks = [p for p in recent if p.get('pick_type', '').upper() == 'TOTAL']
    
    spread_wins = sum(1 for p in spread_picks if p.get('status', '').lower() == 'win')
    spread_losses = sum(1 for p in spread_picks if p.get('status', '').lower() == 'loss')
    spread_pushes = sum(1 for p in spread_picks if p.get('status', '').lower() == 'push')
    spread_total = spread_wins + spread_losses + spread_pushes
    spread_profit_cents = sum(p.get('profit_loss', 0) for p in spread_picks if p.get('profit_loss') is not None)
    spread_profit_units = spread_profit_cents / 100.0
    spread_wr = (spread_wins / spread_total * 100) if spread_total > 0 else 0
    spread_roi = (spread_profit_cents / (spread_total * UNIT_SIZE) * 100) if spread_total > 0 else 0
    
    total_wins = sum(1 for p in total_picks if p.get('status', '').lower() == 'win')
    total_losses = sum(1 for p in total_picks if p.get('status', '').lower() == 'loss')
    total_pushes = sum(1 for p in total_picks if p.get('status', '').lower() == 'push')
    total_total = total_wins + total_losses + total_pushes
    total_profit_cents = sum(p.get('profit_loss', 0) for p in total_picks if p.get('profit_loss') is not None)
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
    """Generate HTML dashboard for tracking picks with last 100/50/20 breakdown"""
    tracking_data = load_picks_tracking()
    stats = calculate_tracking_stats(tracking_data)
    
    # Get current time in Eastern timezone
    est_tz = pytz.timezone('America/New_York')
    current_time = datetime.now(est_tz)
    
    # Separate pending and completed picks
    pending_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() == 'pending']
    completed_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    # Sort by game_time (soccer uses game_time instead of game_date)
    pending_picks.sort(key=lambda x: x.get('game_time', ''))
    completed_picks.sort(key=lambda x: x.get('game_time', ''), reverse=True)
    
    # Calculate Last 100, Last 50, and Last 20 picks performance
    last_100 = calculate_recent_performance(completed_picks, 100)
    last_50 = calculate_recent_performance(completed_picks, 50)
    last_20 = calculate_recent_performance(completed_picks, 20)
    
    def format_game_date(date_str):
        """Format game_time to display date"""
        try:
            dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
            dt_est = dt.astimezone(est_tz)
            return dt_est.strftime('%m/%d %I:%M %p')
        except:
            return str(date_str) if date_str else 'N/A'
    
    timestamp = datetime.now(est_tz).strftime('%Y-%m-%d %I:%M %p')
    
    template_str = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soccer Model - Performance Dashboard</title>
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
        .text-orange-400 { color: #fb923c; }
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

            div[style*="grid-template-columns: repeat(5, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            div[style*="grid-template-columns: repeat(4, 1fr)"] {
                grid-template-columns: repeat(2, 1fr) !important;
            }

            div[style*="grid-template-columns: repeat(2, 1fr)"] {
                grid-template-columns: 1fr !important;
            }

            .grid {
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
                gap: 0.75rem;
            }

            .stat-card {
                padding: 1rem;
            }
            .stat-value {
                font-size: 1.75rem;
            }
            .stat-label {
                font-size: 0.6875rem;
            }

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

            div[style*="grid-template-columns"] {
                grid-template-columns: 1fr !important;
            }

            .grid {
                grid-template-columns: 1fr;
            }

            table { font-size: 0.75rem; }
            th, td { padding: 0.5rem 0.375rem; font-size: 0.75rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1 class="text-center">⚽ Soccer Model Performance</h1>
            <p class="text-center subtitle" style="margin-bottom: 2rem;">CourtSide Analytics</p>

            <!-- Overall Performance Card -->
            <div style="background: #262626; border-radius: 1.25rem; padding: 2rem; margin-bottom: 1.5rem;">
                <h3 style="color: #fb923c; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
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
                        <h4 style="color: #60a5fa; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Spreads ({{ stats.spread_wins + stats.spread_losses + stats.spread_pushes }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #60a5fa; margin-bottom: 0.5rem;">{{ stats.spread_wins }}-{{ stats.spread_losses }}{% if stats.spread_pushes > 0 %}-{{ stats.spread_pushes }}{% endif %}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-blue-400 font-bold">{% if stats.spread_wins + stats.spread_losses > 0 %}{{ "%.1f"|format(stats.spread_wins / (stats.spread_wins + stats.spread_losses) * 100) }}%{% else %}0.0%{% endif %}</span></div>
                            <div><span class="text-gray-400">Profit:</span> <span class="{% if (stats.spread_wins * 91 - stats.spread_losses * 100) > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.2f"|format((stats.spread_wins * 91 - stats.spread_losses * 100) / 100) }}u</span></div>
                        </div>
                    </div>
                    <div style="background: #1a1a1a; border-radius: 1rem; padding: 1.5rem;">
                        <h4 style="color: #f472b6; font-size: 1.125rem; margin-bottom: 1rem; text-align: center;">Totals ({{ stats.total_wins + stats.total_losses + stats.total_pushes }} picks)</h4>
                        <div style="text-align: center; font-size: 1.75rem; font-weight: 700; color: #f472b6; margin-bottom: 0.5rem;">{{ stats.total_wins }}-{{ stats.total_losses }}{% if stats.total_pushes > 0 %}-{{ stats.total_pushes }}{% endif %}</div>
                        <div style="display: flex; justify-content: space-around; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #2a3441;">
                            <div><span class="text-gray-400">Win%:</span> <span class="text-pink-400 font-bold">{% if stats.total_wins + stats.total_losses > 0 %}{{ "%.1f"|format(stats.total_wins / (stats.total_wins + stats.total_losses) * 100) }}%{% else %}0.0%{% endif %}</span></div>
                            <div><span class="text-gray-400">Profit:</span> <span class="{% if (stats.total_wins * 91 - stats.total_losses * 100) > 0 %}text-green-400{% else %}text-red-400{% endif %} font-bold">{{ "%.2f"|format((stats.total_wins * 91 - stats.total_losses * 100) / 100) }}u</span></div>
                        </div>
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
                            <td class="text-sm font-bold">{{ format_game_date(pick.game_time) }}</td>
                            <td class="font-bold">{{ pick.matchup }}</td>
                            <td>{{ pick.pick_type }}</td>
                            <td class="text-yellow-400">{{ pick.pick }}</td>
                            <td>{{ pick.market_line }}</td>
                            <td>{{ "%+.2f"|format(pick.edge) }}</td>
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
                <h3 style="color: #fb923c; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
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
                <h3 style="color: #fb923c; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    🚀 Last 50 Picks
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">{{ last_50.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_50.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">{{ "%.1f"|format(last_50.win_rate) }}%</div>
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
                <h3 style="color: #fb923c; font-size: 1.5rem; margin-bottom: 1.5rem; text-align: center;">
                    ⚡ Last 20 Picks (Hot Streak)
                </h3>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem;">
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">{{ last_20.record }}</div>
                        <div class="stat-label">Record</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value {% if last_20.win_rate >= 50 %}text-green-400{% else %}text-red-400{% endif %}">{{ "%.1f"|format(last_20.win_rate) }}%</div>
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
    
    template = Template(template_str)
    html_output = template.render(
        stats=stats,
        pending_picks=pending_picks,
        last_100=last_100,
        last_50=last_50,
        last_20=last_20,
        timestamp=timestamp,
        format_game_date=format_game_date,
    )
    
    tracking_html_file = SCRIPT_DIR / "soccer_tracking_dashboard.html"
    with open(tracking_html_file, 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print(f"\n✅ Tracking dashboard saved: {tracking_html_file}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("⚽ SOCCER MODEL - FULL MATCHUP ANALYSIS")
    print("=" * 80)
    
    # Update pending picks with real results first
    update_pick_results()
    
    # Fetch odds
    games = fetch_soccer_odds(ODDS_API_KEY)
    
    if not games:
        print("\n⚠️  No games found.")
        return
    
    # Analyze all games
    print("\n🔍 Analyzing games...")
    analyses = []
    
    # Get historical performance for rating
    tracking_data = load_tracking()
    historical_edge_performance = get_historical_performance_by_edge(tracking_data)
    
    # Debug counters
    games_past = 0
    games_too_future = 0
    games_no_markets = 0
    games_no_edges = 0
    
    for game in games:
        analysis = analyze_game(game)
        if analysis:
            # Calculate A.I. Rating
            ai_rating = calculate_ai_rating(analysis, historical_edge_performance)
            analysis['ai_rating'] = ai_rating
            
            # Track games without bets for debugging
            if not analysis.get('bets'):
                games_no_edges += 1
            
            analyses.append(analysis)
        else:
            # Track why games were filtered (rough estimate)
            # Note: analyze_game returns None for various reasons, so this is approximate
            if game.get('commence_time'):
                try:
                    from datetime import datetime as dt_class
                    import pytz
                    dt = dt_class.fromisoformat(game.get('commence_time', '').replace('Z', '+00:00'))
                    now = dt_class.now(pytz.utc)
                    if dt < now:
                        games_past += 1
                    elif (dt - now).total_seconds() > (7 * 24 * 3600):
                        games_too_future += 1
                    else:
                        games_no_markets += 1
                except:
                    games_no_markets += 1
            else:
                games_no_markets += 1
    
    # Debug output
    if games_past > 0 or games_too_future > 0 or games_no_markets > 0:
        print(f"\n🔍 Filtering Breakdown:")
        if games_past > 0:
            print(f"   Games already started: {games_past}")
        if games_too_future > 0:
            print(f"   Games > 7 days away: {games_too_future}")
        if games_no_markets > 0:
            print(f"   Games without markets: {games_no_markets}")
        if games_no_edges > 0:
            print(f"   Games without edges meeting thresholds: {games_no_edges}")
    
    # Count recommendations and add debug output
    games_with_bets = sum(1 for a in analyses if a.get('bets'))
    total_bets = sum(len(a.get('bets', [])) for a in analyses)
    sharp_bets = sum(1 for a in analyses for b in a.get('bets', []) if b.get('recommendation'))
    
    print(f"\n📊 Analysis Summary:")
    print(f"   Games fetched: {len(games)}")
    print(f"   Games analyzed: {len(analyses)}")
    print(f"   Games with bets: {games_with_bets}")
    print(f"   Total bets found: {total_bets}")
    print(f"   Sharp +EV recommendations: {sharp_bets}")
    
    # Generate HTML
    tracking_data = load_tracking()
    
    # Sort analyses by A.I. Rating
    def get_sort_score(analysis):
        rating = analysis.get('ai_rating', 2.3)
        max_edge = 0.0
        for bet in analysis.get('bets', []):
            max_edge = max(max_edge, abs(bet.get('edge', 0)))
        return (rating, max_edge)
    
    analyses = sorted(analyses, key=get_sort_score, reverse=True)
    
    generate_html(analyses, tracking_data)
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

