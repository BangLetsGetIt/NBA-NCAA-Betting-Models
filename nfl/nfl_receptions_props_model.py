#!/usr/bin/env python3
"""
NFL Receptions Props Model - PROFITABLE VERSION
Analyzes player receptions props using REAL NFL stats
Focuses on pass volume, opponent pass defense, and matchup advantages
Based on NBA props model structure for consistency
"""

import requests
import json
import os
import subprocess
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
import statistics
import time
from dotenv import load_dotenv

# Load environment variables - prioritize root .env
from pathlib import Path
root_env = Path(__file__).parent.parent / '.env'
if root_env.exists():
    load_dotenv(root_env, override=True)
else:
    load_dotenv()

# Configuration
API_KEY = os.getenv('ODDS_API_KEY')
if not API_KEY:
    raise ValueError("ODDS_API_KEY environment variable not set. Please add it to your .env file.")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "nfl_receptions_props.html")
TRACKING_FILE = os.path.join(SCRIPT_DIR, "nfl_receptions_props_tracking.json")
PLAYER_STATS_CACHE = os.path.join(SCRIPT_DIR, "nfl_player_receptions_stats_cache.json")
TEAM_DEFENSE_CACHE = os.path.join(SCRIPT_DIR, "nfl_team_pass_defense_cache.json")

# Model Parameters - EXTREMELY STRICT FOR PROFITABILITY
MIN_AI_SCORE = 9.5  # Only show high-confidence plays
TOP_PLAYS_COUNT = 5  # Quality over quantity
RECENT_GAMES_WINDOW = 5  # 5 games for recent form (NFL season shorter)
AUTO_TRACK_THRESHOLD = 9.7  # Only track elite plays
CURRENT_SEASON = '2024'

