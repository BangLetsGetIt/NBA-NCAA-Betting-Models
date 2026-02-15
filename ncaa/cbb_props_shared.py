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

        /* Navigation */
        .nav-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 25px;
            overflow-x: auto;
            padding-bottom: 5px;
        }
        .nav-pill {
            padding: 8px 16px;
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
            white-space: nowrap;
        }
        .nav-pill:hover, .nav-pill.active {
            background-color: var(--bg-card-secondary);
            color: var(--text-primary);
            border-color: var(--text-primary);
        }

        /* Stats Row */
        .stats-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            background-color: var(--bg-main);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid var(--border-color);
        }
        .stat-item { text-align: center; }
        .stat-title {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: 2px;
            letter-spacing: 0.5px;
        }
        .stat-val { font-size: 15px; font-weight: 700; }

        /* Glow Effects */
        .glow-green {
            box-shadow: 0 0 15px rgba(74, 222, 128, 0.15);
            border: 1px solid rgba(74, 222, 128, 0.3);
        }
        .glow-blue {
            box-shadow: 0 0 15px rgba(96, 165, 250, 0.15);
            border: 1px solid rgba(96, 165, 250, 0.3);
        }

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
        # Combo props
        elif self.prop_type == 'pra':
            self.stat_col = ['PTS', 'TRB', 'AST']
            self.prop_unit = 'PRA'
            self.market_key = 'player_points_rebounds_assists'
        elif self.prop_type == 'points_rebounds':
            self.stat_col = ['PTS', 'TRB']
            self.prop_unit = 'P+R'
            self.market_key = 'player_points_rebounds'
        elif self.prop_type == 'points_assists':
            self.stat_col = ['PTS', 'AST']
            self.prop_unit = 'P+A'
            self.market_key = 'player_points_assists'
        elif self.prop_type == 'rebounds_assists':
            self.stat_col = ['TRB', 'AST']
            self.prop_unit = 'R+A'
            self.market_key = 'player_rebounds_assists'
        else: # points
            self.stat_col = 'PTS'
            self.prop_unit = 'PTS'
            self.market_key = 'player_points'

        # Combo props need wider edges due to higher variance
        self.is_combo = isinstance(self.stat_col, list)

        # Model Parameters - Adjusted for CBB (less data/predictability than NBA)
        self.min_ai_score = 7.5  # Moderate confidence for CBB
        self.min_edge_over = 1.2  # CBB needs lower edge threshold
        self.min_edge_under = 1.0  # CBB needs lower edge threshold
        self.min_recent_form_edge = 0.8  # Recent form support
        self.pause_unders = False  # UNDERs enabled for CBB - will track performance separately
        self.top_plays_count = 10
        self.recent_games_window = 5  # Use last 5 games for recent form (CBB has fewer games than NBA)

        # Combo props need wider edges due to higher variance
        if self.is_combo:
            self.min_edge_over = 2.0
            self.min_edge_under = 1.5
    
    def get_composite_stat(self, player_stats):
        """Get the relevant stat value, handling both single and combo props."""
        if self.is_combo:
            # Combo: sum individual stats (map SR column names to cache keys)
            col_map = {'PTS': 'pts', 'TRB': 'reb', 'AST': 'ast'}
            return sum(player_stats.get(col_map.get(col, col.lower()), 0) for col in self.stat_col)
        # Single stat
        if self.prop_type == 'points':
            return player_stats.get('pts', 0)
        return player_stats.get(self.prop_type[:3], 0)

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

    def calculate_clv_status(self, opening_odds, latest_odds):
        """
        Calculate if a pick beat the closing line (positive CLV).
        Better odds at open = positive CLV.
        """
        try:
            if opening_odds == latest_odds:
                return "neutral"
            if opening_odds < 0 and latest_odds < 0:
                return "positive" if opening_odds > latest_odds else "negative"
            elif opening_odds > 0 and latest_odds > 0:
                return "positive" if opening_odds > latest_odds else "negative"
            elif opening_odds > 0 and latest_odds < 0:
                return "positive"
            else:
                return "negative"
        except Exception:
            return "neutral"

    def fetch_boxscores_espn(self, date_str):
        """
        Fetch all CBB box scores for a given date from ESPN API (fast, reliable).
        Returns dict: lowercase player_name -> stat value
        Also returns set of team display names that played (for game-final detection).
        """
        print(f"  {Colors.CYAN}Fetching CBB box scores from ESPN for {date_str}...{Colors.END}")

        player_stats = {}
        completed_teams = set()

        try:
            espn_date = date_str.replace('-', '')  # YYYYMMDD
            scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={espn_date}&groups=50&limit=300"
            resp = requests.get(scoreboard_url, timeout=15)
            if resp.status_code != 200:
                print(f"    {Colors.RED}✗ ESPN scoreboard failed (Status {resp.status_code}){Colors.END}")
                return player_stats, completed_teams

            events = resp.json().get('events', [])
            completed_events = [e for e in events if e.get('status', {}).get('type', {}).get('completed', False)]

            if not completed_events:
                print(f"    {Colors.YELLOW}⚠ No completed games found on ESPN for {date_str}{Colors.END}")
                return player_stats, completed_teams

            print(f"    Found {len(completed_events)} completed games on ESPN")

            # Determine which stat columns to extract
            stat_labels_needed = []
            if self.is_combo:
                col_map = {'PTS': 'PTS', 'TRB': 'REB', 'AST': 'AST'}
                stat_labels_needed = [col_map.get(c, c) for c in self.stat_col]
            elif self.prop_type == 'points':
                stat_labels_needed = ['PTS']
            elif self.prop_type == 'rebounds':
                stat_labels_needed = ['REB']
            elif self.prop_type == 'assists':
                stat_labels_needed = ['AST']
            else:
                stat_labels_needed = ['PTS']

            for event in completed_events:
                game_id = event['id']
                try:
                    summary_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event={game_id}"
                    box_resp = requests.get(summary_url, timeout=15)
                    if box_resp.status_code != 200:
                        continue

                    box_data = box_resp.json()
                    teams_data = box_data.get('boxscore', {}).get('players', [])

                    for team_data in teams_data:
                        team_name = team_data.get('team', {}).get('displayName', '')
                        team_slug = team_name.lower().replace(' ', '-').replace('.', '').replace("'", '')
                        completed_teams.add(team_slug)
                        completed_teams.add(team_name)  # Also add display name for matching

                        for stat_group in team_data.get('statistics', []):
                            labels = stat_group.get('labels', [])
                            # Find indices for needed stats
                            indices = {}
                            for needed in stat_labels_needed:
                                if needed in labels:
                                    indices[needed] = labels.index(needed)

                            if not indices:
                                continue

                            for athlete in stat_group.get('athletes', []):
                                name = athlete.get('athlete', {}).get('displayName', '')
                                if not name:
                                    continue
                                stat_vals = athlete.get('stats', [])
                                try:
                                    total = sum(float(stat_vals[idx]) for idx in indices.values() if idx < len(stat_vals))
                                    player_stats[name.lower()] = total
                                except (ValueError, TypeError, IndexError):
                                    continue

                except Exception as e:
                    print(f"    {Colors.RED}✗ Error fetching ESPN game {game_id}: {e}{Colors.END}")
                    continue

            print(f"    {Colors.GREEN}✓ Found stats for {len(player_stats)} players across {len(completed_teams)} teams{Colors.END}")

        except Exception as e:
            print(f"    {Colors.RED}✗ ESPN error: {e}{Colors.END}")

        return player_stats, completed_teams

    def fetch_boxscores_for_date(self, date_str):
        """
        Fetch all CBB box scores for a given date from Sports-Reference (fallback).
        Returns dict: lowercase player_name -> {stat_col value, team}
        Also returns set of teams that played (for game-final detection).
        """
        print(f"  {Colors.CYAN}Fetching CBB box scores for {date_str}...{Colors.END}")

        dt = datetime.strptime(date_str, '%Y-%m-%d')
        url = f"https://www.sports-reference.com/cbb/boxscores/index.cgi?month={dt.month}&day={dt.day}&year={dt.year}"

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        player_stats = {}  # player_name_lower -> stat value
        completed_teams = set()

        try:
            time.sleep(4.5)
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"    {Colors.RED}✗ Failed to fetch scoreboard (Status {resp.status_code}){Colors.END}")
                return player_stats, completed_teams

            # Parse box score links from the scoreboard page
            boxscore_links = re.findall(r'/cbb/boxscores/(\d{4}-\d{2}-\d{2}-[^"]+)\.html', resp.text)

            if not boxscore_links:
                print(f"    {Colors.YELLOW}⚠ No box scores found for {date_str}{Colors.END}")
                return player_stats, completed_teams

            print(f"    Found {len(boxscore_links)} games")

            for box_id in boxscore_links:
                box_url = f"https://www.sports-reference.com/cbb/boxscores/{box_id}.html"
                try:
                    time.sleep(4.5)
                    box_resp = requests.get(box_url, headers=headers, timeout=15)
                    if box_resp.status_code == 429:
                        print(f"    {Colors.YELLOW}⚠ Rate limited. Waiting 90s...{Colors.END}")
                        time.sleep(90)
                        box_resp = requests.get(box_url, headers=headers, timeout=15)
                    if box_resp.status_code != 200:
                        continue

                    dfs = pd.read_html(StringIO(box_resp.text))
                    for df in dfs:
                        # Flatten MultiIndex columns
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = [c[-1] if isinstance(c, tuple) else str(c) for c in df.columns]

                        cols = [str(c) for c in df.columns]
                        if 'Starters' not in cols and 'Reserves' not in cols:
                            continue
                        # This is a box score table - has 'Starters' or player names in first col
                        # The column with player names could be 'Starters' or 'Reserves'
                        name_col = 'Starters' if 'Starters' in cols else 'Reserves' if 'Reserves' in cols else None
                        if not name_col:
                            continue

                        # Determine which columns to extract
                        stat_cols = self.stat_col if self.is_combo else [self.stat_col]
                        # Check all needed columns exist
                        if not all(col in cols for col in stat_cols):
                            continue

                        for _, row in df.iterrows():
                            p_name = str(row.get(name_col, '')).strip()
                            if not p_name or p_name in ('nan', 'Starters', 'Reserves', 'Team Totals', 'School Totals'):
                                continue
                            try:
                                stat_val = sum(float(row[col]) for col in stat_cols)
                                player_stats[p_name.lower()] = stat_val
                            except (ValueError, TypeError):
                                continue

                    # Extract team names from the box score page title or tables
                    # The box_id format is like "2026-02-10-north-carolina"
                    # But easier: find team names from the HTML
                    team_matches = re.findall(r'<a href="/cbb/schools/([^/]+)/men/', box_resp.text)
                    for tm in set(team_matches):
                        completed_teams.add(tm)  # These are slugs

                except Exception as e:
                    print(f"    {Colors.RED}✗ Error fetching box score {box_id}: {e}{Colors.END}")
                    continue

            print(f"    {Colors.GREEN}✓ Found stats for {len(player_stats)} players across {len(completed_teams)} teams{Colors.END}")

        except Exception as e:
            print(f"    {Colors.RED}✗ Error fetching scoreboard: {e}{Colors.END}")

        return player_stats, completed_teams

    def backfill_profit_loss(self):
        """Backfill profit_loss for graded picks that are missing it"""
        data = self.load_tracking_data()
        updated_count = 0

        for pick in data['picks']:
            if pick.get('status') in ['win', 'loss'] and 'profit_loss' not in pick:
                odds = pick.get('opening_odds') or pick.get('odds', -110)
                if pick.get('status') == 'win':
                    if odds > 0:
                        profit_loss = int(odds)
                    else:
                        profit_loss = int((100.0 / abs(odds)) * 100)
                else:
                    profit_loss = -100

                pick['profit_loss'] = profit_loss
                pick['profit_loss_backfilled'] = True
                updated_count += 1

        if updated_count > 0:
            self.save_tracking_data(data)
            print(f"{Colors.GREEN}✓ Backfilled profit_loss for {updated_count} picks{Colors.END}")

        return updated_count

    def calculate_tracking_stats(self, tracking_data):
        """Calculate performance statistics from tracking data"""
        completed_picks = [p for p in tracking_data['picks'] if p.get('status') in ['win', 'loss']]

        # Deduplicate picks by player + date + bet_type (keep most recent)
        unique_picks_map = {}
        def get_sort_key(p):
            return p.get('updated_at') or p.get('added_at') or p.get('tracked_at') or "0"

        sorted_picks = sorted(completed_picks, key=get_sort_key)

        for p in sorted_picks:
            player = p.get('player')
            bet_type = p.get('bet_type', '')
            gt_str = p.get('game_time', '')
            if not gt_str:
                continue
            try:
                dt_str = gt_str.split('T')[0]
            except:
                continue
            key = f"{player}_{dt_str}_{bet_type}"
            unique_picks_map[key] = p

        completed_picks = list(unique_picks_map.values())

        if not completed_picks:
            return {
                'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0,
                'total_profit': 0.0, 'roi': 0.0, 'roi_pct': 0.0,
                'over_record': '0-0', 'over_win_rate': 0.0, 'over_roi': 0.0,
                'under_record': '0-0', 'under_win_rate': 0.0, 'under_roi': 0.0
            }

        wins = [p for p in completed_picks if p.get('status') == 'win']
        losses = [p for p in completed_picks if p.get('status') == 'loss']
        total = len(completed_picks)

        total_profit = sum(p.get('profit_loss', 0) for p in completed_picks)
        roi = (total_profit / (total * 100)) * 100 if total > 0 else 0.0

        # Over/Under breakdown
        over_picks = [p for p in completed_picks if p.get('bet_type') == 'over']
        under_picks = [p for p in completed_picks if p.get('bet_type') == 'under']

        over_wins = len([p for p in over_picks if p.get('status') == 'win'])
        over_losses = len([p for p in over_picks if p.get('status') == 'loss'])
        over_profit = sum(p.get('profit_loss', 0) for p in over_picks)
        over_total = len(over_picks)

        under_wins = len([p for p in under_picks if p.get('status') == 'win'])
        under_losses = len([p for p in under_picks if p.get('status') == 'loss'])
        under_profit = sum(p.get('profit_loss', 0) for p in under_picks)
        under_total = len(under_picks)

        # --- DAILY PERFORMANCE TRACKING ---
        et_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(et_tz)
        today_str = now_et.strftime('%Y-%m-%d')
        yesterday_str = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')

        def calc_daily_stats(target_date_str):
            daily_picks = []
            for p in completed_picks:
                gt_str = p.get('game_time', '')
                if not gt_str:
                    continue
                try:
                    dt_utc = datetime.fromisoformat(gt_str.replace('Z', '+00:00'))
                    dt_et = dt_utc.astimezone(et_tz)
                    if dt_et.strftime('%Y-%m-%d') == target_date_str:
                        daily_picks.append(p)
                except:
                    continue
            d_wins = sum(1 for p in daily_picks if p.get('status') == 'win')
            d_losses = sum(1 for p in daily_picks if p.get('status') == 'loss')
            d_total = d_wins + d_losses
            d_profit_cents = sum(p.get('profit_loss', 0) for p in daily_picks)
            d_profit = d_profit_cents / 100.0
            d_roi = (d_profit / d_total * 100) if d_total > 0 else 0.0
            return {'record': f"{d_wins}-{d_losses}", 'profit': d_profit, 'roi': d_roi, 'count': d_total}

        today_stats = calc_daily_stats(today_str)
        yesterday_stats = calc_daily_stats(yesterday_str)

        # --- LAST N PICKS PERFORMANCE ---
        def calc_last_n(n):
            # Sort by game_time descending to get most recent
            sorted_by_time = sorted(completed_picks, key=lambda p: p.get('game_time', ''), reverse=True)
            recent = sorted_by_time[:n]
            r_wins = sum(1 for p in recent if p.get('status') == 'win')
            r_losses = sum(1 for p in recent if p.get('status') == 'loss')
            r_total = r_wins + r_losses
            r_profit_cents = sum(p.get('profit_loss', 0) for p in recent)
            r_profit = r_profit_cents / 100.0
            r_roi = (r_profit / r_total * 100) if r_total > 0 else 0.0
            r_wr = (r_wins / r_total * 100) if r_total > 0 else 0.0
            return {'record': f"{r_wins}-{r_losses}", 'win_rate': r_wr, 'profit': r_profit, 'roi': r_roi}

        last_10 = calc_last_n(10)
        last_20 = calc_last_n(20)
        last_50 = calc_last_n(50)

        return {
            'total': total,
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': (len(wins) / total * 100) if total > 0 else 0.0,
            'total_profit': total_profit / 100.0,
            'roi': roi,
            'roi_pct': roi,
            'over_record': f"{over_wins}-{over_losses}",
            'over_win_rate': (over_wins / over_total * 100) if over_total > 0 else 0.0,
            'over_roi': (over_profit / (over_total * 100)) * 100 if over_total > 0 else 0.0,
            'under_record': f"{under_wins}-{under_losses}",
            'under_win_rate': (under_wins / under_total * 100) if under_total > 0 else 0.0,
            'under_roi': (under_profit / (under_total * 100)) * 100 if under_total > 0 else 0.0,
            'today': today_stats,
            'yesterday': yesterday_stats,
            'last_10': last_10,
            'last_20': last_20,
            'last_50': last_50
        }

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
        """Fetch player props odds using centralized caching client."""
        print(f"\n{Colors.CYAN}Fetching {self.prop_type} props via centralized cache...{Colors.END}")

        # Import CBB Odds Client
        try:
            from cbb_api_client import CBBOddsClient
        except ImportError:
            import sys
            sys.path.append(os.path.dirname(__file__))
            from cbb_api_client import CBBOddsClient

        client = CBBOddsClient()
        # Fetch ALL markets so we populate cache for other models in one go
        games_data = client.get_odds_data()

        all_props = []
        teams_playing = set()

        for game in games_data:
            home_team = game['home_team']
            away_team = game['away_team']
            commence_time = game['commence_time']
            teams_playing.add(home_team)
            teams_playing.add(away_team)

            bookmakers = game.get('bookmakers', [])
            if not bookmakers:
                continue

            # Prioritize Hard Rock Bet, then FanDuel, then first available
            selected_book = next((b for b in bookmakers if b.get("key") == "hardrockbet"),
                               next((b for b in bookmakers if b.get("key") == "fanduel"),
                                    bookmakers[0]))

            for market in selected_book.get("markets", []):
                if market.get("key") == self.market_key:
                    # Process outcomes
                    grouped = {}  # (player, line) -> {over, under}

                    for outcome in market['outcomes']:
                        player_name = outcome['description']
                        bet_type = outcome['name'].lower()  # over/under
                        price = outcome['price']
                        point = outcome['point']

                        key = (player_name, point)
                        if key not in grouped:
                            grouped[key] = {
                                'player': player_name,
                                'line': point,
                                'over': None,
                                'under': None,
                                'home_team': home_team,
                                'away_team': away_team,
                                'game_time': commence_time
                            }

                        if bet_type == 'over':
                            grouped[key]['over'] = price
                        else:
                            grouped[key]['under'] = price

                    all_props.extend(grouped.values())

        print(f"{Colors.GREEN}✓ Fetched {len(all_props)} total {self.prop_type} props{Colors.END}")
        return all_props, list(teams_playing)

    def calculate_ev(self, ai_score, prop_line, season_avg, odds, bet_type):
        """
        Calculate Expected Value based on AI score and player stats
        Adapted from NBA model for CBB
        """
        # Convert American odds to implied probability
        if odds > 0:
            implied_prob = 100 / (odds + 100)
        else:
            implied_prob = abs(odds) / (abs(odds) + 100)

        # Calculate true probability from AI score and stats
        base_prob = 0.50
        ai_multiplier = max(0, (ai_score - 9.0) / 1.0)  # Scale from 9.0-10.0

        # Edge factor
        if bet_type == 'over':
            edge = season_avg - prop_line
        else:
            edge = prop_line - season_avg

        edge_factor = min(abs(edge) / 2.5, 1.0)  # Slightly adjusted for CBB

        true_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15)
        true_prob = min(max(true_prob, 0.40), 0.70)  # Cap between 40-70%

        # Calculate EV
        if odds > 0:
            ev = (true_prob * (odds / 100)) - (1 - true_prob)
        else:
            ev = (true_prob * (100 / abs(odds))) - (1 - true_prob)

        return ev * 100, true_prob * 100  # Return EV% and win-prob%

    def calculate_ai_score(self, player_stats, line, bet_type):
        """
        Calculate STRICT A.I. Score for CBB props using real stats
        Adapted from NBA model with CBB-specific adjustments
        """
        score = 4.0

        stat_avg = self.get_composite_stat(player_stats)

        games_played = player_stats.get('games', 0)
        minutes = player_stats.get('min', 0)
        fg_pct = player_stats.get('fg_pct', 0)

        # Minimum requirements
        if games_played < 3:  # Need at least 3 games
            return 0.0

        if minutes < 12:  # Need significant playing time
            return 0.0

        if bet_type == 'over':
            edge_above_line = stat_avg - line

            # Edge requirements (strict)
            if edge_above_line >= self.min_edge_over:
                score += 3.5
            elif edge_above_line >= 1.5:
                score += 2.5
            elif edge_above_line >= 1.0:
                score += 1.5
            elif edge_above_line >= 0.5:
                score += 0.5
            else:
                score -= 2.0
                return 0.0  # Fail if no edge

            # Minutes bonus (more minutes = more opportunity)
            if minutes >= 30:
                score += 1.5
            elif minutes >= 25:
                score += 1.0
            elif minutes >= 20:
                score += 0.5

            # Shooting efficiency bonus (for single-stat points only)
            if self.prop_type == 'points' and not self.is_combo:
                if fg_pct >= 0.50:
                    score += 1.0
                elif fg_pct >= 0.45:
                    score += 0.5

        else:  # under
            edge_below_line = line - stat_avg

            # Edge requirements
            if edge_below_line >= self.min_edge_under:
                score += 3.5
            elif edge_below_line >= 1.2:
                score += 2.5
            elif edge_below_line >= 0.8:
                score += 1.5
            elif edge_below_line >= 0.4:
                score += 0.5
            else:
                score -= 2.0
                return 0.0

            # Low minutes bonus (less playing time = easier UNDER)
            if minutes < 20:
                score += 1.5
            elif minutes < 25:
                score += 1.0

        final_score = min(10.0, max(0.0, score))
        return final_score

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
                
            # Get specific stat (handles single and combo props)
            val = self.get_composite_stat(p_stats)
            
            line = p['line']
            
            # Calc Score and EV
            # OVER
            if p['over']:
                score = self.calculate_ai_score(p_stats, line, 'over')
                if score >= self.min_ai_score:
                    ev, win_prob = self.calculate_ev(score, line, val, p['over'], 'over')
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
                        'ev': ev,
                        'win_prob': win_prob,
                        'prop_line': line
                    }
                    over_plays.append(obj)

            # UNDER (only if not paused)
            if p['under'] and not self.pause_unders:
                score = self.calculate_ai_score(p_stats, line, 'under')
                if score >= self.min_ai_score:
                    ev, win_prob = self.calculate_ev(score, line, val, p['under'], 'under')
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
                        'ev': ev,
                        'win_prob': win_prob,
                        'prop_line': line
                    }
                    under_plays.append(obj)
                    
        # Sort
        over_plays.sort(key=lambda x: x['ai_score'], reverse=True)
        under_plays.sort(key=lambda x: x['ai_score'], reverse=True)
        
        # Top Plays
        over_plays = over_plays[:self.top_plays_count]
        under_plays = under_plays[:self.top_plays_count]
        
        # 4. Generate HTML (with tracking stats)
        tracking_data = self.load_tracking_data()
        stats = self.calculate_tracking_stats(tracking_data)
        self.generate_html(over_plays, under_plays, stats)

        # 5. Track
        self.track_picks(over_plays + under_plays)

    def generate_html(self, over_plays, under_plays, stats=None):
        css = get_shared_css()
        et_tz = pytz.timezone('US/Eastern')

        if stats is None:
            stats = {'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0,
                     'total_profit': 0.0, 'roi': 0.0, 'roi_pct': 0.0,
                     'over_record': '0-0', 'over_win_rate': 0.0, 'over_roi': 0.0,
                     'under_record': '0-0', 'under_win_rate': 0.0, 'under_roi': 0.0,
                     'today': {'record': '0-0', 'profit': 0, 'roi': 0, 'count': 0},
                     'yesterday': {'record': '0-0', 'profit': 0, 'roi': 0, 'count': 0},
                     'last_10': {'record': '0-0', 'win_rate': 0, 'profit': 0, 'roi': 0},
                     'last_20': {'record': '0-0', 'win_rate': 0, 'profit': 0, 'roi': 0},
                     'last_50': {'record': '0-0', 'win_rate': 0, 'profit': 0, 'roi': 0}}

        # --- Header with season record ---
        s_wins = stats.get('wins', 0)
        s_losses = stats.get('losses', 0)
        s_wr = round(stats.get('win_rate', 0.0), 1)
        s_prof = stats.get('total_profit', 0.0)
        s_prof_str = f"{s_prof:+.1f}u"
        s_prof_color = 'var(--accent-green)' if s_prof >= 0 else 'var(--accent-red)'

        # Nav pill active class
        nav_points = ' active' if self.prop_type == 'points' else ''
        nav_assists = ' active' if self.prop_type == 'assists' else ''
        nav_rebounds = ' active' if self.prop_type == 'rebounds' else ''
        nav_pra = ' active' if self.prop_type == 'pra' else ''
        nav_pr = ' active' if self.prop_type == 'points_rebounds' else ''
        nav_pa = ' active' if self.prop_type == 'points_assists' else ''
        nav_ra = ' active' if self.prop_type == 'rebounds_assists' else ''

        # --- Build prop cards ---
        def format_odds(odds_value):
            if odds_value is None:
                return 'N/A'
            try:
                odds = int(odds_value)
                return f'+{odds}' if odds > 0 else str(odds)
            except:
                return str(odds_value) if odds_value else 'N/A'

        def format_game_time(game_time_str):
            try:
                dt_utc = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
                dt_et = dt_utc.astimezone(et_tz)
                return dt_et.strftime('%b %d %I:%M%p ET')
            except:
                return game_time_str

        def build_cards(plays, label, color_class):
            html = ""
            for p in plays:
                game_dt = format_game_time(p.get('game_time', ''))
                ev = p.get('ev', 0)
                ev_display = f"{ev:+.1f}%" if ev != 0 else "0.0%"
                ev_color = "txt-green" if ev > 0 else "txt-red" if ev < 0 else ""

                glow_class = ""
                if p.get('ai_score', 0) >= 10.0:
                    glow_class = "glow-green"
                elif p.get('ai_score', 0) >= 9.0:
                    glow_class = "glow-blue"

                edge = p.get('edge', 0)
                season_avg = p.get('season_avg', 0)
                if label == 'OVER':
                    model_pred = season_avg + edge if edge > 0 else season_avg - abs(edge)
                else:
                    model_pred = season_avg - abs(edge)

                html += f"""
                <div class="prop-card {glow_class}">
                    <div class="card-header">
                        <div class="header-left">
                            <div class="player-info">
                                <h2>{p['player']}</h2>
                                <div class="matchup-info">{p['opponent']} @ {p['team']}</div>
                            </div>
                        </div>
                        <div class="game-meta">
                            <div class="game-date-time">{game_dt}</div>
                        </div>
                    </div>
                    <div class="card-body">
                        <div class="bet-main-row">
                            <div class="bet-selection">
                                <span class="{color_class}">{label}</span>
                                <span class="line">{p['prop'].split(' ')[1]} {self.prop_unit}</span>
                                <span class="bet-odds">{format_odds(p.get('odds'))}</span>
                            </div>
                        </div>
                        <div class="model-subtext">
                            Model Predicts: <strong>{model_pred:.1f} {self.prop_unit}</strong> (Edge: {edge:+.1f})
                        </div>
                        <div class="metrics-grid">
                            <div class="metric-item">
                                <span class="metric-lbl">AI SCORE</span>
                                <span class="metric-val txt-green">{p['ai_score']:.1f}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-lbl">EV</span>
                                <span class="metric-val {ev_color}">{ev_display}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-lbl">AVG</span>
                                <span class="metric-val">{season_avg:.1f}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-lbl">EDGE</span>
                                <span class="metric-val">{edge:+.1f}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-lbl">WIN PROB</span>
                                <span class="metric-val">{p.get('win_prob', 50):.0f}%</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
            return html

        over_html = build_cards(over_plays, "OVER", "txt-green")
        under_html = build_cards(under_plays, "UNDER", "txt-red")

        # --- Daily Performance (Today / Yesterday) ---
        t_stats = stats.get('today', {'record': '0-0', 'profit': 0, 'roi': 0})
        y_stats = stats.get('yesterday', {'record': '0-0', 'profit': 0, 'roi': 0})
        t_profit_class = "txt-green" if t_stats['profit'] > 0 else ("txt-red" if t_stats['profit'] < 0 else "")
        y_profit_class = "txt-green" if y_stats['profit'] > 0 else ("txt-red" if y_stats['profit'] < 0 else "")

        daily_html = f"""
        <section style="margin-top: 2rem;">
            <div class="section-title">Daily Performance</div>
            <div class="metrics-grid" style="grid-template-columns: repeat(2, 1fr);">
                <div class="prop-card" style="padding: 1rem; margin:0;">
                    <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">TODAY</div>
                    <div style="text-align:center;">
                        <div style="font-weight:700; font-size:1.1rem;">{t_stats['record']}</div>
                        <div class="{t_profit_class}">{t_stats['profit']:+.1f}u</div>
                        <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">{t_stats['roi']:.1f}% ROI</div>
                    </div>
                </div>
                <div class="prop-card" style="padding: 1rem; margin:0;">
                    <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">YESTERDAY</div>
                    <div style="text-align:center;">
                        <div style="font-weight:700; font-size:1.1rem;">{y_stats['record']}</div>
                        <div class="{y_profit_class}">{y_stats['profit']:+.1f}u</div>
                        <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">{y_stats['roi']:.1f}% ROI</div>
                    </div>
                </div>
            </div>
        </section>
        """

        # --- Recent Form (Last 10 / 20 / 50) ---
        l10 = stats.get('last_10', {'record': '0-0', 'win_rate': 0, 'profit': 0, 'roi': 0})
        l20 = stats.get('last_20', {'record': '0-0', 'win_rate': 0, 'profit': 0, 'roi': 0})
        l50 = stats.get('last_50', {'record': '0-0', 'win_rate': 0, 'profit': 0, 'roi': 0})

        def wr_class(wr): return 'good' if wr >= 55 else ('text-red' if wr < 50 else '')
        def prf_class(p): return 'good' if p > 0 else ('text-red' if p < 0 else '')

        recent_form_html = f"""
        <div class="tracking-section">
            <div class="tracking-header">Recent Form</div>
            <div class="metrics-row" style="margin-bottom: 1.5rem;">
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 10</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div><div class="metric-label">Record</div><div class="metric-value">{l10['record']}</div></div>
                        <div><div class="metric-label">Win Rate</div><div class="metric-value {wr_class(l10['win_rate'])}">{round(l10['win_rate'])}%</div></div>
                        <div><div class="metric-label">Profit</div><div class="metric-value {prf_class(l10['profit'])}">{l10['profit']:+.1f}u</div></div>
                        <div><div class="metric-label">ROI</div><div class="metric-value {prf_class(l10['roi'])}">{l10['roi']:+.1f}%</div></div>
                    </div>
                </div>
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 20</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div><div class="metric-label">Record</div><div class="metric-value">{l20['record']}</div></div>
                        <div><div class="metric-label">Win Rate</div><div class="metric-value {wr_class(l20['win_rate'])}">{round(l20['win_rate'])}%</div></div>
                        <div><div class="metric-label">Profit</div><div class="metric-value {prf_class(l20['profit'])}">{l20['profit']:+.1f}u</div></div>
                        <div><div class="metric-label">ROI</div><div class="metric-value {prf_class(l20['roi'])}">{l20['roi']:+.1f}%</div></div>
                    </div>
                </div>
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 50</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div><div class="metric-label">Record</div><div class="metric-value">{l50['record']}</div></div>
                        <div><div class="metric-label">Win Rate</div><div class="metric-value {wr_class(l50['win_rate'])}">{round(l50['win_rate'])}%</div></div>
                        <div><div class="metric-label">Profit</div><div class="metric-value {prf_class(l50['profit'])}">{l50['profit']:+.1f}u</div></div>
                        <div><div class="metric-label">ROI</div><div class="metric-value {prf_class(l50['roi'])}">{l50['roi']:+.1f}%</div></div>
                    </div>
                </div>
            </div>
        </div>
        """

        # --- Over/Under Performance Breakdown ---
        over_record = stats.get('over_record', '0-0')
        over_wr = stats.get('over_win_rate', 0)
        over_roi = stats.get('over_roi', 0)
        under_record = stats.get('under_record', '0-0')
        under_wr = stats.get('under_win_rate', 0)
        under_roi = stats.get('under_roi', 0)
        over_roi_class = "txt-green" if over_roi > 0 else "txt-red"
        under_roi_class = "txt-green" if under_roi > 0 else "txt-red"
        roi_pct = stats.get('roi', 0)
        roi_class = "txt-green" if roi_pct > 0 else "txt-red"
        roi_sign = '+' if roi_pct > 0 else ''
        over_roi_sign = '+' if over_roi > 0 else ''
        under_roi_sign = '+' if under_roi > 0 else ''

        performance_html = ""
        if stats.get('total', 0) > 0:
            performance_html = f"""
        <section>
            <div class="section-title">CBB {self.prop_type.capitalize()} Model Performance</div>
            <div class="summary-grid">
                <div class="stat-box">
                    <div class="stat-label">Overall Record</div>
                    <div class="stat-value">{s_wins}-{s_losses}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">ROI</div>
                    <div class="stat-value {roi_class}">{roi_sign}{roi_pct:.1f}%</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">OVER: {over_record}</div>
                    <div class="stat-value {over_roi_class}">{over_roi_sign}{over_roi:.1f}% ROI</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">UNDER: {under_record}</div>
                    <div class="stat-value {under_roi_class}">{under_roi_sign}{under_roi:.1f}% ROI</div>
                </div>
            </div>
        </section>
            """

        # --- Assemble Full HTML ---
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
            <div class="date-sub">Season {CURRENT_SEASON} &bull; {'UNDERs Paused' if self.pause_unders else 'All Bets Active'}</div>
        </div>
        <div style="text-align: right;">
            <div class="metric-title">SEASON RECORD</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                {s_wins}-{s_losses} ({s_wr}%)
            </div>
            <div style="font-size: 0.9rem; color: {s_prof_color};">
                {s_prof_str}
            </div>
        </div>
    </header>

    <div class="nav-bar">
        <a href="cbb_points_props.html" class="nav-pill{nav_points}">Points</a>
        <a href="cbb_assists_props.html" class="nav-pill{nav_assists}">Assists</a>
        <a href="cbb_rebounds_props.html" class="nav-pill{nav_rebounds}">Rebounds</a>
        <a href="cbb_pra_props.html" class="nav-pill{nav_pra}">PRA</a>
        <a href="cbb_points_rebounds_props.html" class="nav-pill{nav_pr}">P+R</a>
        <a href="cbb_points_assists_props.html" class="nav-pill{nav_pa}">P+A</a>
        <a href="cbb_rebounds_assists_props.html" class="nav-pill{nav_ra}">R+A</a>
    </div>

    <section>
        <div class="section-title">Top OVER Plays</div>
        {over_html}
    </section>

    <section>
        <div class="section-title">Top UNDER Plays</div>
        {under_html}
    </section>

    {daily_html}
    {recent_form_html}
    {performance_html}
</div>
</body>
</html>
"""
        with open(self.output_html, 'w') as f:
            f.write(full_html)
        print(f"Saved HTML to {self.output_html}")

    def track_picks(self, picks):
        """Track new picks with full NBA-style tracking (bet_type, CLV, odds updates)"""
        data = self.load_tracking_data()

        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.CYAN}📊 TRACKING NEW {self.prop_type.upper()} PICKS{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")

        new_count = 0
        updated_count = 0

        for p in picks:
            prop_str = p.get('prop', '')
            bet_type = 'over' if 'OVER' in prop_str else 'under'

            # Skip UNDER bets if paused
            if bet_type == 'under' and self.pause_unders:
                continue

            prop_line = p.get('prop_line', 0)
            game_time = p.get('game_time', '')

            # Generate pick ID matching NBA format
            pick_id = f"{p['player']}_{prop_line}_{bet_type}_{game_time}"

            # Check if pick already exists (same player + date + bet_type)
            existing_pick = None
            for ep in data['picks']:
                if ep.get('player') == p['player'] and \
                   ep.get('bet_type') == bet_type and \
                   ep.get('game_time') == game_time:
                    existing_pick = ep
                    break

            if not existing_pick:
                existing_pick = next((ep for ep in data['picks'] if ep.get('pick_id') == pick_id), None)

            if existing_pick:
                # Update latest odds if different
                if existing_pick.get('latest_odds') != p.get('odds'):
                    existing_pick['latest_odds'] = p.get('odds')
                    existing_pick['updated_at'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
                    existing_pick['clv_status'] = self.calculate_clv_status(
                        existing_pick.get('opening_odds', p.get('odds')),
                        p.get('odds')
                    )
                    updated_count += 1
            else:
                # Add new pick
                new_pick = {
                    'pick_id': pick_id,
                    'player': p['player'],
                    'prop_line': prop_line,
                    'bet_type': bet_type,
                    'team': p.get('team'),
                    'opponent': p.get('opponent'),
                    'ai_score': p.get('ai_score'),
                    'odds': p.get('odds'),
                    'opening_odds': p.get('odds'),
                    'latest_odds': p.get('odds'),
                    'game_time': game_time,
                    'season_avg': p.get('season_avg'),
                    'edge': p.get('edge'),
                    'ev': p.get('ev'),
                    'win_prob': p.get('win_prob'),
                    'tracked_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
                    'status': 'pending',
                    'result': None,
                    f'actual_{self.prop_unit.lower()}': None,
                    'profit_loss': None,
                    'clv_status': None
                }
                data['picks'].append(new_pick)
                new_count += 1

        self.save_tracking_data(data)

        if new_count > 0:
            print(f"{Colors.GREEN}✓ Tracked {new_count} new picks{Colors.END}")
        if updated_count > 0:
            print(f"{Colors.YELLOW}✓ Updated odds for {updated_count} existing picks{Colors.END}")
        if new_count == 0 and updated_count == 0:
            print(f"{Colors.CYAN}No new picks to track{Colors.END}")

    def grade_pending_picks(self):
        """Grade pending picks by fetching actual game results from Sports-Reference box scores"""
        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.CYAN}🎯 GRADING PENDING CBB {self.prop_type.upper()} PICKS{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")

        data = self.load_tracking_data()
        pending_picks = [p for p in data['picks'] if p.get('status') == 'pending']

        if not pending_picks:
            print(f"{Colors.GREEN}✓ No pending picks to grade{Colors.END}")
            return 0

        print(f"{Colors.YELLOW}📋 Found {len(pending_picks)} pending picks...{Colors.END}\n")

        graded_count = 0
        et_tz = pytz.timezone('US/Eastern')

        # Group picks by date to minimize API calls (batch like NBA model)
        picks_by_date = defaultdict(list)
        for pick in pending_picks:
            game_time_str = pick.get('game_time', '')
            if not game_time_str:
                continue
            try:
                game_time_utc = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
                current_time = datetime.now(pytz.UTC)
                hours_since_game = (current_time - game_time_utc).total_seconds() / 3600

                # Only grade games that started at least 3 hours ago (CBB games ~2hrs)
                if hours_since_game >= 3:
                    game_date = game_time_utc.astimezone(et_tz).strftime('%Y-%m-%d')
                    picks_by_date[game_date].append(pick)
            except:
                continue

        # Process each date
        for date_str, picks in picks_by_date.items():
            print(f"\n{Colors.CYAN}Processing {len(picks)} picks for {date_str}...{Colors.END}")

            # Batch fetch stats for this date - try ESPN first (fast), fall back to SR
            daily_stats, completed_team_slugs = self.fetch_boxscores_espn(date_str)

            if not daily_stats:
                print(f"  {Colors.YELLOW}ESPN had no stats, trying Sports-Reference...{Colors.END}")
                daily_stats, completed_team_slugs = self.fetch_boxscores_for_date(date_str)

            if not daily_stats:
                print(f"{Colors.YELLOW}  ⚠ No stats found for {date_str} yet{Colors.END}")
                continue

            for pick in picks:
                try:
                    player_name = pick.get('player', '')
                    team_name = pick.get('team', '')
                    team_slug = self.get_team_slug(team_name)

                    # Check if game is final (team slug or name found in completed teams)
                    is_game_final = (team_slug in completed_team_slugs or
                                     team_name in completed_team_slugs or
                                     team_name.lower() in {t.lower() for t in completed_team_slugs})

                    # Try to find player stats - exact match first
                    player_key = player_name.lower()
                    actual_stat = daily_stats.get(player_key)

                    if actual_stat is None:
                        # Fuzzy match: first + last name
                        name_parts = player_key.split()
                        if len(name_parts) >= 2:
                            for p_name, stat_val in daily_stats.items():
                                p_parts = p_name.split()
                                if len(p_parts) >= 2:
                                    if name_parts[0] == p_parts[0] and name_parts[-1] == p_parts[-1]:
                                        actual_stat = stat_val
                                        break

                    if actual_stat is None:
                        # Last name only match (fallback)
                        last_name = player_key.split()[-1] if player_key.split() else ''
                        for p_name, stat_val in daily_stats.items():
                            if last_name and p_name.split()[-1] == last_name:
                                # Verify it's likely the right player by checking first initial
                                if player_key[0] == p_name[0]:
                                    actual_stat = stat_val
                                    break

                    if actual_stat is None:
                        if is_game_final:
                            print(f"  {Colors.YELLOW}⚠ {player_name} has no stats but game is final -> DNP/Void{Colors.END}")
                            pick['status'] = 'void'
                            pick['result'] = 'DNP'
                            pick['profit_loss'] = 0
                            pick['updated_at'] = datetime.now(et_tz).isoformat()
                            graded_count += 1
                        continue

                    # We have the actual stat - determine result
                    prop_line = pick.get('prop_line', 0)
                    # Determine bet_type from pick or parse from prop string
                    bet_type = pick.get('bet_type', '')
                    if not bet_type:
                        prop_str = pick.get('prop', '')
                        bet_type = 'over' if 'OVER' in prop_str else 'under'

                    # Check if result is determined
                    is_determined = False
                    if is_game_final:
                        is_determined = True
                    elif bet_type == 'over' and actual_stat > prop_line:
                        is_determined = True  # Early win
                    elif bet_type == 'under' and actual_stat > prop_line:
                        is_determined = True  # Early loss

                    if not is_determined:
                        continue

                    # Grade the pick
                    if bet_type == 'over':
                        is_win = actual_stat > prop_line
                    else:
                        is_win = actual_stat < prop_line

                    # Calculate profit/loss using opening odds
                    odds = pick.get('opening_odds') or pick.get('odds', -110)
                    if is_win:
                        if odds > 0:
                            profit_loss = int(odds)
                        else:
                            profit_loss = int((100.0 / abs(odds)) * 100)
                        status = 'win'
                        result = 'WIN'
                        result_color = Colors.GREEN
                    else:
                        profit_loss = -100
                        status = 'loss'
                        result = 'LOSS'
                        result_color = Colors.RED

                    # Update pick
                    pick['status'] = status
                    pick['result'] = result
                    pick['bet_type'] = bet_type
                    pick[f'actual_{self.prop_unit.lower()}'] = actual_stat
                    pick['profit_loss'] = profit_loss
                    pick['updated_at'] = datetime.now(et_tz).isoformat()

                    print(f"    {result_color}{result}{Colors.END}: {player_name} had {actual_stat} {self.prop_unit} (line: {prop_line}, bet: {bet_type.upper()}) | Profit: {profit_loss/100.0:+.2f}u")
                    graded_count += 1

                except Exception as e:
                    print(f"  {Colors.RED}✗ Error grading {pick.get('player')}: {e}{Colors.END}")
                    continue

        if graded_count > 0:
            self.save_tracking_data(data)
            print(f"\n{Colors.GREEN}✓ Graded {graded_count} picks{Colors.END}")
        else:
            print(f"\n{Colors.YELLOW}No picks ready for grading yet{Colors.END}")

        return graded_count

    def run(self):
        """Run the model: grade pending picks, backfill, analyze new props, generate HTML"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}CBB {self.prop_type.upper()} PROPS A.I. MODEL{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")

        # 1. Grade pending picks first
        self.grade_pending_picks()

        # 2. Backfill any missing profit_loss on previously graded picks
        self.backfill_profit_loss()

        # 3. Print tracking stats summary
        tracking_data = self.load_tracking_data()
        stats = self.calculate_tracking_stats(tracking_data)
        if stats['total'] > 0:
            print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
            print(f"{Colors.CYAN}📈 {self.prop_type.upper()} TRACKING SUMMARY{Colors.END}")
            print(f"{Colors.CYAN}{'='*70}{Colors.END}")
            print(f"  Record: {stats['wins']}-{stats['losses']} ({stats['win_rate']:.1f}%)")
            print(f"  Profit: {stats['total_profit']:+.2f}u | ROI: {stats['roi']:+.1f}%")
            print(f"  OVER:  {stats['over_record']} ({stats['over_win_rate']:.1f}%) | ROI: {stats['over_roi']:+.1f}%")
            print(f"  UNDER: {stats['under_record']} ({stats['under_win_rate']:.1f}%) | ROI: {stats['under_roi']:+.1f}%")
            print()

        # 4. Analyze new props
        self.analyze()
