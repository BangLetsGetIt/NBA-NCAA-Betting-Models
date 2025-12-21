import json
import os
import re
import time
import requests
import pandas as pd
import pytz
from datetime import datetime, timedelta
from io import StringIO
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Constants & Config
# =============================================================================

API_KEY = os.getenv("ODDS_API_KEY")
CURRENT_SEASON = "2025"  # Sports-Reference uses 2025 for 2024-25 season

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"

# =============================================================================
# Shared CSS & HTML Helpers
# =============================================================================

def get_shared_css():
    return """
        :root {
            --bg-main: #121212;
            --bg-card: #1e1e1e;
            --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --accent-green: #4ade80;
            --accent-red: #f87171;
            --accent-blue: #60a5fa;
            --border-color: #333333;
        }

        body {
            margin: 0;
            padding: 20px;
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            -webkit-font-smoothing: antialiased;
        }

        .container { max-width: 800px; margin: 0 auto; }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
        }
        h1 { margin: 0; font-size: 24px; font-weight: 700; margin-bottom: 5px; }
        .subheader { font-size: 18px; font-weight: 600; color: var(--text-primary); margin-bottom: 5px; }
        .date-sub { color: var(--text-secondary); font-size: 14px; margin-top: 5px; }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 30px;
        }
        .stat-box {
            background-color: var(--bg-card);
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            border: 1px solid var(--border-color);
        }
        .stat-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 5px; }
        .stat-value { font-size: 20px; font-weight: 700; }

        .section-title {
            font-size: 18px;
            margin-bottom: 15px;
            display: flex; align-items: center;
        }
        .section-title span.highlight { color: var(--accent-green); margin-left: 8px; font-size: 14px; }

        .prop-card {
            background-color: var(--bg-card);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
        }

        .card-header {
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: var(--bg-card-secondary);
            border-bottom: 1px solid var(--border-color);
        }

        .header-left { display: flex; align-items: center; gap: 12px; }
        .team-logo { width: 45px; height: 45px; border-radius: 50%; padding: 2px; object-fit: contain; }
        .player-info h2 { margin: 0; font-size: 18px; line-height: 1.2; }
        .matchup-info { color: var(--text-secondary); font-size: 13px; margin-top: 2px; }
        .game-meta { text-align: right; }
        .game-date-time { font-size: 12px; color: var(--text-secondary); background: #333; padding: 6px 10px; border-radius: 6px; font-weight: 500; white-space: nowrap; }

        .card-body { padding: 20px; }
        .bet-main-row { margin-bottom: 15px; }
        .bet-selection { font-size: 22px; font-weight: 800; }
        .bet-selection .line { color: var(--text-primary); }
        .bet-odds { font-size: 18px; color: var(--text-secondary); font-weight: 500; margin-left: 8px; }

        .model-subtext { color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid var(--border-color); }
        .model-subtext strong { color: var(--text-primary); }

        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }
        .metric-item { background-color: var(--bg-main); padding: 10px; border-radius: 8px; text-align: center; }
        .metric-lbl { display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }
        .metric-val { font-size: 16px; font-weight: 700; }

        .player-stats { background-color: var(--bg-card-secondary); border-radius: 8px; padding: 12px 15px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border-color); }
        .player-stats-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
        .player-stats-value { font-size: 16px; font-weight: 700; }
        .player-stats-item { text-align: center; flex: 1; }
        .player-stats-divider { width: 1px; height: 30px; background-color: var(--border-color); }

        .tags-container { display: flex; flex-wrap: wrap; gap: 8px; }
        .tag { font-size: 12px; padding: 6px 10px; border-radius: 6px; font-weight: 500; }

        .txt-green { color: var(--accent-green); }
        .txt-red { color: var(--accent-red); }
        
        .tag-green { background-color: rgba(74, 222, 128, 0.15); color: var(--accent-green); }
        .tag-red { background-color: rgba(248, 113, 113, 0.15); color: var(--accent-red); }
        .tag-blue { background-color: rgba(96, 165, 250, 0.15); color: var(--accent-blue); }
        
        .metric-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
        }
        .text-red { color: var(--accent-red); }
        .tracking-section { margin-top: 3rem; }
        .tracking-header { 
            font-size: 1.5rem; 
            font-weight: 700; 
            color: var(--text-primary); 
            margin-bottom: 1.5rem; 
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 0.5rem;
        }
        .metrics-row {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
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

        @media (max-width: 600px) {
            .summary-grid { grid-template-columns: repeat(2, 1fr); }
            .stat-box:last-child { grid-column: span 2; }
            .card-header { padding: 12px 15px; }
            .team-logo { width: 38px; height: 38px; }
            .player-info h2 { font-size: 16px; }
        }
    """