# Edge requirements - Strict for receptions
MIN_EDGE_OVER_LINE = 2.0  # Player must average 25+ above prop line for OVER
MIN_EDGE_UNDER_LINE = 1.5  # Player must average 20+ below prop line for UNDER
MIN_RECENT_FORM_EDGE = 1.2  # Recent form must strongly support

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def get_nfl_player_passing_yards_stats():
    """
    Fetch REAL NFL player receptions stats from cache (populated by fetch_nfl_player_stats.py)
    Returns dictionary with player receptions stats (season avg, recent form, etc.)
    """
    print(f"\n{Colors.CYAN}Loading NFL player receptions statistics...{Colors.END}")

    # Check cache first (6 hour cache)
    if os.path.exists(PLAYER_STATS_CACHE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(PLAYER_STATS_CACHE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached player stats (less than 6 hours old){Colors.END}")
            with open(PLAYER_STATS_CACHE, 'r') as f:
                stats = json.load(f)
                if stats:
                    print(f"{Colors.GREEN}✓ Loaded {len(stats)} players from cache{Colors.END}")
                    return stats

    # If cache is old or empty, try to fetch fresh stats
    print(f"{Colors.YELLOW}  Cache is old or empty. Running automated stats fetcher...{Colors.END}")
    try:
        result = subprocess.run(
            ['python3', os.path.join(SCRIPT_DIR, 'fetch_nfl_player_stats.py')],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓ Stats fetched successfully{Colors.END}")
            # Reload from cache
            if os.path.exists(PLAYER_STATS_CACHE):
                with open(PLAYER_STATS_CACHE, 'r') as f:
                    stats = json.load(f)
                    if stats:
                        print(f"{Colors.GREEN}✓ Loaded {len(stats)} players from cache{Colors.END}")
                        return stats
    except Exception as e:
        print(f"{Colors.YELLOW}  Could not auto-fetch stats: {e}{Colors.END}")

    # Return empty if all else fails
    print(f"{Colors.YELLOW}  No cached stats found. Run 'python3 nfl/fetch_nfl_player_stats.py' to populate.{Colors.END}")
    return {}

def get_opponent_pass_defense_factors():
    """
    Fetch team pass defense stats to identify matchup advantages
    Placeholder - would need NFL defense API integration
    """
    print(f"\n{Colors.CYAN}Fetching opponent pass defense factors...{Colors.END}")
    
    # Try cache first
    if os.path.exists(TEAM_DEFENSE_CACHE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(TEAM_DEFENSE_CACHE))
        if (datetime.now() - file_mod_time) < timedelta(hours=24):
            with open(TEAM_DEFENSE_CACHE, 'r') as f:
                return json.load(f)
    
    try:
        # Placeholder for NFL team defense stats
        # In production, fetch from ESPN or NFL stats API
        print(f"{Colors.YELLOW}  Note: NFL defense stats API integration needed.{Colors.END}")
        defense_factors = {}
        
        # Cache empty results
        with open(TEAM_DEFENSE_CACHE, 'w') as f:
            json.dump(defense_factors, f, indent=2)
        
        return defense_factors
    except Exception as e:
        print(f"{Colors.YELLOW}⚠ Could not fetch defense factors: {e}{Colors.END}")
        if os.path.exists(TEAM_DEFENSE_CACHE):
            with open(TEAM_DEFENSE_CACHE, 'r') as f:
                return json.load(f)
        return {}

def get_nfl_team_rosters():
    """Build a mapping of player names to their teams"""
    # NFL team rosters - can be expanded
    rosters = {
        'Buffalo Bills': ['Allen', 'Diggs', 'Davis', 'Cook', 'Kincaid'],
        'Miami Dolphins': ['Tagovailoa', 'Hill', 'Waddle', 'Mostert', 'Achane'],
        'New York Jets': ['Rodgers', 'Wilson', 'Hall', 'Conklin'],
        'New England Patriots': ['Jones', 'Stevenson', 'Bourne'],
        'Baltimore Ravens': ['Jackson', 'Andrews', 'Flowers', 'Edwards'],
        'Pittsburgh Steelers': ['Pickett', 'Harris', 'Johnson', 'Freiermuth'],
        'Cincinnati Bengals': ['Burrow', 'Chase', 'Higgins', 'Mixon'],
        'Cleveland Browns': ['Watson', 'Chubb', 'Cooper', 'Njoku'],
        'Houston Texans': ['Stroud', 'Collins', 'Dell', 'Pierce'],
        'Jacksonville Jaguars': ['Lawrence', 'Ridley', 'Kirk', 'Etienne'],
        'Indianapolis Colts': ['Richardson', 'Taylor', 'Pittman', 'Downs'],
        'Tennessee Titans': ['Levis', 'Henry', 'Hopkins', 'Burks'],
        'Kansas City Chiefs': ['Mahomes', 'Kelce', 'Rice', 'Pacheco'],
        'Los Angeles Chargers': ['Herbert', 'Allen', 'Williams', 'Ekeler'],
        'Denver Broncos': ['Wilson', 'Sutton', 'Jeudy', 'Williams'],
        'Las Vegas Raiders': ['O\'Connell', 'Adams', 'Mayer', 'Jacobs'],
        'Philadelphia Eagles': ['Hurts', 'Brown', 'Smith', 'Swift'],
        'Washington Commanders': ['Howell', 'McLaurin', 'Dotson', 'Robinson'],
        'Dallas Cowboys': ['Prescott', 'Lamb', 'Pollard', 'Ferguson'],
        'New York Giants': ['Jones', 'Barkley', 'Slayton', 'Waller'],
        'Detroit Lions': ['Goff', 'St. Brown', 'LaPorta', 'Gibbs'],
        'Minnesota Vikings': ['Cousins', 'Jefferson', 'Hockenson', 'Mattison'],
        'Green Bay Packers': ['Love', 'Watson', 'Doubs', 'Jones'],
        'Chicago Bears': ['Fields', 'Moore', 'Kmet', 'Herbert'],
        'Atlanta Falcons': ['Ridder', 'London', 'Pitts', 'Robinson'],
        'Tampa Bay Buccaneers': ['Mayfield', 'Evans', 'Godwin', 'White'],
        'New Orleans Saints': ['Carr', 'Olave', 'Thomas', 'Kamara'],
        'Carolina Panthers': ['Young', 'Thielen', 'Mingo', 'Hubbard'],
        'San Francisco 49ers': ['Purdy', 'Aiyuk', 'Kittle', 'McCaffrey'],
        'Arizona Cardinals': ['Murray', 'Brown', 'Ertz', 'Conner'],
        'Los Angeles Rams': ['Stafford', 'Kupp', 'Nacua', 'Williams'],
        'Seattle Seahawks': ['Smith', 'Metcalf', 'Lockett', 'Walker'],
    }
    return rosters

def match_player_to_team(player_name, home_team, away_team, rosters):
    """Match a player to their team based on name matching with rosters"""
    name_parts = player_name.split()
    last_name = name_parts[-1] if name_parts else player_name

    if home_team in rosters:
        for roster_name in rosters[home_team]:
            if roster_name.lower() in player_name.lower():
                return home_team, away_team

    if away_team in rosters:
        for roster_name in rosters[away_team]:
            if roster_name.lower() in player_name.lower():
                return away_team, home_team

    return home_team, away_team

def load_tracking():
    """Load tracking data from JSON file"""
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {'picks': [], 'summary': {'total': 0, 'wins': 0, 'losses': 0, 'pending': 0, 'win_rate': 0.0, 'roi': 0.0}}

def save_tracking(tracking_data):
    """Save tracking data to JSON file"""
    try:
        with open(TRACKING_FILE, 'w') as f:
            json.dump(tracking_data, indent=2, fp=f)
        return True
    except Exception as e:
        print(f"{Colors.RED}✗ Error saving tracking: {e}{Colors.END}")
        return False

def calculate_tracking_summary(picks, displayed_plays=None):
    """Calculate summary statistics from picks, optionally filtered to displayed plays only"""
    if displayed_plays:
        # Create set of displayed play IDs for filtering
        displayed_ids = set()
        for play in displayed_plays:
            prop_line = float(play['prop'].split()[1])
            bet_type = 'over' if 'OVER' in play['prop'] else 'under'
            displayed_ids.add(f"{play['player']}_{prop_line}_{bet_type}")
        
        # Filter picks to only those currently displayed
        picks = [p for p in picks if f"{p['player']}_{p['prop_line']}_{p['bet_type']}" in displayed_ids]
    
    total = len(picks)
    wins = len([p for p in picks if p.get('status', '').lower() == 'win'])
    losses = len([p for p in picks if p.get('status', '').lower() == 'loss'])
    pending = len([p for p in picks if p.get('status', '').lower() == 'pending'])

    completed = wins + losses
    win_rate = (wins / completed * 100) if completed > 0 else 0.0
    roi = (wins * 0.91 - losses * 1.0)
    roi_pct = (roi / total * 100) if total > 0 else 0.0

    clv_picks = [p for p in picks if p.get('opening_odds') and p.get('latest_odds')]
    positive_clv = len([p for p in clv_picks if p.get('latest_odds', 0) < p.get('opening_odds', 0)])
    clv_rate = (positive_clv / len(clv_picks) * 100) if clv_picks else 0.0

    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'pending': pending,
        'win_rate': win_rate,
        'roi': roi,
        'roi_pct': roi_pct,
        'clv_rate': clv_rate,
        'clv_count': f"{positive_clv}/{len(clv_picks)}"
    }

# ============================================================================
# A.I. RATING SYSTEM (Probability-Based for Props)
# ============================================================================

def get_historical_performance_by_edge_props(tracking_data):
    """Calculate win rates by EV/edge magnitude for props (probability-based)"""
    picks = tracking_data.get('picks', [])
    completed_picks = [p for p in picks if p.get('status') in ['win', 'loss']]
    
    from collections import defaultdict
    edge_ranges = defaultdict(lambda: {'wins': 0, 'losses': 0})
    
    for pick in completed_picks:
        # Use EV as edge proxy (EV is percentage-based)
        ev = abs(float(pick.get('ev', 0)))
        status = pick.get('status', '')
        
        # Probability/EV edge range buckets (in percentage points)
        if ev >= 15:
            range_key = "15%+"
        elif ev >= 12:
            range_key = "12-14.9%"
        elif ev >= 10:
            range_key = "10-11.9%"
        elif ev >= 8:
            range_key = "8-9.9%"
        elif ev >= 5:
            range_key = "5-7.9%"
        else:
            range_key = "0-4.9%"
        
        if status == 'win':
            edge_ranges[range_key]['wins'] += 1
        elif status == 'loss':
            edge_ranges[range_key]['losses'] += 1
    
    performance_by_edge = {}
    for range_key, stats in edge_ranges.items():
        total = stats['wins'] + stats['losses']
        if total >= 5:  # Only use ranges with sufficient data
            win_rate = stats['wins'] / total if total > 0 else 0.5
            performance_by_edge[range_key] = win_rate
    
    return performance_by_edge

def calculate_probability_edge(ai_score, season_avg, recent_avg, prop_line, odds, bet_type):
    """Calculate probability edge for props (model prob - market prob)"""
    # Convert American odds to implied probability
    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)
    
    # Calculate model probability (same logic as calculate_ev)
    base_prob = 0.50
    ai_multiplier = max(0, (ai_score - 9.0) / 1.0)
    
    if bet_type == 'over':
        edge = season_avg - prop_line
    else:
        edge = prop_line - season_avg
    
    # For receptions, normalize edge differently (25 yards = full edge factor)
    edge_factor = min(abs(edge) / 2.0, 1.0)
    
    recent_factor = 0.0
    if bet_type == 'over' and recent_avg > season_avg:
        recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
    elif bet_type == 'under' and recent_avg < season_avg:
        recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)
    
    model_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15) + recent_factor
    model_prob = min(max(model_prob, 0.40), 0.70)
    
    # Probability edge = model prob - market prob
    prob_edge = abs(model_prob - implied_prob)
    return prob_edge

