#!/usr/bin/env python3
"""
NBA 3-Point Props Model - PROFITABLE VERSION
Analyzes player 3PM (3-pointers made) props using REAL NBA stats
"""

import requests
import json
import os
from datetime import datetime, timedelta
import pytz
from collections import defaultdict
import statistics
import time
import pandas as pd
from dotenv import load_dotenv

# Import NBA API for real stats
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats, playergamelog
from nba_api.stats.static import players

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('ODDS_API_KEY')
if not API_KEY:
    raise ValueError("ODDS_API_KEY environment variable not set. Please add it to your .env file.")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "nba_3pt_props.html")
TRACKING_FILE = os.path.join(SCRIPT_DIR, "nba_3pt_props_tracking.json")
PLAYER_STATS_CACHE = os.path.join(SCRIPT_DIR, "nba_player_3pt_stats_cache.json")
TEAM_DEFENSE_CACHE = os.path.join(SCRIPT_DIR, "nba_team_defense_3pt_cache.json")

# Model Parameters - MUCH STRICTER FOR PROFITABILITY
MIN_AI_SCORE = 9.5  # Raised from 8.5 - only show high-confidence plays
TOP_PLAYS_COUNT = 5  # Reduced from 8 - quality over quantity
RECENT_GAMES_WINDOW = 10  # 10 games for recent form
AUTO_TRACK_THRESHOLD = 9.7  # Raised from 9.2 - only track elite plays
CURRENT_SEASON = '2025-26'  # Update season as needed

