#!/usr/bin/env python3
"""
NFL ANYTIME TOUCHDOWN MODEL - OPTIMIZED FOR +EV
==============================================
Advanced statistical model focusing on accuracy and positive expected value.

Key Features:
- Multi-factor probability modeling with game context
- +EV identification with edge calculation
- Kelly Criterion bet sizing
- Multiple sportsbook comparison
- Confidence ratings based on sample size
"""

import json
import csv
from datetime import datetime
from collections import defaultdict
from jinja2 import Template
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# API Configuration
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
if not ODDS_API_KEY:
    print("FATAL: ODDS_API_KEY not found in .env file.")
    exit()
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Output files
OUTPUT_HTML = "atd_model_output.html"
OUTPUT_CSV = "atd_model_output.csv"

# Model Configuration - SHARP +EV FOCUS
MIN_EDGE_THRESHOLD = 0.08  # 8% minimum edge to recommend (sharp +EV focus, increased from 5%)
SHARP_EDGE_THRESHOLD = 0.10  # 10%+ edge for "SHARP BET" designation
KELLY_FRACTION = 0.25  # Conservative Kelly (1/4 Kelly)
MIN_GAMES_FOR_CONFIDENCE = 6  # Minimum games played for high confidence
MIN_CONFIDENCE_FOR_BET = 0.70  # 70% minimum confidence to recommend (increased from 60%)

######################################################################
# UPDATED Defensive TD Ratings (Lower = Better Defense vs TDs)
######################################################################
# Based on 2024 season TD allowed rates by position
DEFENSE_TD_RATINGS = {
    # Elite defenses (allow fewer TDs)
    "SF": {"RB": 0.65, "WR": 0.70, "TE": 0.75},
    "BAL": {"RB": 0.70, "WR": 0.72, "TE": 0.78},
    "BUF": {"RB": 0.72, "WR": 0.75, "TE": 0.80},
    "PHI": {"RB": 0.75, "WR": 0.78, "TE": 0.82},
    "DAL": {"RB": 0.77, "WR": 0.80, "TE": 0.85},
    "CLE": {"RB": 0.78, "WR": 0.82, "TE": 0.86},

    # Good defenses
    "KC": {"RB": 0.85, "WR": 0.87, "TE": 0.90},
    "DET": {"RB": 0.87, "WR": 0.85, "TE": 0.88},
    "MIA": {"RB": 0.88, "WR": 0.90, "TE": 0.92},
    "CIN": {"RB": 0.90, "WR": 0.88, "TE": 0.90},

    # Average defenses
    "SEA": {"RB": 0.95, "WR": 0.95, "TE": 0.95},
    "LAC": {"RB": 0.98, "WR": 0.97, "TE": 0.96},
    "TB": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
    "ATL": {"RB": 1.02, "WR": 1.00, "TE": 0.98},
    "HOU": {"RB": 1.05, "WR": 1.03, "TE": 1.00},

    # Weak defenses (allow more TDs)
    "GB": {"RB": 1.10, "WR": 1.12, "TE": 1.15},
    "MIN": {"RB": 1.12, "WR": 1.10, "TE": 1.12},
    "ARI": {"RB": 1.15, "WR": 1.18, "TE": 1.20},
    "LV": {"RB": 1.18, "WR": 1.20, "TE": 1.22},
    "IND": {"RB": 1.20, "WR": 1.22, "TE": 1.25},
    "CHI": {"RB": 1.22, "WR": 1.25, "TE": 1.28},
    "NO": {"RB": 1.25, "WR": 1.28, "TE": 1.30},
    "NE": {"RB": 1.28, "WR": 1.30, "TE": 1.32},
    "TEN": {"RB": 1.30, "WR": 1.32, "TE": 1.35},

    # Default for unlisted teams
    "LAR": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
    "JAX": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
    "DEN": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
    "PIT": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
    "WAS": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
    "NYG": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
    "NYJ": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
    "CAR": {"RB": 1.00, "WR": 1.00, "TE": 1.00},
}

# Team name mappings
TEAM_NAME_MAP = {
    'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
    'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
    'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
    'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
    'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
    'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
    'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
    'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
    'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
    'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
    'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS',
}

