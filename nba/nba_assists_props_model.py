#!/usr/bin/env python3
"""
NBA Assists Props Model - PROFITABLE VERSION
Analyzes player assists props using REAL NBA stats
Focuses on pace, opponent factors, and matchup advantages
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

# Import NBA API for real stats
from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats, playergamelog
from nba_api.stats.static import players

# Configuration
API_KEY = os.environ.get('ODDS_API_KEY', 'faabaed9ec8604dcc24db96c53d6ae01')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "nba_assists_props.html")
TRACKING_FILE = os.path.join(SCRIPT_DIR, "nba_assists_props_tracking.json")
PLAYER_STATS_CACHE = os.path.join(SCRIPT_DIR, "nba_player_assists_stats_cache.json")
TEAM_ASSISTS_CACHE = os.path.join(SCRIPT_DIR, "nba_team_assists_cache.json")

# Model Parameters - EXTREMELY STRICT FOR PROFITABILITY
MIN_AI_SCORE = 9.5  # Only show high-confidence plays
TOP_PLAYS_COUNT = 5  # Quality over quantity
RECENT_GAMES_WINDOW = 10  # 10 games for recent form
AUTO_TRACK_THRESHOLD = 9.7  # Only track elite plays
CURRENT_SEASON = '2025-26'

# Edge requirements - STRICTER for assists (more variance)
MIN_EDGE_OVER_LINE = 1.5  # Player must average 1.5+ above prop line for OVER
MIN_EDGE_UNDER_LINE = 1.2  # Player must average 1.2+ below prop line for UNDER
MIN_RECENT_FORM_EDGE = 1.0  # Recent form must strongly support

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def get_nba_player_assists_stats():
    """
    Fetch REAL NBA player assists stats from NBA API
    Returns dictionary with player assists stats (season avg, recent form, etc.)
    """
    print(f"\n{Colors.CYAN}Fetching REAL NBA player assists statistics...{Colors.END}")

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
        print(f"{Colors.CYAN}  Fetching season assists stats...{Colors.END}")
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
            season_ast = row.get('AST', 0)  # Total assists per game
            games_played = row.get('GP', 0)
            team = row.get('TEAM_ABBREVIATION', '')
            minutes = row.get('MIN', 0)

            # Get recent form
            recent_row = recent_df[recent_df['PLAYER_NAME'] == player_name]
            if not recent_row.empty:
                recent_ast = recent_row.iloc[0].get('AST', season_ast)
            else:
                recent_ast = season_ast

            # Calculate consistency (assists per 36 minutes)
            ast_per_36 = (season_ast / minutes * 36) if minutes > 0 else 0
            consistency = min(1.0, ast_per_36 / 8.0) if ast_per_36 > 0 else 0.3  # Normalize to 8 ast/36

            player_stats[player_name] = {
                'season_ast_avg': round(season_ast, 2),
                'recent_ast_avg': round(recent_ast, 2),
                'ast_per_36': round(ast_per_36, 2),
                'consistency_score': round(consistency, 2),
                'games_played': int(games_played),
                'team': team,
                'minutes': round(minutes, 1)
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

def get_opponent_assists_factors():
    """
    Fetch team assists stats to identify matchup advantages
    Returns dict with opponent assists factors (assists allowed, pace, team assist rate)
    """
    print(f"\n{Colors.CYAN}Fetching opponent assists factors...{Colors.END}")

    # Check cache
    if os.path.exists(TEAM_ASSISTS_CACHE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(TEAM_ASSISTS_CACHE))
        if (datetime.now() - file_mod_time) < timedelta(hours=6):
            print(f"{Colors.GREEN}✓ Using cached assists factors{Colors.END}")
            with open(TEAM_ASSISTS_CACHE, 'r') as f:
                return json.load(f)

    assists_factors = {}

    try:
        # Fetch team stats
        team_stats = leaguedashteamstats.LeagueDashTeamStats(
            season=CURRENT_SEASON,
            measure_type_detailed_defense='Base',
            timeout=30
        )
        team_df = team_stats.get_data_frames()[0]
        time.sleep(0.6)

        # Process team assists stats
        for _, row in team_df.iterrows():
            team_name = row.get('TEAM_NAME', '')
            if not team_name:
                continue

            # Opponent assists stats (what they allow)
            opp_ast = row.get('OPP_AST', 0)  # Opponent assists allowed
            
            # Team pace
            pace = row.get('PACE', 100)
            
            # Team assist rate (assists per field goal made)
            team_ast = row.get('AST', 0)
            team_fgm = row.get('FGM', 0)
            assist_rate = (team_ast / team_fgm) if team_fgm > 0 else 0.5
            
            # Calculate assists advantage factors
            # High opponent assists allowed = easier to get assists
            # High pace = more possessions = more assists opportunities
            # High team assist rate = more ball movement = more assists
            
            assists_factors[team_name] = {
                'opp_ast_allowed': round(opp_ast, 2),
                'pace': round(pace, 2),
                'team_assist_rate': round(assist_rate, 3),
                'assists_factor': round((opp_ast / 25.0) * (pace / 100) * assist_rate, 2)  # Higher = better for assists
            }

        # Cache results
        with open(TEAM_ASSISTS_CACHE, 'w') as f:
            json.dump(assists_factors, f, indent=2)

        print(f"{Colors.GREEN}✓ Fetched assists factors for {len(assists_factors)} teams{Colors.END}")
        return assists_factors

    except Exception as e:
        print(f"{Colors.YELLOW}⚠ Could not fetch assists factors: {e}{Colors.END}")
        # Try cache
        if os.path.exists(TEAM_ASSISTS_CACHE):
            with open(TEAM_ASSISTS_CACHE, 'r') as f:
                return json.load(f)
        return {}

def get_nba_team_rosters():
    """Build a mapping of player names to their teams"""
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

def calculate_tracking_summary(picks):
    """Calculate summary statistics from picks"""
    total = len(picks)
    wins = len([p for p in picks if p.get('status') == 'win'])
    losses = len([p for p in picks if p.get('status') == 'loss'])
    pending = len([p for p in picks if p.get('status') == 'pending'])

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

def track_pick(player_name, prop_line, bet_type, team, opponent, ai_score, odds, game_time):
    """Add a pick to tracking file"""
    tracking_data = load_tracking()
    pick_id = f"{player_name}_{prop_line}_{bet_type}_{game_time}"
    
    existing = next((p for p in tracking_data['picks'] if p['pick_id'] == pick_id), None)
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
        'actual_ast': None
    }

    tracking_data['picks'].append(pick)
    tracking_data['summary'] = calculate_tracking_summary(tracking_data['picks'])
    save_tracking(tracking_data)
    return True

def fetch_player_assists_from_nba_api(player_name, team_name, game_date_str):
    """
    Fetch actual player assists from NBA API for a specific game
    Returns the actual assists count or None if not found
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
        # Convert game_date_str to match NBA API date format
        target_date = datetime.strptime(game_date_str, '%Y-%m-%d').date()
        
        for _, row in df.iterrows():
            game_date_str_nba = row.get('GAME_DATE', '')
            if not game_date_str_nba:
                continue
            
            # Parse NBA date format (usually "DEC 11, 2025" or similar)
            try:
                game_date = datetime.strptime(game_date_str_nba, '%b %d, %Y').date()
            except:
                try:
                    game_date = datetime.strptime(game_date_str_nba, '%Y-%m-%d').date()
                except:
                    continue
            
            if game_date == target_date:
                assists = row.get('AST', 0)
                return int(assists) if assists else 0
        
        return None
        
    except Exception as e:
        print(f"{Colors.YELLOW}  Error fetching stats from NBA API for {player_name}: {str(e)}{Colors.END}")
        return None