# Edge requirements (similar to successful NBA model)
MIN_EDGE_OVER_LINE = 1.2  # Player must average 1.2+ above prop line for OVER
MIN_EDGE_UNDER_LINE = 1.0  # Player must average 1.0+ below prop line for UNDER
MIN_RECENT_FORM_EDGE = 0.8  # Recent form must support the bet

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def get_nba_player_stats():
    """
    Fetch REAL NBA player 3PT stats from NBA API
    Returns dictionary with player 3PT stats (season avg, recent form, etc.)
    """
    print(f"\n{Colors.CYAN}Fetching REAL NBA player 3PT statistics...{Colors.END}")

    # Check cache first (6 hour cache)
    if os.path.exists(PLAYER_STATS_CACHE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(PLAYER_STATS_CACHE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached player stats (less than 6 hours old){Colors.END}")
            with open(PLAYER_STATS_CACHE, 'r') as f:
                return json.load(f)

    player_stats = {}

    try:
        # Fetch season stats
        print(f"{Colors.CYAN}  Fetching season stats...{Colors.END}")
        season_stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense='Base',
            per_mode_detailed='PerGame',
            timeout=30
        )
        season_df = season_stats.get_data_frames()[0]
        time.sleep(0.6)

        # Fetch recent form (last N games)
        print(f"{Colors.CYAN}  Fetching recent form (last {RECENT_GAMES_WINDOW} games)...{Colors.END}")
        recent_stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense='Base',
            per_mode_detailed='PerGame',
            last_n_games=RECENT_GAMES_WINDOW,
            timeout=30
        )
        recent_df = recent_stats.get_data_frames()[0]
        time.sleep(0.6)

        # Process player stats
        for _, row in season_df.iterrows():
            player_name = row.get('PLAYER_NAME', '')
            if not player_name:
                continue

            # Season averages
            season_3pm = row.get('FG3M', 0)  # 3-pointers made per game
            season_3pa = row.get('FG3A', 0)  # 3-pointers attempted per game
            season_3pct = row.get('FG3_PCT', 0)  # 3-point percentage
            games_played = row.get('GP', 0)
            team = row.get('TEAM_ABBREVIATION', '')

            # Get recent form
            recent_row = recent_df[recent_df['PLAYER_NAME'] == player_name]
            if not recent_row.empty:
                recent_3pm = recent_row.iloc[0].get('FG3M', season_3pm)
                recent_3pa = recent_row.iloc[0].get('FG3A', season_3pa)
                recent_3pct = recent_row.iloc[0].get('FG3_PCT', season_3pct)
            else:
                recent_3pm = season_3pm
                recent_3pa = season_3pa
                recent_3pct = season_3pct

            # Calculate consistency (lower std dev = more consistent)
            # For now, estimate consistency based on 3pt% and attempts
            # Higher attempts + good % = more consistent
            consistency = min(1.0, (season_3pa / 10.0) * (season_3pct / 0.40)) if season_3pa > 0 else 0.3

            player_stats[player_name] = {
                'season_3pm_avg': round(season_3pm, 2),
                'season_3pa_avg': round(season_3pa, 2),
                'season_3pct': round(season_3pct, 3),
                'recent_3pm_avg': round(recent_3pm, 2),
                'recent_3pa_avg': round(recent_3pa, 2),
                'recent_3pct': round(recent_3pct, 3),
                'consistency_score': round(consistency, 2),
                'games_played': int(games_played),
                'team': team
            }

        # Cache results
        with open(PLAYER_STATS_CACHE, 'w') as f:
            json.dump(player_stats, f, indent=2)

        print(f"{Colors.GREEN}✓ Fetched REAL stats for {len(player_stats)} players{Colors.END}")
        return player_stats

    except Exception as e:
        print(f"{Colors.RED}✗ Error fetching NBA stats: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        # Try to load from cache if available
        if os.path.exists(PLAYER_STATS_CACHE):
            print(f"{Colors.YELLOW}  Loading from cache as fallback...{Colors.END}")
            with open(PLAYER_STATS_CACHE, 'r') as f:
                return json.load(f)
        return {}

def get_opponent_defense_3pt():
    """
    Fetch team defense vs 3PT shooting stats
    Returns dict with opponent 3PT defense ratings
    """
    print(f"\n{Colors.CYAN}Fetching opponent 3PT defense stats...{Colors.END}")

    # Check cache
    if os.path.exists(TEAM_DEFENSE_CACHE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(TEAM_DEFENSE_CACHE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached defense stats{Colors.END}")
            with open(TEAM_DEFENSE_CACHE, 'r') as f:
                return json.load(f)

    defense_stats = {}

    try:
        # Fetch team defense stats
        team_stats = leaguedashteamstats.LeagueDashTeamStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense='Base',
            timeout=30
        )
        team_df = team_stats.get_data_frames()[0]
        time.sleep(0.6)

        # Process defense stats
        for _, row in team_df.iterrows():
            team_name = row.get('TEAM_NAME', '')
            if not team_name:
                continue

            # Opponent 3PT stats allowed
            opp_3pm = row.get('OPP_FG3M', 0)  # Opponent 3PM per game
            opp_3pa = row.get('OPP_FG3A', 0)  # Opponent 3PA per game
            opp_3pct = row.get('OPP_FG3_PCT', 0)  # Opponent 3PT% allowed

            # Calculate defense rating (higher = worse defense, better for shooters)
            # League average is ~12.5 3PM allowed, 35% 3PT% allowed
            defense_rating = (opp_3pm / 12.5) * (opp_3pct / 0.35)  # >1.0 = bad defense

            defense_stats[team_name] = {
                'opp_3pm_allowed': round(opp_3pm, 2),
                'opp_3pa_allowed': round(opp_3pa, 2),
                'opp_3pct_allowed': round(opp_3pct, 3),
                'defense_rating': round(defense_rating, 2)  # >1.0 = favorable matchup
            }

        # Cache results
        with open(TEAM_DEFENSE_CACHE, 'w') as f:
            json.dump(defense_stats, f, indent=2)

        print(f"{Colors.GREEN}✓ Fetched defense stats for {len(defense_stats)} teams{Colors.END}")
        return defense_stats

    except Exception as e:
        print(f"{Colors.YELLOW}⚠ Could not fetch defense stats: {e}{Colors.END}")
        # Try cache
        if os.path.exists(TEAM_DEFENSE_CACHE):
            with open(TEAM_DEFENSE_CACHE, 'r') as f:
                return json.load(f)
        return {}

def get_nba_team_rosters():
    """
    Build a mapping of player names to their teams
    This is a simplified version - in production would use official NBA roster API
    """
    # Key players for each team (last name matching)
    rosters = {
        'Boston Celtics': ['Tatum', 'Brown', 'White', 'Holiday', 'Porzingis', 'Horford', 'Hauser', 'Pritchard'],
        'Washington Wizards': ['Kuzma', 'Poole', 'Coulibaly', 'Bagley', 'Jones', 'Kispert', 'Sarr'],
        'Golden State Warriors': ['Curry', 'Wiggins', 'Green', 'Kuminga', 'Podziemski', 'Looney', 'Payton', 'Melton'],
        'Philadelphia 76ers': ['Embiid', 'Maxey', 'Harris', 'Oubre', 'Batum', 'McCain', 'Drummond', 'Reed', 'Martin'],
        'Brooklyn Nets': ['Johnson', 'Claxton', 'Thomas', 'Finney-Smith', 'Sharpe', 'Whitehead', 'Clowney', 'Schroder', 'Wilson'],
        'Utah Jazz': ['Markkanen', 'Sexton', 'Clarkson', 'Collins', 'Kessler', 'George', 'Hendricks', 'Williams'],
        'Los Angeles Lakers': ['James', 'Davis', 'Reaves', 'Russell', 'Hachimura', 'Reddish', 'Prince', 'Christie', 'Knecht'],
        'Toronto Raptors': ['Barnes', 'Quickley', 'Poeltl', 'Dick', 'Battle', 'Agbaji', 'Shead', 'Brown'],
        'Minnesota Timberwolves': ['Edwards', 'Gobert', 'McDaniels', 'Conley', 'Reid', 'Alexander-Walker', 'DiVincenzo', 'Randle'],
        'New Orleans Pelicans': ['Williamson', 'Ingram', 'McCollum', 'Murphy', 'Alvarado', 'Hawkins', 'Jones'],
        'Miami Heat': ['Butler', 'Adebayo', 'Herro', 'Rozier', 'Love', 'Highsmith', 'Robinson', 'Jovic', 'Ware'],
        'Orlando Magic': ['Banchero', 'Wagner', 'Carter', 'Isaac', 'Suggs', 'Anthony', 'Fultz', 'Caldwell-Pope'],
        'New York Knicks': ['Brunson', 'Towns', 'Bridges', 'Hart', 'Anunoby', 'McBride', 'Achiuwa'],
        'Phoenix Suns': ['Durant', 'Booker', 'Beal', 'Nurkic', 'Allen', 'Gordon', 'Okogie', 'O\'Neale'],
        'Oklahoma City Thunder': ['Gilgeous-Alexander', 'Williams', 'Holmgren', 'Wallace', 'Joe', 'Dort', 'Caruso', 'Hartenstein'],
        'San Antonio Spurs': ['Wembanyama', 'Vassell', 'Johnson', 'Sochan', 'Jones', 'Branham', 'Collins', 'Castle'],
        'Los Angeles Clippers': ['Leonard', 'Harden', 'Westbrook', 'Zubac', 'Mann', 'Powell', 'Coffey', 'Dunn'],
        'Denver Nuggets': ['Jokic', 'Murray', 'Porter', 'Gordon', 'Watson', 'Braun', 'Strawther', 'Westbrook'],
        'Dallas Mavericks': ['Doncic', 'Irving', 'Washington', 'Gafford', 'Lively', 'Grimes', 'Kleber', 'Exum'],
        'Sacramento Kings': ['Fox', 'Sabonis', 'Murray', 'DeRozan', 'Huerter', 'Monk', 'McDermott'],
        'Memphis Grizzlies': ['Morant', 'Bane', 'Jackson', 'Smart', 'Williams', 'Konchar', 'Edey', 'Wells'],
        'Cleveland Cavaliers': ['Mitchell', 'Garland', 'Mobley', 'Allen', 'LeVert', 'Strus', 'Okoro', 'Wade'],
        'Milwaukee Bucks': ['Antetokounmpo', 'Lillard', 'Middleton', 'Lopez', 'Portis', 'Connaughton', 'Trent'],
        'Indiana Pacers': ['Haliburton', 'Turner', 'Mathurin', 'Nembhard', 'Nesmith', 'Siakam', 'Brown'],
        'Atlanta Hawks': ['Young', 'Murray', 'Johnson', 'Hunter', 'Bogdanovic', 'Okongwu', 'Daniels', 'Risacher'],
        'Chicago Bulls': ['LaVine', 'Vucevic', 'Williams', 'Dosunmu', 'White', 'Giddey', 'Ball'],
        'Charlotte Hornets': ['Ball', 'Miller', 'Bridges', 'Williams', 'Richards', 'Martin', 'Knueppel', 'Green'],
        'Detroit Pistons': ['Cunningham', 'Ivey', 'Duren', 'Harris', 'Beasley', 'Stewart', 'Thompson', 'Holland', 'Robinson'],
        'Houston Rockets': ['Green', 'Smith', 'Sengun', 'VanVleet', 'Dillon', 'Thompson', 'Whitmore', 'Eason'],
        'Portland Trail Blazers': ['Simons', 'Grant', 'Sharpe', 'Ayton', 'Thybulle', 'Camara', 'Henderson', 'Clingan'],
    }
    return rosters

def match_player_to_team(player_name, home_team, away_team, rosters):
    """
    Match a player to their team based on name matching with rosters
    """
    # Extract last name from player name
    name_parts = player_name.split()
    last_name = name_parts[-1] if name_parts else player_name

    # Check home team roster
    if home_team in rosters:
        for roster_name in rosters[home_team]:
            if roster_name.lower() in player_name.lower():
                return home_team, away_team

    # Check away team roster
    if away_team in rosters:
        for roster_name in rosters[away_team]:
            if roster_name.lower() in player_name.lower():
                return away_team, home_team

    # Default to home team if no match found
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
        ev = abs(float(pick.get('ev', 0)))
        status = pick.get('status', '')
        
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
        if total >= 5:
            win_rate = stats['wins'] / total if total > 0 else 0.5
            performance_by_edge[range_key] = win_rate
    
    return performance_by_edge

def calculate_probability_edge(ai_score, season_avg, recent_avg, prop_line, odds, bet_type):
    """Calculate probability edge for props (model prob - market prob)"""
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
    
    edge_factor = min(abs(edge) / 2.0, 1.0)
    
    recent_factor = 0.0
    if bet_type == 'over' and recent_avg > season_avg:
        recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
    elif bet_type == 'under' and recent_avg < season_avg:
        recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)
    
    model_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15) + recent_factor
    model_prob = min(max(model_prob, 0.40), 0.70)
    
    prob_edge = abs(model_prob - implied_prob)
    return prob_edge

def calculate_ai_rating_props(play, historical_edge_performance):
    """Calculate A.I. Rating for props models (probability-based edges)"""
    prob_edge = play.get('probability_edge')
    
    if prob_edge is None:
        ev = abs(play.get('ev', 0))
        prob_edge = ev / 100.0
    
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