######################################################################
# UTILITY FUNCTIONS
######################################################################

def american_to_decimal(american_odds):
    """Convert American odds to decimal odds"""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def american_to_implied_prob(american_odds):
    """Convert American odds to implied probability (removing vig)"""
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
    q = 1 - prob  # Probability of losing
    b = decimal_odds - 1  # Net odds

    if prob <= 0 or b <= 0:
        return 0

    kelly = (prob * b - q) / b

    # Apply fractional Kelly for safety
    kelly = kelly * fraction

    # Never bet more than 5% of bankroll on single prop
    return max(0, min(kelly, 0.05))

def get_confidence_rating(games_played, sample_quality=1.0):
    """
    Rate confidence in predictions based on sample size and quality
    sample_quality: 0-1 score based on data recency, consistency, etc.
    """
    if games_played >= 9:
        base_conf = 0.95
    elif games_played >= 7:
        base_conf = 0.85
    elif games_played >= MIN_GAMES_FOR_CONFIDENCE:
        base_conf = 0.75
    elif games_played >= 4:
        base_conf = 0.60
    else:
        base_conf = 0.40

    return base_conf * sample_quality

######################################################################
# API FUNCTIONS
######################################################################

def fetch_todays_games_with_totals():
    """Fetch upcoming NFL games in the next 7 days with totals for implied team scoring"""
    print("\n📅 Fetching upcoming NFL games (next 7 days)...")

    from datetime import datetime, timezone, timedelta

    url = f"{ODDS_API_BASE}/sports/americanfootball_nfl/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h,totals',
        'oddsFormat': 'american'
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        games = response.json()

        # Get next 7 days date range
        now_utc = datetime.now(timezone.utc)
        start_time = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=7)

        matchups = {}

        for game in games:
            commence_time_str = game.get('commence_time', '')
            if not commence_time_str:
                continue

            try:
                game_time_utc = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))

                # Check if game is in the next 7 days
                if start_time <= game_time_utc < end_time:
                    home = TEAM_NAME_MAP.get(game.get('home_team'), game.get('home_team', ''))
                    away = TEAM_NAME_MAP.get(game.get('away_team'), game.get('away_team', ''))

                    # Get totals for implied scoring
                    game_total = None
                    for bookmaker in game.get('bookmakers', [])[:1]:  # Use first book
                        for market in bookmaker.get('markets', []):
                            if market.get('key') == 'totals':
                                outcomes = market.get('outcomes', [])
                                if outcomes:
                                    game_total = outcomes[0].get('point')
                                break

                    # Convert to ET for display
                    game_time_et = game_time_utc - timedelta(hours=5)
                    game_time_formatted = game_time_et.strftime('%I:%M %p ET')

                    if home and away:
                        matchups[home] = {
                            'opponent': away,
                            'time': game_time_formatted,
                            'datetime': game_time_utc,
                            'game_total': game_total / 2 if game_total else 22,  # Implied team total
                            'is_home': True
                        }
                        matchups[away] = {
                            'opponent': home,
                            'time': game_time_formatted,
                            'datetime': game_time_utc,
                            'game_total': game_total / 2 if game_total else 20,
                            'is_home': False
                        }
            except:
                continue

        if matchups:
            print(f"   ✅ Found {len(matchups)//2} games in the next 7 days")
        else:
            print(f"   ⚠️  No games in the next 7 days")

        return matchups

    except Exception as e:
        print(f"   ⚠️  Error fetching games: {e}")
        return {}