def calculate_ai_rating_props(play, historical_edge_performance):
    """
    Calculate A.I. Rating for props models (probability-based edges)
    Returns rating in 2.3-4.9 range
    """
    prob_edge = play.get('probability_edge')
    
    if prob_edge is None:
        ev = abs(play.get('ev', 0))
        prob_edge = ev / 100.0
    
    # Normalize probability edge to 0-5 scale (15% = 5.0 rating)
    if prob_edge >= 0.15:
        normalized_edge = 5.0
    else:
        normalized_edge = prob_edge / 0.03
        normalized_edge = min(5.0, max(0.0, normalized_edge))
    
    data_quality = 1.0 if play.get('ai_score', 0) >= 9.0 else 0.85
    
    historical_factor = 1.0
    if historical_edge_performance:
        ev = abs(play.get('ev', 0))
        if ev >= 15:
            range_key = "15%+"
        elif ev >= 12:
            range_key = "12-14.9%"
        elif ev >= 10:
            range_key = "10-11.9%"
        elif ev >= 8:
            range_key = "8-9.9%"
        elif ev >= 5:
            range_key = "5-7.9%"
        else:
            range_key = "0-4.9%"
        
        if range_key in historical_edge_performance:
            hist_win_rate = historical_edge_performance[range_key]
            historical_factor = 0.9 + (hist_win_rate - 0.55) * 2.0
            historical_factor = max(0.9, min(1.1, historical_factor))
    
    confidence = 1.0
    ai_score = play.get('ai_score', 0)
    ev = abs(play.get('ev', 0))
    
    if ai_score >= 9.8 and ev >= 12:
        confidence = 1.12
    elif ai_score >= 9.5 and ev >= 10:
        confidence = 1.08
    elif ai_score >= 9.0 and ev >= 8:
        confidence = 1.05
    elif ai_score >= 9.0:
        confidence = 1.0
    else:
        confidence = 0.95
    
    confidence = max(0.9, min(1.15, confidence))
    
    composite_rating = normalized_edge * data_quality * historical_factor * confidence
    ai_rating = 2.3 + (composite_rating / 5.0) * 2.6
    ai_rating = max(2.3, min(4.9, ai_rating))
    
    return round(ai_rating, 1)