def fetch_player_assists_from_espn(player_name, team_name, game_date_str):
    """
    Fetch actual player assists from ESPN API for a specific game
    Returns the actual assists count or None if not found
    """
    try:
        # Convert date to ESPN format (YYYYMMDD)
        date_obj = datetime.strptime(game_date_str, '%Y-%m-%d')
        api_date = date_obj.strftime('%Y%m%d')
        
        # Fetch scoreboard for the date
        url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={api_date}'
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            print(f"{Colors.YELLOW}    ESPN API returned {response.status_code}{Colors.END}")
            return None
            
        data = response.json()
        events = data.get('events', [])
        
        if not events:
            print(f"{Colors.YELLOW}    No events found for {game_date_str}{Colors.END}")
            return None
        
        # Team name mapping for ESPN (use last word or common name)
        def get_team_key(team_name):
            # Extract key part of team name
            parts = team_name.split()
            if 'Trail Blazers' in team_name:
                return 'Blazers'
            elif 'Pelicans' in team_name:
                return 'Pelicans'
            elif 'Nuggets' in team_name:
                return 'Nuggets'
            elif 'Kings' in team_name:
                return 'Kings'
            elif 'Cavaliers' in team_name:
                return 'Cavaliers'
            elif 'Wizards' in team_name:
                return 'Wizards'
            elif 'Hornets' in team_name:
                return 'Hornets'
            elif 'Bulls' in team_name:
                return 'Bulls'
            elif 'Grizzlies' in team_name:
                return 'Grizzlies'
            elif 'Jazz' in team_name:
                return 'Jazz'
            return parts[-1] if parts else team_name
        
        team_key = get_team_key(team_name)
        
        # Find the game
        for event in events:
            competitions = event.get('competitions', [{}])
            if not competitions:
                continue
                
            comp = competitions[0]
            competitors = comp.get('competitors', [])
            
            # Check if this is the right game
            event_teams = []
            for comp_team in competitors:
                team_display = comp_team.get('team', {}).get('displayName', '')
                event_teams.append(team_display)
            
            # Check if team is in this game
            if not any(team_key in team or any(word in team for word in team_name.split()[-2:]) for team in event_teams):
                continue
            
            # Game is final?
            status = event.get('status', {}).get('type', {}).get('description', '')
            if 'final' not in status.lower() and 'final' not in status.lower():
                continue
            
            # Get box score
            event_id = event.get('id')
            if not event_id:
                continue
                
            boxscore_url = f'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={event_id}'
            boxscore_response = requests.get(boxscore_url, timeout=10)
            
            if boxscore_response.status_code != 200:
                continue
                
            boxscore_data = boxscore_response.json()
            
            # Try to find player in boxscore
            # ESPN boxscore structure: boxscore -> teams -> statistics -> athletes
            boxscore = boxscore_data.get('boxscore', {})
            if not boxscore:
                # Try alternative structure
                boxscore = boxscore_data
            
            # Check both teams
            for team_data in boxscore.get('teams', []):
                team_statistics = team_data.get('statistics', [])
                
                for stat_group in team_statistics:
                    athletes = stat_group.get('athletes', [])
                    if not athletes:
                        continue
                    
                    for athlete_data in athletes:
                        athlete = athlete_data.get('athlete', {})
                        if not athlete:
                            continue
                        
                        athlete_name = athlete.get('displayName', '')
                        # Match player name (handle variations like "Malik Monk" vs "M. Monk")
                        name_parts = player_name.lower().split()
                        athlete_parts = athlete_name.lower().split()
                        
                        # Check if names match (first and last name)
                        if (len(name_parts) >= 2 and len(athlete_parts) >= 2 and
                            name_parts[0] in athlete_parts[0] and name_parts[-1] in athlete_parts[-1]):
                            
                            # Get stats
                            stats = athlete_data.get('stats', [])
                            for stat in stats:
                                if stat.get('name') == 'assists' or stat.get('label') == 'AST':
                                    assists_value = stat.get('value', stat.get('displayValue', '0'))
                                    try:
                                        return int(float(str(assists_value).replace(',', '')))
                                    except:
                                        pass
                            
                            # Try alternative stat format
                            for key, value in athlete_data.items():
                                if 'assist' in key.lower() and isinstance(value, (int, float)):
                                    return int(value)
        
        return None
        
    except Exception as e:
        print(f"{Colors.YELLOW}  Error fetching stats for {player_name}: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
        return None

def update_pick_results():
    """Check pending picks and update their status using ESPN API"""
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
                
                # Fetch actual assists (try NBA API first, then ESPN)
                actual_assists = fetch_player_assists_from_nba_api(player_name, team_name, game_date_str)
                if actual_assists is None:
                    actual_assists = fetch_player_assists_from_espn(player_name, team_name, game_date_str)
                
                if actual_assists is None:
                    print(f"{Colors.YELLOW}    Could not fetch stats, skipping...{Colors.END}")
                    continue
                
                # Determine win/loss
                prop_line = pick['prop_line']
                bet_type = pick['bet_type'].lower()
                
                if bet_type == 'over':
                    is_win = actual_assists > prop_line
                else:  # under
                    is_win = actual_assists < prop_line
                
                # Update pick
                pick['status'] = 'win' if is_win else 'loss'
                pick['result'] = 'WIN' if is_win else 'LOSS'
                pick['actual_ast'] = actual_assists
                pick['updated_at'] = current_time.isoformat()
                
                result_str = f"{Colors.GREEN}WIN{Colors.END}" if is_win else f"{Colors.RED}LOSS{Colors.END}"
                print(f"    {result_str}: {player_name} had {actual_assists} assists (line: {prop_line}, bet: {bet_type.upper()})")
                updated += 1
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)

        except Exception as e:
            print(f"{Colors.RED}    Error processing pick: {e}{Colors.END}")
            continue

    if updated > 0:
        tracking_data['summary'] = calculate_tracking_summary(tracking_data['picks'])
        save_tracking(tracking_data)
        print(f"\n{Colors.GREEN}✓ Updated {updated} picks{Colors.END}")

    return updated

