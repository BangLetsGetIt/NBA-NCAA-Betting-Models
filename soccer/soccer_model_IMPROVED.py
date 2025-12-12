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
            'regions': 'us',
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
# GAME ANALYSIS
# ============================================================================

def analyze_game(game):
    """Analyze a single game for spreads and totals"""
    home_team = game.get('home_team', '')
    away_team = game.get('away_team', '')
    commence_time = game.get('commence_time', '')
    league = game.get('league', 'Unknown')
    sport_key = game.get('sport_key', '')
    
    if not home_team or not away_team:
        return None
    
    league_avg = LEAGUE_AVG_GOALS.get(sport_key, 2.65)
    
    # Get market lines from first bookmaker
    bookmakers = game.get('bookmakers', [])
    if not bookmakers:
        return None
    
    bookmaker = bookmakers[0]
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
                    recommendation = f"{home_team} {market_spread:+.2f}"
                else:
                    recommendation = f"{away_team} {-market_spread:+.2f}"
                
                bet_data = {
                    'type': 'SPREAD',
                    'market_line': market_spread,
                    'model_prediction': predicted_spread,
                    'edge': spread_edge,
                    'recommendation': recommendation if abs(spread_edge) >= CONFIDENT_SPREAD_EDGE else None,
                }
                bets.append(bet_data)
                
                # Log confident picks
                if abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
                    log_confident_pick(game, 'SPREAD', spread_edge, predicted_spread, market_spread, recommendation)
    
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
                    recommendation = f"Under {market_total}" if under_edge >= CONFIDENT_TOTAL_EDGE else None
                    
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
                        log_confident_pick(game, 'TOTAL', -under_edge, predicted_total, market_total, recommendation)
            elif total_edge >= TOTAL_THRESHOLD:  # Over value
                recommendation = f"Over {market_total}" if total_edge >= CONFIDENT_TOTAL_EDGE else None
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
                    log_confident_pick(game, 'TOTAL', total_edge, predicted_total, market_total, recommendation)
    
    return {
        'home_team': home_team,
        'away_team': away_team,
        'league': league,
        'commence_time': commence_time,
        'predicted_spread': predicted_spread,
        'predicted_total': predicted_total,
        'home_score': home_score,
        'away_score': away_score,
        'confidence': confidence,
        'bets': bets,
    }

# ============================================================================
# HTML GENERATION (NBA Style)
# ============================================================================

def generate_html(analyses):
    """Generate NBA-style HTML with game cards"""
    
    # Filter to games with analysis
    analyses = [a for a in analyses if a and a.get('bets')]
    
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Soccer Model - Full Matchup Analysis</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
    background: #0a1628;
    color: #ffffff;
    padding: 1.5rem;
    min-height: 100vh;
}
.container { max-width: 1200px; margin: 0 auto; }
.card {
    background: #1a2332;
    border-radius: 1.25rem;
    border: none;
    padding: 2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}