def calculate_tracking_summary(picks, displayed_plays=None):
    """Calculate summary - all plays for wins/losses/total, displayed for pending"""
    # Total, wins, losses from ALL tracked plays (preserve history)
    total = len(picks)
    wins = len([p for p in picks if p.get('status', '').lower() == 'win'])
    losses = len([p for p in picks if p.get('status', '').lower() == 'loss'])
    
    # Pending: only count displayed plays that are pending (match what's shown)
    if displayed_plays:
        displayed_ids = set()
        for play in displayed_plays:
            prop_line = float(play['prop'].split()[1])
            bet_type = 'over' if 'OVER' in play['prop'] else 'under'
            displayed_ids.add(f"{play['player']}_{prop_line}_{bet_type}")
        
        pending = len([p for p in picks 
                      if p.get('status', '').lower() == 'pending' 
                      and f"{p['player']}_{p['prop_line']}_{p['bet_type']}" in displayed_ids])
    else:
        pending = len([p for p in picks if p.get('status', '').lower() == 'pending'])

    completed = wins + losses
    win_rate = (wins / completed * 100) if completed > 0 else 0.0

    # Calculate ROI (assuming -110 odds for simplicity)
    roi = (wins * 0.91 - losses * 1.0)
    roi_pct = (roi / total * 100) if total > 0 else 0.0

    # Calculate CLV (Closing Line Value)
    clv_picks = [p for p in picks if p.get('opening_odds') and p.get('latest_odds')]
    positive_clv = len([p for p in clv_picks if p.get('latest_odds', 0) < p.get('opening_odds', 0)])  # Odds got worse = we got better value
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

def track_pick(player_name, prop_line, bet_type, team, opponent, ai_score, odds, game_time):
    """Add a pick to tracking file"""
    tracking_data = load_tracking()

    # Create unique ID for this pick
    pick_id = f"{player_name}_{prop_line}_{bet_type}_{game_time}"

    # Check if already tracked
    existing = next((p for p in tracking_data['picks'] if p['pick_id'] == pick_id), None)
    if existing:
        # Update odds if they changed (for CLV tracking)
        if odds != existing.get('odds'):
            existing['opening_odds'] = existing.get('opening_odds', existing.get('odds'))
            existing['latest_odds'] = odds
            existing['last_updated'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
            save_tracking(tracking_data)
        return False  # Already tracked

    pick = {
        'pick_id': pick_id,
        'player': player_name,
        'prop_line': prop_line,
        'bet_type': bet_type,
        'team': team,
        'opponent': opponent,
        'ai_score': ai_score,
        'odds': odds,
        'opening_odds': odds,  # Track opening odds for CLV
        'latest_odds': odds,
        'game_time': game_time,
        'tracked_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
        'status': 'pending',
        'result': None,
        'actual_3pm': None
    }

    tracking_data['picks'].append(pick)
    # Don't recalculate summary here - it will be recalculated in main() based on displayed plays
    save_tracking(tracking_data)

    return True

def fetch_player_3pt_from_nba_api(player_name, team_name, game_date_str):
    """
    Fetch actual player 3-pointers made from NBA API for a specific game
    Returns the actual 3pt made count or None if not found
    """
    try:
        # Find player ID
        player_list = players.get_players()
        player_info = None
        
        # Match player name (handle variations)
        name_parts = player_name.lower().split()
        for p in player_list:
            p_name = p['full_name'].lower()
            p_parts = p_name.split()
            if len(name_parts) >= 2 and len(p_parts) >= 2:
                if name_parts[0] in p_parts[0] and name_parts[-1] in p_parts[-1]:
                    player_info = p
                    break
        
        if not player_info:
            print(f"{Colors.YELLOW}    Could not find player {player_name} in NBA API{Colors.END}")
            return None
        
        player_id = player_info['id']
        
        # Get player game log
        game_log = playergamelog.PlayerGameLog(player_id=player_id, season=CURRENT_SEASON, timeout=30)
        df = game_log.get_data_frames()[0]
        
        if df.empty:
            return None
        
        # Find the game by date
        target_date = datetime.strptime(game_date_str, '%Y-%m-%d').date()
        
        for _, row in df.iterrows():
            game_date_str_nba = row.get('GAME_DATE', '')
            if not game_date_str_nba:
                continue
            
            # Parse NBA date format
            try:
                game_date = datetime.strptime(game_date_str_nba, '%b %d, %Y').date()
            except:
                try:
                    game_date = datetime.strptime(game_date_str_nba, '%Y-%m-%d').date()
                except:
                    continue
            
            if game_date == target_date:
                fg3m = row.get('FG3M', 0)  # 3-pointers made
                return int(fg3m) if fg3m else 0
        
        return None
        
    except Exception as e:
        print(f"{Colors.YELLOW}  Error fetching 3pt stats from NBA API for {player_name}: {str(e)}{Colors.END}")
        return None

def update_pick_results():
    """Check pending picks and update their status using NBA API"""
    tracking_data = load_tracking()
    pending_picks = [p for p in tracking_data['picks'] if p.get('status') == 'pending']

    if not pending_picks:
        return 0

    print(f"\n{Colors.CYAN}Checking {len(pending_picks)} pending picks...{Colors.END}")
    updated = 0
    et = pytz.timezone('US/Eastern')
    current_time = datetime.now(et)

    for pick in pending_picks:
        try:
            game_dt = datetime.fromisoformat(pick['game_time'].replace('Z', '+00:00'))
            game_dt_et = game_dt.astimezone(et)
            hours_ago = (current_time - game_dt_et).total_seconds() / 3600

            # Only check games that finished at least 4 hours ago
            if hours_ago > 4:
                game_date_str = game_dt_et.strftime('%Y-%m-%d')
                player_name = pick['player']
                team_name = pick['team']
                
                print(f"{Colors.CYAN}  Checking {player_name} ({team_name}) from {game_date_str}...{Colors.END}")
                
                # Fetch actual 3pt made
                actual_3pt = fetch_player_3pt_from_nba_api(player_name, team_name, game_date_str)
                
                if actual_3pt is None:
                    print(f"{Colors.YELLOW}    Could not fetch stats, skipping...{Colors.END}")
                    continue
                
                # Determine win/loss
                prop_line = pick['prop_line']
                bet_type = pick['bet_type'].lower()
                
                if bet_type == 'over':
                    is_win = actual_3pt > prop_line
                else:  # under
                    is_win = actual_3pt < prop_line
                
                # Update pick
                pick['status'] = 'win' if is_win else 'loss'
                pick['result'] = 'WIN' if is_win else 'LOSS'
                pick['actual_3pt'] = actual_3pt
                pick['updated_at'] = current_time.isoformat()
                
                result_str = f"{Colors.GREEN}WIN{Colors.END}" if is_win else f"{Colors.RED}LOSS{Colors.END}"
                print(f"    {result_str}: {player_name} made {actual_3pt} 3-pointers (line: {prop_line}, bet: {bet_type.upper()})")
                updated += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)

        except Exception as e:
            print(f"{Colors.RED}    Error processing pick: {e}{Colors.END}")
            continue

    if updated > 0:
        # Save updated picks - summary will be recalculated in main() based on displayed plays
        save_tracking(tracking_data)
        print(f"\n{Colors.GREEN}✓ Updated {updated} picks{Colors.END}")

    return updated