def reverify_completed_picks():
    """Re-verify all completed picks to ensure accuracy"""
    tracking_data = load_tracking()
    completed_picks = [p for p in tracking_data['picks'] 
                      if p.get('status') in ['win', 'loss'] and p.get('actual_ast') is None]
    
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
            
            # Fetch actual assists (try NBA API first, then ESPN)
            actual_assists = fetch_player_assists_from_nba_api(player_name, team_name, game_date_str)
            if actual_assists is None:
                actual_assists = fetch_player_assists_from_espn(player_name, team_name, game_date_str)
            
            if actual_assists is None:
                print(f"{Colors.YELLOW}    Could not fetch stats, skipping...{Colors.END}")
                continue
            
            # Determine correct win/loss
            prop_line = pick['prop_line']
            bet_type = pick['bet_type'].lower()
            
            if bet_type == 'over':
                correct_result = 'win' if actual_assists > prop_line else 'loss'
            else:  # under
                correct_result = 'win' if actual_assists < prop_line else 'loss'
            
            current_status = pick.get('status', '').lower()
            
            # Update if incorrect
            if correct_result != current_status:
                old_status = pick['status']
                pick['status'] = correct_result
                pick['result'] = 'WIN' if correct_result == 'win' else 'LOSS'
                pick['actual_ast'] = actual_assists
                
                print(f"    {Colors.RED}FIXED: Was {old_status.upper()}, now {correct_result.upper()}{Colors.END}")
                print(f"    {player_name} had {actual_assists} assists (line: {prop_line}, bet: {bet_type.upper()})")
                updated += 1
            else:
                pick['actual_ast'] = actual_assists
                print(f"    {Colors.GREEN}Verified: {correct_result.upper()} - {actual_assists} assists{Colors.END}")
                updated += 1
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"{Colors.RED}    Error verifying pick: {e}{Colors.END}")
            continue
    
    if updated > 0:
        tracking_data['summary'] = calculate_tracking_summary(tracking_data['picks'])
        save_tracking(tracking_data)
        print(f"\n{Colors.GREEN}✓ Re-verified {updated} picks{Colors.END}")
    
    return updated