# =============================================================================
# CBB Props Model Engine
# =============================================================================

class CBBPropsEngine:
    def __init__(self, prop_type):
        """
        prop_type: 'points', 'rebounds', 'assists'
        """
        self.prop_type = prop_type.lower()
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # File paths
        self.tracking_file = os.path.join(self.script_dir, f"cbb_{self.prop_type}_props_tracking.json")
        self.output_html = os.path.join(self.script_dir, f"cbb_{self.prop_type}_props.html")
        self.stats_cache_file = os.path.join(self.script_dir, "cbb_player_stats_cache.json")
        
        # Map prop_type to Odds API market key and Stats column
        self.market_key = f"player_{self.prop_type}"
        if self.prop_type == 'rebounds':
            self.stat_col = 'TRB' # Sports-Reference column
            self.prop_unit = 'REB'
        elif self.prop_type == 'assists':
            self.stat_col = 'AST'
            self.prop_unit = 'AST'
        else: # points
            self.stat_col = 'PTS'
            self.prop_unit = 'PTS'
            self.market_key = 'player_points'

        # Model Parameters
        self.min_ai_score = 7.0 
        self.top_plays_count = 10
    
    def load_tracking_data(self):
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {'picks': [], 'summary': {}}

    def save_tracking_data(self, data):
        with open(self.tracking_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_team_slug(self, team_name):
        """Convert team name to Sports-Reference slug using the map"""
        slug_file = os.path.join(self.script_dir, "cbb_team_slugs.json")
        if not os.path.exists(slug_file):
             # Fallback
             return team_name.lower().replace(' ', '-').replace('.', '')
             
        try:
            with open(slug_file, 'r') as f:
                slugs_map = json.load(f)
        except:
            return team_name.lower().replace(' ', '-')
            
        # Try direct match
        if team_name in slugs_map:
            return slugs_map[team_name]
            
        # Try cleaning input
        clean_name = team_name.replace('State', 'St').replace('St.', 'St').replace('Saint', 'St')
        
        # Iterative search - Sort by length descending to match "North Carolina A&T" before "North Carolina"
        sorted_schools = sorted(slugs_map.keys(), key=len, reverse=True)
        
        for school in sorted_schools:
            slug = slugs_map[school]
            if school == team_name: return slug
            
            # Simple substring
            if school in team_name:
                return slug
                
            # Handle "St" vs "State" vs "Saint"
            school_clean = school.replace('State', 'St').replace('St.', 'St').replace('Saint', 'St')
            if school_clean in clean_name:
                return slug
                
        # 2. Check override map for tough ones
        manual_map = {
            "uconn": "connecticut",
            "unc": "north-carolina",
            "miami (fl)": "miami-fl",
            "miami (oh)": "miami-oh",
            "penn state": "penn-state",
            "ole miss": "mississippi",
            "nc state": "north-carolina-state"
        }
        lower_name = team_name.lower()
        for k, v in manual_map.items():
            if k in lower_name:
                return v
                
        # 3. Last ditch: slugify
        return team_name.lower().replace('.', '').replace(' ', '-')

    def fetch_player_stats(self, teams_playing):
        """Fetch player stats for teams from Sports-Reference"""
        print(f"{Colors.CYAN}Fetching CBB player stats...{Colors.END}")
        
        # Load cache
        stats_cache = {}
        if os.path.exists(self.stats_cache_file):
            with open(self.stats_cache_file, 'r') as f:
                stats_cache = json.load(f)
        
        # Determine which teams need fetching
        # We'll fetch if cache is older than 24h OR team is missing
        # BUT for "teams_playing" we want fresh data if older than ~6h since last game might have happened
        
        updated = False
        
        # Convert cache keys: "slug" -> data
        # "teams_playing" is a list of team names from Odds API
        
        for team_name in teams_playing:
            slug = self.get_team_slug(team_name)
            
            # Check cache age
            cached_team = stats_cache.get(slug)
            needs_fetch = True
            if cached_team:
                fetched_at = cached_team.get('fetched_at')
                if fetched_at:
                    age = (datetime.now() - datetime.fromisoformat(fetched_at)).total_seconds() / 3600
                    if age < 12: # Cache for 12 hours
                        needs_fetch = False
            
            if not needs_fetch:
                continue
                
            # Fetch from Sports-Reference
            print(f"  Fetching stats for {team_name} ({slug})...")
            url = f"https://www.sports-reference.com/cbb/schools/{slug}/men/{CURRENT_SEASON}.html"
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            # Rate limit handling loop
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Base delay (SR allows ~20 req/min, but we want to be very safe: 4.5s)
                    time.sleep(4.5) 
                    
                    response = requests.get(url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        break # Success
                    elif response.status_code == 429:
                        wait_time = 90 * (attempt + 1) # 90s, 180s...
                        print(f"    {Colors.YELLOW}⚠ Rate limited (429). Waiting {wait_time}s...{Colors.END}")
                        time.sleep(wait_time)
                        continue # Retry
                    else:
                        break # Other error, don't retry
                except Exception as e:
                     print(f"    {Colors.RED}✗ Error: {e}{Colors.END}")
                     break

            try:
                if 'response' in locals() and response.status_code == 200:
                    dfs = pd.read_html(StringIO(response.text))
                    # Find 'Per Game' table. Usually table with 'PTS', 'TRB' and 'Player'
                    target_df = None
                    for df in dfs:
                        cols = [str(c) for c in df.columns]
                        # Flatten if multiindex
                        if isinstance(df.columns, pd.MultiIndex):
                            cols = [c[1] if isinstance(c, tuple) else str(c) for c in df.columns]
                            
                        if 'Player' in df.columns or any('Player' in str(c) for c in df.columns):
                            # Check for stats
                            # We need check if columns contain 'PTS' etc
                            # Usually the "Per Game" table has G, GS, MP, FG, ..., TRB, AST, STL, BLK, PTS
                            if 'PTS' in cols or any('PTS' in str(c) for c in df.columns):
                                target_df = df
                                break
                    
                    if target_df is not None:
                        # Process DF
                        # Fix columns if multi-index
                        if isinstance(target_df.columns, pd.MultiIndex):
                             target_df.columns = ['_'.join(map(str, col)).strip() for col in target_df.columns]
                        
                        # Normalize columns (remove 'Per Game_' prefix if exists)
                        target_df.columns = [str(c).split('_')[-1] for c in target_df.columns]
                        
                        # Extract players
                        team_players = {}
                        for _, row in target_df.iterrows():
                            p_name = str(row.get('Player', '')).strip()
                            if not p_name or p_name == 'nan' or p_name == 'Player':
                                continue
                            
                            # Clean name (remove footnotes like "Did not play...")
                            # Usually just take string
                            
                            # Get stats
                            try:
                                stats = {
                                    'games': int(row.get('G', 0)),
                                    'pts': float(row.get('PTS', 0)),
                                    'reb': float(row.get('TRB', 0)),
                                    'ast': float(row.get('AST', 0)),
                                    'min': float(row.get('MP', 0)),
                                    'fg_pct': float(row.get('FG%', 0) or 0),
                                }
                                team_players[p_name] = stats
                            except:
                                continue
                        
                        stats_cache[slug] = {
                            'fetched_at': datetime.now().isoformat(),
                            'players': team_players
                        }
                        updated = True
                        print(f"    {Colors.GREEN}✓ Found {len(team_players)} players{Colors.END}")
                    else:
                         print(f"    {Colors.YELLOW}⚠ No stats table found{Colors.END}")
                else:
                    print(f"    {Colors.RED}✗ Failed to fetch (Status {response.status_code}){Colors.END}")
                    
            except Exception as e:
                print(f"    {Colors.RED}✗ Error: {e}{Colors.END}")
        
        if updated:
            with open(self.stats_cache_file, 'w') as f:
                json.dump(stats_cache, f, indent=2)
                
        return stats_cache

    def get_player_stat(self, player_stats_cache, team_name, player_name):
        """Get stats for a specific player from cache using fuzzy matching"""
        slug = self.get_team_slug(team_name)
        team_data = player_stats_cache.get(slug)
        
        if not team_data:
            return None
            
        players = team_data.get('players', {})
        
        # Exact match
        if player_name in players:
            return players[player_name]
            
        # Fuzzy match (last name)
        p_last = player_name.split()[-1].lower()
        for pname, stats in players.items():
            if p_last in pname.lower():
                return stats
        
        return None

    def fetch_odds(self):
        print(f"\n{Colors.CYAN}Fetching {self.prop_type} props from Odds API...{Colors.END}")
        
        if not API_KEY:
            print(f"{Colors.RED}Missing API Key{Colors.END}")
            return []

        # Get upcoming games
        events_url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab/events"
        try:
            resp = requests.get(events_url, params={"apiKey": API_KEY}, timeout=10)
            if resp.status_code != 200:
                print(f"{Colors.RED}Error: {resp.status_code}{Colors.END}")
                return []
            
            events = resp.json()
            # Filter for next 24h
            upcoming = []
            now = datetime.now(pytz.UTC)
            for e in events:
                game_time = datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00'))
                if now <= game_time <= now + timedelta(hours=36):
                    upcoming.append(e)
            
            print(f"  Found {len(upcoming)} upcoming games (next 36h)")
            
            all_props = []
            teams_playing = set()
            
            for i, event in enumerate(upcoming[:15]): # Limit to 15 games to save calls/time
                event_id = event['id']
                home = event['home_team']
                away = event['away_team']
                teams_playing.add(home)
                teams_playing.add(away)
                
                print(f"  Fetching odds for {away} @ {home}...")
                
                odds_url = f"https://api.the-odds-api.com/v4/sports/basketball_ncaab/events/{event_id}/odds"
                params = {
                    "apiKey": API_KEY,
                    "regions": "us,us2",
                    "markets": self.market_key,
                    "oddsFormat": "american"
                }
                
                odds_resp = requests.get(odds_url, params=params, timeout=5)
                if odds_resp.status_code == 200:
                    data = odds_resp.json()
                    bookmakers = data.get('bookmakers', [])
                    
                    # Find best book (Hard Rock, FanDuel or DraftKings usually good for props)
                    book = next((b for b in bookmakers if b['key'] == 'hardrockbet'), 
                                next((b for b in bookmakers if b['key'] in ['fanduel', 'draftkings']), 
                                     None) or (bookmakers[0] if bookmakers else None))
                    
                    if book:
                        for market in book.get('markets', []):
                            if market['key'] == self.market_key:
                                # Process outcomes
                                grouped = {} # player -> {over, under, line}
                                
                                for outcome in market['outcomes']:
                                    pname = outcome['description']
                                    label = outcome['name'].lower() # over/under
                                    price = outcome['price']
                                    point = outcome['point']
                                    
                                    key = (pname, point)
                                    if key not in grouped:
                                        grouped[key] = {
                                            'player': pname,
                                            'line': point,
                                            'over': None,
                                            'under': None,
                                            'team': None, # Need to infer
                                            'opponent': None
                                        }
                                    
                                    if label == 'over':
                                        grouped[key]['over'] = price
                                    else:
                                        grouped[key]['under'] = price
                                
                                # Infer team? Difficult without roster match.
                                # Use fuzzy matching against home/away teams later.
                                for item in grouped.values():
                                    item['home_team'] = home
                                    item['away_team'] = away
                                    item['game_time'] = event['commence_time']
                                    all_props.append(item)
                                    
            return all_props, list(teams_playing)
            
        except Exception as e:
            print(f"{Colors.RED}Error fetching odds: {e}{Colors.END}")
            return [], []

    def calculate_ai_score(self, stat_avg, line, bet_type):
        """Simple AI Score calculation based on edge"""
        score = 5.0
        
        if bet_type == 'over':
            edge = stat_avg - line
            if edge > 0:
                score += edge * 1.5 # Boost for +edge
            else:
                score -= abs(edge) * 2.0
                
            # Cap/Floor
            if score > 10: score = 9.9
            if score < 0: score = 1.0
            
        else: # under
            edge = line - stat_avg
            if edge > 0:
                score += edge * 1.5
            else:
                score -= abs(edge) * 2.0
        
        return max(0, min(10, score))

    def analyze(self):
        # 1. Fetch Odds
        props, teams = self.fetch_odds()
        if not props:
            print("No props found.")
            return
            
        # 2. Fetch/Load Stats
        stats_cache = self.fetch_player_stats(teams)
        
        # 3. Analyze
        over_plays = []
        under_plays = []
        
        print("\nAnalyzing props...")
        for p in props:
            # Determine player team
            # We have home/away. Check if player in home stats or away stats.
            player_name = p['player']
            home_team = p['home_team']
            away_team = p['away_team']
            
            p_stats = self.get_player_stat(stats_cache, home_team, player_name)
            p_team = home_team
            p_opp = away_team
            
            if not p_stats:
                p_stats = self.get_player_stat(stats_cache, away_team, player_name)
                p_team = away_team
                p_opp = home_team
                
            if not p_stats:
                continue # Skip if no stats
                
            # Get specific stat
            val = p_stats.get(self.prop_type[:3], 0) # pts, reb, ast
            if self.prop_type == 'points': val = p_stats.get('pts', 0)
            
            line = p['line']
            
            # Calc Score
            # OVER
            if p['over']:
                score = self.calculate_ai_score(val, line, 'over')
                if score >= self.min_ai_score:
                    obj = {
                        'player': player_name,
                        'team': p_team,
                        'opponent': p_opp,
                        'prop': f"OVER {line} {self.prop_unit}",
                        'odds': p['over'],
                        'ai_score': score,
                        'edge': val - line,
                        'season_avg': val,
                        'game_time': p['game_time'],
                        'ev': (score - 5) * 5 # Pseudo EV
                    }
                    over_plays.append(obj)
                    
            # UNDER
            if p['under']:
                score = self.calculate_ai_score(val, line, 'under')
                if score >= self.min_ai_score:
                    obj = {
                        'player': player_name,
                        'team': p_team,
                        'opponent': p_opp,
                        'prop': f"UNDER {line} {self.prop_unit}",
                        'odds': p['under'],
                        'ai_score': score,
                        'edge': line - val,
                        'season_avg': val,
                        'game_time': p['game_time'],
                         'ev': (score - 5) * 5
                    }
                    under_plays.append(obj)
                    
        # Sort
        over_plays.sort(key=lambda x: x['ai_score'], reverse=True)
        under_plays.sort(key=lambda x: x['ai_score'], reverse=True)
        
        # Top Plays
        over_plays = over_plays[:self.top_plays_count]
        under_plays = under_plays[:self.top_plays_count]
        
        # 4. Generate HTML
        self.generate_html(over_plays, under_plays)
        
        # 5. Track
        self.track_picks(over_plays + under_plays)

    def generate_html(self, over_plays, under_plays):
        css = get_shared_css()
        
        # Build cards (simplified version of NBA logic)
        def build_cards(plays, label, color_class):
            html = ""
            for p in plays: # Only top few
                ai_stars = "⭐" * int(max(0, p['ai_score'] - 6))
                html += f"""
                <div class="prop-card">
                    <div class="card-header">
                        <div class="header-left">
                            <div class="player-info">
                                <h2>{p['player']}</h2>
                                <div class="matchup-info">{p['opponent']} @ {p['team']}</div>
                            </div>
                        </div>
                         <div class="game-meta">
                            <div class="metric-val" style="font-size: 0.9em">{p['game_time'].split('T')[0]}</div>
                        </div>
                    </div>
                    <div class="card-body">
                         <div class="bet-main-row">
                            <div class="bet-selection">
                                <span class="{color_class}">{label}</span> 
                                <span class="line">{p['prop'].split(' ')[1]} {self.prop_unit}</span> 
                                <span class="bet-odds">{p['odds']}</span>
                            </div>
                        </div>
                        <div class="metrics-grid">
                            <div class="metric-item">
                                <span class="metric-lbl">AI SCORE</span>
                                <span class="metric-val txt-green">{p['ai_score']:.1f}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-lbl">AVG</span>
                                <span class="metric-val">{p['season_avg']:.1f}</span>
                            </div>
                             <div class="metric-item">
                                <span class="metric-lbl">EDGE</span>
                                <span class="metric-val">{p['edge']:+.1f}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
            return html

        over_html = build_cards(over_plays, "OVER", "txt-green")
        under_html = build_cards(under_plays, "UNDER", "txt-red")
        
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide CBB {self.prop_type.capitalize()}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>{css}</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">CBB {self.prop_type.capitalize()} Model</div>
             <div class="date-sub">Automated Props Analysis</div>
        </div>
    </header>
    
    <section>
        <div class="section-title">Top OVER Plays</div>
        {over_html}
    </section>
    
    <section>
        <div class="section-title">Top UNDER Plays</div>
        {under_html}
    </section>
</div>
</body>
</html>
"""
        with open(self.output_html, 'w') as f:
            f.write(full_html)
        print(f"Saved HTML to {self.output_html}")

    def track_picks(self, picks):
        data = self.load_tracking_data()
        
        new_count = 0
        for p in picks:
            # Simple ID
            pid = f"{p['player']}_{p['prop']}_{p['game_time'][:10]}"
            if not any(x['id'] == pid for x in data['picks']):
                entry = p.copy()
                entry['id'] = pid
                entry['status'] = 'pending'
                entry['added_at'] = datetime.now().isoformat()
                data['picks'].append(entry)
                new_count += 1
        
        if new_count > 0:
            self.save_tracking_data(data)
            print(f"Tracked {new_count} new picks")
            
    def run(self):
        self.analyze()