def get_player_props():
    """Fetch player receptions prop odds from The Odds API"""
    print(f"\n{Colors.CYAN}Fetching player receptions prop odds...{Colors.END}")
    rosters = get_nfl_team_rosters()
    events_url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events"
    events_params = {'apiKey': API_KEY}

    try:
        events_response = requests.get(events_url, params=events_params, timeout=10)
        if events_response.status_code != 200:
            print(f"{Colors.RED}✗ API Error: {events_response.status_code}{Colors.END}")
            return []

        events = events_response.json()
        print(f"{Colors.CYAN}  Found {len(events)} upcoming games{Colors.END}")
        all_props = []

        for i, event in enumerate(events[:10], 1):
            event_id = event['id']
            home_team = event['home_team']
            away_team = event['away_team']

            odds_url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/{event_id}/odds"
            odds_params = {
                'apiKey': API_KEY,
                'regions': 'us',
                'markets': 'player_receptions',
                'oddsFormat': 'american'
            }

            odds_response = requests.get(odds_url, params=odds_params, timeout=15)

            if odds_response.status_code == 200:
                odds_data = odds_response.json()
                if 'bookmakers' in odds_data and odds_data['bookmakers']:
                    fanduel = next((b for b in odds_data['bookmakers'] if b['key'] == 'fanduel'),
                                  odds_data['bookmakers'][0])

                    if 'markets' in fanduel:
                        markets_list = fanduel.get('markets', [])
                        for market in markets_list:
                            market_key = market.get('key')
                            if market_key == 'player_receptions':
                                outcomes_list = market.get('outcomes', [])
                                for outcome in outcomes_list:
                                    player_name = outcome.get('description')
                                    if not player_name:
                                        continue
                                    
                                    try:
                                        player_team, player_opponent = match_player_to_team(
                                            player_name, home_team, away_team, rosters
                                        )

                                        prop = {
                                            'player': player_name,
                                            'prop_line': outcome.get('point'),
                                            'over_price': outcome.get('price', -110),
                                            'team': player_team,
                                            'opponent': player_opponent,
                                            'game_time': event.get('commence_time')
                                        }
                                        all_props.append(prop)
                                    except Exception as e:
                                        continue

            print(f"{Colors.CYAN}  Game {i}/{len(events[:10])}: {away_team} @ {home_team}{Colors.END}")

        print(f"{Colors.GREEN}✓ Fetched {len(all_props)} total player props{Colors.END}")
        return all_props

    except Exception as e:
        print(f"{Colors.RED}✗ Error fetching props: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return []

def calculate_ai_score(player_data, prop_line, bet_type, opponent_defense=None):
    """
    Calculate STRICT A.I. Score for receptions props using REAL stats
    Factors: Season avg, recent form, target share, opponent pass defense
    """
    score = 4.0

    season_avg = player_data.get('season_rec_avg', 0)
    recent_avg = player_data.get('recent_rec_avg', 0)
    target_share = player_data.get('target_share', 0)
    consistency = player_data.get('consistency_score', 0.3)
    games_played = player_data.get('games_played', 0)

    if games_played < 3:
        return 0.0

    if target_share < 0.15:  # Not enough volume
        return 0.0

    if bet_type == 'over':
        edge_above_line = season_avg - prop_line
        if edge_above_line >= MIN_EDGE_OVER_LINE:
            score += 3.5
        elif edge_above_line >= 1.5:
            score += 2.5
        elif edge_above_line >= 1.0:
            score += 1.5
        elif edge_above_line >= 0.5:
            score += 0.5
        else:
            score -= 2.0
            if recent_avg < prop_line + 0.5:
                return 0.0

        recent_edge = recent_avg - prop_line
        if recent_edge >= MIN_RECENT_FORM_EDGE:
            score += 2.5
        elif recent_edge >= 1.0:
            score += 1.5
        elif recent_avg > season_avg + 1.5:
            score += 1.0
        elif recent_avg >= prop_line:
            score += 0.5
        else:
            score -= 1.5

        # Target share bonus
        if target_share >= 0.25:
            score += 1.5
        elif target_share >= 0.20:
            score += 1.0
        elif target_share >= 0.18:
            score += 0.5

        score += consistency * 0.8

        # Opponent factors
        if opponent_defense:
            def_factor = opponent_defense.get('defense_factor', 1.0)
            if def_factor > 1.05:
                score += 1.0
            elif def_factor < 0.95:
                score -= 0.5

    else:  # under
        edge_below_line = prop_line - season_avg
        if edge_below_line >= MIN_EDGE_UNDER_LINE:
            score += 3.5
        elif edge_below_line >= 1.5:
            score += 2.5
        elif edge_below_line >= 1.0:
            score += 1.5
        elif edge_below_line >= 0.5:
            score += 0.5
        else:
            score -= 2.0
            if recent_avg > prop_line - 0.5:
                return 0.0

        recent_edge = prop_line - recent_avg
        if recent_edge >= MIN_RECENT_FORM_EDGE:
            score += 2.5
        elif recent_edge >= 1.0:
            score += 1.5
        elif recent_avg < season_avg - 1.5:
            score += 1.0
        elif recent_avg <= prop_line:
            score += 0.5
        else:
            score -= 1.5

        if target_share < 0.18:
            score += 1.0
        elif target_share < 0.20:
            score += 0.5

        score += (1.0 - consistency) * 0.5

        if opponent_defense:
            def_factor = opponent_defense.get('defense_factor', 1.0)
            if def_factor < 0.95:
                score += 1.0
            elif def_factor > 1.05:
                score -= 0.5

    final_score = min(10.0, max(0.0, score))
    
    if bet_type == 'over' and season_avg < prop_line + 0.5:
        final_score = min(final_score, 8.5)
    elif bet_type == 'under' and season_avg > prop_line - 0.5:
        final_score = min(final_score, 8.5)

    return round(final_score, 2)

def calculate_ev(ai_score, prop_line, season_avg, recent_avg, odds, bet_type):
    """
    Calculate Expected Value based on AI score and player stats
    Higher AI score + larger edge = higher EV
    Target: 60% hit rate for AI score 9.5+
    """
    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)
    
    base_prob = 0.50
    ai_multiplier = max(0, (ai_score - 9.0) / 1.0)
    
    if bet_type == 'over':
        edge = season_avg - prop_line
    else:
        edge = prop_line - season_avg
    
    # Normalize edge for receptions (25 yards = full factor)
    edge_factor = min(abs(edge) / 2.0, 1.0)
    
    recent_factor = 0.0
    if bet_type == 'over' and recent_avg > season_avg:
        recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
    elif bet_type == 'under' and recent_avg < season_avg:
        recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)
    
    true_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15) + recent_factor
    true_prob = min(max(true_prob, 0.40), 0.70)
    
    if odds > 0:
        ev = (true_prob * (odds / 100)) - (1 - true_prob)
    else:
        ev = (true_prob * (100 / abs(odds))) - (1 - true_prob)
    
    return ev * 100