def get_player_props():
    """Fetch player assists prop odds from The Odds API"""
    print(f"\n{Colors.CYAN}Fetching player assists prop odds...{Colors.END}")
    rosters = get_nba_team_rosters()
    events_url = "https://api.the-odds-api.com/v4/sports/basketball_nba/events"
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

            odds_url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{event_id}/odds"
            odds_params = {
                'apiKey': API_KEY,
                'regions': 'us',
                'markets': 'player_assists',
                'oddsFormat': 'american'
            }

            odds_response = requests.get(odds_url, params=odds_params, timeout=15)

            if odds_response.status_code == 200:
                odds_data = odds_response.json()
                if 'bookmakers' in odds_data and odds_data['bookmakers']:
                    fanduel = next((b for b in odds_data['bookmakers'] if b['key'] == 'fanduel'),
                                  odds_data['bookmakers'][0])

                    if 'markets' in fanduel:
                        for market in fanduel['markets']:
                            if market['key'] == 'player_assists':
                                for outcome in market['outcomes']:
                                    player_name = outcome['description']
                                    player_team, player_opponent = match_player_to_team(
                                        player_name, home_team, away_team, rosters
                                    )

                                    prop = {
                                        'player': player_name,
                                        'prop_line': outcome['point'],
                                        'over_price': outcome.get('price', -110),
                                        'team': player_team,
                                        'opponent': player_opponent,
                                        'game_time': event['commence_time']
                                    }
                                    all_props.append(prop)

            print(f"{Colors.CYAN}  Game {i}/{len(events[:10])}: {away_team} @ {home_team}{Colors.END}")

        print(f"{Colors.GREEN}✓ Fetched {len(all_props)} total player props{Colors.END}")
        return all_props

    except Exception as e:
        print(f"{Colors.RED}✗ Error fetching props: {e}{Colors.END}")
        return []