def reverify_completed_picks():
    """Re-verify all completed picks to ensure accuracy"""
    tracking_data = load_tracking()
    completed_picks = [p for p in tracking_data['picks'] 
                      if p.get('status') in ['win', 'loss'] and p.get('actual_3pt') is None]
    
    if not completed_picks:
        print(f"{Colors.GREEN}✓ All completed picks already have actual stats{Colors.END}")
        return 0
    
    print(f"\n{Colors.CYAN}Re-verifying {len(completed_picks)} completed picks...{Colors.END}")
    updated = 0
    et = pytz.timezone('US/Eastern')
    
    for pick in completed_picks:
        try:
            game_dt = datetime.fromisoformat(pick['game_time'].replace('Z', '+00:00'))
            game_dt_et = game_dt.astimezone(et)
            game_date_str = game_dt_et.strftime('%Y-%m-%d')
            
            player_name = pick['player']
            team_name = pick['team']
            
            print(f"{Colors.CYAN}  Verifying {player_name} ({team_name}) from {game_date_str}...{Colors.END}")
            
            # Fetch actual 3pt made
            actual_3pt = fetch_player_3pt_from_nba_api(player_name, team_name, game_date_str)
            
            if actual_3pt is None:
                print(f"{Colors.YELLOW}    Could not fetch stats, skipping...{Colors.END}")
                continue
            
            # Determine correct win/loss
            prop_line = pick['prop_line']
            bet_type = pick['bet_type'].lower()
            
            if bet_type == 'over':
                correct_result = 'win' if actual_3pt > prop_line else 'loss'
            else:  # under
                correct_result = 'win' if actual_3pt < prop_line else 'loss'
            
            current_status = pick.get('status', '').lower()
            
            # Update if incorrect
            if correct_result != current_status:
                old_status = pick['status']
                pick['status'] = correct_result
                pick['result'] = 'WIN' if correct_result == 'win' else 'LOSS'
                pick['actual_3pt'] = actual_3pt
                
                print(f"    {Colors.RED}FIXED: Was {old_status.upper()}, now {correct_result.upper()}{Colors.END}")
                print(f"    {player_name} made {actual_3pt} 3-pointers (line: {prop_line}, bet: {bet_type.upper()})")
                updated += 1
            else:
                pick['actual_3pt'] = actual_3pt
                print(f"    {Colors.GREEN}Verified: {correct_result.upper()} - {actual_3pt} 3-pointers{Colors.END}")
                updated += 1
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"{Colors.RED}    Error verifying pick: {e}{Colors.END}")
            continue
    
    if updated > 0:
        # Save updated picks - summary will be recalculated in main() based on displayed plays
        save_tracking(tracking_data)
        print(f"\n{Colors.GREEN}✓ Re-verified {updated} picks{Colors.END}")
    
    return updated

def get_player_props():
    """
    Fetch player prop odds from The Odds API
    Returns list of all player props across all upcoming games
    """
    print(f"\n{Colors.CYAN}Fetching player prop odds...{Colors.END}")

    # Load team rosters for player matching
    rosters = get_nba_team_rosters()

    # Step 1: Get all upcoming events
    events_url = "https://api.the-odds-api.com/v4/sports/basketball_nba/events"
    events_params = {'apiKey': API_KEY}

    try:
        events_response = requests.get(events_url, params=events_params, timeout=10)

        if events_response.status_code != 200:
            print(f"{Colors.RED}✗ API Error: {events_response.status_code}{Colors.END}")
            return []

        events = events_response.json()
        print(f"{Colors.CYAN}  Found {len(events)} upcoming games{Colors.END}")

        # Step 2: Get player props for each event
        all_props = []

        for i, event in enumerate(events[:10], 1):  # Limit to first 10 games to save API calls
            event_id = event['id']
            home_team = event['home_team']
            away_team = event['away_team']

            # Get odds for this event
            odds_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
            odds_params = {
                'apiKey': API_KEY,
                'regions': 'us',
                'markets': 'player_threes',
                'oddsFormat': 'american'
            }

            odds_response = requests.get(odds_url, params=odds_params, timeout=15)

            if odds_response.status_code == 200:
                odds_data = odds_response.json()

                # Extract player props from bookmakers
                if 'bookmakers' in odds_data and odds_data['bookmakers']:
                    # Use FanDuel as primary bookmaker
                    fanduel = next((b for b in odds_data['bookmakers'] if b['key'] == 'fanduel'),
                                  odds_data['bookmakers'][0])

                    if 'markets' in fanduel:
                        for market in fanduel['markets']:
                            if market['key'] == 'player_threes':
                                for outcome in market['outcomes']:
                                    player_name = outcome['description']

                                    # Match player to correct team using roster
                                    player_team, player_opponent = match_player_to_team(
                                        player_name, home_team, away_team, rosters
                                    )

                                    prop = {
                                        'player': player_name,
                                        'prop_line': outcome['point'],
                                        'over_price': outcome.get('price', -110),
                                        'team': player_team,
                                        'opponent': player_opponent,
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'game_time': event['commence_time']
                                    }
                                    all_props.append(prop)

                print(f"{Colors.CYAN}  Game {i}/{len(events[:10])}: {away_team} @ {home_team} - "
                      f"{len([p for p in all_props if p['team'] == home_team or p['opponent'] == home_team])} props{Colors.END}")

        print(f"{Colors.GREEN}✓ Fetched {len(all_props)} total player props{Colors.END}")
        remaining = events_response.headers.get('x-requests-remaining', 'unknown')
        print(f"{Colors.YELLOW}  API requests remaining: {remaining}{Colors.END}")

        return all_props

    except Exception as e:
        print(f"{Colors.RED}✗ Error fetching props: {e}{Colors.END}")
        return []