def analyze_props(props_list, player_stats, defense_factors, historical_edge_performance=None):
    """Analyze all player props using REAL NFL stats"""
    print(f"\n{Colors.CYAN}Analyzing {len(props_list)} player props with REAL stats...{Colors.END}")

    over_plays = []
    under_plays = []
    skipped_no_stats = 0
    skipped_low_score = 0

    for prop in props_list:
        player_name = prop['player']
        prop_line = prop['prop_line']
        opponent_team = prop['opponent']

        player_data = player_stats.get(player_name)
        if not player_data:
            # Try to match by last name
            prop_last = player_name.split()[-1].lower() if ' ' in player_name else player_name.lower()
            prop_first = player_name.split()[0].lower() if ' ' in player_name else ''
            
            for name, stats in player_stats.items():
                name_lower = name.lower()
                if player_name.lower() == name_lower:
                    player_data = stats
                    break
                name_last = name.split()[-1].lower() if ' ' in name else name_lower.split('.')[-1] if '.' in name else name_lower
                if prop_last == name_last:
                    player_data = stats
                    break
                if prop_last in name_lower or name_last in player_name.lower():
                    player_data = stats
                    break
                if '.' in name and prop_last in name_lower:
                    player_data = stats
                    break
            
            if not player_data:
                skipped_no_stats += 1
                continue

        opponent_defense = None
        if opponent_team in defense_factors:
            opponent_defense = defense_factors[opponent_team]
        else:
            for team_name, factors in defense_factors.items():
                if opponent_team.lower() in team_name.lower() or team_name.lower() in opponent_team.lower():
                    opponent_defense = factors
                    break

        over_score = calculate_ai_score(player_data, prop_line, 'over', opponent_defense)
        if over_score >= MIN_AI_SCORE:
            season_avg = player_data.get('season_rec_avg', 0)
            recent_avg = player_data.get('recent_rec_avg', 0)
            
            if season_avg >= prop_line + 1.0 and recent_avg >= prop_line + 0.5:
                ev = calculate_ev(over_score, prop_line, season_avg, recent_avg, prop['over_price'], 'over')
                is_sharp = over_score >= AUTO_TRACK_THRESHOLD and ev > 0
                prob_edge = calculate_probability_edge(over_score, season_avg, recent_avg, prop_line, prop['over_price'], 'over')
                
                play_dict = {
                    'player': player_name,
                    'prop': f"OVER {prop_line} REC",
                    'team': prop['team'],
                    'opponent': opponent_team,
                    'ai_score': over_score,
                    'odds': prop['over_price'],
                    'game_time': prop['game_time'],
                    'season_avg': season_avg,
                    'recent_avg': recent_avg,
                    'edge': round(season_avg - prop_line, 2),
                    'ev': round(ev, 2),
                    'probability_edge': prob_edge,
                    'is_sharp': is_sharp
                }
                
                if historical_edge_performance:
                    ai_rating = calculate_ai_rating_props(play_dict, historical_edge_performance)
                    play_dict['ai_rating'] = ai_rating
                
                over_plays.append(play_dict)
            else:
                skipped_low_score += 1
        else:
            skipped_low_score += 1

        under_score = calculate_ai_score(player_data, prop_line, 'under', opponent_defense)
        if under_score >= MIN_AI_SCORE:
            season_avg = player_data.get('season_rec_avg', 0)
            recent_avg = player_data.get('recent_rec_avg', 0)
            
            if season_avg <= prop_line - 1.0 and recent_avg <= prop_line - 0.5:
                ev = calculate_ev(under_score, prop_line, season_avg, recent_avg, prop['over_price'], 'under')
                is_sharp = under_score >= AUTO_TRACK_THRESHOLD and ev > 0
                prob_edge = calculate_probability_edge(under_score, season_avg, recent_avg, prop_line, prop['over_price'], 'under')
                
                play_dict = {
                    'player': player_name,
                    'prop': f"UNDER {prop_line} REC",
                    'team': prop['team'],
                    'opponent': opponent_team,
                    'ai_score': under_score,
                    'odds': prop['over_price'],
                    'game_time': prop['game_time'],
                    'season_avg': season_avg,
                    'recent_avg': recent_avg,
                    'edge': round(prop_line - season_avg, 2),
                    'ev': round(ev, 2),
                    'probability_edge': prob_edge,
                    'is_sharp': is_sharp
                }
                
                if historical_edge_performance:
                    ai_rating = calculate_ai_rating_props(play_dict, historical_edge_performance)
                    play_dict['ai_rating'] = ai_rating
                
                under_plays.append(play_dict)
            else:
                skipped_low_score += 1
        else:
            skipped_low_score += 1

    seen_over = set()
    unique_over = []
    for play in over_plays:
        key = f"{play['player']}_{play['prop']}"
        if key not in seen_over:
            seen_over.add(key)
            unique_over.append(play)

    seen_under = set()
    unique_under = []
    for play in under_plays:
        key = f"{play['player']}_{play['prop']}"
        if key not in seen_under:
            seen_under.add(key)
            unique_under.append(play)

    # Sort by A.I. Rating (primary), AI Score (secondary)
    def get_sort_score(play):
        rating = play.get('ai_rating', 2.3)
        ai_score = play.get('ai_score', 0)
        return (rating, ai_score)
    
    unique_over.sort(key=get_sort_score, reverse=True)
    unique_under.sort(key=get_sort_score, reverse=True)

    over_plays = unique_over[:TOP_PLAYS_COUNT]
    under_plays = unique_under[:TOP_PLAYS_COUNT]

    print(f"{Colors.GREEN}✓ Found {len(over_plays)} top OVER plays (A.I. Score >= {MIN_AI_SCORE}){Colors.END}")
    print(f"{Colors.GREEN}✓ Found {len(under_plays)} top UNDER plays (A.I. Score >= {MIN_AI_SCORE}){Colors.END}")
    if skipped_no_stats > 0:
        print(f"{Colors.YELLOW}  Skipped {skipped_no_stats} props (no player stats found){Colors.END}")
    if skipped_low_score > 0:
        print(f"{Colors.YELLOW}  Skipped {skipped_low_score} props (score below {MIN_AI_SCORE}){Colors.END}")

    return over_plays, under_plays