def calculate_ai_score(player_data, prop_line, bet_type, opponent_assists=None):
    """
    Calculate STRICT A.I. Score for assists props using REAL stats
    Factors: Season avg, recent form, pace, opponent assists factors, consistency
    """
    score = 4.0

    season_avg = player_data.get('season_ast_avg', 0)
    recent_avg = player_data.get('recent_ast_avg', 0)
    ast_per_36 = player_data.get('ast_per_36', 0)
    consistency = player_data.get('consistency_score', 0.3)
    games_played = player_data.get('games_played', 0)
    minutes = player_data.get('minutes', 0)

    if games_played < 5:
        return 0.0

    if minutes < 15:  # Not enough playing time
        return 0.0

    if bet_type == 'over':
        edge_above_line = season_avg - prop_line
        if edge_above_line >= MIN_EDGE_OVER_LINE:
            score += 3.5
        elif edge_above_line >= 1.0:
            score += 2.0
        elif edge_above_line >= 0.6:
            score += 1.0
        elif edge_above_line >= 0.3:
            score += 0.3
        else:
            score -= 2.0
            if recent_avg < prop_line + 0.5:
                return 0.0

        recent_edge = recent_avg - prop_line
        if recent_edge >= MIN_RECENT_FORM_EDGE:
            score += 2.5
        elif recent_edge >= 0.7:
            score += 1.5
        elif recent_avg > season_avg + 0.5:
            score += 1.0
        elif recent_avg >= prop_line:
            score += 0.5
        else:
            score -= 1.5

        # Assists rate bonus
        if ast_per_36 >= 8.0:
            score += 1.5
        elif ast_per_36 >= 6.0:
            score += 1.0
        elif ast_per_36 >= 4.0:
            score += 0.5

        score += consistency * 0.8

        # Opponent factors (pace, assists allowed, team assist rate)
        if opponent_assists:
            ast_factor = opponent_assists.get('assists_factor', 1.0)
            if ast_factor > 1.05:
                score += 1.0
            elif ast_factor < 0.95:
                score -= 0.5

    else:  # under
        edge_below_line = prop_line - season_avg
        if edge_below_line >= MIN_EDGE_UNDER_LINE:
            score += 3.5
        elif edge_below_line >= 0.9:
            score += 2.0
        elif edge_below_line >= 0.5:
            score += 1.0
        elif edge_below_line >= 0.2:
            score += 0.3
        else:
            score -= 2.0
            if recent_avg > prop_line - 0.5:
                return 0.0

        recent_edge = prop_line - recent_avg
        if recent_edge >= MIN_RECENT_FORM_EDGE:
            score += 2.5
        elif recent_edge >= 0.7:
            score += 1.5
        elif recent_avg < season_avg - 0.5:
            score += 1.0
        elif recent_avg <= prop_line:
            score += 0.5
        else:
            score -= 1.5

        if ast_per_36 < 4.0:
            score += 1.0
        elif ast_per_36 < 6.0:
            score += 0.5

        score += (1.0 - consistency) * 0.5

        if opponent_assists:
            ast_factor = opponent_assists.get('assists_factor', 1.0)
            if ast_factor < 0.95:
                score += 1.0
            elif ast_factor > 1.05:
                score -= 0.5

    final_score = min(10.0, max(0.0, score))
    
    if bet_type == 'over' and season_avg < prop_line + 0.4:
        final_score = min(final_score, 8.5)
    elif bet_type == 'under' and season_avg > prop_line - 0.4:
        final_score = min(final_score, 8.5)

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