def calculate_ai_score(player_data, prop_line, bet_type, opponent_defense=None):
    """
    Calculate STRICT A.I. Score (0-10) for a player prop using REAL stats
    
    Much stricter criteria for profitability:
    - Requires significant edge above/below line
    - Recent form must strongly support
    - Consistency and matchup factors heavily weighted
    - Only high-confidence plays score 9.5+
    """

    score = 4.0  # Start lower - require strong edge to reach high scores

    season_avg = player_data.get('season_3pm_avg', 0)
    recent_avg = player_data.get('recent_3pm_avg', 0)
    season_3pa = player_data.get('season_3pa_avg', 0)
    season_3pct = player_data.get('season_3pct', 0)
    consistency = player_data.get('consistency_score', 0.3)
    games_played = player_data.get('games_played', 0)

    # REQUIREMENT: Must have played enough games (minimum 5 games)
    if games_played < 5:
        return 0.0  # Not enough data

    # REQUIREMENT: Must have meaningful 3PT volume (at least 2 attempts/game)
    if season_3pa < 2.0:
        return 0.0  # Not a 3PT shooter

    if bet_type == 'over':
        # STRICT OVER REQUIREMENTS
        
        # Factor 1: Season average MUST be significantly above line (40% weight)
        edge_above_line = season_avg - prop_line
        if edge_above_line >= MIN_EDGE_OVER_LINE:  # 1.2+ above line
            score += 3.5  # Strong edge
        elif edge_above_line >= 0.8:
            score += 2.0  # Good edge
        elif edge_above_line >= 0.5:
            score += 1.0  # Moderate edge
        elif edge_above_line >= 0.2:
            score += 0.3  # Small edge
        else:
            score -= 2.0  # Below line - major penalty
            # If below line, require recent form to be MUCH better
            if recent_avg < prop_line + 0.5:
                return 0.0  # Reject if both season and recent below line

        # Factor 2: Recent form MUST support (35% weight) - STRICT
        recent_edge = recent_avg - prop_line
        if recent_edge >= MIN_RECENT_FORM_EDGE:  # 0.8+ above line
            score += 2.5  # Recent form strongly supports
        elif recent_edge >= 0.5:
            score += 1.5  # Recent form supports
        elif recent_avg > season_avg + 0.3:  # Hot streak
            score += 1.0  # Trending up
        elif recent_avg >= prop_line:
            score += 0.5  # Just above line
        else:
            score -= 1.5  # Recent form doesn't support - penalty

        # Factor 3: Volume and consistency (15% weight)
        # Higher volume + good % = more reliable
        if season_3pa >= 7.0 and season_3pct >= 0.38:  # High volume, good %
            score += 1.5
        elif season_3pa >= 5.0 and season_3pct >= 0.35:
            score += 1.0
        elif season_3pa >= 3.0:
            score += 0.5
        else:
            score -= 0.5  # Low volume penalty

        # Consistency bonus
        score += consistency * 0.8

        # Factor 4: Matchup (opponent defense) - 10% weight
        if opponent_defense and opponent_defense.get('defense_rating', 1.0) > 1.05:
            score += 1.0  # Opponent allows more 3PM (favorable)
        elif opponent_defense and opponent_defense.get('defense_rating', 1.0) < 0.95:
            score -= 0.5  # Opponent good at defending 3PT

    else:  # under
        # STRICT UNDER REQUIREMENTS
        
        # Factor 1: Season average MUST be significantly below line
        edge_below_line = prop_line - season_avg
        if edge_below_line >= MIN_EDGE_UNDER_LINE:  # 1.0+ below line
            score += 3.5  # Strong edge
        elif edge_below_line >= 0.7:
            score += 2.0  # Good edge
        elif edge_below_line >= 0.4:
            score += 1.0  # Moderate edge
        elif edge_below_line >= 0.2:
            score += 0.3  # Small edge
        else:
            score -= 2.0  # Above line - major penalty
            # If above line, require recent form to be MUCH worse
            if recent_avg > prop_line - 0.5:
                return 0.0  # Reject if both season and recent above line

        # Factor 2: Recent form MUST support UNDER
        recent_edge = prop_line - recent_avg
        if recent_edge >= MIN_RECENT_FORM_EDGE:  # 0.8+ below line
            score += 2.5  # Recent form strongly supports
        elif recent_edge >= 0.5:
            score += 1.5  # Recent form supports
        elif recent_avg < season_avg - 0.3:  # Cold streak
            score += 1.0  # Trending down
        elif recent_avg <= prop_line:
            score += 0.5  # Just below line
        else:
            score -= 1.5  # Recent form doesn't support - penalty

        # Factor 3: Low volume or poor % helps UNDER
        if season_3pa < 3.0:  # Low volume shooter
            score += 1.0
        elif season_3pct < 0.30:  # Poor shooter
            score += 0.8
        else:
            score -= 0.3  # Good shooter - harder to go under

        # Consistency (lower consistency = more variance = better for under)
        score += (1.0 - consistency) * 0.5

        # Factor 4: Matchup (good defense = better for under)
        if opponent_defense and opponent_defense.get('defense_rating', 1.0) < 0.95:
            score += 1.0  # Opponent good at defending 3PT (favorable for under)
        elif opponent_defense and opponent_defense.get('defense_rating', 1.0) > 1.05:
            score -= 0.5  # Opponent allows more 3PM (unfavorable for under)

    # Cap score at 10.0
    final_score = min(10.0, max(0.0, score))
    
    # ADDITIONAL STRICT FILTER: Even if score is high, require minimum edge
    if bet_type == 'over' and season_avg < prop_line + 0.3:
        final_score = min(final_score, 8.5)  # Cap at 8.5 if edge too small
    elif bet_type == 'under' and season_avg > prop_line - 0.3:
        final_score = min(final_score, 8.5)  # Cap at 8.5 if edge too small

    return round(final_score, 2)

def calculate_ev(ai_score, prop_line, season_avg, recent_avg, odds, bet_type):
    """
    Calculate Expected Value based on AI score and player stats
    Higher AI score + larger edge = higher EV
    Target: 60% hit rate for AI score 9.5+
    """
    # Convert American odds to implied probability
    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)
    
    # Calculate true probability from AI score and stats
    # AI score 9.5+ = ~60% win probability (user's target)
    # Scale based on edge above/below line
    base_prob = 0.50  # Starting point
    ai_multiplier = max(0, (ai_score - 9.0) / 1.0)  # Scale from 9.0-10.0 to 0-1.0
    
    # Edge factor: larger edge = higher true probability
    if bet_type == 'over':
        edge = season_avg - prop_line
    else:  # under
        edge = prop_line - season_avg
    
    edge_factor = min(abs(edge) / 2.0, 1.0)  # Normalize edge contribution
    
    # Recent form bonus
    recent_factor = 0.0
    if bet_type == 'over' and recent_avg > season_avg:
        recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
    elif bet_type == 'under' and recent_avg < season_avg:
        recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)
    
    true_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15) + recent_factor
    true_prob = min(max(true_prob, 0.40), 0.70)  # Cap between 40-70%
    
    # Calculate EV
    if odds > 0:
        ev = (true_prob * (odds / 100)) - (1 - true_prob)
    else:
        ev = (true_prob * (100 / abs(odds))) - (1 - true_prob)
    
    return ev * 100  # Return as percentage