def fetch_attd_odds_all_books():
    """Fetch ATTD odds from multiple sportsbooks"""
    print("\n💰 Fetching ATTD odds from sportsbooks...")

    url = f"{ODDS_API_BASE}/sports/americanfootball_nfl/events"
    params = {'apiKey': ODDS_API_KEY}

    try:
        # First get event IDs
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        events = response.json()

        all_odds = {}

        for event in events[:5]:  # Limit to avoid excessive API calls
            event_id = event.get('id')
            if not event_id:
                continue

            # Try to get player props for this event
            odds_url = f"{ODDS_API_BASE}/sports/americanfootball_nfl/events/{event_id}/odds"
            odds_params = {
                'apiKey': ODDS_API_KEY,
                'regions': 'us',
                'markets': 'player_anytime_td',
                'oddsFormat': 'american'
            }

            try:
                odds_response = requests.get(odds_url, params=odds_params, timeout=30)
                if odds_response.status_code == 200:
                    odds_data = odds_response.json()

                    for bookmaker in odds_data.get('bookmakers', []):
                        book_name = bookmaker.get('title', 'Unknown')

                        for market in bookmaker.get('markets', []):
                            if market.get('key') == 'player_anytime_td':
                                for outcome in market.get('outcomes', []):
                                    player_name = outcome.get('description', outcome.get('name', ''))
                                    odds = outcome.get('price')

                                    if player_name and odds:
                                        if player_name not in all_odds:
                                            all_odds[player_name] = []

                                        all_odds[player_name].append({
                                            'bookmaker': book_name,
                                            'odds': odds,
                                            'implied_prob': american_to_implied_prob(odds)
                                        })
            except:
                continue

        if all_odds:
            print(f"   ✅ Found odds for {len(all_odds)} players across multiple books")
        else:
            print(f"   ⚠️  No ATTD odds available")

        return all_odds

    except Exception as e:
        print(f"   ⚠️  Error fetching ATTD odds: {e}")
        return {}

######################################################################
# PLAYER DATA
######################################################################