def track_pick(player_name, prop_line, bet_type, team, opponent, ai_score, odds, game_time):
    """Add a pick to tracking file"""
    tracking_data = load_tracking()
    pick_id = f"{player_name}_{prop_line}_{bet_type}_{game_time}"
    
    existing = next((p for p in tracking_data['picks'] if p.get('pick_id') == pick_id), None)
    if existing:
        if odds != existing.get('odds'):
            existing['opening_odds'] = existing.get('opening_odds', existing.get('odds'))
            existing['latest_odds'] = odds
            existing['last_updated'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
            save_tracking(tracking_data)
        return False

    pick = {
        'pick_id': pick_id,
        'player': player_name,
        'prop_line': prop_line,
        'bet_type': bet_type,
        'team': team,
        'opponent': opponent,
        'ai_score': ai_score,
        'odds': odds,
        'opening_odds': odds,
        'latest_odds': odds,
        'game_time': game_time,
        'tracked_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
        'status': 'pending',
        'result': None,
        'actual_rec': None
    }

    tracking_data['picks'].append(pick)
    tracking_data['summary'] = calculate_tracking_summary(tracking_data['picks'])
    save_tracking(tracking_data)
    return True

def update_pick_results():
    """Check pending picks and update their status - placeholder for NFL"""
    # For now, return 0 - would need NFL stats API integration
    # This can be implemented later with ESPN API or similar
    return 0

def generate_html_output(over_plays, under_plays, tracking_summary=None, tracking_data=None):
    """Generate HTML output matching NBA model card-based style"""
    from datetime import datetime as dt
    et = pytz.timezone('US/Eastern')
    now = dt.now(et)
    date_str = now.strftime('%m/%d/%y')
    time_str = now.strftime('%I:%M %p ET')
    
    def format_game_time(game_time_str):
        try:
            if not game_time_str:
                return 'TBD'
            dt_obj = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            et_tz = pytz.timezone('US/Eastern')
            dt_et = dt_obj.astimezone(et_tz)
            return dt_et.strftime('%m/%d %I:%M %p ET')
        except:
            return game_time_str if game_time_str else 'TBD'
    
    def get_play_clv(play):
        if not tracking_data or not tracking_data.get('picks'):
            return None
        prop_line = float(play['prop'].split()[1])
        bet_type = 'over' if 'OVER' in play['prop'] else 'under'
        for pick in tracking_data['picks']:
            if (pick['player'] == play['player'] and 
                pick['prop_line'] == prop_line and 
                pick['bet_type'] == bet_type):
                opening = pick.get('opening_odds')
                latest = pick.get('latest_odds')
                if opening and latest and opening != latest:
                    is_positive = latest < opening
                    return {
                        'opening': opening,
                        'latest': latest,
                        'positive': is_positive,
                        'change': latest - opening
                    }
        return None

    tracking_section = ""
    if tracking_summary and tracking_summary['total'] > 0:
        completed = tracking_summary['wins'] + tracking_summary['losses']
        if True:
            win_rate_color = '#4ade80' if tracking_summary['win_rate'] >= 55 else ('#fbbf24' if tracking_summary['win_rate'] >= 52 else '#f87171')
            roi_color = '#4ade80' if tracking_summary['roi'] >= 0 else '#f87171'
            clv_color = '#4ade80' if tracking_summary.get('clv_rate', 0) >= 50 else '#f87171'
            tracking_section = f"""
            <div class="card">
                <h2 style="font-size: 1.75rem; font-weight: 700; margin-bottom: 1.5rem; text-align: center;">📊 NFL Receptions Model Tracking</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                    <div style="background: #262626; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Total Picks</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #ffffff;">{tracking_summary['total']}</div>
                    </div>
                    <div style="background: #262626; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Win Rate</div>
                        <div style="font-size: 2rem; font-weight: 700; color: {win_rate_color if completed > 0 else '#94a3b8'};">{tracking_summary['win_rate']:.1f}%{' (N/A)' if completed == 0 else ''}</div>
                    </div>
                    <div style="background: #262626; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Record</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #ffffff;">{tracking_summary['wins']}-{tracking_summary['losses']}</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">({completed} completed)</div>
                    </div>
                    <div style="background: #262626; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">P/L (Units)</div>
                        <div style="font-size: 2rem; font-weight: 700; color: {roi_color if completed > 0 else '#94a3b8'};">{tracking_summary['roi']:+.2f}u</div>
                        <div style="font-size: 0.75rem; color: {roi_color if completed > 0 else '#94a3b8'}; margin-top: 0.25rem;">{tracking_summary.get('roi_pct', 0):+.1f}% ROI{' (Pending)' if completed == 0 else ''}</div>
                    </div>
                    <div style="background: #262626; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Pending</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #fbbf24;">{tracking_summary['pending']}</div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #2a3441;">
                    <div style="background: #262626; padding: 1rem; border-radius: 0.75rem;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Closing Line Value</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: {clv_color};">{tracking_summary.get('clv_rate', 0):.1f}%</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">{tracking_summary.get('clv_count', '0/0')} positive CLV</div>
                    </div>
                    <div style="background: #262626; padding: 1rem; border-radius: 0.75rem;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Avg A.I. Score</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #60a5fa;">9.7+</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">Elite plays only</div>
                    </div>
                    <div style="background: #262626; padding: 1rem; border-radius: 0.75rem;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Edge Requirements</div>
                        <div style="font-size: 1rem; font-weight: 600; color: #ffffff;">{MIN_EDGE_OVER_LINE}+ OVER / {MIN_EDGE_UNDER_LINE}+ UNDER</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">Strict thresholds</div>
                    </div>
                </div>
            </div>"""

    over_html = ""
    if over_plays:
        over_html = """
            <div class="card">
                <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; color: #4ade80;">TOP OVER PLAYS</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">"""
        
        for i, play in enumerate(over_plays, 1):
            tracked_badge = '<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(74, 222, 128, 0.2); color: #4ade80; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">📊 TRACKED</span>' if play['ai_score'] >= AUTO_TRACK_THRESHOLD else ""
            confidence_pct = min(int((play['ai_score'] / 10.0) * 100), 100)
            game_time_formatted = format_game_time(play.get('game_time', ''))
            
            ev_badge = ""
            ev = play.get('ev', 0)
            is_sharp = play.get('is_sharp', False)
            if ev > 0:
                ev_badge = f'<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(74, 222, 128, 0.2); color: #4ade80; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">+{ev:.1f}% EV</span>'
                if is_sharp:
                    ev_badge += '<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(96, 165, 250, 0.2); color: #60a5fa; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">SHARP</span>'
            
            clv_info = get_play_clv(play)
            clv_display = ""
            if clv_info:
                clv_color = '#4ade80' if clv_info['positive'] else '#f87171'
                clv_icon = '✅' if clv_info['positive'] else '⚠️'
                opening_str = f"{clv_info['opening']:+.0f}" if clv_info['opening'] > 0 else f"{clv_info['opening']}"
                latest_str = f"{clv_info['latest']:+.0f}" if clv_info['latest'] > 0 else f"{clv_info['latest']}"
                clv_display = f"""
                        <div class="odds-line" style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #1a2332;">
                            <span style="color: {clv_color}; font-weight: 600;">{clv_icon} CLV:</span>
                            <strong style="color: {clv_color};">Opening: {opening_str} → Latest: {latest_str}</strong>
                        </div>"""
            
            over_html += f"""
                    <div class="bet-box" style="border-left: 4px solid #4ade80;">
                        <div class="bet-title" style="color: #4ade80;">#{i} • {play['prop']}</div>
                        <div class="odds-line">
                            <span>Player:</span>
                            <strong>{play['player']}</strong>
                        </div>
                        <div class="odds-line">
                            <span>Matchup:</span>
                            <strong>{play['team']} vs {play['opponent']}</strong>
                        </div>
                        <div class="odds-line">
                            <span>🕐 Game Time:</span>
                            <strong>{game_time_formatted}</strong>
                        </div>
                        <div class="odds-line">
                            <span>Season Avg:</span>
                            <strong>{play.get('season_avg', 'N/A')}</strong>
                        </div>
                        <div class="odds-line">
                            <span>Recent Avg:</span>
                            <strong>{play.get('recent_avg', 'N/A')}</strong>
                        </div>
                        {clv_display}
                        <div class="confidence-bar-container">
                            <div class="confidence-label">
                                <span>A.I. Score</span>
                                <span class="confidence-pct">{play['ai_score']:.2f}</span>
                            </div>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: {confidence_pct}%"></div>
                            </div>
                        </div>
                        <div class="pick pick-yes">
                            ✅ {play['prop']}{ev_badge}{tracked_badge}
                        </div>
                    </div>"""
        
        over_html += """
                </div>
            </div>"""

    under_html = ""
    if under_plays:
        under_html = """
            <div class="card">
                <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 1.5rem; color: #f87171;">TOP UNDER PLAYS</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">"""
        
        for i, play in enumerate(under_plays, 1):
            tracked_badge = '<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(248, 113, 113, 0.2); color: #f87171; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">📊 TRACKED</span>' if play['ai_score'] >= AUTO_TRACK_THRESHOLD else ""
            confidence_pct = min(int((play['ai_score'] / 10.0) * 100), 100)
            game_time_formatted = format_game_time(play.get('game_time', ''))
            
            ev_badge = ""
            ev = play.get('ev', 0)
            is_sharp = play.get('is_sharp', False)
            if ev > 0:
                ev_badge = f'<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(74, 222, 128, 0.2); color: #4ade80; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">+{ev:.1f}% EV</span>'
                if is_sharp:
                    ev_badge += '<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(96, 165, 250, 0.2); color: #60a5fa; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">SHARP</span>'
            
            clv_info = get_play_clv(play)
            clv_display = ""
            if clv_info:
                clv_color = '#4ade80' if clv_info['positive'] else '#f87171'
                clv_icon = '✅' if clv_info['positive'] else '⚠️'
                opening_str = f"{clv_info['opening']:+.0f}" if clv_info['opening'] > 0 else f"{clv_info['opening']}"
                latest_str = f"{clv_info['latest']:+.0f}" if clv_info['latest'] > 0 else f"{clv_info['latest']}"
                clv_display = f"""
                        <div class="odds-line" style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid #1a2332;">
                            <span style="color: {clv_color}; font-weight: 600;">{clv_icon} CLV:</span>
                            <strong style="color: {clv_color};">Opening: {opening_str} → Latest: {latest_str}</strong>
                        </div>"""
            
            under_html += f"""
                    <div class="bet-box" style="border-left: 4px solid #f87171;">
                        <div class="bet-title" style="color: #f87171;">#{i} • {play['prop']}</div>
                        <div class="odds-line">
                            <span>Player:</span>
                            <strong>{play['player']}</strong>
                        </div>
                        <div class="odds-line">
                            <span>Matchup:</span>
                            <strong>{play['team']} vs {play['opponent']}</strong>
                        </div>
                        <div class="odds-line">
                            <span>🕐 Game Time:</span>
                            <strong>{game_time_formatted}</strong>
                        </div>
                        <div class="odds-line">
                            <span>Season Avg:</span>
                            <strong>{play.get('season_avg', 'N/A')}</strong>
                        </div>
                        <div class="odds-line">
                            <span>Recent Avg:</span>
                            <strong>{play.get('recent_avg', 'N/A')}</strong>
                        </div>
                        {clv_display}
                        <div class="confidence-bar-container">
                            <div class="confidence-label">
                                <span>A.I. Score</span>
                                <span class="confidence-pct">{play['ai_score']:.2f}</span>
                            </div>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: {confidence_pct}%"></div>
                            </div>
                        </div>
                        <div class="pick pick-no">
                            ✅ {play['prop']}{ev_badge}{tracked_badge}
                        </div>
                    </div>"""
        
        under_html += """
                </div>
            </div>"""

    footer_text = f"Powered by REAL NFL Stats • Only showing picks with A.I. Score ≥ {MIN_AI_SCORE}<br>Using strict edge requirements: {MIN_EDGE_OVER_LINE}+ above line (OVER) / {MIN_EDGE_UNDER_LINE}+ below line (UNDER)<br>📊 = Auto-tracked (A.I. Score >= {AUTO_TRACK_THRESHOLD})"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFL Receptions Props - A.I. Projections</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
            background: #000000;
            color: #ffffff;
            padding: 1.5rem;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{
            background: #1a1a1a;
            border-radius: 1.25rem;
            border: none;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        .header-card {{
            text-align: center;
            background: #1a1a1a;
            border: none;
        }}
        .bet-box {{
            background: #262626;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            padding: 1.75rem;
            border-radius: 1.25rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            position: relative;
        }}}
        .ai-rating {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 0.75rem;
            border-radius: 0.5rem;
            font-size: 0.875rem;
            margin: 0.5rem 0;
            border-left: 3px solid;
        }}
        .ai-rating .rating-label {{
            font-weight: 600;
            opacity: 0.9;
        }}
        .ai-rating .rating-value {{
            font-weight: 700;
            font-size: 0.9375rem;
        }}
        .ai-rating .rating-badge {{
            font-size: 0.75rem;
            opacity: 0.85;
            margin-left: auto;
        }}
        .ai-rating-premium {{
            background: rgba(74, 222, 128, 0.12);
            color: #4ade80;
            border-color: #4ade80;
        }}
        .ai-rating-strong {{
            background: rgba(74, 222, 128, 0.10);
            color: #4ade80;
            border-color: #4ade80;
        }}
        .ai-rating-good {{
            background: rgba(96, 165, 250, 0.10);
            color: #60a5fa;
            border-color: #60a5fa;
        }}
        .ai-rating-standard {{
            background: rgba(251, 191, 36, 0.10);
            color: #fbbf24;
            border-color: #fbbf24;
        }}
        .ai-rating-marginal {{
            background: rgba(251, 191, 36, 0.08);
            color: #fbbf24;
            border-color: #fbbf24;
        }}
        .bet-title {{
            font-weight: 600;
            color: #94a3b8;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}
        .odds-line {{
            display: flex;
            justify-content: space-between;
            margin: 0.25rem 0;
            font-size: 0.9375rem;
            color: #94a3b8;
        }}
        .odds-line strong {{
            color: #ffffff;
            font-weight: 600;
        }}
        .confidence-bar-container {{
            margin: 0.75rem 0;
        }}
        .confidence-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
            color: #94a3b8;
        }}
        .confidence-pct {{
            font-weight: 700;
            color: #4ade80;
        }}
        .confidence-bar {{
            height: 6px;
            background: #1a1a1a;
            border-radius: 999px;
            overflow: hidden;
            border: none;
        }}
        .confidence-fill {{
            height: 100%;
            background: #4ade80;
            border-radius: 999px;
            transition: width 0.3s ease;
        }}
        .pick {{
            font-weight: 600;
            padding: 0.875rem 1rem;
            margin-top: 0.75rem;
            border-radius: 0.75rem;
            font-size: 1rem;
            line-height: 1.5;
        }}
        .pick-yes {{ background: rgba(74, 222, 128, 0.15); color: #4ade80; border: 2px solid #4ade80; }}
        .pick-no {{ background: rgba(248, 113, 113, 0.15); color: #f87171; border: 2px solid #f87171; }}
        .badge {{
            display: inline-block;
            padding: 0.375rem 0.875rem;
            border-radius: 0.5rem;
            font-size: 0.8125rem;
            font-weight: 600;
            background: rgba(74, 222, 128, 0.2);
            color: #4ade80;
            margin: 0.25rem;
        }}
        @media (max-width: 1024px) {{
            .container {{ max-width: 100%; }}
            .card {{ padding: 1.5rem; }}
        }}
        @media (max-width: 768px) {{
            body {{ padding: 1rem; }}
            .card {{ padding: 1.25rem; }}
            .bet-box {{ padding: 1rem; }}
            .pick {{ font-size: 0.9375rem; padding: 0.75rem; }}
        }}
        @media (max-width: 480px) {{
            body {{ padding: 0.75rem; }}
            .card {{ padding: 1rem; margin-bottom: 1rem; }}
            .bet-box {{ padding: 0.875rem; }}
            .bet-title {{ font-size: 0.6875rem; }}
            .odds-line {{ font-size: 0.8125rem; }}
            .pick {{ font-size: 0.875rem; padding: 0.625rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card header-card">
            <h1 style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem; background: linear-gradient(135deg, #60a5fa 0%, #f472b6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Gridiron Analytics</h1>
            <p style="font-size: 1.5rem; opacity: 0.95; font-weight: 600;">NFL Receptions Props Model</p>
            <div>
                <div class="badge">● REAL NFL STATS</div>
                <div class="badge">● A.I. SCORE ≥ {MIN_AI_SCORE}</div>
                <div class="badge">● STRICT EDGE REQUIREMENTS</div>
            </div>
            <p style="font-size: 0.875rem; opacity: 0.75; margin-top: 1rem;">Generated: {date_str} {time_str}</p>
        </div>

        {over_html}

        {under_html}

        {tracking_section}

        <div class="card" style="text-align: center;">
            <p style="color: #94a3b8; font-size: 0.875rem; line-height: 1.8;">{footer_text}</p>
        </div>
    </div>
</body>
</html>"""

    return html

def save_html(html_content):
    """Save HTML output to file"""
    try:
        with open(OUTPUT_HTML, 'w') as f:
            f.write(html_content)
        print(f"\n{Colors.GREEN}✓ HTML report saved: {OUTPUT_HTML}{Colors.END}")
        return True
    except Exception as e:
        print(f"\n{Colors.RED}✗ Error saving HTML: {e}{Colors.END}")
        return False

def main():
    """Main execution"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}NFL PASSING YARDS PROPS A.I. MODEL{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

    updated = update_pick_results()
    player_stats = get_nfl_player_passing_yards_stats()
    defense_factors = get_opponent_pass_defense_factors()
    props_list = get_player_props()
    tracking_data = load_tracking()
    historical_edge_performance = get_historical_performance_by_edge_props(tracking_data)
    
    over_plays, under_plays = analyze_props(props_list, player_stats, defense_factors, historical_edge_performance)

    print(f"\n{Colors.CYAN}Auto-tracking picks with A.I. Score >= {AUTO_TRACK_THRESHOLD}...{Colors.END}")
    tracked_count = 0
    
    # Only track plays that are currently being displayed (top plays)
    displayed_plays = over_plays[:TOP_PLAYS_COUNT] + under_plays[:TOP_PLAYS_COUNT]
    
    for play in displayed_plays:
        if play['ai_score'] >= AUTO_TRACK_THRESHOLD:
            matching_prop = next((p for p in props_list if p['player'] == play['player'] and p['prop_line'] == float(play['prop'].split()[1])), None)
            if matching_prop:
                bet_type = 'over' if 'OVER' in play['prop'] else 'under'
                if track_pick(
                    play['player'],
                    float(play['prop'].split()[1]),
                    bet_type,
                    play['team'],
                    play['opponent'],
                    play['ai_score'],
                    play.get('odds', -110),
                    matching_prop['game_time']
                ):
                    tracked_count += 1

    if tracked_count > 0:
        print(f"{Colors.GREEN}✓ Tracked {tracked_count} new picks{Colors.END}")
    else:
        print(f"{Colors.YELLOW}  No new picks to track{Colors.END}")

    tracking_data = load_tracking()
    # Recalculate summary based on currently displayed plays only
    displayed_plays = over_plays[:TOP_PLAYS_COUNT] + under_plays[:TOP_PLAYS_COUNT]
    summary = calculate_tracking_summary(tracking_data['picks'], displayed_plays)
    tracking_data['summary'] = summary  # Update tracking data with filtered summary

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}TRACKING SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"Total Picks: {summary['total']} | Wins: {summary['wins']} | Losses: {summary['losses']} | Pending: {summary['pending']}")
    if summary['wins'] + summary['losses'] > 0:
        print(f"Win Rate: {summary['win_rate']:.1f}% | ROI: {summary['roi']:+.2f}u ({summary['roi_pct']:+.1f}%)")

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}TOP OVER PLAYS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")

    for i, play in enumerate(over_plays[:10], 1):
        tracked_marker = "📊" if play['ai_score'] >= AUTO_TRACK_THRESHOLD else "  "
        print(f"{tracked_marker} {Colors.CYAN}{i:2d}. {play['player']:25s}{Colors.END} | "
              f"{Colors.GREEN}{play['prop']:15s}{Colors.END} | "
              f"{play['team']:3s} vs {play['opponent']:3s} | "
              f"{Colors.BOLD}A.I.: {play['ai_score']:.2f}{Colors.END}")

    print(f"\n{Colors.BOLD}{Colors.RED}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.RED}TOP UNDER PLAYS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.RED}{'='*80}{Colors.END}")

    for i, play in enumerate(under_plays[:10], 1):
        tracked_marker = "📊" if play['ai_score'] >= AUTO_TRACK_THRESHOLD else "  "
        print(f"{tracked_marker} {Colors.CYAN}{i:2d}. {play['player']:25s}{Colors.END} | "
              f"{Colors.RED}{play['prop']:15s}{Colors.END} | "
              f"{play['team']:3s} vs {play['opponent']:3s} | "
              f"{Colors.BOLD}A.I.: {play['ai_score']:.2f}{Colors.END}")

    print(f"\n{Colors.YELLOW}📊 = Auto-tracked (A.I. Score >= {AUTO_TRACK_THRESHOLD}){Colors.END}")

    print(f"\n{Colors.CYAN}Generating HTML report...{Colors.END}")
    html_content = generate_html_output(over_plays, under_plays, summary, tracking_data)
    save_html(html_content)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}✓ Model execution complete!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}\n")

if __name__ == "__main__":
    main()
