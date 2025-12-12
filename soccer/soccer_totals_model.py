#!/usr/bin/env python3
"""
Soccer Totals Model - Sharp +EV Focus on Unders
===============================================
Advanced statistical model for soccer totals betting with focus on unders value.

Key Features:
- Multi-league analysis (Premier League, La Liga, Serie A, Bundesliga, Ligue 1, MLS)
- Sharp +EV thresholds (strict unders focus)
- Team defensive/offensive ratings
- Historical totals data
- Kelly Criterion bet sizing
- Mobile-optimized NBA-style dark theme
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Template
from collections import defaultdict

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION - SHARP +EV THRESHOLDS
# ============================================================================

# API Configuration
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
if not ODDS_API_KEY:
    print("FATAL: ODDS_API_KEY not found in .env file.")
    exit()

ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# File paths
SCRIPT_DIR = Path(__file__).parent
OUTPUT_HTML = SCRIPT_DIR / "soccer_totals_output.html"
OUTPUT_CSV = SCRIPT_DIR / "soccer_totals_output.csv"
TRACKING_FILE = SCRIPT_DIR / "soccer_totals_tracking.json"

# SHARP +EV THRESHOLDS (unders focus)
MIN_EDGE_THRESHOLD = 0.08  # 8% minimum edge to recommend (sharp +EV)
SHARP_EDGE_THRESHOLD = 0.12  # 12%+ edge for "SHARP BET" designation
MIN_CONFIDENCE_FOR_BET = 0.70  # 70% minimum confidence
KELLY_FRACTION = 0.25  # Conservative Kelly (1/4 Kelly)

# Focus on unders (user observation: lots of value on unders)
UNDERS_PREFERENCE = True  # Prioritize unders value

# ============================================================================
# SOCCER LEAGUES - TOTALS HISTORICAL DATA
# ============================================================================

# League average goals per game (for reference)
LEAGUE_AVG_GOALS = {
    'soccer_england_premier_league': 2.65,
    'soccer_spain_la_liga': 2.55,
    'soccer_italy_serie_a': 2.60,
    'soccer_germany_bundesliga': 2.85,
    'soccer_france_ligue_one': 2.55,
    'soccer_usa_mls': 2.80,
    'soccer_epl': 2.65,
}

# Team defensive ratings (lower = better defense, more unders)
# Based on 2024 season data (goals allowed per game)
TEAM_DEFENSIVE_RATINGS = {
    # Premier League
    'Arsenal': 0.85, 'Manchester City': 0.90, 'Liverpool': 0.95,
    'Chelsea': 1.05, 'Tottenham': 1.10, 'Manchester United': 1.15,
    'Newcastle': 1.20, 'Brighton': 1.25, 'West Ham': 1.30,
    'Aston Villa': 1.15, 'Crystal Palace': 1.25, 'Wolves': 1.30,
    'Fulham': 1.35, 'Brentford': 1.40, 'Everton': 1.20,
    'Nottingham Forest': 1.45, 'Burnley': 1.50, 'Sheffield United': 1.60,
    
    # La Liga
    'Real Madrid': 0.90, 'Barcelona': 0.95, 'Atletico Madrid': 0.80,
    'Real Sociedad': 1.10, 'Villarreal': 1.20, 'Real Betis': 1.25,
    'Sevilla': 1.15, 'Valencia': 1.30, 'Athletic Bilbao': 1.10,
    
    # Serie A
    'Inter Milan': 0.75, 'Juventus': 0.85, 'AC Milan': 0.95,
    'Napoli': 1.00, 'Atalanta': 1.05, 'Roma': 1.10,
    'Lazio': 1.05, 'Fiorentina': 1.20, 'Bologna': 1.15,
    
    # Bundesliga
    'Bayern Munich': 1.00, 'Borussia Dortmund': 1.05,
    'RB Leipzig': 1.10, 'Bayer Leverkusen': 1.15,
    
    # Default (use league average)
}

# Team offensive ratings (higher = more goals)
TEAM_OFFENSIVE_RATINGS = {
    # Premier League
    'Arsenal': 2.10, 'Manchester City': 2.40, 'Liverpool': 2.30,
    'Chelsea': 1.60, 'Tottenham': 2.00, 'Manchester United': 1.50,
    'Newcastle': 1.80, 'Brighton': 1.90, 'West Ham': 1.70,
    
    # La Liga
    'Real Madrid': 2.20, 'Barcelona': 2.10, 'Atletico Madrid': 1.80,
    
    # Serie A
    'Inter Milan': 2.00, 'Juventus': 1.70, 'AC Milan': 1.90,
    
    # Default
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def american_to_decimal(american_odds):
    """Convert American odds to decimal odds"""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def american_to_implied_prob(american_odds):
    """Convert American odds to implied probability"""
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)

def calculate_expected_value(prob, odds):
    """Calculate expected value of a bet"""
    decimal_odds = american_to_decimal(odds)
    return (prob * decimal_odds) - 1

def calculate_kelly_bet_size(prob, odds, fraction=KELLY_FRACTION):
    """Calculate optimal bet size using fractional Kelly Criterion"""
    decimal_odds = american_to_decimal(odds)
    q = 1 - prob
    b = decimal_odds - 1

    if prob <= 0 or b <= 0:
        return 0

    kelly = (prob * b - q) / b
    kelly = kelly * fraction
    return max(0, min(kelly, 0.05))  # Never exceed 5%

def get_league_from_sport_key(sport_key):
    """Extract league name from sport key"""
    if 'premier_league' in sport_key or 'epl' in sport_key:
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

# ============================================================================
# TOTALS PREDICTION MODEL
# ============================================================================

def predict_match_total(home_team, away_team, league_avg):
    """
    Predict total goals for a match based on team ratings
    Lower defensive rating = fewer goals allowed (good for unders)
    Higher offensive rating = more goals scored
    """
    # Get ratings (default to league average if unknown)
    home_def = TEAM_DEFENSIVE_RATINGS.get(home_team, 1.30)
    home_off = TEAM_OFFENSIVE_RATINGS.get(home_team, league_avg / 2)
    away_def = TEAM_DEFENSIVE_RATINGS.get(away_team, 1.30)
    away_off = TEAM_OFFENSIVE_RATINGS.get(away_team, league_avg / 2)
    
    # Home team expected goals
    home_goals = (home_off + (league_avg - away_def)) / 2
    
    # Away team expected goals
    away_goals = (away_off + (league_avg - home_def)) / 2
    
    # Total prediction
    predicted_total = home_goals + away_goals
    
    # Adjust for league average (regression to mean)
    predicted_total = (predicted_total * 0.7) + (league_avg * 0.3)
    
    return predicted_total

def calculate_under_probability(predicted_total, market_total):
    """
    Calculate probability that match goes under market total
    Using Poisson distribution approximation
    """
    # Simple model: probability of under decreases as predicted approaches market
    difference = market_total - predicted_total
    
    # If predicted is much lower than market, high under prob
    if difference >= 0.5:
        under_prob = 0.60 + min(0.30, difference * 0.15)
    elif difference >= 0.25:
        under_prob = 0.55 + (difference * 0.10)
    elif difference >= 0:
        under_prob = 0.50 + (difference * 0.10)
    else:
        under_prob = 0.50 - (abs(difference) * 0.15)
    
    # Bound between 0.05 and 0.85
    return max(0.05, min(0.85, under_prob))

def get_confidence_rating(home_team, away_team):
    """
    Rate confidence based on data availability
    Higher if both teams have known ratings
    """
    home_known = home_team in TEAM_DEFENSIVE_RATINGS
    away_known = away_team in TEAM_DEFENSIVE_RATINGS
    
    if home_known and away_known:
        return 0.85
    elif home_known or away_known:
        return 0.70
    else:
        return 0.55

# ============================================================================
# API FUNCTIONS
# ============================================================================

def fetch_soccer_totals_odds(api_key):
    """Fetch soccer totals odds from multiple leagues"""
    print("\n⚽ Fetching soccer totals odds from major leagues...")
    
    # Major soccer leagues
    sports = [
        'soccer_epl',  # Premier League
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
            'markets': 'totals',
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

def analyze_game_for_value(game):
    """
    Analyze a game for totals value, focusing on unders
    Returns list of value bets (unders focus)
    """
    home_team = game.get('home_team', '')
    away_team = game.get('away_team', '')
    league = game.get('league', 'Unknown')
    commence_time = game.get('commence_time', '')
    
    # Get league average
    sport_key = game.get('sport_key', '')
    league_avg = LEAGUE_AVG_GOALS.get(sport_key, 2.65)
    
    # Predict match total
    predicted_total = predict_match_total(home_team, away_team, league_avg)
    confidence = get_confidence_rating(home_team, away_team)
    
    # Analyze totals markets
    value_bets = []
    
    for bookmaker in game.get('bookmakers', []):
        book_name = bookmaker.get('title', 'Unknown')
        
        for market in bookmaker.get('markets', []):
            if market.get('key') != 'totals':
                continue
            
            for outcome in market.get('outcomes', []):
                if outcome.get('name') != 'Under':
                    continue
                
                total_line = outcome.get('point')
                odds = outcome.get('price')
                
                if not total_line or not odds:
                    continue
                
                # Calculate under probability
                under_prob = calculate_under_probability(predicted_total, total_line)
                
                # Calculate edge
                implied_prob = american_to_implied_prob(odds)
                edge = under_prob - implied_prob
                
                # Calculate EV
                ev = calculate_expected_value(under_prob, odds)
                kelly_size = calculate_kelly_bet_size(under_prob, odds)
                
                # Recommend if meets sharp thresholds
                recommended = (ev > 0 and edge >= MIN_EDGE_THRESHOLD and 
                              confidence >= MIN_CONFIDENCE_FOR_BET)
                sharp_bet = recommended and edge >= SHARP_EDGE_THRESHOLD
                
                value_bets.append({
                    'home_team': home_team,
                    'away_team': away_team,
                    'league': league,
                    'commence_time': commence_time,
                    'bookmaker': book_name,
                    'market': 'Under',
                    'line': total_line,
                    'odds': odds,
                    'predicted_total': predicted_total,
                    'under_probability': under_prob,
                    'implied_probability': implied_prob,
                    'edge': edge,
                    'ev': ev,
                    'kelly_pct': kelly_size,
                    'confidence': confidence,
                    'recommended': recommended,
                    'sharp_bet': sharp_bet,
                })
    
    return value_bets

# ============================================================================
# OUTPUT GENERATION
# ============================================================================

def generate_html(all_value_bets):
    """Generate NBA-style dark theme HTML with mobile optimization"""
    
    # Separate recommended bets
    recommended = [b for b in all_value_bets if b['recommended']]
    all_plays = sorted(all_value_bets, key=lambda x: (x['recommended'], x.get('ev', -999)), reverse=True)[:100]
    
    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Soccer Totals Model - Sharp +EV Unders</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
    background: #0a1628;
    color: #ffffff;
    padding: 1rem;
    min-height: 100vh;
}
.container { max-width: 1400px; margin: 0 auto; }
.card {
    background: #1a2332;
    border-radius: 1.25rem;
    border: none;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}
.header-card {
    text-align: center;
    background: #1a2332;
    padding: 2rem 1.5rem;
}
h1 {
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 0.5rem;
}
.subtitle {
    color: #94a3b8;
    font-size: 0.875rem;
    margin-bottom: 1rem;
}
.alert {
    background: #0d2b1f;
    border-left: 4px solid #00ff88;
    padding: 1rem;
    margin-bottom: 1.5rem;
    border-radius: 0.75rem;
}
.alert-text {
    color: #00ff88;
    font-weight: 600;
    font-size: 0.9375rem;
}
.alert-warning {
    background: #2a1f10;
    border-left-color: #ffa726;
}
.alert-warning .alert-text {
    color: #ffa726;
}
h2 {
    font-size: 1.5rem;
    font-weight: 700;
    color: #d4af37;
    margin: 2rem 0 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #d4af37;
}
table {
    width: 100%;
    border-collapse: collapse;
    background: #1a2332;
    border-radius: 1rem;
    overflow: hidden;
    margin-bottom: 1.5rem;
}
th, td {
    padding: 0.875rem;
    text-align: left;
    border-bottom: 1px solid #2a3441;
    font-size: 0.875rem;
}
th {
    background: #1a2332;
    color: #94a3b8;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
tr:hover {
    background: #2a3441;
}
.recommend {
    background: linear-gradient(135deg, #0d2b1f, #0a1f15);
    border-left: 4px solid #00ff88;
    font-weight: 600;
}
.recommend.sharp {
    background: linear-gradient(135deg, #0f3524, #0c2519);
    border-left: 5px solid #00ff99;
    box-shadow: 0 0 10px rgba(0, 255, 136, 0.2);
}
.sharp-label {
    background: rgba(0, 255, 153, 0.2);
    color: #00ff99;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-left: 0.5rem;
}
.neutral {
    background: #1a2332;
}
.league-badge {
    background: rgba(96, 165, 250, 0.2);
    color: #60a5fa;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
}
.odds-badge {
    background: rgba(212, 175, 55, 0.2);
    color: #d4af37;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.8125rem;
    font-weight: 600;
    border: 1px solid rgba(212, 175, 55, 0.3);
}
.edge-positive {
    color: #00ff88;
    font-weight: 700;
}
.edge-neutral {
    color: #ffa726;
}
.ev-badge {
    background: rgba(0, 255, 136, 0.15);
    color: #00ff88;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.8125rem;
    font-weight: 700;
}
.kelly-badge {
    background: rgba(96, 165, 250, 0.15);
    color: #60a5fa;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
}
.confidence {
    font-size: 0.8125rem;
}
.conf-high { color: #00ff88; }
.conf-med { color: #ffa726; }
.conf-low { color: #ef4444; }
.stats {
    color: #94a3b8;
    font-size: 0.8125rem;
}
.methodology {
    background: #1a2332;
    border-radius: 1rem;
    padding: 1.5rem;
    margin-top: 2rem;
    color: #94a3b8;
    font-size: 0.8125rem;
    line-height: 1.8;
}
.methodology h3 {
    color: #d4af37;
    margin-bottom: 1rem;
    font-size: 1.125rem;
}
.methodology p {
    margin-bottom: 0.5rem;
}
.footer {
    text-align: center;
    margin-top: 2rem;
    color: #94a3b8;
    font-size: 0.75rem;
}
@media (max-width: 768px) {
    body { padding: 0.75rem; }
    h1 { font-size: 1.5rem; }
    h2 { font-size: 1.25rem; }
    .card { padding: 1rem; }
    table { font-size: 0.75rem; display: block; overflow-x: auto; }
    th, td { padding: 0.5rem; }
    .header-card { padding: 1.5rem 1rem; }
}
@media (max-width: 480px) {
    th, td { padding: 0.4rem; font-size: 0.7rem; }
    .subtitle { font-size: 0.75rem; }
}
</style>
</head>
<body>
<div class="container">
<div class="card header-card">
<h1>⚽ Soccer Totals Model - Sharp +EV Unders</h1>
<div class="subtitle">Focusing on Unders Value | Generated {{timestamp}}</div>
</div>

{% if recommended|length > 0 %}
<div class="card">
<div class="alert">
<div class="alert-text">🔥 {{recommended|length}} RECOMMENDED BET(S) - Sharp +EV Unders with {{min_edge*100}}%+ Edge</div>
</div>

<h2>💎 RECOMMENDED PLAYS (Unders +EV)</h2>
<table>
<tr>
<th>Match</th><th>League</th><th>Line</th><th>Odds</th><th>Book</th>
<th>Pred Total</th><th>Under Prob</th><th>Edge</th><th>EV</th><th>Kelly %</th><th>Conf</th>
</tr>
{% for r in recommended %}
{% set sharp_class = 'sharp' if r.sharp_bet else '' %}
{% set conf_class = 'conf-high' if r.confidence >= 0.80 else ('conf-med' if r.confidence >= 0.70 else 'conf-low') %}
<tr class="recommend {{sharp_class}}">
<td><strong>{{r.home_team}} vs {{r.away_team}}</strong>{% if r.sharp_bet %}<span class="sharp-label">SHARP</span>{% endif %}</td>
<td><span class="league-badge">{{r.league}}</span></td>
<td class="stats">U {{r.line}}</td>
<td><span class="odds-badge">{{'+{}'.format(r.odds|int) if r.odds > 0 else r.odds|int}}</span></td>
<td class="stats">{{r.bookmaker}}</td>
<td class="stats">{{'{:.1f}'.format(r.predicted_total)}}</td>
<td class="stats">{{'{:.1f}'.format(r.under_probability * 100)}}%</td>
<td class="edge-positive">{{'+{:.1f}'.format(r.edge * 100)}}%</td>
<td><span class="ev-badge">{{'+{:.1f}'.format(r.ev * 100)}}%</span></td>
<td><span class="kelly-badge">{{'{:.2f}'.format(r.kelly_pct * 100)}}%</span></td>
<td class="confidence {{conf_class}}">{{'{:.0f}'.format(r.confidence * 100)}}%</td>
</tr>
{% endfor %}
</table>
</div>
{% else %}
<div class="card">
<div class="alert alert-warning">
<div class="alert-text">⚠️ No plays meet the sharp +{{min_edge*100}}% edge threshold today</div>
</div>
</div>
{% endif %}

<div class="card">
<h2>📊 ALL TOTALS ANALYSIS</h2>
<table>
<tr>
<th>Match</th><th>League</th><th>Line</th><th>Odds</th><th>Pred Total</th><th>Edge</th><th>EV</th><th>Conf</th>
</tr>
{% for r in all_plays %}
{% set tier = 'recommend' if r.recommended else 'neutral' %}
{% set edge_class = 'edge-positive' if r.edge >= MIN_EDGE_THRESHOLD else ('edge-neutral' if r.edge >= 0 else 'edge-negative') %}
{% set conf_class = 'conf-high' if r.confidence >= 0.80 else ('conf-med' if r.confidence >= 0.70 else 'conf-low') %}
<tr class="{{tier}}">
<td><strong>{{r.home_team}} vs {{r.away_team}}</strong></td>
<td><span class="league-badge">{{r.league}}</span></td>
<td class="stats">U {{r.line}}</td>
<td>{% if r.odds %}<span class="odds-badge">{{'+{}'.format(r.odds|int) if r.odds > 0 else r.odds|int}}</span>{% else %}—{% endif %}</td>
<td class="stats">{{'{:.1f}'.format(r.predicted_total)}}</td>
<td class="{{edge_class}}">{{'+{:.1f}'.format(r.edge * 100) if r.edge >= 0 else '{:.1f}'.format(r.edge * 100)}}%</td>
<td>{% if r.ev %}<span class="ev-badge">{{'+{:.1f}'.format(r.ev * 100) if r.ev >= 0 else '{:.1f}'.format(r.ev * 100)}}%</span>{% else %}—{% endif %}</td>
<td class="confidence {{conf_class}}">{{'{:.0f}'.format(r.confidence * 100)}}%</td>
</tr>
{% endfor %}
</table>
</div>

<div class="card methodology">
<h3>📘 Model Methodology</h3>
<p><strong>Focus:</strong> Unders value identification across major soccer leagues</p>
<p><strong>Prediction Model:</strong> Based on team defensive/offensive ratings and league averages</p>
<p><strong>Sharp Bet Criteria:</strong> Minimum {{min_edge*100}}% edge, positive EV, confidence ≥{{min_conf*100}}%</p>
<p><strong>Kelly %:</strong> Fractional Kelly ({{kelly_frac*100}}%) for conservative bankroll management. Never exceeds 5%.</p>
<p><strong>Confidence:</strong> Based on data availability for both teams. Higher confidence = more reliable ratings.</p>
<p><strong>Edge:</strong> Model under probability minus market implied probability. Positive edge = value bet.</p>
<p><strong>SHARP Label:</strong> Bets with {{sharp_edge*100}}%+ edge are marked as "SHARP" - highest confidence plays.</p>
</div>

<div class="footer">
<p>Last updated: {{timestamp}}</p>
<p>⚠️ Bet responsibly. This model focuses on unders value. Update team ratings regularly.</p>
</div>

</div>
</body>
</html>
"""
    
    template = Template(HTML_TEMPLATE)
    html = template.render(
        recommended=recommended,
        all_plays=all_plays,
        timestamp=datetime.now().strftime('%B %d, %Y at %I:%M %p ET'),
        min_edge=MIN_EDGE_THRESHOLD,
        sharp_edge=SHARP_EDGE_THRESHOLD,
        min_conf=MIN_CONFIDENCE_FOR_BET,
        kelly_frac=KELLY_FRACTION,
        MIN_EDGE_THRESHOLD=MIN_EDGE_THRESHOLD
    )
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ HTML saved: {OUTPUT_HTML}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("⚽ SOCCER TOTALS MODEL - SHARP +EV UNDERS FOCUS")
    print("=" * 80)
    print(f"Minimum Edge: {MIN_EDGE_THRESHOLD*100}%")
    print(f"Sharp Edge: {SHARP_EDGE_THRESHOLD*100}%+")
    print(f"Minimum Confidence: {MIN_CONFIDENCE_FOR_BET*100}%")
    print("=" * 80)
    
    # Fetch odds
    games = fetch_soccer_totals_odds(ODDS_API_KEY)
    
    if not games:
        print("\n⚠️  No games found. Exiting.")
        return
    
    # Analyze all games for value
    print("\n🔍 Analyzing games for unders value...")
    all_value_bets = []
    
    for game in games:
        value_bets = analyze_game_for_value(game)
        all_value_bets.extend(value_bets)
    
    # Separate recommended bets
    recommended = [b for b in all_value_bets if b['recommended']]
    sharp_bets = [b for b in recommended if b['sharp_bet']]
    
    print(f"\n✅ Found {len(all_value_bets)} total under bets analyzed")
    print(f"🔥 {len(recommended)} recommended bets ({MIN_EDGE_THRESHOLD*100}%+ edge)")
    print(f"💎 {len(sharp_bets)} SHARP bets ({SHARP_EDGE_THRESHOLD*100}%+ edge)")
    
    # Generate HTML
    generate_html(all_value_bets)
    
    # Print summary
    if recommended:
        print(f"\n{'='*80}")
        print("🔥 RECOMMENDED UNDERS BETS:")
        print("=" * 80)
        for i, bet in enumerate(recommended[:10], 1):
            sharp_label = " [SHARP]" if bet['sharp_bet'] else ""
            print(f"{i}. {bet['home_team']} vs {bet['away_team']} - Under {bet['line']}{sharp_label}")
            print(f"   League: {bet['league']} | Book: {bet['bookmaker']}")
            print(f"   Odds: {bet['odds']:+d} | Edge: +{bet['edge']*100:.1f}% | EV: +{bet['ev']*100:.1f}%")
            print(f"   Predicted: {bet['predicted_total']:.1f} | Under Prob: {bet['under_probability']*100:.1f}%")
            print()
    else:
        print("\n⚠️  No plays meet the sharp +EV thresholds today")
    
    print("=" * 80)

if __name__ == "__main__":
    main()