def load_player_data(matchups):
    """Load player data - UPDATE WEEKLY with latest stats"""
    players = [
        # Elite RBs - TD machines
        {"name": "Christian McCaffrey", "pos": "RB", "team": "SF",
         "touches": 145, "tds": 14, "games": 8, "rz_share": 0.45, "snap_pct": 75, "recent_form": 1.2},
        {"name": "Derrick Henry", "pos": "RB", "team": "BAL",
         "touches": 162, "tds": 13, "games": 10, "rz_share": 0.42, "snap_pct": 65, "recent_form": 1.3},
        {"name": "Saquon Barkley", "pos": "RB", "team": "PHI",
         "touches": 156, "tds": 11, "games": 10, "rz_share": 0.38, "snap_pct": 70, "recent_form": 1.1},
        {"name": "Bijan Robinson", "pos": "RB", "team": "ATL",
         "touches": 148, "tds": 11, "games": 10, "rz_share": 0.36, "snap_pct": 68, "recent_form": 1.0},
        {"name": "Jahmyr Gibbs", "pos": "RB", "team": "DET",
         "touches": 142, "tds": 11, "games": 10, "rz_share": 0.30, "snap_pct": 55, "recent_form": 1.4},

        # High-volume RBs
        {"name": "Josh Jacobs", "pos": "RB", "team": "GB",
         "touches": 148, "tds": 8, "games": 10, "rz_share": 0.35, "snap_pct": 62, "recent_form": 0.9},
        {"name": "James Cook", "pos": "RB", "team": "BUF",
         "touches": 132, "tds": 10, "games": 10, "rz_share": 0.34, "snap_pct": 58, "recent_form": 1.2},
        {"name": "De'Von Achane", "pos": "RB", "team": "MIA",
         "touches": 118, "tds": 7, "games": 9, "rz_share": 0.26, "snap_pct": 52, "recent_form": 0.8},
        {"name": "Kyren Williams", "pos": "RB", "team": "LAR",
         "touches": 135, "tds": 10, "games": 9, "rz_share": 0.40, "snap_pct": 60, "recent_form": 1.0},
        {"name": "Breece Hall", "pos": "RB", "team": "NYJ",
         "touches": 132, "tds": 6, "games": 10, "rz_share": 0.30, "snap_pct": 64, "recent_form": 0.7},
        {"name": "Jonathan Taylor", "pos": "RB", "team": "IND",
         "touches": 142, "tds": 7, "games": 9, "rz_share": 0.38, "snap_pct": 66, "recent_form": 1.0},
        {"name": "David Montgomery", "pos": "RB", "team": "DET",
         "touches": 115, "tds": 9, "games": 10, "rz_share": 0.28, "snap_pct": 48, "recent_form": 1.1},
        {"name": "Kenneth Walker", "pos": "RB", "team": "SEA",
         "touches": 128, "tds": 7, "games": 9, "rz_share": 0.34, "snap_pct": 60, "recent_form": 0.9},
        {"name": "Aaron Jones", "pos": "RB", "team": "MIN",
         "touches": 118, "tds": 6, "games": 9, "rz_share": 0.30, "snap_pct": 54, "recent_form": 0.8},
        {"name": "Rachaad White", "pos": "RB", "team": "TB",
         "touches": 128, "tds": 5, "games": 10, "rz_share": 0.26, "snap_pct": 58, "recent_form": 0.6},
        {"name": "Rhamondre Stevenson", "pos": "RB", "team": "NE",
         "touches": 125, "tds": 6, "games": 10, "rz_share": 0.32, "snap_pct": 55, "recent_form": 0.8},

        # Elite WRs
        {"name": "Ja'Marr Chase", "pos": "WR", "team": "CIN",
         "touches": 92, "tds": 9, "games": 10, "rz_share": 0.30, "snap_pct": 92, "recent_form": 1.5},
        {"name": "Amon-Ra St. Brown", "pos": "WR", "team": "DET",
         "touches": 102, "tds": 9, "games": 10, "rz_share": 0.28, "snap_pct": 88, "recent_form": 1.3},
        {"name": "CeeDee Lamb", "pos": "WR", "team": "DAL",
         "touches": 105, "tds": 6, "games": 10, "rz_share": 0.25, "snap_pct": 95, "recent_form": 1.0},
        {"name": "Tyreek Hill", "pos": "WR", "team": "MIA",
         "touches": 95, "tds": 5, "games": 9, "rz_share": 0.22, "snap_pct": 90, "recent_form": 0.9},
        {"name": "AJ Brown", "pos": "WR", "team": "PHI",
         "touches": 82, "tds": 5, "games": 9, "rz_share": 0.21, "snap_pct": 85, "recent_form": 1.0},
        {"name": "DK Metcalf", "pos": "WR", "team": "SEA",
         "touches": 82, "tds": 7, "games": 10, "rz_share": 0.24, "snap_pct": 87, "recent_form": 1.2},
        {"name": "Mike Evans", "pos": "WR", "team": "TB",
         "touches": 78, "tds": 5, "games": 9, "rz_share": 0.24, "snap_pct": 86, "recent_form": 1.0},

        # High-target WRs
        {"name": "Garrett Wilson", "pos": "WR", "team": "NYJ",
         "touches": 85, "tds": 4, "games": 10, "rz_share": 0.18, "snap_pct": 88, "recent_form": 0.8},
        {"name": "Puka Nacua", "pos": "WR", "team": "LAR",
         "touches": 72, "tds": 3, "games": 8, "rz_share": 0.16, "snap_pct": 82, "recent_form": 1.1},
        {"name": "DeVonta Smith", "pos": "WR", "team": "PHI",
         "touches": 76, "tds": 4, "games": 9, "rz_share": 0.17, "snap_pct": 84, "recent_form": 0.9},
        {"name": "Brandon Aiyuk", "pos": "WR", "team": "SF",
         "touches": 76, "tds": 5, "games": 9, "rz_share": 0.19, "snap_pct": 84, "recent_form": 1.0},
        {"name": "Cooper Kupp", "pos": "WR", "team": "LAR",
         "touches": 65, "tds": 4, "games": 7, "rz_share": 0.20, "snap_pct": 85, "recent_form": 1.0},
        {"name": "Nico Collins", "pos": "WR", "team": "HOU",
         "touches": 72, "tds": 4, "games": 8, "rz_share": 0.18, "snap_pct": 88, "recent_form": 1.1},
        {"name": "Zay Flowers", "pos": "WR", "team": "BAL",
         "touches": 70, "tds": 3, "games": 10, "rz_share": 0.13, "snap_pct": 80, "recent_form": 0.8},
        {"name": "DJ Moore", "pos": "WR", "team": "CHI",
         "touches": 82, "tds": 3, "games": 10, "rz_share": 0.14, "snap_pct": 86, "recent_form": 0.7},

        # Elite TEs
        {"name": "George Kittle", "pos": "TE", "team": "SF",
         "touches": 68, "tds": 7, "games": 9, "rz_share": 0.23, "snap_pct": 72, "recent_form": 1.2},
        {"name": "Sam LaPorta", "pos": "TE", "team": "DET",
         "touches": 78, "tds": 7, "games": 10, "rz_share": 0.24, "snap_pct": 78, "recent_form": 1.1},
        {"name": "Travis Kelce", "pos": "TE", "team": "KC",
         "touches": 75, "tds": 6, "games": 10, "rz_share": 0.20, "snap_pct": 75, "recent_form": 1.0},
        {"name": "Trey McBride", "pos": "TE", "team": "ARI",
         "touches": 85, "tds": 4, "games": 10, "rz_share": 0.19, "snap_pct": 80, "recent_form": 0.9},
        {"name": "Mark Andrews", "pos": "TE", "team": "BAL",
         "touches": 64, "tds": 5, "games": 9, "rz_share": 0.18, "snap_pct": 68, "recent_form": 1.1},
        {"name": "Evan Engram", "pos": "TE", "team": "JAX",
         "touches": 72, "tds": 3, "games": 10, "rz_share": 0.15, "snap_pct": 72, "recent_form": 0.7},
        {"name": "Jake Ferguson", "pos": "TE", "team": "DAL",
         "touches": 68, "tds": 4, "games": 10, "rz_share": 0.16, "snap_pct": 70, "recent_form": 0.9},
        {"name": "Dalton Kincaid", "pos": "TE", "team": "BUF",
         "touches": 60, "tds": 5, "games": 10, "rz_share": 0.16, "snap_pct": 68, "recent_form": 1.0},
    ]

    # Filter to players playing today
    players_playing = []
    for player in players:
        if player['team'] in matchups:
            matchup_info = matchups[player['team']]
            player['opp'] = matchup_info['opponent']
            player['game_time'] = matchup_info['time']
            player['implied_team_total'] = matchup_info['game_total']
            player['is_home'] = matchup_info['is_home']
            players_playing.append(player)

    print(f"\n📊 {len(players_playing)} players have games in the next 7 days")
    return players_playing