def analyze_props(props_list, player_stats, assists_factors):
    """Analyze all player props using REAL NBA stats"""
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
            for name, stats in player_stats.items():
                if player_name.split()[-1].lower() in name.lower() or name.split()[-1].lower() in player_name.lower():
                    player_data = stats
                    break
            
            if not player_data:
                skipped_no_stats += 1
                continue

        opponent_assists = None
        if opponent_team in assists_factors:
            opponent_assists = assists_factors[opponent_team]
        else:
            for team_name, factors in assists_factors.items():
                if opponent_team.lower() in team_name.lower() or team_name.lower() in opponent_team.lower():
                    opponent_assists = factors
                    break

        over_score = calculate_ai_score(player_data, prop_line, 'over', opponent_assists)
        if over_score >= MIN_AI_SCORE:
            season_avg = player_data.get('season_ast_avg', 0)
            recent_avg = player_data.get('recent_ast_avg', 0)
            
            if season_avg >= prop_line + 0.3 and recent_avg >= prop_line + 0.2:
                # Calculate EV
                ev = calculate_ev(over_score, prop_line, season_avg, recent_avg, prop['over_price'], 'over')
                is_sharp = over_score >= AUTO_TRACK_THRESHOLD and ev > 0
                
                over_plays.append({
                    'player': player_name,
                    'prop': f"OVER {prop_line} AST",
                    'team': prop['team'],
                    'opponent': opponent_team,
                    'ai_score': over_score,
                    'odds': prop['over_price'],
                    'game_time': prop['game_time'],
                    'season_avg': season_avg,
                    'recent_avg': recent_avg,
                    'edge': round(season_avg - prop_line, 2),
                    'ev': round(ev, 2),
                    'is_sharp': is_sharp
                })
            else:
                skipped_low_score += 1
        else:
            skipped_low_score += 1

        under_score = calculate_ai_score(player_data, prop_line, 'under', opponent_assists)
        if under_score >= MIN_AI_SCORE:
            season_avg = player_data.get('season_ast_avg', 0)
            recent_avg = player_data.get('recent_ast_avg', 0)
            
            if season_avg <= prop_line - 0.3 and recent_avg <= prop_line - 0.2:
                # Calculate EV
                ev = calculate_ev(under_score, prop_line, season_avg, recent_avg, prop['over_price'], 'under')
                is_sharp = under_score >= AUTO_TRACK_THRESHOLD and ev > 0
                
                under_plays.append({
                    'player': player_name,
                    'prop': f"UNDER {prop_line} AST",
                    'team': prop['team'],
                    'opponent': opponent_team,
                    'ai_score': under_score,
                    'odds': prop['over_price'],
                    'game_time': prop['game_time'],
                    'season_avg': season_avg,
                    'recent_avg': recent_avg,
                    'edge': round(prop_line - season_avg, 2),
                    'ev': round(ev, 2),
                    'is_sharp': is_sharp
                })
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

    unique_over.sort(key=lambda x: x['ai_score'], reverse=True)
    unique_under.sort(key=lambda x: x['ai_score'], reverse=True)

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
                <h2 style="font-size: 1.75rem; font-weight: 700; margin-bottom: 1.5rem; text-align: center;">📊 Model Performance Tracking</h2>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                    <div style="background: #2a3441; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Total Picks</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #ffffff;">{tracking_summary['total']}</div>
                    </div>
                    <div style="background: #2a3441; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Win Rate</div>
                        <div style="font-size: 2rem; font-weight: 700; color: {win_rate_color if completed > 0 else '#94a3b8'};">{tracking_summary['win_rate']:.1f}%{' (N/A)' if completed == 0 else ''}</div>
                    </div>
                    <div style="background: #2a3441; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Record</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #ffffff;">{tracking_summary['wins']}-{tracking_summary['losses']}</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">({completed} completed)</div>
                    </div>
                    <div style="background: #2a3441; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">P/L (Units)</div>
                        <div style="font-size: 2rem; font-weight: 700; color: {roi_color if completed > 0 else '#94a3b8'};">{tracking_summary['roi']:+.2f}u</div>
                        <div style="font-size: 0.75rem; color: {roi_color if completed > 0 else '#94a3b8'}; margin-top: 0.25rem;">{tracking_summary.get('roi_pct', 0):+.1f}% ROI{' (Pending)' if completed == 0 else ''}</div>
                    </div>
                    <div style="background: #2a3441; padding: 1.25rem; border-radius: 0.75rem; text-align: center;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Pending</div>
                        <div style="font-size: 2rem; font-weight: 700; color: #fbbf24;">{tracking_summary['pending']}</div>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 1.5rem; padding-top: 1.5rem; border-top: 1px solid #2a3441;">
                    <div style="background: #2a3441; padding: 1rem; border-radius: 0.75rem;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Closing Line Value</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: {clv_color};">{tracking_summary.get('clv_rate', 0):.1f}%</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">{tracking_summary.get('clv_count', '0/0')} positive CLV</div>
                    </div>
                    <div style="background: #2a3441; padding: 1rem; border-radius: 0.75rem;">
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.05em;">Avg A.I. Score</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #60a5fa;">9.7+</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;">Elite plays only</div>
                    </div>
                    <div style="background: #2a3441; padding: 1rem; border-radius: 0.75rem;">
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

    footer_text = f"Powered by REAL NBA Stats API • Only showing picks with A.I. Score ≥ {MIN_AI_SCORE}<br>Using strict edge requirements: {MIN_EDGE_OVER_LINE}+ above line (OVER) / {MIN_EDGE_UNDER_LINE}+ below line (UNDER)<br>📊 = Auto-tracked (A.I. Score >= {AUTO_TRACK_THRESHOLD})"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Assists Props - A.I. Projections</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
            background: #0a1628;
            color: #ffffff;
            padding: 1.5rem;
            min-height: 100vh;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{
            background: #1a2332;
            border-radius: 1.25rem;
            border: none;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        .header-card {{
            text-align: center;
            background: #1a2332;
            border: none;
        }}
        .bet-box {{
            background: #2a3441;
            padding: 1.25rem;
            border-radius: 1rem;
            border-left: none;
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
            <p style="font-size: 1.5rem; opacity: 0.95; font-weight: 600;">NBA Assists Props Model</p>
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
    print(f"{Colors.BOLD}{Colors.CYAN}NBA ASSISTS PROPS A.I. MODEL{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

    updated = update_pick_results()
    player_stats = get_nba_player_assists_stats()
    assists_factors = get_opponent_assists_factors()
    props_list = get_player_props()
    over_plays, under_plays = analyze_props(props_list, player_stats, assists_factors)

    print(f"\n{Colors.CYAN}Auto-tracking picks with A.I. Score >= {AUTO_TRACK_THRESHOLD}...{Colors.END}")
    tracked_count = 0

    for play in over_plays + under_plays:
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
    summary = tracking_data['summary']

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