def analyze_props(props_list, player_stats, defense_stats, historical_edge_performance=None):
    """
    Analyze all player props using REAL NBA stats
    Much stricter filtering for profitability
    """
    print(f"\n{Colors.CYAN}Analyzing {len(props_list)} player props with REAL stats...{Colors.END}")

    over_plays = []
    under_plays = []
    skipped_no_stats = 0
    skipped_low_score = 0

    # Process each prop from live data
    for prop in props_list:
        player_name = prop['player']
        prop_line = prop['prop_line']
        opponent_team = prop['opponent']

        # Get REAL player stats
        player_data = player_stats.get(player_name)
        if not player_data:
            # Try fuzzy matching (last name only)
            for name, stats in player_stats.items():
                if player_name.split()[-1].lower() in name.lower() or name.split()[-1].lower() in player_name.lower():
                    player_data = stats
                    break
            
            if not player_data:
                skipped_no_stats += 1
                continue  # Skip if no stats found

        # Get opponent defense stats
        opponent_defense = None
        if opponent_team in defense_stats:
            opponent_defense = defense_stats[opponent_team]
        else:
            # Try to find team by partial match
            for team_name, defense in defense_stats.items():
                if opponent_team.lower() in team_name.lower() or team_name.lower() in opponent_team.lower():
                    opponent_defense = defense
                    break

        # Calculate over score with REAL stats
        over_score = calculate_ai_score(player_data, prop_line, 'over', opponent_defense)
        if over_score >= MIN_AI_SCORE:
            # Additional validation: ensure edge is real
            season_avg = player_data.get('season_3pm_avg', 0)
            recent_avg = player_data.get('recent_3pm_avg', 0)
            
            # Require both season and recent to support
            if season_avg >= prop_line + 0.2 and recent_avg >= prop_line + 0.1:
                # Calculate EV
                ev = calculate_ev(over_score, prop_line, season_avg, recent_avg, prop['over_price'], 'over')
                is_sharp = over_score >= AUTO_TRACK_THRESHOLD and ev > 0
                
                prob_edge = calculate_probability_edge(over_score, season_avg, recent_avg, prop_line, prop['over_price'], 'over')
                
                play_dict = {
                    'player': player_name,
                    'prop': f"OVER {prop_line} 3PT",
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
                    play_dict['ai_rating'] = calculate_ai_rating_props(play_dict, historical_edge_performance)
                
                over_plays.append(play_dict)
            else:
                skipped_low_score += 1
        else:
            skipped_low_score += 1

        # Calculate under score with REAL stats
        under_score = calculate_ai_score(player_data, prop_line, 'under', opponent_defense)
        if under_score >= MIN_AI_SCORE:
            # Additional validation: ensure edge is real
            season_avg = player_data.get('season_3pm_avg', 0)
            recent_avg = player_data.get('recent_3pm_avg', 0)
            
            # Require both season and recent to support
            if season_avg <= prop_line - 0.2 and recent_avg <= prop_line - 0.1:
                # Calculate EV
                ev = calculate_ev(under_score, prop_line, season_avg, recent_avg, prop['over_price'], 'under')
                is_sharp = under_score >= AUTO_TRACK_THRESHOLD and ev > 0
                
                prob_edge = calculate_probability_edge(under_score, season_avg, recent_avg, prop_line, prop['over_price'], 'under')
                
                play_dict = {
                    'player': player_name,
                    'prop': f"UNDER {prop_line} 3PT",
                    'team': prop['team'],
                    'opponent': opponent_team,
                    'ai_score': under_score,
                    'odds': prop['over_price'],  # Under odds would need separate fetch
                    'game_time': prop['game_time'],
                    'season_avg': season_avg,
                    'recent_avg': recent_avg,
                    'edge': round(prop_line - season_avg, 2),
                    'ev': round(ev, 2),
                    'probability_edge': prob_edge,
                    'is_sharp': is_sharp
                }
                
                if historical_edge_performance:
                    play_dict['ai_rating'] = calculate_ai_rating_props(play_dict, historical_edge_performance)
                
                under_plays.append(play_dict)
            else:
                skipped_low_score += 1
        else:
            skipped_low_score += 1

    # Remove duplicates (same player + prop line)
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

    # Sort by A.I. score (highest first)
    # Sort by A.I. Rating (primary), AI Score (secondary)
    def get_sort_score(play):
        rating = play.get('ai_rating', 2.3)
        ai_score = play.get('ai_score', 0)
        return (rating, ai_score)
    
    unique_over.sort(key=get_sort_score, reverse=True)
    unique_under.sort(key=get_sort_score, reverse=True)

    # Limit to top plays (quality over quantity)
    over_plays = unique_over[:TOP_PLAYS_COUNT]
    under_plays = unique_under[:TOP_PLAYS_COUNT]

    print(f"{Colors.GREEN}✓ Found {len(over_plays)} top OVER plays (A.I. Score >= {MIN_AI_SCORE}){Colors.END}")
    print(f"{Colors.GREEN}✓ Found {len(under_plays)} top UNDER plays (A.I. Score >= {MIN_AI_SCORE}){Colors.END}")
    if skipped_no_stats > 0:
        print(f"{Colors.YELLOW}  Skipped {skipped_no_stats} props (no player stats found){Colors.END}")
    if skipped_low_score > 0:
        print(f"{Colors.YELLOW}  Skipped {skipped_low_score} props (score below {MIN_AI_SCORE}){Colors.END}")

    return over_plays, under_plays

def generate_html_output(over_plays, under_plays, tracking_summary=None, tracking_data=None):
    """
    Generate HTML output matching NBA model card-based style
    """
    from datetime import datetime as dt
    et = pytz.timezone('US/Eastern')
    now = dt.now(et)
    date_str = now.strftime('%m/%d/%y')
    time_str = now.strftime('%I:%M %p ET')
    
    # Helper function to format game time
    def format_game_time(game_time_str):
        """Format game time from ISO format to readable date/time"""
        try:
            if not game_time_str:
                return 'TBD'
            dt_obj = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
            et_tz = pytz.timezone('US/Eastern')
            dt_et = dt_obj.astimezone(et_tz)
            return dt_et.strftime('%m/%d %I:%M %p ET')
        except:
            return game_time_str if game_time_str else 'TBD'
    

    # Helper function to get shortened team name
    def get_short_team_name(team_name):
        """Get shortened team name (city or nickname) for display"""
        short_name_map = {
            "Atlanta Hawks": "Hawks", "Boston Celtics": "Celtics", "Brooklyn Nets": "Nets",
            "Charlotte Hornets": "Hornets", "Chicago Bulls": "Bulls", "Cleveland Cavaliers": "Cavaliers",
            "Dallas Mavericks": "Mavericks", "Denver Nuggets": "Nuggets", "Detroit Pistons": "Pistons",
            "Golden State Warriors": "Warriors", "Houston Rockets": "Rockets", "Indiana Pacers": "Pacers",
            "LA Clippers": "Clippers", "Los Angeles Clippers": "Clippers", "Los Angeles Lakers": "Lakers",
            "LA Lakers": "Lakers", "Memphis Grizzlies": "Grizzlies", "Miami Heat": "Heat",
            "Milwaukee Bucks": "Bucks", "Minnesota Timberwolves": "Timberwolves", "New Orleans Pelicans": "Pelicans",
            "New York Knicks": "Knicks", "Oklahoma City Thunder": "Thunder", "Orlando Magic": "Magic",
            "Philadelphia 76ers": "76ers", "Phoenix Suns": "Suns", "Portland Trail Blazers": "Trail Blazers",
            "Sacramento Kings": "Kings", "San Antonio Spurs": "Spurs", "Toronto Raptors": "Raptors",
            "Utah Jazz": "Jazz", "Washington Wizards": "Wizards"
        }
        return short_name_map.get(team_name, team_name)

    # Helper function to get team logo URL
    def get_team_logo_url(team_name):
        """Map team names to NBA.com logo URLs using team IDs"""
        team_id_map = {
            "Atlanta Hawks": "1610612737", "Boston Celtics": "1610612738", "Brooklyn Nets": "1610612751",
            "Charlotte Hornets": "1610612766", "Chicago Bulls": "1610612741", "Cleveland Cavaliers": "1610612739",
            "Dallas Mavericks": "1610612742", "Denver Nuggets": "1610612743", "Detroit Pistons": "1610612765",
            "Golden State Warriors": "1610612744", "Houston Rockets": "1610612745", "Indiana Pacers": "1610612754",
            "LA Clippers": "1610612746", "Los Angeles Clippers": "1610612746", "Los Angeles Lakers": "1610612747",
            "LA Lakers": "1610612747", "Memphis Grizzlies": "1610612763", "Miami Heat": "1610612748",
            "Milwaukee Bucks": "1610612749", "Minnesota Timberwolves": "1610612750", "New Orleans Pelicans": "1610612740",
            "New York Knicks": "1610612752", "Oklahoma City Thunder": "1610612760", "Orlando Magic": "1610612753",
            "Philadelphia 76ers": "1610612755", "Phoenix Suns": "1610612756", "Portland Trail Blazers": "1610612757",
            "Sacramento Kings": "1610612758", "San Antonio Spurs": "1610612759", "Toronto Raptors": "1610612761",
            "Utah Jazz": "1610612762", "Washington Wizards": "1610612764"
        }
        team_id = team_id_map.get(team_name, "")
        if team_id:
            return f"https://cdn.nba.com/logos/nba/{team_id}/primary/L/logo.svg"
        return ""

        # Helper function to get CLV for a play
    def get_play_clv(play):
        if not tracking_data or not tracking_data.get('picks'):
            return None
        prop_line = float(play['prop'].split()[1])
        bet_type = 'over' if 'OVER' in play['prop'] else 'under'
        # Try to find matching tracked pick
        for pick in tracking_data['picks']:
            if (pick['player'] == play['player'] and 
                pick['prop_line'] == prop_line and 
                pick['bet_type'] == bet_type):
                opening = pick.get('opening_odds')
                latest = pick.get('latest_odds')
                if opening and latest and opening != latest:
                    # Positive CLV calculation for American odds:
                    # For positive odds (+): latest < opening = odds got worse = better value = positive CLV
                    # For negative odds (-): latest < opening = odds got worse = better value = positive CLV
                    # So: latest < opening always means positive CLV (we got better value)
                    is_positive = latest < opening
                    return {
                        'opening': opening,
                        'latest': latest,
                        'positive': is_positive,
                        'change': latest - opening
                    }
        return None

    # Format tracking summary (will be placed at bottom)
    tracking_section = ""
    if tracking_summary and tracking_summary['total'] > 0:
        completed = tracking_summary['wins'] + tracking_summary['losses']
        # Show tracking even if no completed picks yet
        if True:
            win_rate_color = '#4ade80' if tracking_summary['win_rate'] >= 55 else ('#fbbf24' if tracking_summary['win_rate'] >= 52 else '#f87171')
            roi_color = '#4ade80' if tracking_summary['roi'] >= 0 else '#f87171'
            clv_color = '#4ade80' if tracking_summary.get('clv_rate', 0) >= 50 else '#f87171'
            tracking_section = f"""
            <div class="card">
                <h2 style="font-size: 1.75rem; font-weight: 700; margin-bottom: 1.5rem; text-align: center;">📊 NBA 3PT Model Tracking</h2>
                
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

    # Generate OVER plays cards
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
            
            # A.I. Rating display
            ai_rating = play.get('ai_rating', 2.3)
            if ai_rating >= 4.5:
                rating_class = 'ai-rating-premium'
                rating_label = 'PREMIUM PLAY'
                rating_stars = '⭐⭐⭐'
            elif ai_rating >= 4.0:
                rating_class = 'ai-rating-strong'
                rating_label = 'STRONG PLAY'
                rating_stars = '⭐⭐'
            elif ai_rating >= 3.5:
                rating_class = 'ai-rating-good'
                rating_label = 'GOOD PLAY'
                rating_stars = '⭐'
            elif ai_rating >= 3.0:
                rating_class = 'ai-rating-standard'
                rating_label = 'STANDARD PLAY'
                rating_stars = ''
            else:
                rating_class = 'ai-rating-marginal'
                rating_label = 'MARGINAL PLAY'
                rating_stars = ''
            rating_display = f'<div class="ai-rating {rating_class}"><span class="rating-value">{ai_rating:.1f}</span> {rating_stars}</div>'
            
            # Create +EV and SHARP badges
            ev_badge = ""
            ev = play.get('ev', 0)
            is_sharp = play.get('is_sharp', False)
            if ev > 0:
                ev_badge = f'<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(74, 222, 128, 0.2); color: #4ade80; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">+{ev:.1f}% EV</span>'
                if is_sharp:
                    ev_badge += '<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(96, 165, 250, 0.2); color: #60a5fa; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">SHARP</span>'
            
            # Get CLV for this play
            clv_info = get_play_clv(play)
            clv_display = ""
            if clv_info:
                clv_color = '#4ade80' if clv_info['positive'] else '#f87171'
                clv_icon = '✅' if clv_info['positive'] else '⚠️'
                opening_str = f"{clv_info['opening']:+.0f}" if clv_info['opening'] > 0 else f"{clv_info['opening']}"
                latest_str = f"{clv_info['latest']:+.0f}" if clv_info['latest'] > 0 else f"{clv_info['latest']}"
                clv_display = f"""
                        <div class="odds-line clv-line">
                            <span style="color: {clv_color}; font-weight: 600;">{clv_icon} CLV:</span>
                            <strong style="color: {clv_color};">Opening: {opening_str} → Latest: {latest_str}</strong>
                        </div>"""
            
            # Get team logo and short names
            team_logo_url = get_team_logo_url(play['team'])
            logo_html = f'<img src="{team_logo_url}" alt="{play["team"]}" class="team-logo">' if team_logo_url else ''
            short_team = get_short_team_name(play['team'])
            short_opponent = get_short_team_name(play['opponent'])
            home_team = play.get('home_team', '')
            away_team = play.get('away_team', '')
            
            # Format matchup: away @ home
            if play['team'] == home_team:
                matchup_display = f"{short_opponent} @ {short_team}"
            else:
                matchup_display = f"{short_team} @ {short_opponent}"
            
            over_html += f"""
                    <div class="bet-box">
                        <div class="prop-title" style="color: #10b981;">{play['prop']}</div>
                        <div class="odds-line" style="text-align: left;">
                            <strong style="display: flex; align-items: center; gap: 0.5rem; justify-content: flex-start;">{play['player']}{logo_html}</strong>
                        </div>
                        <div class="odds-line" style="text-align: left;">
                            <strong>{matchup_display}</strong>
                        </div>
                        <div class="odds-line" style="text-align: left;">
                            <strong>{game_time_formatted}</strong>
                        </div>
                        {rating_display}
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

    # Generate UNDER plays cards
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
            
            # A.I. Rating display
            ai_rating = play.get('ai_rating', 2.3)
            if ai_rating >= 4.5:
                rating_class = 'ai-rating-premium'
                rating_label = 'PREMIUM PLAY'
                rating_stars = '⭐⭐⭐'
            elif ai_rating >= 4.0:
                rating_class = 'ai-rating-strong'
                rating_label = 'STRONG PLAY'
                rating_stars = '⭐⭐'
            elif ai_rating >= 3.5:
                rating_class = 'ai-rating-good'
                rating_label = 'GOOD PLAY'
                rating_stars = '⭐'
            elif ai_rating >= 3.0:
                rating_class = 'ai-rating-standard'
                rating_label = 'STANDARD PLAY'
                rating_stars = ''
            else:
                rating_class = 'ai-rating-marginal'
                rating_label = 'MARGINAL PLAY'
                rating_stars = ''
            rating_display = f'<div class="ai-rating {rating_class}"><span class="rating-value">{ai_rating:.1f}</span> {rating_stars}</div>'
            
            # Create +EV and SHARP badges
            ev_badge = ""
            ev = play.get('ev', 0)
            is_sharp = play.get('is_sharp', False)
            if ev > 0:
                ev_badge = f'<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(74, 222, 128, 0.2); color: #4ade80; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">+{ev:.1f}% EV</span>'
                if is_sharp:
                    ev_badge += '<span style="display: inline-block; padding: 0.25rem 0.5rem; background: rgba(96, 165, 250, 0.2); color: #60a5fa; border-radius: 0.5rem; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem;">SHARP</span>'
            
            # Get CLV for this play
            clv_info = get_play_clv(play)
            clv_display = ""
            if clv_info:
                clv_color = '#4ade80' if clv_info['positive'] else '#f87171'
                clv_icon = '✅' if clv_info['positive'] else '⚠️'
                opening_str = f"{clv_info['opening']:+.0f}" if clv_info['opening'] > 0 else f"{clv_info['opening']}"
                latest_str = f"{clv_info['latest']:+.0f}" if clv_info['latest'] > 0 else f"{clv_info['latest']}"
                clv_display = f"""
                        <div class="odds-line clv-line">
                            <span style="color: {clv_color}; font-weight: 600;">{clv_icon} CLV:</span>
                            <strong style="color: {clv_color};">Opening: {opening_str} → Latest: {latest_str}</strong>
                        </div>"""
            
            # Get team logo and short names for UNDER plays
            team_logo_url = get_team_logo_url(play['team'])
            logo_html = f'<img src="{team_logo_url}" alt="{play["team"]}" class="team-logo">' if team_logo_url else ''
            short_team = get_short_team_name(play['team'])
            short_opponent = get_short_team_name(play['opponent'])
            home_team = play.get('home_team', '')
            away_team = play.get('away_team', '')
            
            # Format matchup: away @ home
            if play['team'] == home_team:
                matchup_display = f"{short_opponent} @ {short_team}"
            else:
                matchup_display = f"{short_team} @ {short_opponent}"
            
            under_html += f"""
                    <div class="bet-box">
                        <div class="prop-title" style="color: #ef4444;">{play['prop']}</div>
                        <div class="odds-line" style="text-align: left;">
                            <strong style="display: flex; align-items: center; gap: 0.5rem; justify-content: flex-start;">{play['player']}{logo_html}</strong>
                        </div>
                        <div class="odds-line" style="text-align: left;">
                            <strong>{matchup_display}</strong>
                        </div>
                        <div class="odds-line" style="text-align: left;">
                            <strong>{game_time_formatted}</strong>
                        </div>
                        {rating_display}
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

    footer_text = f"Powered by REAL NBA Stats API • Only showing picks with A.I. Score ≥ {MIN_AI_SCORE}<br>Using strict edge requirements: {MIN_EDGE_OVER_LINE}+ above line (OVER) / {MIN_EDGE_UNDER_LINE}+ below line (UNDER)<br>📊 = Auto-tracked (A.I. Score >= {AUTO_TRACK_THRESHOLD})"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA 3PT Props - A.I. Projections</title>
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
        }}
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
            justify-content: flex-start;
            align-items: center;
            margin: 0.5rem 0;
            font-size: 0.9375rem;
            color: #94a3b8;
        }}
        .prop-title {{
            font-weight: 700;
            margin-bottom: 1rem;
            font-size: 1.25rem;
            letter-spacing: 0.02em;
        }}
        .odds-line.clv-line {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .confidence-bar-container {{
            margin: 1rem 0;
        }}
        .confidence-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.625rem;
            font-size: 0.875rem;
            color: #94a3b8;
        }}
        .confidence-pct {{
            font-weight: 700;
            color: #10b981;
        }}
        .confidence-bar {{
            height: 8px;
            background: #1a1a1a;
            border-radius: 999px;
            overflow: hidden;
            border: none;
        }}
        .confidence-fill {{
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            border-radius: 999px;
            transition: width 0.3s ease;
        }}
        .team-logo {{
            width: 24px;
            height: 24px;
            object-fit: contain;
            opacity: 0.95;
            filter: brightness(1.1);
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
            background: #1a2332;
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
            <h1 style="font-size: 3rem; font-weight: 900; margin-bottom: 0.5rem; background: linear-gradient(135deg, #60a5fa 0%, #f472b6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">CourtSide Analytics</h1>
            <p style="font-size: 1.5rem; opacity: 0.95; font-weight: 600;">NBA 3PT Props Model</p>
            <div>
                <div class="badge">● REAL NBA STATS API</div>
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
    print(f"{Colors.BOLD}{Colors.CYAN}NBA 3-POINT PROPS A.I. MODEL{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

    # Step 0: Update results for pending picks
    updated = update_pick_results()

    # Step 1: Fetch REAL NBA player 3PT stats
    player_stats = get_nba_player_stats()

    # Step 2: Fetch opponent defense stats
    defense_stats = get_opponent_defense_3pt()

    # Step 3: Fetch player props from odds API
    props_list = get_player_props()

    # Step 4: Analyze props with REAL stats and generate A.I. scores
    # Load historical performance for rating calculation
    tracking_data = load_tracking()
    historical_edge_performance = get_historical_performance_by_edge_props(tracking_data)
    
    over_plays, under_plays = analyze_props(props_list, player_stats, defense_stats, historical_edge_performance)

    # Step 3.5: Automatically track high-confidence picks
    print(f"\n{Colors.CYAN}Auto-tracking picks with A.I. Score >= {AUTO_TRACK_THRESHOLD}...{Colors.END}")
    tracked_count = 0

    for play in over_plays + under_plays:
        if play['ai_score'] >= AUTO_TRACK_THRESHOLD:
            # Find the original prop data to get game_time
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
        print(f"{Colors.YELLOW}  No new picks to track (all already tracked){Colors.END}")

    # Calculate summary: all plays for wins/losses/total, displayed plays for pending count
    tracking_data = load_tracking()
    displayed_plays = over_plays[:TOP_PLAYS_COUNT] + under_plays[:TOP_PLAYS_COUNT]
    summary = calculate_tracking_summary(tracking_data['picks'], displayed_plays)
    tracking_data['summary'] = summary  # Update tracking data with summary

    # Display tracking summary
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}TRACKING SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"Total Picks: {summary['total']} | Wins: {summary['wins']} | Losses: {summary['losses']} | Pending: {summary['pending']}")
    if summary['wins'] + summary['losses'] > 0:
        print(f"Win Rate: {summary['win_rate']:.1f}% | ROI: {summary['roi']:+.2f}u ({summary['roi_pct']:+.1f}%)")

    # Step 4: Display terminal output
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}TOP OVER PLAYS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")

    for i, play in enumerate(over_plays[:10], 1):
        tracked_marker = "📊" if play['ai_score'] >= AUTO_TRACK_THRESHOLD else "  "
        ai_rating = play.get('ai_rating', 2.3)
        rating_stars = '⭐' * (int(ai_rating) - 2) if ai_rating >= 3.0 else ''
        print(f"{tracked_marker} {Colors.CYAN}{i:2d}. {play['player']:25s}{Colors.END} | "
              f"{Colors.GREEN}{play['prop']:15s}{Colors.END} | "
              f"{play['team']:3s} vs {play['opponent']:3s} | "
              f"{Colors.BOLD}A.I.: {play['ai_score']:.2f}{Colors.END} | "
              f"Rating: {ai_rating:.1f} {rating_stars}")

    print(f"\n{Colors.BOLD}{Colors.RED}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.RED}TOP UNDER PLAYS{Colors.END}")
    print(f"{Colors.BOLD}{Colors.RED}{'='*80}{Colors.END}")

    for i, play in enumerate(under_plays[:10], 1):
        tracked_marker = "📊" if play['ai_score'] >= AUTO_TRACK_THRESHOLD else "  "
        ai_rating = play.get('ai_rating', 2.3)
        rating_stars = '⭐' * (int(ai_rating) - 2) if ai_rating >= 3.0 else ''
        print(f"{tracked_marker} {Colors.CYAN}{i:2d}. {play['player']:25s}{Colors.END} | "
              f"{Colors.RED}{play['prop']:15s}{Colors.END} | "
              f"{play['team']:3s} vs {play['opponent']:3s} | "
              f"{Colors.BOLD}A.I.: {play['ai_score']:.2f}{Colors.END} | "
              f"Rating: {ai_rating:.1f} {rating_stars}")

    print(f"\n{Colors.YELLOW}📊 = Auto-tracked (A.I. Score >= {AUTO_TRACK_THRESHOLD}){Colors.END}")

    # Step 5: Generate HTML output
    print(f"\n{Colors.CYAN}Generating HTML report...{Colors.END}")
    html_content = generate_html_output(over_plays, under_plays, summary, tracking_data)
    save_html(html_content)

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}✓ Model execution complete!{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*80}{Colors.END}\n")

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