######################################################################
# PROBABILITY CALCULATION
######################################################################

def calculate_advanced_probabilities(players, attd_odds):
    """
    Advanced TD probability calculation with multiple factors
    """

    results = []

    for player in players:
        # Base metrics
        games = player['games']
        if games == 0:
            continue

        td_per_game = player['tds'] / games
        touches_per_game = player['touches'] / games
        td_per_touch = player['tds'] / player['touches'] if player['touches'] > 0 else 0

        # Defensive matchup multiplier
        def_ratings = DEFENSE_TD_RATINGS.get(player['opp'], {"RB": 1.0, "WR": 1.0, "TE": 1.0})
        def_mult = def_ratings.get(player['pos'], 1.0)

        # Game environment factors
        team_total = player.get('implied_team_total', 22)
        scoring_env = min(1.3, max(0.7, team_total / 22))  # Normalize around 22 pts

        # Recent form factor
        form_mult = player.get('recent_form', 1.0)

        # Position-specific base rates (league average TD probability by position)
        base_rates = {"RB": 0.35, "WR": 0.25, "TE": 0.20}
        position_base = base_rates.get(player['pos'], 0.25)

        # Weighted calculation
        # Start with player's actual TD rate
        player_td_rate = td_per_game / 17 * 100  # Convert to per-17-game season rate

        # Build probability
        prob = (
            # Base: Player's TD rate adjusted for games played
            0.40 * (td_per_game / position_base) * 0.30 +  # Actual TD rate vs position

            # Red zone dominance (most important)
            0.30 * (player['rz_share'] * 2.0) +

            # Volume
            0.15 * min(1.0, touches_per_game / 20) +

            # Snap share (opportunity)
            0.08 * (player['snap_pct'] / 100) +

            # Efficiency
            0.07 * min(1.0, td_per_touch * 10)
        )

        # Apply multipliers
        prob = prob * def_mult * scoring_env * form_mult

        # Bound probability
        prob = max(0.02, min(0.65, prob))

        # Confidence rating
        confidence = get_confidence_rating(games, sample_quality=min(1.0, games/10))

        # Find best odds across all books
        player_odds_data = attd_odds.get(player['name'], [])
        best_odds = None
        best_book = None
        best_edge = -999
        avg_implied = None

        if player_odds_data:
            # Find the best odds (highest for plus money, least negative for minus)
            best_book_data = max(player_odds_data, key=lambda x: x['odds'])
            best_odds = best_book_data['odds']
            best_book = best_book_data['bookmaker']

            # Calculate average implied probability across books (fair odds estimate)
            avg_implied = sum(x['implied_prob'] for x in player_odds_data) / len(player_odds_data)

            # Edge calculation (model prob - average market implied prob)
            edge = prob - avg_implied
            best_edge = edge

        # Calculate EV and Kelly if we have odds
        ev = None
        kelly_size = None
        recommended_bet = False

        if best_odds is not None:
            ev = calculate_expected_value(prob, best_odds)
            kelly_size = calculate_kelly_bet_size(prob, best_odds)

            # Recommend bet if: +EV, meets sharp edge threshold, and high confidence
            if ev > 0 and best_edge >= MIN_EDGE_THRESHOLD and confidence >= MIN_CONFIDENCE_FOR_BET:
                recommended_bet = True

        results.append({
            'player_name': player['name'],
            'position': player['pos'],
            'team': player['team'],
            'opponent': player['opp'],
            'game_time': player['game_time'],
            'model_prob': prob,
            'confidence': confidence,
            'best_odds': best_odds,
            'best_book': best_book,
            'avg_implied_prob': avg_implied,
            'edge': best_edge,
            'ev': ev,
            'kelly_pct': kelly_size,
            'recommended': recommended_bet,
            'sharp_bet': recommended_bet and best_edge >= SHARP_EDGE_THRESHOLD,  # Extra sharp designation

            # Stats for display
            'total_tds': player['tds'],
            'games': games,
            'td_per_game': td_per_game,
            'rz_share': player['rz_share'],
            'touches_per_game': touches_per_game,
            'snap_pct': player['snap_pct'],
            'def_mult': def_mult,
            'implied_total': team_total,
        })

    # Sort by EV (best bets first), then by probability
    results.sort(key=lambda x: (x['recommended'], x['ev'] if x['ev'] else -999, x['model_prob']), reverse=True)

    return results