.header-card {
    text-align: center;
    background: #1a2332;
    border: none;
}
.game-card {
    padding: 1.5rem;
    border-bottom: 1px solid #2a3441;
}
.game-card:last-child { border-bottom: none; }
.matchup { font-size: 1.5rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem; }
.game-time { color: #94a3b8; font-size: 0.875rem; margin-bottom: 1rem; }
.league-badge {
    background: rgba(96, 165, 250, 0.2);
    color: #60a5fa;
    padding: 0.25rem 0.75rem;
    border-radius: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 0.5rem;
}
.bet-section {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-top: 1rem;
}
.bet-box {
    background: #2a3441;
    padding: 1.25rem;
    border-radius: 1rem;
    border-left: none;
}
.bet-box-spread {
    border-left: 4px solid #60a5fa;
}
.bet-box-total {
    border-left: 4px solid #f472b6;
}
.bet-title {
    font-weight: 600;
    color: #94a3b8;
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
}
.bet-title-spread { color: #60a5fa; }
.bet-title-total { color: #f472b6; }
.odds-line {
    display: flex;
    justify-content: space-between;
    margin: 0.25rem 0;
    font-size: 0.9375rem;
    color: #94a3b8;
}
.odds-line strong {
    color: #ffffff;
    font-weight: 600;
}
.confidence-bar-container {
    margin: 0.75rem 0;
}
.confidence-label {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    color: #94a3b8;
}
.confidence-pct {
    font-weight: 700;
    color: #4ade80;
}
.confidence-bar {
    height: 6px;
    background: #1a2332;
    border-radius: 999px;
    overflow: hidden;
    border: none;
}
.confidence-fill {
    height: 100%;
    background: #4ade80;
    border-radius: 999px;
    transition: width 0.3s ease;
}
.pick {
    font-weight: 600;
    padding: 0.875rem 1rem;
    margin-top: 0.75rem;
    border-radius: 0.75rem;
    font-size: 1rem;
    line-height: 1.5;
}
.pick small {
    display: block;
    font-size: 0.8125rem;
    font-weight: 400;
    margin-top: 0.5rem;
    opacity: 0.85;
    line-height: 1.4;
}
.pick-yes { background: rgba(74, 222, 128, 0.15); color: #4ade80; border: 2px solid #4ade80; }
.pick-no { background: rgba(248, 113, 113, 0.15); color: #f87171; border: 2px solid #f87171; }
.pick-none { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 2px solid #475569; }
.prediction {
    background: #2a3441;
    color: #4ade80;
    padding: 1rem;
    border-radius: 1rem;
    text-align: center;
    font-weight: 700;
    font-size: 1.125rem;
    margin-top: 1rem;
    border: 1px solid #2a3441;
}
@media (max-width: 768px) {
    body { padding: 1rem; }
    .card { padding: 1.25rem; }
    .game-card { padding: 1.25rem; }
    .bet-section { grid-template-columns: 1fr; gap: 1rem; }
    .matchup { font-size: 1.25rem; }
}
</style>
</head>
<body>
<div class="container">
<div class="card header-card">
<h1>⚽ Soccer Model - Full Matchup Analysis</h1>
<p style="color: #94a3b8; margin-top: 0.5rem;">Focusing on Unders Value | Generated {{timestamp}}</p>
</div>

{% for analysis in analyses %}
{% set game_time = analysis.commence_time %}
{% set matchup = analysis.away_team + " @ " + analysis.home_team %}
{% set spread_bet = analysis.bets|selectattr('type', 'equalto', 'SPREAD')|first %}
{% set total_bet = analysis.bets|selectattr('type', 'equalto', 'TOTAL')|first %}

<div class="card game-card">
<div class="matchup">{{matchup}}<span class="league-badge">{{analysis.league}}</span></div>
<div class="game-time">🕐 {{game_time[0:10]}}</div>

<div class="bet-section">
{% if spread_bet %}
{% set edge = spread_bet.edge %}
{% set edge_abs = edge|abs %}
{% set pick_class = 'pick-yes' if edge_abs >= CONFIDENT_SPREAD_EDGE else 'pick-none' %}
{% set pick_icon = '✅' if edge_abs >= CONFIDENT_SPREAD_EDGE else '⚠️' %}
{% set explanation = 'SHARP +EV' if edge_abs >= CONFIDENT_SPREAD_EDGE else 'Below sharp threshold' %}
<div class="bet-box bet-box-spread">
<div class="bet-title bet-title-spread">📊 SPREAD</div>
<div class="odds-line">
<span>Market Line:</span>
<strong>{{"{:+.2f}".format(spread_bet.market_line)}}</strong>
</div>
<div class="odds-line">
<span>Model Prediction:</span>
<strong>{{"{:+.2f}".format(spread_bet.model_prediction)}}</strong>
</div>
<div class="odds-line">
<span>Edge:</span>
<strong>{{"{:+.2f}".format(edge)}} goals</strong>
</div>
<div class="confidence-bar-container">
<div class="confidence-label">
<span>Confidence</span>
<span class="confidence-pct">{{(analysis.confidence * 100)|int}}%</span>
</div>
<div class="confidence-bar">
<div class="confidence-fill" style="width: {{(analysis.confidence * 100)|int}}%"></div>
</div>
</div>
<div class="pick {{pick_class}}">
{{pick_icon}} {{spread_bet.recommendation if spread_bet.recommendation else 'NO BET'}}<br>
<small>{{explanation}}</small>
</div>
</div>
{% else %}
<div class="bet-box bet-box-spread">
<div class="bet-title bet-title-spread">📊 SPREAD</div>
<div class="pick pick-none">❌ NO BET<br><small>Insufficient edge</small></div>
</div>
{% endif %}

{% if total_bet %}
{% set edge = total_bet.edge %}
{% set is_under = total_bet.direction == 'UNDER' %}
{% set edge_abs = edge|abs %}
{% set pick_class = 'pick-yes' if edge_abs >= CONFIDENT_TOTAL_EDGE else 'pick-none' %}
{% set pick_icon = '✅' if edge_abs >= CONFIDENT_TOTAL_EDGE else '⚠️' %}
{% if edge_abs >= CONFIDENT_TOTAL_EDGE and is_under %}
{% set explanation = 'SHARP +EV UNDER' %}
{% elif edge_abs >= TOTAL_THRESHOLD %}
{% set explanation = 'Below threshold' %}
{% else %}
{% set explanation = 'Insufficient edge' %}
{% endif %}
<div class="bet-box bet-box-total">
<div class="bet-title bet-title-total">🎯 TOTAL</div>
<div class="odds-line">
<span>Market Total:</span>
<strong>{{"{:.2f}".format(total_bet.market_line)}}</strong>
</div>
<div class="odds-line">
<span>Model Projects:</span>
<strong>{{"{:.2f}".format(total_bet.model_prediction)}} goals</strong>
</div>
<div class="odds-line">
<span>Edge:</span>
<strong>{{"{:.2f}".format(edge_abs)}} goals {% if is_under %}(UNDER){% else %}(OVER){% endif %}</strong>
</div>
<div class="confidence-bar-container">
<div class="confidence-label">
<span>Confidence</span>
<span class="confidence-pct">{{(analysis.confidence * 100)|int}}%</span>
</div>
<div class="confidence-bar">
<div class="confidence-fill" style="width: {{(analysis.confidence * 100)|int}}%"></div>
</div>
</div>
<div class="pick {{pick_class}}">
{{pick_icon}} {{total_bet.recommendation if total_bet.recommendation else 'NO BET'}}<br>
<small>{{explanation}}</small>
</div>
</div>
{% else %}
<div class="bet-box bet-box-total">
<div class="bet-title bet-title-total">🎯 TOTAL</div>
<div class="pick pick-none">❌ NO BET<br><small>Insufficient edge</small></div>
</div>
{% endif %}
</div>

<div class="prediction">
Predicted: {{analysis.home_team}} {{analysis.home_score}} - {{analysis.away_score}} {{analysis.away_team}}
</div>
</div>
{% endfor %}

</div>
</body>
</html>
"""
    
    template = Template(HTML_TEMPLATE)
    html = template.render(
        analyses=analyses,
        timestamp=datetime.now().strftime('%B %d, %Y at %I:%M %p ET'),
        CONFIDENT_SPREAD_EDGE=CONFIDENT_SPREAD_EDGE,
        CONFIDENT_TOTAL_EDGE=CONFIDENT_TOTAL_EDGE,
        TOTAL_THRESHOLD=TOTAL_THRESHOLD,
    )
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ HTML saved: {OUTPUT_HTML}")

# ============================================================================
# TRACKING FUNCTIONS
# ============================================================================

def load_tracking():
    """Load tracking data from JSON file"""
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return {
        'picks': [],
        'summary': {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'pushes': 0,
            'pending': 0
        }
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
    
    # Check if already logged
    if any(p.get('pick_id') == pick_id for p in tracking_data['picks']):
        return
    
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
        'status': 'pending',
        'result': None,
        'actual_home_score': None,
        'actual_away_score': None,
        'profit_loss': None
    }
    
    tracking_data['picks'].append(pick)
    tracking_data['summary']['total'] = len(tracking_data['picks'])
    tracking_data['summary']['pending'] = sum(1 for p in tracking_data['picks'] if p.get('status') == 'pending')
    
    save_tracking(tracking_data)
    print(f"📝 LOGGED: {pick_type} - {pick_text} (Edge: {edge:+.2f})")

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
            home_score = scores[0].get('score', 0)
            away_score = scores[1].get('score', 0)
            key = (home_team, away_team, sport_key)
            scores_dict[key] = (home_score, away_score)
    
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
    tracking_data['summary'] = {
        'total': len(tracking_data['picks']),
        'wins': sum(1 for p in tracking_data['picks'] if p.get('status', '').lower() == 'win'),
        'losses': sum(1 for p in tracking_data['picks'] if p.get('status', '').lower() == 'loss'),
        'pushes': sum(1 for p in tracking_data['picks'] if p.get('status', '').lower() == 'push'),
        'pending': sum(1 for p in tracking_data['picks'] if p.get('status', '').lower() == 'pending')
    }
    
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
    
    for game in games:
        analysis = analyze_game(game)
        if analysis:
            analyses.append(analysis)
    
    # Count recommendations
    sharp_bets = sum(1 for a in analyses for b in a.get('bets', []) if b.get('recommendation'))
    print(f"\n✅ Analyzed {len(analyses)} games")
    print(f"🔥 {sharp_bets} sharp +EV recommendations")
    
    # Generate HTML
    generate_html(analyses)
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