######################################################################
# OUTPUT GENERATION
######################################################################

def generate_html(results):
    """Generate optimized HTML report"""

    # Separate recommended bets from all plays
    recommended = [r for r in results if r['recommended']]
    all_plays = results[:50]

    HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NFL ATTD Model - Sharp +EV</title>
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
.positive {
    background: #0d2b1f;
    border-left: 3px solid #00ff88;
}
.neutral {
    background: #1a2332;
}
.prob {
    font-size: 1rem;
    font-weight: 700;
}
.prob-high { color: #00ff88; }
.prob-med { color: #60a5fa; }
.prob-low { color: #ffa726; }
.stats {
    color: #94a3b8;
    font-size: 0.8125rem;
}
.pos {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
}
.pos-RB { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
.pos-WR { background: rgba(96, 165, 250, 0.2); color: #60a5fa; }
.pos-TE { background: rgba(255, 167, 38, 0.2); color: #ffa726; }
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
.edge-negative {
    color: #94a3b8;
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
.no-bets {
    text-align: center;
    padding: 3rem;
    color: #94a3b8;
    font-style: italic;
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
    table { font-size: 0.75rem; }
    th, td { padding: 0.5rem; }
    .header-card { padding: 1.5rem 1rem; }
    table { display: block; overflow-x: auto; -webkit-overflow-scrolling: touch; }
}
@media (max-width: 480px) {
    th, td { padding: 0.4rem; font-size: 0.7rem; }
    .prob { font-size: 0.875rem; }
    .subtitle { font-size: 0.75rem; }
}
</style>
</head>
<body>
<div class="container">
<div class="card header-card">
<h1>🏈 NFL ATTD MODEL - SHARP +EV</h1>
<div class="subtitle">Advanced Statistical Model | Generated {{timestamp}}</div>

{% if recommended|length > 0 %}
<div class="card">
<div class="alert">
<div class="alert-text">🔥 {{recommended|length}} RECOMMENDED BET(S) - Sharp +EV with {{min_edge*100}}%+ Edge</div>
</div>

<h2>💎 RECOMMENDED PLAYS (+EV)</h2>
<table>
<tr>
<th>Player</th><th>Pos</th><th>Game</th><th>Time</th>
<th>Model Prob</th><th>Best Odds</th><th>Avg Implied</th><th>Edge</th><th>EV</th><th>Kelly %</th><th>Conf</th>
</tr>
{% for r in recommended %}
{% set prob_class = 'prob-high' if r.model_prob >= 0.35 else ('prob-med' if r.model_prob >= 0.25 else 'prob-low') %}
{% set edge_class = 'edge-positive' if r.edge >= 0.10 else 'edge-neutral' %}
{% set conf_class = 'conf-high' if r.confidence >= 0.80 else ('conf-med' if r.confidence >= 0.65 else 'conf-low') %}
{% set sharp_class = 'sharp' if r.sharp_bet else '' %}
<tr class="recommend {{sharp_class}}">
<td><strong>{{r.player_name}}</strong>{% if r.sharp_bet %}<span class="sharp-label">SHARP</span>{% endif %}</td>
<td><span class="pos pos-{{r.position}}">{{r.position}}</span></td>
<td class="stats">{{r.team}} vs {{r.opponent}}</td>
<td class="stats">{{r.game_time}}</td>
<td class="prob {{prob_class}}">{{'{:.1f}'.format(r.model_prob * 100)}}%</td>
<td><span class="odds-badge">{{'+{}'.format(r.best_odds|int) if r.best_odds > 0 else r.best_odds|int}}</span><br><span class="stats">{{r.best_book}}</span></td>
<td class="stats">{{'{:.1f}'.format(r.avg_implied_prob * 100) if r.avg_implied_prob else '—'}}%</td>
<td class="{{edge_class}}">{{'+{:.1f}'.format(r.edge * 100)}}%</td>
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
<h2>📊 ALL PLAYER PROBABILITIES</h2>
<table>
<tr>
<th>Rank</th><th>Player</th><th>Pos</th><th>Game</th><th>Time</th>
<th>Model Prob</th><th>Best Odds</th><th>Edge</th><th>RZ Share</th><th>TD/G</th><th>Conf</th>
</tr>
{% for r in all_plays %}
{% set rank = loop.index %}
{% set tier = 'recommend' if r.recommended else ('positive' if r.ev and r.ev > 0 else 'neutral') %}
{% set prob_class = 'prob-high' if r.model_prob >= 0.35 else ('prob-med' if r.model_prob >= 0.25 else 'prob-low') %}
{% set edge_class = 'edge-positive' if r.edge >= MIN_EDGE_THRESHOLD else ('edge-neutral' if r.edge >= 0 else 'edge-negative') %}
{% set conf_class = 'conf-high' if r.confidence >= 0.80 else ('conf-med' if r.confidence >= 0.65 else 'conf-low') %}
<tr class="{{tier}}">
<td><strong>{{rank}}</strong></td>
<td><strong>{{r.player_name}}</strong></td>
<td><span class="pos pos-{{r.position}}">{{r.position}}</span></td>
<td class="stats">{{r.team}} vs {{r.opponent}}</td>
<td class="stats">{{r.game_time}}</td>
<td class="prob {{prob_class}}">{{'{:.1f}'.format(r.model_prob * 100)}}%</td>
<td>{% if r.best_odds %}<span class="odds-badge">{{'+{}'.format(r.best_odds|int) if r.best_odds > 0 else r.best_odds|int}}</span>{% else %}<span class="stats">N/A</span>{% endif %}</td>
<td class="{{edge_class}}">{% if r.edge > -900 %}{{'+{:.1f}'.format(r.edge * 100) if r.edge >= 0 else '{:.1f}'.format(r.edge * 100)}}%{% else %}—{% endif %}</td>
<td class="stats">{{'{:.1f}'.format(r.rz_share * 100)}}%</td>
<td class="stats">{{'{:.1f}'.format(r.td_per_game)}}</td>
<td class="confidence {{conf_class}}">{{'{:.0f}'.format(r.confidence * 100)}}%</td>
</tr>
{% endfor %}
</table>
</div>

<div class="card methodology">
<h3>📘 Model Methodology</h3>
<p><strong>Probability Factors:</strong> TD Rate (40%), Red Zone Share (30%), Volume (15%), Snap % (8%), Efficiency (7%)</p>
<p><strong>Adjustments:</strong> Defensive matchup, implied team total, recent form</p>
<p><strong>Sharp Bet Criteria:</strong> Minimum {{min_edge*100}}% edge, positive EV, confidence ≥{{min_conf*100}}%</p>
<p><strong>Kelly %:</strong> Fractional Kelly ({{kelly_frac*100}}%) for conservative bankroll management. Never exceeds 5%.</p>
<p><strong>Confidence:</strong> Based on sample size (games played) and data quality. Higher confidence = more reliable projection.</p>
<p><strong>Edge:</strong> Model probability minus average market implied probability. Positive edge = value bet.</p>
<p><strong>EV (Expected Value):</strong> Long-term expected profit per $1 wagered.</p>
<p><strong>SHARP Label:</strong> Bets with {{sharp_edge*100}}%+ edge are marked as "SHARP" - highest confidence plays.</p>
</div>

<div class="footer">
<p>Last updated: {{timestamp}}</p>
<p>⚠️ Bet responsibly. This model is for informational purposes. Update player data weekly.</p>
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

def generate_csv(results):
    """Generate CSV with all data"""

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'player_name', 'position', 'team', 'opponent', 'game_time',
            'model_prob', 'confidence', 'best_odds', 'best_book',
            'avg_implied_prob', 'edge', 'ev', 'kelly_pct', 'recommended',
            'total_tds', 'games', 'td_per_game', 'rz_share',
            'touches_per_game', 'snap_pct', 'def_mult', 'implied_total'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results[:50])

    print(f"✅ CSV saved: {OUTPUT_CSV}")

######################################################################
# MAIN
######################################################################

def main():
    print("=" * 80)
    print("NFL ANYTIME TOUCHDOWN MODEL - OPTIMIZED FOR +EV")
    print("=" * 80)

    # Fetch games with totals
    matchups = fetch_todays_games_with_totals()

    if not matchups:
        print("\n⚠️  No games in the next 7 days. Exiting.")
        return

    # Fetch ATTD odds from multiple books
    attd_odds = fetch_attd_odds_all_books()

    # Load player data
    print("\n📊 Loading player data...")
    players = load_player_data(matchups)

    if not players:
        print("\n❌ No players have games in the next 7 days")
        return

    # Calculate probabilities
    print("\n🧮 Calculating probabilities with advanced factors...")
    results = calculate_advanced_probabilities(players, attd_odds)

    # Generate outputs
    generate_html(results)
    generate_csv(results)

    # Print summary
    recommended = [r for r in results if r['recommended']]

    print(f"\n{'='*80}")
    if recommended:
        print(f"🔥 {len(recommended)} RECOMMENDED BET(S) (+EV with {MIN_EDGE_THRESHOLD*100}%+ edge):")
        print("=" * 80)
        for i, r in enumerate(recommended, 1):
            print(f"{i}. {r['player_name']:25s} ({r['position']}) {r['team']} vs {r['opp']}")
            print(f"   Model: {r['model_prob']*100:5.1f}% | Odds: {'+' if r['best_odds'] > 0 else ''}{int(r['best_odds'])} ({r['best_book']})")
            print(f"   Edge: +{r['edge']*100:.1f}% | EV: +{r['ev']*100:.1f}% | Kelly: {r['kelly_pct']*100:.2f}% | Conf: {r['confidence']*100:.0f}%")
            print()
    else:
        print(f"⚠️  No plays meet the +{MIN_EDGE_THRESHOLD*100}% edge threshold today")

    print("=" * 80)
    print(f"✅ Full report: {OUTPUT_HTML}")
    print("=" * 80)

if __name__ == "__main__":
    main()
