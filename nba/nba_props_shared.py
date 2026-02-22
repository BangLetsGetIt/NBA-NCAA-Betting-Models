#!/usr/bin/env python3
"""NBA Props Shared Engine - Unified engine for all NBA player prop types.

Supports: points, assists, rebounds, threes, pra, points_rebounds, points_assists, rebounds_assists
Each prop type is a 5-line wrapper that calls NBAPropsEngine(prop_type).run()
"""

import json
import os
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import pytz
import requests
from dotenv import load_dotenv

from nba_api.stats.endpoints import leaguedashplayerstats, leaguedashteamstats
from nba_api.stats.static import players
import pandas as pd  # noqa: F401

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(os.path.dirname(SCRIPT_DIR), '.env')
load_dotenv(dotenv_path)

# ── ESPN grading cache ────────────────────────────────────────────────────────
# Maps date_str -> (player_stats_dict, completed_teams_set)
# player_stats_dict: {player_name_lower: {'PTS': x, 'REB': x, 'AST': x, 'FG3M': x}}
_ESPN_DATE_CACHE: dict = {}

# ESPN stat name → internal column name
_ESPN_STAT_MAP = {
    'PTS': 'PTS',
    'REB': 'REB',
    'AST': 'AST',
    '3PT': 'FG3M',   # ESPN format is "made-attempted" e.g. "3-8"
}

def _fetch_espn_date_data(date_str: str):
    """Fetch scoreboard + box scores from ESPN for a date (no API key needed).
    Returns (player_stats, completed_teams) from cache if already fetched.
    player_stats: {player_name_lower: {'PTS': x, 'REB': x, 'AST': x, 'FG3M': x}}
    completed_teams: set of full team display names e.g. {'Charlotte Hornets', ...}
    """
    if date_str in _ESPN_DATE_CACHE:
        return _ESPN_DATE_CACHE[date_str]

    date_compact = date_str.replace('-', '')  # YYYYMMDD
    player_stats: dict = {}
    completed_teams: set = set()

    try:
        sb_url = (
            f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
            f"/scoreboard?dates={date_compact}"
        )
        sb_resp = requests.get(sb_url, timeout=15)
        sb_resp.raise_for_status()
        sb_data = sb_resp.json()

        game_ids = []
        for event in sb_data.get('events', []):
            is_completed = event.get('status', {}).get('type', {}).get('completed', False)
            competition = event.get('competitions', [{}])[0]
            for competitor in competition.get('competitors', []):
                team_name = competitor.get('team', {}).get('displayName', '')
                if is_completed and team_name:
                    completed_teams.add(team_name)
            if is_completed:
                game_ids.append(event.get('id'))

        for game_id in game_ids:
            if not game_id:
                continue
            try:
                box_url = (
                    f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
                    f"/summary?event={game_id}"
                )
                box_resp = requests.get(box_url, timeout=15)
                box_resp.raise_for_status()
                box_data = box_resp.json()

                for team_section in box_data.get('boxscore', {}).get('players', []):
                    for stat_section in team_section.get('statistics', []):
                        names = stat_section.get('names', [])
                        for athlete_entry in stat_section.get('athletes', []):
                            athlete = athlete_entry.get('athlete', {})
                            player_name = athlete.get('displayName', '').lower()
                            if not player_name:
                                continue
                            stats_arr = athlete_entry.get('stats', [])
                            if not stats_arr:
                                continue
                            p = {}
                            for espn_col, our_col in _ESPN_STAT_MAP.items():
                                if espn_col in names:
                                    idx = names.index(espn_col)
                                    if idx < len(stats_arr):
                                        raw = str(stats_arr[idx])
                                        # "3PT" comes as "made-attempted"
                                        if '-' in raw and espn_col == '3PT':
                                            raw = raw.split('-')[0]
                                        try:
                                            p[our_col] = float(raw)
                                        except (ValueError, TypeError):
                                            p[our_col] = 0.0
                            if p:
                                player_stats[player_name] = p
                time.sleep(0.3)
            except Exception as e:
                print(f"  ESPN box score error for game {game_id}: {e}")
                continue

    except Exception as e:
        print(f"  ESPN API error for {date_str}: {e}")

    result = (player_stats, completed_teams)
    _ESPN_DATE_CACHE[date_str] = result
    return result

CURRENT_SEASON = "2025-26"
RECENT_GAMES_WINDOW = 10

# ── Alternative stats sources (used when stats.nba.com is unavailable) ────────
BDL_BASE = "https://api.balldontlie.io/v1"
BDL_SEASON = 2025  # balldontlie uses start year (2025 = 2025-26)
_ALT_PLAYER_CACHE: dict = {}  # module-level cache for player data

_NBA_LEAGUELEADERS_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "x-nba-stats-origin": "stats",
    "Referer": "https://stats.nba.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
}


def _bdl_fetch_player_season_data() -> dict:
    """Fetch season averages via stats.nba.com/stats/leagueleaders (no nba_api wrapper).
    Returns {player_full_name: {PTS, REB, AST, FG3M, FG3A, FGA, OREB, DREB,
                                FG_PCT, FG3_PCT, MIN, GP, TEAM}}
    Only returns the ~263 qualified statistical leaders, which covers all prop-worthy players.
    """
    global _ALT_PLAYER_CACHE
    if _ALT_PLAYER_CACHE:
        return _ALT_PLAYER_CACHE

    try:
        print("  [LeagueLeaders] Fetching player season averages...")
        r = requests.get(
            "https://stats.nba.com/stats/leagueleaders",
            headers=_NBA_LEAGUELEADERS_HEADERS,
            params={
                "LeagueID": "00", "PerMode": "PerGame", "Scope": "S",
                "Season": CURRENT_SEASON, "SeasonType": "Regular Season",
                "StatCategory": "PTS",
            },
            timeout=10,
        )
        r.raise_for_status()
        rs = r.json().get("resultSet", {})
        cols = rs.get("headers", [])
        rows = rs.get("rowSet", [])
        if not rows:
            return {}

        col_idx = {c: i for i, c in enumerate(cols)}
        result = {}
        for row in rows:
            def _v(col):
                idx = col_idx.get(col)
                if idx is None:
                    return 0.0
                v = row[idx]
                try:
                    return float(v) if v is not None else 0.0
                except (TypeError, ValueError):
                    return 0.0

            name = row[col_idx["PLAYER"]] if "PLAYER" in col_idx else ""
            if not name:
                continue
            team = row[col_idx["TEAM"]] if "TEAM" in col_idx else ""
            result[name] = {
                "PTS": _v("PTS"), "REB": _v("REB"), "AST": _v("AST"),
                "FG3M": _v("FG3M"), "FG3A": _v("FG3A"), "FGA": _v("FGA"),
                "OREB": _v("OREB"), "DREB": _v("DREB"),
                "FG_PCT": _v("FG_PCT"), "FG3_PCT": _v("FG3_PCT"),
                "GP": int(_v("GP")), "MIN": _v("MIN"),
                "TEAM": team,
            }

        print(f"  [LeagueLeaders] Got stats for {len(result)} players")
        _ALT_PLAYER_CACHE = result
        return result

    except Exception as e:
        print(f"  [LeagueLeaders] Error: {e}")
        return {}


def _bdl_fetch_team_game_stats() -> dict:
    """Fetch 2025-26 season games, compute per-team pts_for and pts_against.
    Returns {team_full_name: {pts_for, pts_against, gp}}
    """
    api_key = os.getenv("BALLDONTLIE_API_KEY", "")
    if not api_key:
        return {}

    headers = {"Authorization": api_key}
    team_pts_for: dict = {}
    team_pts_against: dict = {}
    team_gp: dict = {}

    cursor = None
    print("  [BDL] Fetching season game results for opponent factors...")
    while True:
        params = [("seasons[]", BDL_SEASON), ("per_page", 100)]
        if cursor:
            params.append(("cursor", cursor))
        try:
            r = requests.get(f"{BDL_BASE}/games", headers=headers,
                             params=params, timeout=15)
            if r.status_code == 429:
                # Rate limited - wait and retry with longer delay
                print("  [BDL] Rate limited, waiting 5s...")
                time.sleep(5)
                r = requests.get(f"{BDL_BASE}/games", headers=headers,
                                 params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  [BDL] Games fetch error: {e}")
            break

        for game in data.get("data", []):
            home = (game.get("home_team") or {}).get("full_name", "")
            away = (game.get("visitor_team") or {}).get("full_name", "")
            hs = game.get("home_team_score")
            vs = game.get("visitor_team_score")
            if hs is None or vs is None:
                continue
            hs, vs = int(hs), int(vs)
            if hs == 0 and vs == 0:
                continue  # unplayed game
            if home:
                team_pts_for[home] = team_pts_for.get(home, 0) + hs
                team_pts_against[home] = team_pts_against.get(home, 0) + vs
                team_gp[home] = team_gp.get(home, 0) + 1
            if away:
                team_pts_for[away] = team_pts_for.get(away, 0) + vs
                team_pts_against[away] = team_pts_against.get(away, 0) + hs
                team_gp[away] = team_gp.get(away, 0) + 1

        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(0.6)  # Respect BDL free-tier rate limit

    result = {}
    for team, gp in team_gp.items():
        if gp == 0:
            continue
        pts_for = team_pts_for.get(team, 0) / gp
        pts_against = team_pts_against.get(team, 0) / gp
        # Pace proxy: higher total scoring per game = faster tempo
        estimated_pace = 100.0 * (pts_for + pts_against) / 224.0
        estimated_pace = max(93.0, min(107.0, estimated_pace))
        result[team] = {
            "pts_for": round(pts_for, 1),
            "pts_against": round(pts_against, 1),
            "pace": round(estimated_pace, 1),
            "gp": gp,
        }
    print(f"  [BDL] Got game data for {len(result)} teams")
    return result


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


# ── Prop type configurations ──────────────────────────────────────────────────

PROP_CONFIGS = {
    "points": {
        "market_key": "player_points",
        "nba_stat_col": "PTS",
        "prop_unit": "PTS",
        "display_name": "Points",
        "html_file": "nba_points_props.html",
        "tracking_file": "nba_points_props_tracking.json",
        "stats_cache": "nba_player_points_stats_cache.json",
        "team_cache": "nba_team_defense_cache.json",
        "min_ai_score": 10.0,
        "min_edge_over": 2.0,
        "min_edge_under": 1.5,
        "min_recent_form_edge": 1.2,
        "top_plays": 10,
        "pause_unders": True,
        "per_36_baseline": 25.0,
        "hot_cold_threshold": 1.0,
        "factor_key": "defense_factor",
    },
    "assists": {
        "market_key": "player_assists",
        "nba_stat_col": "AST",
        "prop_unit": "AST",
        "display_name": "Assists",
        "html_file": "nba_assists_props.html",
        "tracking_file": "nba_assists_props_tracking.json",
        "stats_cache": "nba_player_assists_stats_cache.json",
        "team_cache": "nba_team_assists_cache.json",
        "min_ai_score": 10.0,
        "min_edge_over": 1.5,
        "min_edge_under": 1.0,
        "min_recent_form_edge": 1.2,
        "top_plays": 5,
        "pause_unders": False,
        "per_36_baseline": 8.0,
        "hot_cold_threshold": 0.8,
        "factor_key": "assists_factor",
    },
    "rebounds": {
        "market_key": "player_rebounds",
        "nba_stat_col": "REB",
        "prop_unit": "REB",
        "display_name": "Rebounds",
        "html_file": "nba_rebounds_props.html",
        "tracking_file": "nba_rebounds_props_tracking.json",
        "stats_cache": "nba_player_rebounds_stats_cache.json",
        "team_cache": "nba_team_rebounding_cache.json",
        "min_ai_score": 10.0,
        "min_edge_over": 1.5,
        "min_edge_under": 1.0,
        "min_recent_form_edge": 1.2,
        "top_plays": 10,
        "pause_unders": False,
        "per_36_baseline": 12.0,
        "hot_cold_threshold": 0.8,
        "factor_key": "rebounding_factor",
    },
    "threes": {
        "market_key": "player_threes",
        "nba_stat_col": "FG3M",
        "prop_unit": "3PM",
        "display_name": "3-Pointers",
        "html_file": "nba_3pt_props.html",
        "tracking_file": "nba_3pt_props_tracking.json",
        "stats_cache": "nba_player_3pt_stats_cache.json",
        "team_cache": "nba_team_3pt_cache.json",
        "min_ai_score": 7.5,
        "min_edge_over": 1.0,
        "min_edge_under": 0.8,
        "min_recent_form_edge": 1.2,
        "top_plays": 10,
        "pause_unders": False,
        "per_36_baseline": 3.5,
        "hot_cold_threshold": 0.8,
        "factor_key": "three_point_factor",
    },
    "pra": {
        "market_key": "player_points_rebounds_assists",
        "nba_stat_col": ["PTS", "REB", "AST"],
        "prop_unit": "PRA",
        "display_name": "Pts+Reb+Ast",
        "html_file": "nba_pra_props.html",
        "tracking_file": "nba_pra_props_tracking.json",
        "stats_cache": "nba_player_pra_stats_cache.json",
        "team_cache": "nba_team_defense_cache.json",
        "min_ai_score": 10.0,
        "min_edge_over": 3.0,
        "min_edge_under": 2.5,
        "min_recent_form_edge": 2.0,
        "top_plays": 10,
        "pause_unders": False,
        "per_36_baseline": None,
        "hot_cold_threshold": 1.5,
        "factor_key": None,
    },
    "points_rebounds": {
        "market_key": "player_points_rebounds",
        "nba_stat_col": ["PTS", "REB"],
        "prop_unit": "P+R",
        "display_name": "Pts+Reb",
        "html_file": "nba_points_rebounds_props.html",
        "tracking_file": "nba_points_rebounds_props_tracking.json",
        "stats_cache": "nba_player_points_rebounds_stats_cache.json",
        "team_cache": "nba_team_defense_cache.json",
        "min_ai_score": 10.0,
        "min_edge_over": 2.5,
        "min_edge_under": 2.0,
        "min_recent_form_edge": 1.5,
        "top_plays": 10,
        "pause_unders": False,
        "per_36_baseline": None,
        "hot_cold_threshold": 1.5,
        "factor_key": None,
    },
    "points_assists": {
        "market_key": "player_points_assists",
        "nba_stat_col": ["PTS", "AST"],
        "prop_unit": "P+A",
        "display_name": "Pts+Ast",
        "html_file": "nba_points_assists_props.html",
        "tracking_file": "nba_points_assists_props_tracking.json",
        "stats_cache": "nba_player_points_assists_stats_cache.json",
        "team_cache": "nba_team_defense_cache.json",
        "min_ai_score": 10.0,
        "min_edge_over": 2.5,
        "min_edge_under": 2.0,
        "min_recent_form_edge": 1.5,
        "top_plays": 10,
        "pause_unders": False,
        "per_36_baseline": None,
        "hot_cold_threshold": 1.5,
        "factor_key": None,
    },
    "rebounds_assists": {
        "market_key": "player_rebounds_assists",
        "nba_stat_col": ["REB", "AST"],
        "prop_unit": "R+A",
        "display_name": "Reb+Ast",
        "html_file": "nba_rebounds_assists_props.html",
        "tracking_file": "nba_rebounds_assists_props_tracking.json",
        "stats_cache": "nba_player_rebounds_assists_stats_cache.json",
        "team_cache": "nba_team_defense_cache.json",
        "min_ai_score": 10.0,
        "min_edge_over": 2.0,
        "min_edge_under": 1.5,
        "min_recent_form_edge": 1.5,
        "top_plays": 10,
        "pause_unders": False,
        "per_36_baseline": None,
        "hot_cold_threshold": 1.5,
        "factor_key": None,
    },
}

# ── NBA team constants ────────────────────────────────────────────────────────

NBA_TEAMS = {
    'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets',
    'Chicago Bulls', 'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets',
    'Detroit Pistons', 'Golden State Warriors', 'Houston Rockets', 'Indiana Pacers',
    'LA Clippers', 'Los Angeles Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies',
    'Miami Heat', 'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans',
    'New York Knicks', 'Oklahoma City Thunder', 'Orlando Magic', 'Philadelphia 76ers',
    'Phoenix Suns', 'Portland Trail Blazers', 'Sacramento Kings', 'San Antonio Spurs',
    'Toronto Raptors', 'Utah Jazz', 'Washington Wizards'
}

NBA_ROSTERS = {
    'Boston Celtics': ['Tatum', 'Brown', 'White', 'Holiday', 'Porzingis', 'Horford', 'Hauser', 'Pritchard'],
    'Washington Wizards': ['Kuzma', 'Poole', 'Coulibaly', 'Bagley', 'Jones', 'Kispert', 'Sarr', 'Carrington'],
    'Golden State Warriors': ['Curry', 'Wiggins', 'Green', 'Kuminga', 'Podziemski', 'Looney', 'Payton', 'Melton'],
    'Philadelphia 76ers': ['Embiid', 'Maxey', 'Harris', 'Oubre', 'Batum', 'McCain', 'Drummond', 'Reed', 'Martin', 'George'],
    'Brooklyn Nets': ['Johnson', 'Claxton', 'Thomas', 'Finney-Smith', 'Sharpe', 'Whitehead', 'Clowney', 'Schroder', 'Wilson'],
    'Utah Jazz': ['Markkanen', 'Sexton', 'Clarkson', 'Collins', 'Kessler', 'Hendricks', 'Williams'],
    'Los Angeles Lakers': ['James', 'Reaves', 'Russell', 'Hachimura', 'Reddish', 'Prince', 'Christie', 'Knecht'],
    'Toronto Raptors': ['Quickley', 'Poeltl', 'Dick', 'Battle', 'Agbaji', 'Shead', 'Brown'],
    'Minnesota Timberwolves': ['Edwards', 'Gobert', 'McDaniels', 'Conley', 'Reid', 'Alexander-Walker', 'DiVincenzo', 'Randle'],
    'New Orleans Pelicans': ['Williamson', 'Ingram', 'McCollum', 'Murphy', 'Alvarado', 'Hawkins', 'Jones'],
    'Miami Heat': ['Butler', 'Adebayo', 'Herro', 'Rozier', 'Love', 'Highsmith', 'Robinson', 'Jovic', 'Ware'],
    'Orlando Magic': ['Banchero', 'Wagner', 'Carter', 'Isaac', 'Suggs', 'Anthony', 'Fultz', 'Caldwell-Pope'],
    'New York Knicks': ['Brunson', 'Towns', 'Bridges', 'Hart', 'Anunoby', 'McBride', 'Achiuwa'],
    'Phoenix Suns': ['Durant', 'Booker', 'Beal', 'Nurkic', 'Allen', 'Gordon', 'Okogie', "O'Neale"],
    'Oklahoma City Thunder': ['Gilgeous-Alexander', 'Williams', 'Holmgren', 'Wallace', 'Joe', 'Dort', 'Caruso', 'Hartenstein'],
    'San Antonio Spurs': ['Wembanyama', 'Vassell', 'Johnson', 'Sochan', 'Jones', 'Branham', 'Collins', 'Castle', 'Fox', 'Barnes', 'Harper'],
    'Los Angeles Clippers': ['Leonard', 'Harden', 'Westbrook', 'Zubac', 'Mann', 'Powell', 'Coffey', 'Dunn'],
    'Denver Nuggets': ['Jokic', 'Murray', 'Porter', 'Gordon', 'Watson', 'Braun', 'Strawther', 'Westbrook'],
    'Dallas Mavericks': ['Doncic', 'Irving', 'Davis', 'Washington', 'Gafford', 'Lively', 'Grimes', 'Kleber', 'Exum'],
    'Sacramento Kings': ['Sabonis', 'Murray', 'DeRozan', 'Huerter', 'Monk', 'McDermott'],
    'Memphis Grizzlies': ['Morant', 'Bane', 'Jackson', 'Smart', 'Williams', 'Konchar', 'Edey', 'Wells'],
    'Cleveland Cavaliers': ['Mitchell', 'Garland', 'Mobley', 'Allen', 'LeVert', 'Strus', 'Okoro', 'Wade'],
    'Milwaukee Bucks': ['Antetokounmpo', 'Lillard', 'Middleton', 'Lopez', 'Portis', 'Connaughton', 'Trent'],
    'Indiana Pacers': ['Haliburton', 'Turner', 'Mathurin', 'Nembhard', 'Nesmith', 'Siakam', 'Brown', 'Walker'],
    'Atlanta Hawks': ['Young', 'Murray', 'Johnson', 'Hunter', 'Bogdanovic', 'Okongwu', 'Daniels', 'Risacher'],
    'Chicago Bulls': ['LaVine', 'Vucevic', 'Williams', 'Dosunmu', 'White', 'Giddey', 'Ball', 'Smith'],
    'Charlotte Hornets': ['Ball', 'Miller', 'Bridges', 'Williams', 'Richards', 'Martin', 'Knueppel', 'Green'],
    'Detroit Pistons': ['Cunningham', 'Ivey', 'Duren', 'Harris', 'Beasley', 'Stewart', 'Thompson', 'Holland', 'Robinson'],
    'Houston Rockets': ['Green', 'Smith', 'Sengun', 'VanVleet', 'Dillon', 'Thompson', 'Whitmore', 'Eason', 'Sheppard'],
    'Portland Trail Blazers': ['Simons', 'Grant', 'Sharpe', 'Ayton', 'Thybulle', 'Camara', 'Henderson', 'Clingan'],
}

TEAM_ABBREV_MAP = {
    "Atlanta Hawks": "atl", "Boston Celtics": "bos", "Brooklyn Nets": "bkn",
    "Charlotte Hornets": "cha", "Chicago Bulls": "chi", "Cleveland Cavaliers": "cle",
    "Dallas Mavericks": "dal", "Denver Nuggets": "den", "Detroit Pistons": "det",
    "Golden State Warriors": "gsw", "Houston Rockets": "hou", "Indiana Pacers": "ind",
    "LA Clippers": "lac", "Los Angeles Clippers": "lac", "Los Angeles Lakers": "lal",
    "LA Lakers": "lal", "Memphis Grizzlies": "mem", "Miami Heat": "mia",
    "Milwaukee Bucks": "mil", "Minnesota Timberwolves": "min",
    "New Orleans Pelicans": "no", "New York Knicks": "ny",
    "Oklahoma City Thunder": "okc", "Orlando Magic": "orl",
    "Philadelphia 76ers": "phi", "Phoenix Suns": "phx",
    "Portland Trail Blazers": "por", "Sacramento Kings": "sac",
    "San Antonio Spurs": "sa", "Toronto Raptors": "tor",
    "Utah Jazz": "utah", "Washington Wizards": "was"
}

SHORT_TEAM_NAMES = {
    "Atlanta Hawks": "Hawks", "Boston Celtics": "Celtics", "Brooklyn Nets": "Nets",
    "Charlotte Hornets": "Hornets", "Chicago Bulls": "Bulls",
    "Cleveland Cavaliers": "Cavaliers", "Dallas Mavericks": "Mavericks",
    "Denver Nuggets": "Nuggets", "Detroit Pistons": "Pistons",
    "Golden State Warriors": "Warriors", "Houston Rockets": "Rockets",
    "Indiana Pacers": "Pacers", "LA Clippers": "Clippers",
    "Los Angeles Clippers": "Clippers", "Los Angeles Lakers": "Lakers",
    "LA Lakers": "Lakers", "Memphis Grizzlies": "Grizzlies",
    "Miami Heat": "Heat", "Milwaukee Bucks": "Bucks",
    "Minnesota Timberwolves": "Timberwolves", "New Orleans Pelicans": "Pelicans",
    "New York Knicks": "Knicks", "Oklahoma City Thunder": "Thunder",
    "Orlando Magic": "Magic", "Philadelphia 76ers": "76ers",
    "Phoenix Suns": "Suns", "Portland Trail Blazers": "Trail Blazers",
    "Sacramento Kings": "Kings", "San Antonio Spurs": "Spurs",
    "Toronto Raptors": "Raptors", "Utah Jazz": "Jazz",
    "Washington Wizards": "Wizards"
}

ABBREV_TO_NICKNAME = {
    'ATL': 'Hawks', 'BOS': 'Celtics', 'BKN': 'Nets', 'CHA': 'Hornets', 'CHI': 'Bulls',
    'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors',
    'HOU': 'Rockets', 'IND': 'Pacers', 'LAC': 'Clippers', 'LAL': 'Lakers', 'MEM': 'Grizzlies',
    'MIA': 'Heat', 'MIL': 'Bucks', 'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks',
    'OKC': 'Thunder', 'ORL': 'Magic', 'PHI': '76ers', 'PHX': 'Suns', 'POR': 'Blazers',
    'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz', 'WAS': 'Wizards'
}

PLAYER_ALIASES = {
    "moe wagner": "moritz wagner",
    "mo wagner": "moritz wagner",
    "kelly oubre jr.": "kelly oubre jr",
    "michael porter jr.": "michael porter jr",
    "c.j. mccollum": "cj mccollum",
    "carlton carrington": "bub carrington",
    "jimmy butler": "jimmy butler iii",
}


# ═══════════════════════════════════════════════════════════════════════════════
# NBAPropsEngine
# ═══════════════════════════════════════════════════════════════════════════════

class NBAPropsEngine:
    def __init__(self, prop_type):
        if prop_type not in PROP_CONFIGS:
            raise ValueError(f"Unknown prop type: {prop_type}. Valid: {list(PROP_CONFIGS.keys())}")

        self.prop_type = prop_type
        cfg = PROP_CONFIGS[prop_type]

        self.market_key = cfg["market_key"]
        self.nba_stat_col = cfg["nba_stat_col"]
        self.prop_unit = cfg["prop_unit"]
        self.display_name = cfg["display_name"]
        self.is_combo = isinstance(self.nba_stat_col, list)

        self.output_html = os.path.join(SCRIPT_DIR, cfg["html_file"])
        self.tracking_file = os.path.join(SCRIPT_DIR, cfg["tracking_file"])
        self.stats_cache = os.path.join(SCRIPT_DIR, cfg["stats_cache"])
        self.team_cache = os.path.join(SCRIPT_DIR, cfg["team_cache"])

        self.min_ai_score = cfg["min_ai_score"]
        self.min_edge_over = cfg["min_edge_over"]
        self.min_edge_under = cfg["min_edge_under"]
        self.min_recent_form_edge = cfg["min_recent_form_edge"]
        self.top_plays = cfg["top_plays"]
        self.pause_unders = cfg["pause_unders"]
        self.per_36_baseline = cfg["per_36_baseline"]
        self.hot_cold_threshold = cfg["hot_cold_threshold"]
        self.factor_key = cfg["factor_key"]

        # Stat key prefixes for player_stats dict
        if self.is_combo:
            self.season_avg_key = f"season_{self.prop_unit.lower()}_avg"
            self.recent_avg_key = f"recent_{self.prop_unit.lower()}_avg"
            self.per_36_key = None
        else:
            col_lower = self.nba_stat_col.lower()
            # Map stat col to key name used in player_stats
            stat_name_map = {"pts": "pts", "ast": "ast", "reb": "reb", "fg3m": "3pm"}
            stat_name = stat_name_map.get(col_lower, col_lower)
            self.season_avg_key = f"season_{stat_name}_avg"
            self.recent_avg_key = f"recent_{stat_name}_avg"
            per_36_map = {"pts": "pts_per_36", "ast": "ast_per_36", "reb": "reb_per_36", "fg3m": "fg3m_per_36"}
            self.per_36_key = per_36_map.get(col_lower, f"{col_lower}_per_36")

    # ── Tracking ──────────────────────────────────────────────────────────────

    def load_tracking_data(self):
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r') as f:
                return json.load(f)
        return {'picks': [], 'summary': {}}

    def save_tracking_data(self, tracking_data):
        with open(self.tracking_file, 'w') as f:
            json.dump(tracking_data, f, indent=2)

    def track_new_picks(self, over_plays, under_plays):
        tracking_data = self.load_tracking_data()
        new_count = 0
        updated_count = 0

        for play in over_plays + under_plays:
            prop_str = play.get('prop', '')
            bet_type = 'over' if 'OVER' in prop_str else 'under'

            if bet_type == 'under' and self.pause_unders:
                continue

            match = re.search(r'(\d+\.?\d*)', prop_str)
            prop_line = float(match.group(1)) if match else 0
            pick_id = f"{play['player']}_{prop_line}_{bet_type}_{play.get('game_time', '')}"

            existing_pick = None
            for p in tracking_data['picks']:
                if (p.get('player') == play['player'] and
                    p.get('bet_type') == bet_type and
                    p.get('game_time', '') == play.get('game_time', '')):
                    existing_pick = p
                    break
            if not existing_pick:
                existing_pick = next((p for p in tracking_data['picks'] if p.get('pick_id') == pick_id), None)

            if existing_pick:
                if existing_pick.get('latest_odds') != play.get('odds'):
                    existing_pick['latest_odds'] = play.get('odds')
                    existing_pick['last_updated'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
                    existing_pick['clv_status'] = self._calculate_clv(
                        existing_pick.get('opening_odds', play.get('odds')),
                        play.get('odds'), bet_type
                    )
                    updated_count += 1
            else:
                new_pick = {
                    'pick_id': pick_id,
                    'player': play['player'],
                    'prop_line': prop_line,
                    'bet_type': bet_type,
                    'team': play.get('team'),
                    'opponent': play.get('opponent'),
                    'ai_score': play.get('ai_score'),
                    'odds': play.get('odds'),
                    'opening_odds': play.get('odds'),
                    'latest_odds': play.get('odds'),
                    'game_time': play.get('game_time'),
                    'season_avg': play.get('season_avg'),
                    'recent_avg': play.get('recent_avg'),
                    'edge': play.get('edge'),
                    'ev': play.get('ev'),
                    'tracked_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
                    'status': 'pending',
                    'result': None,
                    f'actual_{self.prop_unit.lower()}': None,
                    'clv_status': None,
                }
                tracking_data['picks'].append(new_pick)
                new_count += 1

        self.save_tracking_data(tracking_data)
        if new_count > 0:
            print(f"{Colors.GREEN}✓ Tracked {new_count} new picks{Colors.END}")
        if updated_count > 0:
            print(f"{Colors.YELLOW}✓ Updated odds for {updated_count} existing picks{Colors.END}")

    @staticmethod
    def _calculate_clv(opening_odds, latest_odds, bet_type):
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

    # ── Grading ───────────────────────────────────────────────────────────────

    def grade_pending_picks(self):
        tracking_data = self.load_tracking_data()
        pending = [p for p in tracking_data['picks'] if p.get('status') == 'pending']
        if not pending:
            print(f"\n{Colors.GREEN}✓ No pending picks to grade{Colors.END}")
            return 0

        print(f"\n{Colors.CYAN}🎯 GRADING {len(pending)} PENDING {self.display_name.upper()} PICKS{Colors.END}")
        graded_count = 0

        GRADE_CUTOFF_DAYS = 7
        picks_by_date = defaultdict(list)
        for pick in pending:
            gt = pick.get('game_time')
            if not gt:
                continue
            try:
                gt_utc = datetime.fromisoformat(gt.replace('Z', '+00:00'))
                hours_ago = (datetime.now(pytz.UTC) - gt_utc).total_seconds() / 3600
                if hours_ago >= 1:
                    if hours_ago > GRADE_CUTOFF_DAYS * 24:
                        pick['status'] = 'void'
                        print(f"{Colors.YELLOW}  ⚠ Voiding stale pick (>{GRADE_CUTOFF_DAYS}d old): {pick.get('player', '?')} {pick.get('prop', '')}{Colors.END}")
                        continue
                    et_tz = pytz.timezone('US/Eastern')
                    game_date = gt_utc.astimezone(et_tz).strftime('%Y-%m-%d')
                    picks_by_date[game_date].append(pick)
            except Exception:
                continue

        for date_str, picks in picks_by_date.items():
            daily_stats = self._fetch_daily_stats(date_str)
            completed_teams = self._fetch_completed_teams(date_str)
            if not daily_stats:
                continue

            for pick in picks:
                try:
                    player_name = pick.get('player')
                    is_game_final = pick.get('team') in completed_teams
                    lookup_key = PLAYER_ALIASES.get(player_name.lower(), player_name.lower())

                    actual_stat = daily_stats.get(lookup_key)
                    if actual_stat is None:
                        # Fuzzy match
                        for p_name, val in daily_stats.items():
                            p_parts = p_name.split()
                            n_parts = lookup_key.split()
                            if len(p_parts) >= 2 and len(n_parts) >= 2:
                                if n_parts[0] == p_parts[0] and n_parts[-1] == p_parts[-1]:
                                    actual_stat = val
                                    break
                        if actual_stat is None:
                            if is_game_final:
                                pick['status'] = 'void'
                                pick['result'] = 'DNP'
                                pick['profit_loss'] = 0
                                graded_count += 1
                            continue

                    prop_line = pick.get('prop_line')
                    bet_type = pick.get('bet_type')

                    is_determined = False
                    if is_game_final:
                        is_determined = True
                    elif bet_type == 'over' and actual_stat > prop_line:
                        is_determined = True
                    elif bet_type == 'under' and actual_stat > prop_line:
                        is_determined = True

                    if not is_determined:
                        continue

                    if bet_type == 'over':
                        is_win = actual_stat > prop_line
                    else:
                        is_win = actual_stat < prop_line

                    odds = pick.get('opening_odds') or pick.get('odds', -110)
                    if is_win:
                        profit_loss = int(odds) if odds > 0 else int((100.0 / abs(odds)) * 100)
                        status, result = 'win', 'WIN'
                    else:
                        profit_loss = -100
                        status, result = 'loss', 'LOSS'

                    pick['status'] = status
                    pick['result'] = result
                    pick[f'actual_{self.prop_unit.lower()}'] = actual_stat
                    pick['profit_loss'] = profit_loss
                    pick['updated_at'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()

                    color = Colors.GREEN if is_win else Colors.RED
                    print(f"    {color}{result}{Colors.END}: {player_name} had {actual_stat} {self.prop_unit} "
                          f"(line: {prop_line}, bet: {bet_type.upper()}) | Profit: {profit_loss/100.0:.2f}u")
                    graded_count += 1
                except Exception as e:
                    print(f"{Colors.RED}  Error grading {pick.get('player')}: {e}{Colors.END}")

        if graded_count > 0:
            self.save_tracking_data(tracking_data)
            print(f"\n{Colors.GREEN}✓ Graded {graded_count} picks{Colors.END}")
        return graded_count

    def _fetch_daily_stats(self, game_date_str):
        """Fetch player stats for a date via ESPN (free, no key).
        Falls back to stats.nba.com if ESPN returns nothing."""
        print(f"  Fetching stats for {game_date_str} via ESPN...")
        player_stats, _ = _fetch_espn_date_data(game_date_str)

        if player_stats:
            stats_map = {}
            for player_name, p in player_stats.items():
                if self.is_combo:
                    val = sum(float(p.get(col, 0) or 0) for col in self.nba_stat_col)
                else:
                    val = float(p.get(self.nba_stat_col, 0) or 0)
                stats_map[player_name] = val
            return stats_map

        # Fallback to stats.nba.com
        print(f"  ESPN returned no data for {game_date_str}, trying stats.nba.com...")
        try:
            target_date = datetime.strptime(game_date_str, '%Y-%m-%d').strftime('%m/%d/%Y')
            daily = leaguedashplayerstats.LeagueDashPlayerStats(
                season=CURRENT_SEASON,
                date_from_nullable=target_date,
                date_to_nullable=target_date,
                measure_type_detailed_defense='Base',
                per_mode_detailed='PerGame',
                timeout=60
            )
            df = daily.get_data_frames()[0]
            if df.empty:
                return {}
            stats_map = {}
            for _, row in df.iterrows():
                name = row.get('PLAYER_NAME', '').lower()
                if self.is_combo:
                    val = sum(float(row.get(col, 0) or 0) for col in self.nba_stat_col)
                else:
                    val = float(row.get(self.nba_stat_col, 0) or 0)
                stats_map[name] = val
            return stats_map
        except Exception as e:
            print(f"{Colors.YELLOW}  Error fetching stats for {game_date_str}: {e}{Colors.END}")
            return {}

    @staticmethod
    def _fetch_completed_teams(date_str):
        """Get set of teams that played on date_str via ESPN (free, no key)."""
        _, completed_teams = _fetch_espn_date_data(date_str)
        if completed_teams:
            return completed_teams
        # Fallback to stats.nba.com
        try:
            stats = leaguedashteamstats.LeagueDashTeamStats(
                date_from_nullable=date_str,
                date_to_nullable=date_str
            ).get_data_frames()[0]
            return set(stats['TEAM_NAME'].unique()) if not stats.empty else set()
        except Exception:
            return set()

    def backfill_profit_loss(self):
        tracking_data = self.load_tracking_data()
        updated = 0
        for pick in tracking_data['picks']:
            if pick.get('status') in ['win', 'loss'] and 'profit_loss' not in pick:
                odds = pick.get('opening_odds') or pick.get('odds', -110)
                if pick['status'] == 'win':
                    pick['profit_loss'] = int(odds) if odds > 0 else int((100.0 / abs(odds)) * 100)
                else:
                    pick['profit_loss'] = -100
                pick['profit_loss_backfilled'] = True
                updated += 1
        if updated > 0:
            self.save_tracking_data(tracking_data)
            print(f"{Colors.GREEN}✓ Backfilled profit_loss for {updated} picks{Colors.END}")

    # ── Tracking Stats ────────────────────────────────────────────────────────

    def calculate_tracking_stats(self, tracking_data):
        completed = [p for p in tracking_data['picks'] if p.get('status') in ['win', 'loss']]

        # Deduplicate
        unique_map = {}
        sorted_picks = sorted(completed, key=lambda p: p.get('last_updated') or p.get('updated_at') or p.get('tracked_at') or "0")
        for p in sorted_picks:
            gt = p.get('game_time', '')
            if not gt:
                continue
            try:
                dt_str = gt.split('T')[0]
            except Exception:
                continue
            key = f"{p.get('player')}_{dt_str}_{p.get('bet_type')}"
            unique_map[key] = p
        completed = list(unique_map.values())

        if not completed:
            return {'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0,
                    'total_profit': 0.0, 'roi': 0.0, 'roi_pct': 0.0,
                    'over_record': '0-0', 'over_win_rate': 0.0, 'over_roi': 0.0,
                    'under_record': '0-0', 'under_win_rate': 0.0, 'under_roi': 0.0}

        def _calc_profit(picks):
            total = 0
            for p in picks:
                if 'profit_loss' in p:
                    total += p['profit_loss']
                else:
                    odds = p.get('opening_odds') or p.get('odds', -110)
                    if p['status'] == 'win':
                        total += int(odds) if odds > 0 else int((100.0 / abs(odds)) * 100)
                    else:
                        total -= 100
            return total

        wins = sum(1 for p in completed if p['status'] == 'win')
        losses = sum(1 for p in completed if p['status'] == 'loss')
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0.0
        profit_cents = _calc_profit(completed)
        profit_units = profit_cents / 100.0
        roi_pct = (profit_units / total * 100) if total > 0 else 0.0

        over_picks = [p for p in completed if p.get('bet_type') == 'over']
        ow = sum(1 for p in over_picks if p['status'] == 'win')
        ol = sum(1 for p in over_picks if p['status'] == 'loss')
        ot = ow + ol
        over_profit = _calc_profit(over_picks) / 100.0
        over_roi = (over_profit / ot * 100) if ot > 0 else 0.0

        under_picks = [p for p in completed if p.get('bet_type') == 'under']
        uw = sum(1 for p in under_picks if p['status'] == 'win')
        ul = sum(1 for p in under_picks if p['status'] == 'loss')
        ut = uw + ul
        under_profit = _calc_profit(under_picks) / 100.0
        under_roi = (under_profit / ut * 100) if ut > 0 else 0.0

        # Daily performance
        et_tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(et_tz)

        def _daily(target_str):
            dp = []
            for p in completed:
                gt = p.get('game_time', '')
                if not gt:
                    continue
                try:
                    dt_utc = datetime.fromisoformat(gt.replace('Z', '+00:00'))
                    if dt_utc.astimezone(et_tz).strftime('%Y-%m-%d') == target_str:
                        dp.append(p)
                except Exception:
                    continue
            dw = sum(1 for p in dp if p['status'] == 'win')
            dl = sum(1 for p in dp if p['status'] == 'loss')
            dt_ = dw + dl
            dp_cents = _calc_profit(dp)
            dp_units = dp_cents / 100.0
            return {'record': f"{dw}-{dl}", 'profit': dp_units, 'roi': (dp_units / dt_ * 100) if dt_ > 0 else 0.0, 'count': dt_}

        return {
            'total': total, 'wins': wins, 'losses': losses,
            'win_rate': round(win_rate, 2), 'total_profit': round(profit_units, 2),
            'roi': round(profit_units, 2), 'roi_pct': round(roi_pct, 2),
            'over_record': f'{ow}-{ol}', 'over_win_rate': round((ow / ot * 100) if ot > 0 else 0, 2), 'over_roi': round(over_roi, 2),
            'under_record': f'{uw}-{ul}', 'under_win_rate': round((uw / ut * 100) if ut > 0 else 0, 2), 'under_roi': round(under_roi, 2),
            'today': _daily(now_et.strftime('%Y-%m-%d')),
            'yesterday': _daily((now_et - timedelta(days=1)).strftime('%Y-%m-%d')),
        }

    # ── Data Fetching ─────────────────────────────────────────────────────────

    def get_player_stats(self):
        """Fetch player stats from NBA API. For combos: sums component stats."""
        print(f"\n{Colors.CYAN}Fetching {self.display_name} player stats...{Colors.END}")

        if os.path.exists(self.stats_cache):
            mod_time = datetime.fromtimestamp(os.path.getmtime(self.stats_cache))
            if (datetime.now() - mod_time) < timedelta(hours=6):
                print(f"{Colors.GREEN}✓ Using cached stats (< 6 hours old){Colors.END}")
                with open(self.stats_cache, 'r') as f:
                    return json.load(f)

        player_stats = {}

        # ── Primary: balldontlie.io ──────────────────────────────────────────
        try:
            bdl_data = _bdl_fetch_player_season_data()
            if bdl_data:
                for player_name, row in bdl_data.items():
                    games_played = row["GP"]
                    team = row["TEAM"]
                    minutes = row["MIN"]

                    if self.is_combo:
                        season_val = sum(row.get(c, 0.0) for c in self.nba_stat_col)
                        player_stats[player_name] = {
                            self.season_avg_key: round(season_val, 2),
                            self.recent_avg_key: round(season_val, 2),
                            "consistency_score": 0.7,
                            "games_played": games_played,
                            "team": team,
                            "minutes": round(minutes, 1),
                        }
                    else:
                        col = self.nba_stat_col
                        season_val = row.get(col, 0.0)
                        per_36 = (season_val / minutes * 36) if minutes > 0 else 0.0
                        consistency = min(1.0, per_36 / self.per_36_baseline) if per_36 > 0 and self.per_36_baseline else 0.3

                        entry = {
                            self.season_avg_key: round(season_val, 2),
                            self.recent_avg_key: round(season_val, 2),
                            self.per_36_key: round(per_36, 2),
                            "consistency_score": round(consistency, 2),
                            "games_played": games_played,
                            "team": team,
                            "minutes": round(minutes, 1),
                        }

                        if self.prop_type == "points":
                            entry["fg_pct"] = round(row.get("FG_PCT", 0.0), 3)
                            entry["fga"] = round(row.get("FGA", 0.0), 1)
                        elif self.prop_type == "rebounds":
                            entry["oreb_avg"] = round(row.get("OREB", 0.0), 2)
                            entry["dreb_avg"] = round(row.get("DREB", 0.0), 2)
                        elif self.prop_type == "threes":
                            entry["fg3_pct"] = round(row.get("FG3_PCT", 0.0), 3)
                            entry["fg3a_avg"] = round(row.get("FG3A", 0.0), 2)

                        player_stats[player_name] = entry

                if player_stats:
                    with open(self.stats_cache, 'w') as f:
                        json.dump(player_stats, f, indent=2)
                    print(f"{Colors.GREEN}✓ Fetched stats for {len(player_stats)} players via BDL{Colors.END}")
                    return player_stats
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ BDL player stats error: {e}, trying stats.nba.com...{Colors.END}")

        # ── Fallback: stats.nba.com ──────────────────────────────────────────
        try:
            season_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=CURRENT_SEASON, measure_type_detailed_defense="Base",
                per_mode_detailed="PerGame", timeout=60
            )
            season_df = season_stats.get_data_frames()[0]
            time.sleep(0.6)

            recent_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=CURRENT_SEASON, measure_type_detailed_defense="Base",
                per_mode_detailed="PerGame", last_n_games=RECENT_GAMES_WINDOW, timeout=60
            )
            recent_df = recent_stats.get_data_frames()[0]
            time.sleep(0.6)

            for _, row in season_df.iterrows():
                player_name = row.get("PLAYER_NAME", "")
                if not player_name:
                    continue

                games_played = int(row.get("GP", 0) or 0)
                team = row.get("TEAM_ABBREVIATION", "")
                minutes = float(row.get("MIN", 0) or 0)

                if self.is_combo:
                    season_val = sum(float(row.get(c, 0) or 0) for c in self.nba_stat_col)
                    recent_row = recent_df[recent_df["PLAYER_NAME"] == player_name]
                    if not recent_row.empty:
                        recent_val = sum(float(recent_row.iloc[0].get(c, 0) or 0) for c in self.nba_stat_col)
                    else:
                        recent_val = season_val

                    player_stats[player_name] = {
                        self.season_avg_key: round(season_val, 2),
                        self.recent_avg_key: round(recent_val, 2),
                        "consistency_score": 0.7,
                        "games_played": games_played,
                        "team": team,
                        "minutes": round(minutes, 1),
                    }
                else:
                    col = self.nba_stat_col
                    season_val = float(row.get(col, 0) or 0)

                    recent_row = recent_df[recent_df["PLAYER_NAME"] == player_name]
                    recent_val = float(recent_row.iloc[0].get(col, season_val) or season_val) if not recent_row.empty else season_val

                    per_36 = (season_val / minutes * 36) if minutes > 0 else 0.0
                    consistency = min(1.0, per_36 / self.per_36_baseline) if per_36 > 0 and self.per_36_baseline else 0.3

                    entry = {
                        self.season_avg_key: round(season_val, 2),
                        self.recent_avg_key: round(recent_val, 2),
                        self.per_36_key: round(per_36, 2),
                        "consistency_score": round(consistency, 2),
                        "games_played": games_played,
                        "team": team,
                        "minutes": round(minutes, 1),
                    }

                    if self.prop_type == "points":
                        entry["fg_pct"] = round(float(row.get("FG_PCT", 0) or 0), 3)
                        entry["fga"] = round(float(row.get("FGA", 0) or 0), 1)
                    elif self.prop_type == "rebounds":
                        entry["oreb_avg"] = round(float(row.get("OREB", 0) or 0), 2)
                        entry["dreb_avg"] = round(float(row.get("DREB", 0) or 0), 2)
                    elif self.prop_type == "threes":
                        entry["fg3_pct"] = round(float(row.get("FG3_PCT", 0) or 0), 3)
                        entry["fg3a_avg"] = round(float(row.get("FG3A", 0) or 0), 2)

                    player_stats[player_name] = entry

            with open(self.stats_cache, 'w') as f:
                json.dump(player_stats, f, indent=2)
            print(f"{Colors.GREEN}✓ Fetched stats for {len(player_stats)} players{Colors.END}")
            return player_stats

        except Exception as e:
            print(f"{Colors.RED}✗ Error fetching stats: {e}{Colors.END}")
            import traceback; traceback.print_exc()
            if os.path.exists(self.stats_cache):
                with open(self.stats_cache, 'r') as f:
                    return json.load(f)
            return {}

    def get_opponent_factors(self):
        """Fetch team opponent factors. For combos: averages component factors."""
        if self.is_combo:
            return self._get_combo_opponent_factors()

        print(f"\n{Colors.CYAN}Fetching opponent {self.display_name.lower()} factors...{Colors.END}")

        if os.path.exists(self.team_cache):
            mod_time = datetime.fromtimestamp(os.path.getmtime(self.team_cache))
            if (datetime.now() - mod_time) < timedelta(hours=6):
                print(f"{Colors.GREEN}✓ Using cached factors{Colors.END}")
                with open(self.team_cache, 'r') as f:
                    return json.load(f)

        factors = {}

        # ── Primary: balldontlie.io game scores ──────────────────────────────
        try:
            bdl_games = _bdl_fetch_team_game_stats()
            if bdl_games:
                league_avg_pts = 112.0
                for team_name, gs in bdl_games.items():
                    if team_name not in NBA_TEAMS:
                        continue
                    pts_against = gs["pts_against"]
                    pace = gs["pace"]

                    if self.prop_type == "points":
                        factor = pts_against / league_avg_pts
                        factors[team_name] = {
                            "opp_pts_allowed": round(pts_against, 1),
                            "pace": round(pace, 1),
                            "def_rating": round(pts_against, 1),
                            "defense_factor": round(factor, 3),
                        }
                    elif self.prop_type == "assists":
                        factor = pace / 100.0
                        factors[team_name] = {
                            "opp_ast_allowed": 25.0,
                            "pace": round(pace, 1),
                            "assists_factor": round(factor, 3),
                        }
                    elif self.prop_type == "rebounds":
                        factor = pace / 100.0
                        factors[team_name] = {
                            "opp_reb_allowed": 44.0,
                            "pace": round(pace, 1),
                            "rebounding_factor": round(factor, 3),
                        }
                    elif self.prop_type == "threes":
                        factor = pace / 100.0
                        factors[team_name] = {
                            "opp_fg3m_allowed": 12.5,
                            "pace": round(pace, 1),
                            "three_point_factor": round(factor, 3),
                        }

                if factors:
                    with open(self.team_cache, 'w') as f:
                        json.dump(factors, f, indent=2)
                    print(f"{Colors.GREEN}✓ Fetched factors for {len(factors)} teams via BDL{Colors.END}")
                    return factors
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ BDL team stats error: {e}, trying stats.nba.com...{Colors.END}")

        # ── Fallback: stats.nba.com ──────────────────────────────────────────
        try:
            opp_stats = leaguedashteamstats.LeagueDashTeamStats(
                season=CURRENT_SEASON, measure_type_detailed_defense="Opponent", timeout=60
            )
            opp_df = opp_stats.get_data_frames()[0]
            time.sleep(0.6)

            adv_stats = leaguedashteamstats.LeagueDashTeamStats(
                season=CURRENT_SEASON, measure_type_detailed_defense="Advanced", timeout=60
            )
            adv_df = adv_stats.get_data_frames()[0]
            time.sleep(0.6)

            adv_lookup = {}
            for _, row in adv_df.iterrows():
                tn = row.get("TEAM_NAME", "")
                if tn:
                    adv_lookup[tn] = {"pace": row.get("PACE", 100), "def_rating": row.get("DEF_RATING", 110)}

            for _, row in opp_df.iterrows():
                tn = row.get("TEAM_NAME", "")
                if not tn or tn not in NBA_TEAMS:
                    continue
                gp = max(row.get("GP", 1), 1)
                adv = adv_lookup.get(tn, {})
                pace = float(adv.get("pace", 100))

                if self.prop_type == "points":
                    opp_val = float(row.get("OPP_PTS", 0) or 0) / gp
                    def_rating = float(adv.get("def_rating", 110))
                    factor = (opp_val / 110.0) * (pace / 100) * (110.0 / def_rating)
                    factors[tn] = {"opp_pts_allowed": round(opp_val, 1), "pace": round(pace, 1),
                                   "def_rating": round(def_rating, 1), "defense_factor": round(factor, 3)}

                elif self.prop_type == "assists":
                    opp_val = float(row.get("OPP_AST", 0) or 0) / gp
                    factor = (opp_val / 25.0) * (pace / 100.0)
                    factors[tn] = {"opp_ast_allowed": round(opp_val, 1), "pace": round(pace, 1),
                                   "assists_factor": round(factor, 3)}

                elif self.prop_type == "rebounds":
                    opp_reb = float(row.get("OPP_REB", 0) or 0) / gp
                    opp_oreb = float(row.get("OPP_OREB", 0) or 0) / gp
                    oreb_factor = max(0.85, min(1.20, opp_oreb / 11.0)) if opp_oreb > 0 else 1.0
                    factor = (opp_reb / 44.0) * (pace / 100.0) * oreb_factor
                    factors[tn] = {"opp_reb_allowed": round(opp_reb, 1), "pace": round(pace, 1),
                                   "rebounding_factor": round(factor, 3)}

                elif self.prop_type == "threes":
                    opp_fg3m = float(row.get("OPP_FG3M", 0) or 0) / gp
                    opp_fg3a = float(row.get("OPP_FG3A", 0) or 0) / gp
                    factor = (opp_fg3m / 12.5) * (opp_fg3a / 35.0) * (pace / 100.0)
                    factors[tn] = {"opp_fg3m_allowed": round(opp_fg3m, 1), "pace": round(pace, 1),
                                   "three_point_factor": round(factor, 3)}

            with open(self.team_cache, 'w') as f:
                json.dump(factors, f, indent=2)
            print(f"{Colors.GREEN}✓ Fetched factors for {len(factors)} teams{Colors.END}")
            return factors

        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Could not fetch factors: {e}{Colors.END}")
            if os.path.exists(self.team_cache):
                with open(self.team_cache, 'r') as f:
                    return json.load(f)
            return {}

    def _get_combo_opponent_factors(self):
        """For combo props, load the defense cache (reuses points' team_cache) and return as-is."""
        if os.path.exists(self.team_cache):
            mod_time = datetime.fromtimestamp(os.path.getmtime(self.team_cache))
            if (datetime.now() - mod_time) < timedelta(hours=6):
                with open(self.team_cache, 'r') as f:
                    return json.load(f)
        # Generate using points logic
        tmp = NBAPropsEngine("points")
        return tmp.get_opponent_factors()

    # ── Odds Fetching ─────────────────────────────────────────────────────────

    def get_player_props(self, player_stats=None):
        print(f"\n{Colors.CYAN}Fetching {self.display_name} prop odds...{Colors.END}")
        rosters = NBA_ROSTERS

        try:
            from nba.nba_api_client import NBAOddsClient
        except ImportError:
            try:
                from nba_api_client import NBAOddsClient
            except ImportError:
                import sys
                sys.path.append(os.path.join(os.path.dirname(__file__)))
                from nba_api_client import NBAOddsClient

        client = NBAOddsClient()
        games_data = client.get_odds_data()

        all_props = []
        for game in games_data:
            home_team = game['home_team']
            away_team = game['away_team']
            commence_time = game['commence_time']
            bookmakers = game.get('bookmakers', [])
            if not bookmakers:
                continue

            # Bookmaker priority with fallback
            preferred_order = [
                next((b for b in bookmakers if b.get("key") == "hardrockbet"), None),
                next((b for b in bookmakers if b.get("key") == "fanduel"), None),
                next((b for b in bookmakers if b.get("key") == "pinnacle"), None),
                next((b for b in bookmakers if b.get("key") == "fliff"), None),
            ]
            tried_keys = {b.get("key") for b in preferred_order if b}
            ordered_books = [b for b in preferred_order if b] + [b for b in bookmakers if b.get("key") not in tried_keys]

            for book in ordered_books:
                found_market = False
                for market in book.get("markets", []):
                    if market.get("key") == self.market_key:
                        found_market = True
                        grouped = {}
                        for outcome in market.get("outcomes", []):
                            pn = outcome.get("description")
                            if not pn:
                                continue
                            pn = pn.strip()
                            point = outcome.get("point")
                            if point is None:
                                continue
                            side = (outcome.get("name") or "").strip().lower()
                            price = outcome.get("price", -110)
                            key = (pn, float(point))
                            if key not in grouped:
                                pt, po = _match_player_to_team(pn, home_team, away_team, rosters, player_stats)
                                grouped[key] = {
                                    "player": pn, "prop_line": float(point),
                                    "over_price": None, "under_price": None,
                                    "team": pt, "opponent": po,
                                    "home_team": home_team, "away_team": away_team,
                                    "game_time": commence_time
                                }
                            if side == "over":
                                grouped[key]["over_price"] = price
                            elif side == "under":
                                grouped[key]["under_price"] = price
                        all_props.extend(grouped.values())
                        break
                if found_market:
                    break

        print(f"{Colors.GREEN}✓ Fetched {len(all_props)} {self.display_name} props{Colors.END}")
        return all_props

    # ── AI Score ──────────────────────────────────────────────────────────────

    def calculate_ai_score(self, player_data, prop_line, bet_type, opponent_factor=None):
        if self.is_combo:
            return self._calculate_combo_ai_score(player_data, prop_line, bet_type, opponent_factor)

        score = 4.0
        season_avg = float(player_data.get(self.season_avg_key, 0) or 0)
        recent_avg = float(player_data.get(self.recent_avg_key, 0) or 0)
        per_36 = float(player_data.get(self.per_36_key, 0) or 0) if self.per_36_key else 0
        consistency = float(player_data.get("consistency_score", 0.3) or 0.3)
        games_played = int(player_data.get("games_played", 0) or 0)
        minutes = float(player_data.get("minutes", 0) or 0)

        if games_played < 5 or minutes < 15:
            return 0.0

        if bet_type == 'over':
            edge = season_avg - prop_line
            if edge >= self.min_edge_over:
                score += 3.5
            elif edge >= 1.5:
                score += 2.5
            elif edge >= 1.0:
                score += 1.5
            elif edge >= 0.5:
                score += 0.5
            else:
                score -= 2.0
                if recent_avg < prop_line + 0.5:
                    return 0.0

            recent_edge = recent_avg - prop_line
            if recent_edge >= self.min_recent_form_edge:
                score += 2.5
            elif recent_edge >= 1.0:
                score += 1.5
            elif recent_avg > season_avg + self.hot_cold_threshold:
                score += 1.0
            elif recent_avg >= prop_line:
                score += 0.5
            else:
                score -= 1.5

            # Per-36 bonus (prop-type specific thresholds)
            if self.prop_type == "points":
                if per_36 >= 25.0: score += 1.5
                elif per_36 >= 20.0: score += 1.0
                elif per_36 >= 15.0: score += 0.5
            elif self.prop_type == "assists":
                if per_36 >= 10.0: score += 1.5
                elif per_36 >= 8.0: score += 1.0
                elif per_36 >= 6.0: score += 0.5
            elif self.prop_type == "rebounds":
                if per_36 >= 12.0: score += 1.5
                elif per_36 >= 10.0: score += 1.0
                elif per_36 >= 8.0: score += 0.5
            elif self.prop_type == "threes":
                if per_36 >= 4.0: score += 1.5
                elif per_36 >= 3.0: score += 1.0
                elif per_36 >= 2.0: score += 0.5

            score += consistency * 0.8

            # Efficiency bonuses
            if self.prop_type == "points":
                fg_pct = float(player_data.get("fg_pct", 0) or 0)
                if fg_pct >= 0.48: score += 0.5
                elif fg_pct >= 0.45: score += 0.3
            elif self.prop_type == "threes":
                fg3_pct = float(player_data.get("fg3_pct", 0) or 0)
                if fg3_pct >= 0.40: score += 0.5
                elif fg3_pct >= 0.38: score += 0.3

            # Opponent factor
            if opponent_factor and self.factor_key:
                f = opponent_factor.get(self.factor_key, 1.0) or 1.0
                if f > 1.05: score += 1.0
                elif f < 0.95: score -= 0.5

        else:  # under
            edge = prop_line - season_avg
            if edge >= self.min_edge_under:
                score += 3.5
            elif edge >= 1.2:
                score += 2.5
            elif edge >= 0.8:
                score += 1.5
            elif edge >= 0.4:
                score += 0.5
            else:
                score -= 2.0
                if recent_avg > prop_line - 0.5:
                    return 0.0

            recent_edge = prop_line - recent_avg
            if recent_edge >= self.min_recent_form_edge:
                score += 2.5
            elif recent_edge >= 1.0:
                score += 1.5
            elif recent_avg < season_avg - self.hot_cold_threshold:
                score += 1.0
            elif recent_avg <= prop_line:
                score += 0.5
            else:
                score -= 1.5

            # Under per-36 bonus (low production = good for under)
            if self.prop_type == "points":
                if per_36 < 15.0: score += 1.0
                elif per_36 < 18.0: score += 0.5
            elif self.prop_type == "assists":
                if per_36 < 4.0: score += 1.0
                elif per_36 < 6.0: score += 0.5
            elif self.prop_type == "rebounds":
                if per_36 < 6.0: score += 1.0
                elif per_36 < 8.0: score += 0.5
            elif self.prop_type == "threes":
                if per_36 < 1.5: score += 1.0
                elif per_36 < 2.0: score += 0.5

            score += (1.0 - consistency) * 0.5

            # Efficiency penalties for under
            if self.prop_type == "threes":
                fg3_pct = float(player_data.get("fg3_pct", 0) or 0)
                if fg3_pct < 0.32: score += 0.3

            if opponent_factor and self.factor_key:
                f = opponent_factor.get(self.factor_key, 1.0) or 1.0
                if f < 0.95: score += 1.0
                elif f > 1.05: score -= 0.5

        final = min(10.0, max(0.0, score))
        if bet_type == 'over' and season_avg < prop_line + 0.5:
            final = min(final, 8.5)
        elif bet_type == 'under' and season_avg > prop_line - 0.5:
            final = min(final, 8.5)
        return round(final, 2)

    def _calculate_combo_ai_score(self, player_data, prop_line, bet_type, opponent_factor=None):
        """AI score for combo props - edge-based only, wider thresholds."""
        score = 4.0
        season_avg = float(player_data.get(self.season_avg_key, 0) or 0)
        recent_avg = float(player_data.get(self.recent_avg_key, 0) or 0)
        games_played = int(player_data.get("games_played", 0) or 0)
        minutes = float(player_data.get("minutes", 0) or 0)

        if games_played < 5 or minutes < 15:
            return 0.0

        if bet_type == 'over':
            edge = season_avg - prop_line
            if edge >= self.min_edge_over:
                score += 3.5
            elif edge >= self.min_edge_over * 0.7:
                score += 2.5
            elif edge >= self.min_edge_over * 0.4:
                score += 1.5
            elif edge >= 0.5:
                score += 0.5
            else:
                score -= 2.0
                if recent_avg < prop_line + 1.0:
                    return 0.0

            recent_edge = recent_avg - prop_line
            if recent_edge >= self.min_recent_form_edge:
                score += 2.5
            elif recent_edge >= self.min_recent_form_edge * 0.6:
                score += 1.5
            elif recent_avg > season_avg + self.hot_cold_threshold:
                score += 1.0
            elif recent_avg >= prop_line:
                score += 0.5
            else:
                score -= 1.5

        else:  # under
            edge = prop_line - season_avg
            if edge >= self.min_edge_under:
                score += 3.5
            elif edge >= self.min_edge_under * 0.7:
                score += 2.5
            elif edge >= self.min_edge_under * 0.4:
                score += 1.5
            elif edge >= 0.5:
                score += 0.5
            else:
                score -= 2.0
                if recent_avg > prop_line - 1.0:
                    return 0.0

            recent_edge = prop_line - recent_avg
            if recent_edge >= self.min_recent_form_edge:
                score += 2.5
            elif recent_edge >= self.min_recent_form_edge * 0.6:
                score += 1.5
            elif recent_avg < season_avg - self.hot_cold_threshold:
                score += 1.0
            elif recent_avg <= prop_line:
                score += 0.5
            else:
                score -= 1.5

        final = min(10.0, max(0.0, score))
        if bet_type == 'over' and season_avg < prop_line + 1.0:
            final = min(final, 8.5)
        elif bet_type == 'under' and season_avg > prop_line - 1.0:
            final = min(final, 8.5)
        return round(final, 2)

    # ── EV Calculation ────────────────────────────────────────────────────────

    @staticmethod
    def calculate_ev(ai_score, prop_line, season_avg, recent_avg, odds, bet_type):
        if odds is None:
            odds = -110
        if odds > 0:
            implied_prob = 100 / (odds + 100)
        else:
            implied_prob = abs(odds) / (abs(odds) + 100)

        base_prob = 0.50
        ai_mult = max(0, (ai_score - 9.0) / 1.0)
        edge = (season_avg - prop_line) if bet_type == 'over' else (prop_line - season_avg)
        edge_factor = min(abs(edge) / 2.0, 1.0)

        recent_factor = 0.0
        if bet_type == 'over' and recent_avg > season_avg:
            recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
        elif bet_type == 'under' and recent_avg < season_avg:
            recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)

        true_prob = base_prob + (ai_mult * 0.15) + (edge_factor * 0.15) + recent_factor
        true_prob = min(max(true_prob, 0.40), 0.70)

        if odds > 0:
            ev = (true_prob * (odds / 100)) - (1 - true_prob)
        else:
            ev = (true_prob * (100 / abs(odds))) - (1 - true_prob)

        return ev * 100, true_prob * 100

    @staticmethod
    def calculate_probability_edge(ai_score, season_avg, recent_avg, prop_line, odds, bet_type):
        if odds is None:
            odds = -110
        if odds > 0:
            implied_prob = 100 / (odds + 100)
        else:
            implied_prob = abs(odds) / (abs(odds) + 100)

        base_prob = 0.50
        ai_mult = max(0, (ai_score - 9.0) / 1.0)
        edge = (season_avg - prop_line) if bet_type == 'over' else (prop_line - season_avg)
        edge_factor = min(abs(edge) / 2.0, 1.0)

        recent_factor = 0.0
        if bet_type == 'over' and recent_avg > season_avg:
            recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
        elif bet_type == 'under' and recent_avg < season_avg:
            recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)

        model_prob = base_prob + (ai_mult * 0.15) + (edge_factor * 0.15) + recent_factor
        model_prob = min(max(model_prob, 0.40), 0.70)
        return abs(model_prob - implied_prob)

    @staticmethod
    def calculate_ai_rating(play):
        prob_edge = play.get('probability_edge')
        if prob_edge is None:
            prob_edge = abs(play.get('ev', 0)) / 100.0

        normalized_edge = min(5.0, prob_edge / 0.03) if prob_edge < 0.15 else 5.0
        normalized_edge = max(0.0, normalized_edge)

        data_quality = 1.0 if play.get('ai_score', 0) >= 9.0 else 0.85
        ai_score = play.get('ai_score', 0)
        ev = abs(play.get('ev', 0))

        if ai_score >= 9.8 and ev >= 12: confidence = 1.12
        elif ai_score >= 9.5 and ev >= 10: confidence = 1.08
        elif ai_score >= 9.0 and ev >= 8: confidence = 1.05
        elif ai_score >= 9.0: confidence = 1.0
        else: confidence = 0.95
        confidence = max(0.9, min(1.15, confidence))

        composite = normalized_edge * data_quality * confidence
        rating = 2.3 + (composite / 5.0) * 2.6
        return round(max(2.3, min(4.9, rating)), 1)

    # ── Analysis ──────────────────────────────────────────────────────────────

    def analyze_props(self, props_list, player_stats, opp_factors):
        print(f"\n{Colors.CYAN}Analyzing {len(props_list)} {self.display_name} props...{Colors.END}")
        over_plays, under_plays = [], []
        skipped_no_stats = skipped_low = 0
        current_time = datetime.now(pytz.utc)

        for prop in props_list:
            player_name = prop.get("player")
            gt_str = prop.get("game_time")
            if gt_str:
                try:
                    if 'Z' in gt_str:
                        gt_dt = datetime.fromisoformat(gt_str.replace('Z', '+00:00'))
                    else:
                        gt_dt = datetime.fromisoformat(gt_str)
                    if gt_dt.tzinfo is None:
                        gt_dt = gt_dt.replace(tzinfo=pytz.utc)
                    else:
                        gt_dt = gt_dt.astimezone(pytz.utc)
                    if gt_dt < (current_time - timedelta(hours=12)):
                        continue
                except Exception:
                    pass

            prop_line = prop.get('prop_line')
            opponent_team = prop.get('opponent')
            if not player_name or prop_line is None:
                continue

            player_data = player_stats.get(player_name)
            if not player_data:
                for name, stats in player_stats.items():
                    if (player_name.split()[-1].lower() in name.lower() or
                        name.split()[-1].lower() in player_name.lower()):
                        player_data = stats
                        break
                if not player_data:
                    skipped_no_stats += 1
                    continue

            opp_data = None
            if opponent_team and opp_factors:
                opp_data = opp_factors.get(opponent_team)
                if not opp_data:
                    for tn, f in opp_factors.items():
                        if opponent_team.lower() in tn.lower() or tn.lower() in opponent_team.lower():
                            opp_data = f
                            break

            season_avg = float(player_data.get(self.season_avg_key, 0) or 0)
            recent_avg = float(player_data.get(self.recent_avg_key, 0) or 0)

            # OVER
            over_score = self.calculate_ai_score(player_data, prop_line, 'over', opp_data)
            if over_score >= self.min_ai_score:
                if season_avg >= prop_line + 0.5 and recent_avg >= prop_line + 0.3:
                    over_odds = prop.get('over_price') or prop.get('under_price') or -110
                    ev, win_prob = self.calculate_ev(over_score, prop_line, season_avg, recent_avg, over_odds, 'over')
                    prob_edge = self.calculate_probability_edge(over_score, season_avg, recent_avg, prop_line, over_odds, 'over')
                    if ev > 0 and win_prob >= 55:
                        play = {
                            'player': player_name,
                            'prop': f"OVER {prop_line} {self.prop_unit}",
                            'team': prop.get('team'), 'opponent': opponent_team,
                            'home_team': prop.get('home_team', ''),
                            'away_team': prop.get('away_team', ''),
                            'ai_score': over_score, 'odds': over_odds,
                            'game_time': prop.get('game_time'),
                            'season_avg': round(season_avg, 2), 'recent_avg': round(recent_avg, 2),
                            'edge': round(season_avg - prop_line, 2),
                            'ev': round(ev, 2), 'win_prob_percent': round(win_prob, 1),
                            'probability_edge': prob_edge,
                        }
                        play['ai_rating'] = self.calculate_ai_rating(play)
                        over_plays.append(play)
                    else:
                        skipped_low += 1
                else:
                    skipped_low += 1
            else:
                skipped_low += 1

            # UNDER
            under_score = self.calculate_ai_score(player_data, prop_line, 'under', opp_data)
            if under_score >= self.min_ai_score:
                if season_avg <= prop_line - 0.5 and recent_avg <= prop_line - 0.3:
                    under_odds = prop.get('under_price') or prop.get('over_price') or -110
                    ev, win_prob = self.calculate_ev(under_score, prop_line, season_avg, recent_avg, under_odds, 'under')
                    prob_edge = self.calculate_probability_edge(under_score, season_avg, recent_avg, prop_line, under_odds, 'under')
                    if ev > 0 and win_prob >= 55:
                        play = {
                            'player': player_name,
                            'prop': f"UNDER {prop_line} {self.prop_unit}",
                            'team': prop.get('team'), 'opponent': opponent_team,
                            'home_team': prop.get('home_team', ''),
                            'away_team': prop.get('away_team', ''),
                            'ai_score': under_score, 'odds': under_odds,
                            'game_time': prop.get('game_time'),
                            'season_avg': round(season_avg, 2), 'recent_avg': round(recent_avg, 2),
                            'edge': round(prop_line - season_avg, 2),
                            'ev': round(ev, 2), 'win_prob_percent': round(win_prob, 1),
                            'probability_edge': prob_edge,
                        }
                        play['ai_rating'] = self.calculate_ai_rating(play)
                        under_plays.append(play)
                    else:
                        skipped_low += 1
                else:
                    skipped_low += 1
            else:
                skipped_low += 1

        # Deduplicate
        for plays in [over_plays, under_plays]:
            deduped = {}
            for play in plays:
                pn = play['player'].strip()
                if pn not in deduped:
                    deduped[pn] = play
                else:
                    if play.get('ai_rating', 0) > deduped[pn].get('ai_rating', 0):
                        deduped[pn] = play
                    elif play.get('ai_rating', 0) == deduped[pn].get('ai_rating', 0):
                        if play.get('ai_score', 0) > deduped[pn].get('ai_score', 0):
                            deduped[pn] = play
            plays.clear()
            plays.extend(deduped.values())

        over_plays.sort(key=lambda x: (x.get('ai_rating', 0), x.get('ai_score', 0)), reverse=True)
        under_plays.sort(key=lambda x: (x.get('ai_rating', 0), x.get('ai_score', 0)), reverse=True)
        over_plays[:] = over_plays[:self.top_plays]
        under_plays[:] = under_plays[:self.top_plays]

        print(f"{Colors.GREEN}✓ Found {len(over_plays)} OVER, {len(under_plays)} UNDER plays{Colors.END}")
        return over_plays, under_plays

    # ── HTML Generation ───────────────────────────────────────────────────────

    def generate_html(self, over_plays, under_plays, stats=None, tracking_data=None,
                      opp_factors=None, player_stats=None):
        et = pytz.timezone('US/Eastern')
        now = datetime.now(et)

        if stats is None:
            stats = {'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0, 'total_profit': 0, 'roi_pct': 0,
                     'over_record': '0-0', 'over_win_rate': 0, 'over_roi': 0,
                     'under_record': '0-0', 'under_win_rate': 0, 'under_roi': 0}

        s_wins = stats.get('wins', 0)
        s_losses = stats.get('losses', 0)
        s_wr = round(stats.get('win_rate', 0.0), 1)
        s_prof = stats.get('total_profit', 0.0)
        s_prof_str = f"{s_prof:+.1f}u"
        s_prof_color = 'var(--accent-green)' if s_prof > 0 else 'var(--accent-red)'

        # Build nav pills for all 8 prop types
        nav_items = [
            ("nba_points_props.html", "Points"),
            ("nba_assists_props.html", "Assists"),
            ("nba_rebounds_props.html", "Rebounds"),
            ("nba_3pt_props.html", "3-Pointers"),
            ("nba_pra_props.html", "PRA"),
            ("nba_points_rebounds_props.html", "P+R"),
            ("nba_points_assists_props.html", "P+A"),
            ("nba_rebounds_assists_props.html", "R+A"),
        ]
        nav_html = ""
        for href, label in nav_items:
            active = " active" if href == os.path.basename(self.output_html) else ""
            nav_html += f'        <a href="{href}" class="nav-pill{active}">{label}</a>\n'

        css = _get_css()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics - NBA {self.display_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>{css}</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">NBA {self.display_name} Model</div>
            <div class="date-sub">Profitable Version &bull; Season {CURRENT_SEASON}</div>
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
{nav_html}    </div>
"""

        # Summary stats
        if stats.get('total', 0) > 0:
            roi_pct = stats.get('roi_pct', 0)
            roi_cc = "txt-green" if roi_pct > 0 else "txt-red"
            roi_sign = '+' if roi_pct > 0 else ''
            html += f"""
    <section>
        <div class="summary-grid">
            <div class="stat-box"><div class="stat-label">Season ROI</div><div class="stat-value {roi_cc}">{roi_sign}{roi_pct:.1f}%</div></div>
            <div class="stat-box"><div class="stat-label">Win Rate</div><div class="stat-value">{stats.get('win_rate', 0):.1f}%</div></div>
            <div class="stat-box"><div class="stat-label">Record</div><div class="stat-value">{s_wins}-{s_losses}</div></div>
        </div>
    </section>
"""

        # Generate play cards
        unit = self.prop_unit
        player_stats_lookup = player_stats or {}
        defense_lookup = opp_factors or {}

        if over_plays:
            html += f'<section><div class="section-title">Top Value Plays <span class="highlight">Min AI Score: {self.min_ai_score}</span></div>'
            for play in over_plays:
                html += self._render_play_card(play, 'over', unit, player_stats_lookup, defense_lookup, tracking_data)
            html += '</section>'

        if under_plays:
            html += '<section><div class="section-title">Under Plays</div>'
            for play in under_plays:
                html += self._render_play_card(play, 'under', unit, player_stats_lookup, defense_lookup, tracking_data)
            html += '</section>'

        # Daily tracking
        if stats and 'today' in stats:
            t = stats.get('today', {'record': '0-0', 'profit': 0, 'roi': 0})
            y = stats.get('yesterday', {'record': '0-0', 'profit': 0, 'roi': 0})
            tc = "txt-green" if t['profit'] > 0 else ("txt-red" if t['profit'] < 0 else "")
            yc = "txt-green" if y['profit'] > 0 else ("txt-red" if y['profit'] < 0 else "")
            html += f"""
        <section style="margin-top: 2rem;">
            <div class="section-title">Daily Performance</div>
            <div class="metrics-grid" style="grid-template-columns: repeat(2, 1fr);">
                <div class="prop-card" style="padding: 1rem; margin:0;">
                    <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">TODAY</div>
                    <div style="text-align:center;"><div style="font-weight:700; font-size:1.1rem;">{t['record']}</div>
                    <div class="{tc}">{t['profit']:+.1f}u</div>
                    <div style="font-size:0.8rem; color:var(--text-secondary);">{t['roi']:.1f}% ROI</div></div>
                </div>
                <div class="prop-card" style="padding: 1rem; margin:0;">
                    <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">YESTERDAY</div>
                    <div style="text-align:center;"><div style="font-weight:700; font-size:1.1rem;">{y['record']}</div>
                    <div class="{yc}">{y['profit']:+.1f}u</div>
                    <div style="font-size:0.8rem; color:var(--text-secondary);">{y['roi']:.1f}% ROI</div></div>
                </div>
            </div>
        </section>
"""

        # Recent form (L10/L20/L50)
        if tracking_data:
            completed_picks = [p for p in tracking_data.get('picks', []) if p.get('status', '').lower() in ['win', 'loss']]
            completed_picks.sort(key=lambda x: x.get('game_time', ''), reverse=True)
            l10 = _calc_recent_perf(completed_picks, 10)
            l20 = _calc_recent_perf(completed_picks, 20)
            l50 = _calc_recent_perf(completed_picks, 50)
            html += _render_recent_form(l10, l20, l50)

        # Performance section
        if stats.get('total', 0) > 0:
            or_rec = stats['over_record']
            or_roi = stats['over_roi']
            ur_rec = stats['under_record']
            ur_roi = stats['under_roi']
            or_cc = "txt-green" if or_roi > 0 else "txt-red"
            ur_cc = "txt-green" if ur_roi > 0 else "txt-red"
            or_s = '+' if or_roi > 0 else ''
            ur_s = '+' if ur_roi > 0 else ''
            roi_pct = stats['roi_pct']
            roi_cc = "txt-green" if roi_pct > 0 else "txt-red"
            roi_s = '+' if roi_pct > 0 else ''
            html += f"""
    <section>
        <div class="section-title">NBA {self.display_name} Model Performance</div>
        <div class="summary-grid">
            <div class="stat-box"><div class="stat-label">Overall Record</div><div class="stat-value">{s_wins}-{s_losses}</div></div>
            <div class="stat-box"><div class="stat-label">ROI</div><div class="stat-value {roi_cc}">{roi_s}{roi_pct:.1f}%</div></div>
            <div class="stat-box"><div class="stat-label">OVER: {or_rec}</div><div class="stat-value {or_cc}">{or_s}{or_roi:.1f}% ROI</div></div>
            <div class="stat-box"><div class="stat-label">UNDER: {ur_rec}</div><div class="stat-value {ur_cc}">{ur_s}{ur_roi:.1f}% ROI</div></div>
        </div>
    </section>
"""

        html += "</div></body></html>"
        return html

    def _render_play_card(self, play, bet_type, unit, player_stats_lookup, defense_lookup, tracking_data):
        prop_str = play.get('prop', '')
        line_match = re.search(rf'(\d+\.?\d*)\s*{re.escape(unit)}', prop_str)
        prop_line_display = line_match.group(0) if line_match else prop_str.replace('OVER ', '').replace('UNDER ', '')

        game_dt = _format_game_datetime(play.get('game_time', ''))
        team_abbrev = TEAM_ABBREV_MAP.get(play.get('team', ''), 'nba')
        logo_url = f"https://a.espncdn.com/i/teamlogos/nba/500/{team_abbrev}.png"

        short_team = SHORT_TEAM_NAMES.get(play.get('team', ''), play.get('team', ''))
        short_opp = SHORT_TEAM_NAMES.get(play.get('opponent', ''), play.get('opponent', ''))
        if play.get('team') == play.get('home_team', ''):
            matchup = f"{short_opp} @ {short_team}"
        else:
            matchup = f"{short_team} @ {short_opp}"

        ai_score = play.get('ai_score', 0)
        season_avg = play.get('season_avg', 0)
        recent_avg = play.get('recent_avg', 0)
        edge = play.get('edge', 0)
        ev = play.get('ev', 0)
        ev_display = f"{ev:+.1f}%" if ev != 0 else "0.0%"
        ev_cc = "txt-green" if ev > 0 else "txt-red" if ev < 0 else ""
        win_prob = min(70, max(40, 50 + (ai_score - 9.5) * 3))

        glow = "glow-green" if ai_score >= 10.0 else ("glow-blue" if ai_score >= 9.0 else "")
        color_class = "txt-green" if bet_type == 'over' else "txt-red"
        direction = "OVER" if bet_type == 'over' else "UNDER"

        model_pred = season_avg + edge if bet_type == 'over' else season_avg - abs(edge)

        def fmt_odds(v):
            if v is None: return 'N/A'
            try:
                o = int(v)
                return f'+{o}' if o > 0 else str(o)
            except: return str(v)

        # Recent avg color
        if bet_type == 'over':
            ra_cc = 'txt-green' if recent_avg > season_avg else 'txt-red'
        else:
            ra_cc = 'txt-green' if recent_avg < season_avg else 'txt-red'

        # Tags
        tags = _generate_tags(play, player_stats_lookup.get(play.get('player')),
                              defense_lookup, play.get('opponent'), self.prop_type, self.hot_cold_threshold)

        tags_html = ""
        for tag in tags:
            tags_html += f'<span class="tag tag-{tag["color"]}">{tag["text"]}</span>\n'

        return f"""
        <div class="prop-card {glow}">
            <div class="card-header">
                <div class="header-left">
                    <img src="{logo_url}" alt="" class="team-logo">
                    <div class="player-info">
                        <h2>{play.get('player', '')}</h2>
                        <div class="matchup-info">{matchup}</div>
                    </div>
                </div>
                <div class="game-meta"><div class="game-date-time">{game_dt}</div></div>
            </div>
            <div class="card-body">
                <div class="bet-main-row">
                    <div class="bet-selection">
                        <span class="{color_class}">{direction}</span>
                        <span class="line">{prop_line_display}</span>
                        <span class="bet-odds">{fmt_odds(play.get('odds'))}</span>
                    </div>
                </div>
                <div class="model-subtext">
                    Model Predicts: <strong>{model_pred:.1f} {unit}</strong> (Edge: {edge:+.1f})
                </div>
                <div class="stats-row">
                    <div class="stat-item"><div class="stat-title">Season Avg</div><div class="stat-val">{season_avg}</div></div>
                    <div class="stat-item"><div class="stat-title">Last 10 Avg</div><div class="stat-val {ra_cc}">{recent_avg}</div></div>
                </div>
                <div class="metrics-grid">
                    <div class="metric-item"><span class="metric-lbl">AI SCORE</span><span class="metric-val txt-green">{ai_score:.1f}</span></div>
                    <div class="metric-item"><span class="metric-lbl">EV</span><span class="metric-val {ev_cc}">{ev_display}</span></div>
                    <div class="metric-item"><span class="metric-lbl">WIN %</span><span class="metric-val">{int(win_prob)}%</span></div>
                </div>
                <div class="tags-container">{tags_html}</div>
            </div>
        </div>
"""

    def save_html(self, html_content):
        try:
            with open(self.output_html, 'w') as f:
                f.write(html_content)
            print(f"\n{Colors.GREEN}✓ HTML saved: {self.output_html}{Colors.END}")
            return True
        except Exception as e:
            print(f"\n{Colors.RED}✗ Error saving HTML: {e}{Colors.END}")
            return False

    # ── Git Push ──────────────────────────────────────────────────────────────

    def push_to_git(self):
        try:
            root = os.path.dirname(SCRIPT_DIR)
            html_rel = os.path.relpath(self.output_html, root)
            track_rel = os.path.relpath(self.tracking_file, root)

            subprocess.run(["git", "add", html_rel, track_rel], cwd=root,
                           capture_output=True, timeout=15)
            result = subprocess.run(
                ["git", "commit", "-m", f"Update {self.display_name} props - {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
                cwd=root, capture_output=True, timeout=15
            )
            if result.returncode == 0:
                subprocess.run(["git", "push"], cwd=root, capture_output=True, timeout=30)
                print(f"{Colors.GREEN}✓ Pushed {self.display_name} to git{Colors.END}")
            else:
                stderr = result.stderr.decode() if result.stderr else ""
                if "nothing to commit" in stderr:
                    print(f"{Colors.YELLOW}  No changes to commit{Colors.END}")
                else:
                    print(f"{Colors.YELLOW}  Git commit: {stderr.strip()}{Colors.END}")
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Git push failed: {e}{Colors.END}")

    # ── Main Run ──────────────────────────────────────────────────────────────

    def run(self):
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}NBA {self.display_name.upper()} PROPS A.I. MODEL{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")

        self.grade_pending_picks()
        self.backfill_profit_loss()

        player_stats = self.get_player_stats()
        opp_factors = self.get_opponent_factors()
        props_list = self.get_player_props(player_stats)

        over_plays, under_plays = self.analyze_props(props_list, player_stats, opp_factors)
        self.track_new_picks(over_plays, under_plays)

        tracking_data = self.load_tracking_data()
        stats = self.calculate_tracking_stats(tracking_data)

        # Reconstruct display list from tracking
        display_plays = self._get_active_plays_for_display(tracking_data)
        display_over = [p for p in display_plays if 'OVER' in p.get('prop', '')]
        display_under = [p for p in display_plays if 'UNDER' in p.get('prop', '')]
        display_over.sort(key=lambda x: x.get('ai_rating', 0), reverse=True)
        display_under.sort(key=lambda x: x.get('ai_rating', 0), reverse=True)

        # Print to console
        if over_plays:
            print(f"\n{Colors.BOLD}{Colors.GREEN}TOP OVER PLAYS{Colors.END}")
            for i, play in enumerate(over_plays[:10], 1):
                print(f"  {i:2d}. {play['player']:25s} | {play['prop']:20s} | AI: {play['ai_score']:.2f}")
        if under_plays:
            print(f"\n{Colors.BOLD}{Colors.RED}TOP UNDER PLAYS{Colors.END}")
            for i, play in enumerate(under_plays[:10], 1):
                print(f"  {i:2d}. {play['player']:25s} | {play['prop']:20s} | AI: {play['ai_score']:.2f}")

        # Always generate HTML (even with 0 plays)
        html = self.generate_html(display_over, display_under, stats, tracking_data, opp_factors, player_stats)
        self.save_html(html)
        self.push_to_git()

        print(f"\n{Colors.BOLD}{Colors.GREEN}✓ {self.display_name} model complete!{Colors.END}\n")

    def _get_active_plays_for_display(self, tracking_data):
        display_plays = []
        if not tracking_data or 'picks' not in tracking_data:
            return display_plays

        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        today_date = now.date()

        for p in tracking_data['picks']:
            try:
                g_time = p.get('game_time') or p.get('game_date')
                if not g_time:
                    continue
                if 'Z' in g_time:
                    dt = datetime.fromisoformat(g_time.replace('Z', '+00:00')).astimezone(et_tz)
                else:
                    dt = datetime.fromisoformat(g_time)
                p_date = dt.date()
                status = (p.get('status') or 'pending').lower()

                should_show = False
                if p_date == today_date and status == 'pending' and dt > now:
                    should_show = True
                elif p_date > today_date and status == 'pending':
                    should_show = True

                if should_show:
                    line = p.get('prop_line', 0)
                    b_type = p.get('bet_type', 'OVER').upper()
                    edge = p.get('edge')
                    if edge is None and p.get('season_avg'):
                        try:
                            val = float(p.get('season_avg'))
                            edge = val - float(line) if 'OVER' in b_type else float(line) - val
                        except Exception:
                            edge = 0

                    display_plays.append({
                        'player': p.get('player'),
                        'prop': f"{b_type} {line} {self.prop_unit}",
                        'game_time': g_time,
                        'team': p.get('team'), 'opponent': p.get('opponent'),
                        'ai_score': p.get('ai_score', 9.5),
                        'odds': p.get('odds'),
                        'season_avg': p.get('season_avg', 0),
                        'recent_avg': p.get('recent_avg', 0),
                        'edge': edge if edge is not None else 0,
                        'ev': p.get('ev', 0),
                        'ai_rating': p.get('ai_rating', 2.5),
                        'status': status,
                    })
            except Exception:
                continue
        return display_plays


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _match_player_to_team(player_name, home_team, away_team, rosters, player_stats=None):
    full_lower = player_name.lower()
    if player_stats:
        p_data = player_stats.get(player_name)
        if not p_data:
            for name, data in player_stats.items():
                if player_name in name or name in player_name:
                    p_data = data
                    break
        if p_data:
            abbrev = p_data.get('team', '').upper()
            nick = ABBREV_TO_NICKNAME.get(abbrev, '')
            if nick and nick in home_team:
                return home_team, away_team
            if nick and nick in away_team:
                return away_team, home_team

    for team in [home_team, away_team]:
        other = away_team if team == home_team else home_team
        if team in rosters:
            for rn in rosters[team]:
                if rn.lower() in full_lower or full_lower.endswith(rn.lower()):
                    return team, other
    return home_team, away_team


def _format_game_datetime(game_time_str):
    try:
        if not game_time_str:
            return 'TBD'
        dt_obj = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
        et_tz = pytz.timezone('US/Eastern')
        dt_et = dt_obj.astimezone(et_tz)
        try:
            return dt_et.strftime('%a, %b %d • %-I:%M %p ET')
        except ValueError:
            return dt_et.strftime('%a, %b %d • %#I:%M %p ET')
    except Exception:
        return game_time_str if game_time_str else 'TBD'


def _generate_tags(play, player_data, defense_lookup, opponent_team, prop_type, hot_cold_threshold):
    tags = []
    opp_data = None
    if opponent_team and defense_lookup:
        opp_data = defense_lookup.get(opponent_team)
        if not opp_data:
            for tn, f in defense_lookup.items():
                if opponent_team.lower() in tn.lower() or tn.lower() in opponent_team.lower():
                    opp_data = f
                    break

    if opp_data and prop_type == "points":
        opp_pts = opp_data.get('opp_pts_allowed', 110)
        if opp_pts >= 120:
            tags.append({"text": f"Opp allows {opp_pts:.1f} PPG (Weak)", "color": "green"})
        elif opp_pts <= 108:
            tags.append({"text": f"Opp allows {opp_pts:.1f} PPG (Elite)", "color": "red"})
        pace = opp_data.get('pace', 100)
        if pace >= 102:
            tags.append({"text": "High Pace Matchup", "color": "blue"})

    season_avg = play.get('season_avg', 0)
    recent_avg = play.get('recent_avg', 0)
    if recent_avg > 0:
        diff = recent_avg - season_avg
        if diff > hot_cold_threshold + 1:
            tags.append({"text": f"Avg {recent_avg:.1f} L10 (Hot)", "color": "green"})
        elif diff < -(hot_cold_threshold + 1):
            tags.append({"text": f"Avg {recent_avg:.1f} L10 (Cold)", "color": "red"})
        else:
            tags.append({"text": f"Avg {recent_avg:.1f} L10", "color": "blue"})

    edge = play.get('edge', 0)
    if abs(edge) >= 4.0:
        tags.append({"text": f"Strong Edge {edge:+.1f}", "color": "green" if edge > 0 else "red"})
    elif abs(edge) >= 2.0:
        tags.append({"text": f"Edge {edge:+.1f}", "color": "green" if edge > 0 else "blue"})

    return tags


def _calc_recent_perf(completed, count):
    recent = completed[:count] if len(completed) >= count else completed
    wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
    total = wins + losses
    profit_cents = sum(p.get('profit_loss', 0) for p in recent if p.get('profit_loss') is not None)
    profit_units = profit_cents / 100.0
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (profit_cents / (total * 100) * 100) if total > 0 else 0
    return {'record': f"{wins}-{losses}", 'win_rate': win_rate, 'profit': profit_units, 'roi': roi}


def _render_recent_form(l10, l20, l50):
    def _cls(val, threshold=0):
        return 'good' if val > threshold else ('text-red' if val < 0 else '')

    return f'''
        <div class="tracking-section">
            <div class="tracking-header">Recent Form</div>
            <div class="metrics-row" style="margin-bottom: 1.5rem;">
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 10</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div><div class="metric-label">Record</div><div class="metric-value">{l10['record']}</div></div>
                        <div><div class="metric-label">Win Rate</div><div class="metric-value {_cls(l10['win_rate'], 55)}">{round(l10['win_rate'])}%</div></div>
                        <div><div class="metric-label">Profit</div><div class="metric-value {_cls(l10['profit'])}">{l10['profit']:+.1f}u</div></div>
                        <div><div class="metric-label">ROI</div><div class="metric-value {_cls(l10['roi'])}">{l10['roi']:+.1f}%</div></div>
                    </div>
                </div>
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 20</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div><div class="metric-label">Record</div><div class="metric-value">{l20['record']}</div></div>
                        <div><div class="metric-label">Win Rate</div><div class="metric-value {_cls(l20['win_rate'], 55)}">{round(l20['win_rate'])}%</div></div>
                        <div><div class="metric-label">Profit</div><div class="metric-value {_cls(l20['profit'])}">{l20['profit']:+.1f}u</div></div>
                        <div><div class="metric-label">ROI</div><div class="metric-value {_cls(l20['roi'])}">{l20['roi']:+.1f}%</div></div>
                    </div>
                </div>
                <div class="prop-card" style="flex: 1; padding: 1.5rem;">
                    <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 50</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                        <div><div class="metric-label">Record</div><div class="metric-value">{l50['record']}</div></div>
                        <div><div class="metric-label">Win Rate</div><div class="metric-value {_cls(l50['win_rate'], 55)}">{round(l50['win_rate'])}%</div></div>
                        <div><div class="metric-label">Profit</div><div class="metric-value {_cls(l50['profit'])}">{l50['profit']:+.1f}u</div></div>
                        <div><div class="metric-label">ROI</div><div class="metric-value {_cls(l50['roi'])}">{l50['roi']:+.1f}%</div></div>
                    </div>
                </div>
            </div>
        </div>
    '''


def _get_css():
    return """
        :root {
            --bg-main: #121212; --bg-card: #1e1e1e; --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff; --text-secondary: #b3b3b3;
            --accent-green: #4ade80; --accent-red: #f87171; --accent-blue: #60a5fa;
            --border-color: #333333;
        }
        body { margin: 0; padding: 20px; font-family: 'Inter', sans-serif; background-color: var(--bg-main); color: var(--text-primary); -webkit-font-smoothing: antialiased; }
        .container { max-width: 650px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; }
        h1 { margin: 0; font-size: 22px; font-weight: 700; margin-bottom: 5px; }
        .subheader { font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 5px; }
        .date-sub { color: var(--text-secondary); font-size: 13px; margin-top: 5px; }
        .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 25px; }
        .stat-box { background-color: var(--bg-card); border-radius: 12px; padding: 12px; text-align: center; border: 1px solid var(--border-color); }
        .stat-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 4px; }
        .stat-value { font-size: 18px; font-weight: 700; }
        .section-title { font-size: 16px; margin-bottom: 12px; display: flex; align-items: center; }
        .section-title span.highlight { color: var(--accent-green); margin-left: 8px; font-size: 13px; }
        .prop-card { background-color: var(--bg-card); border-radius: 16px; overflow: hidden; margin-bottom: 20px; border: 1px solid var(--border-color); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); }
        .card-header { padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; background-color: var(--bg-card-secondary); border-bottom: 1px solid var(--border-color); }
        .header-left { display: flex; align-items: center; gap: 10px; }
        .team-logo { width: 40px; height: 40px; border-radius: 50%; padding: 2px; object-fit: contain; }
        .player-info h2 { margin: 0; font-size: 16px; line-height: 1.2; }
        .matchup-info { color: var(--text-secondary); font-size: 12px; margin-top: 2px; }
        .game-meta { text-align: right; }
        .game-date-time { font-size: 11px; color: var(--text-secondary); background: #333; padding: 4px 8px; border-radius: 4px; font-weight: 500; white-space: nowrap; }
        .card-body { padding: 16px; }
        .bet-main-row { margin-bottom: 12px; }
        .bet-selection { font-size: 20px; font-weight: 800; }
        .bet-selection .line { color: var(--text-primary); }
        .bet-odds { font-size: 16px; color: var(--text-secondary); font-weight: 500; margin-left: 8px; }
        .model-subtext { color: var(--text-secondary); font-size: 13px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border-color); }
        .model-subtext strong { color: var(--text-primary); }
        .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 16px; }
        .metric-item { background-color: var(--bg-main); padding: 8px; border-radius: 8px; text-align: center; }
        .metric-lbl { display: block; font-size: 10px; color: var(--text-secondary); margin-bottom: 2px; }
        .metric-val { font-size: 14px; font-weight: 700; }
        .stats-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background-color: var(--bg-main); padding: 10px; border-radius: 8px; margin-bottom: 15px; border: 1px solid var(--border-color); }
        .stat-item { text-align: center; }
        .stat-title { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 2px; letter-spacing: 0.5px; }
        .stat-val { font-size: 15px; font-weight: 700; }
        .tags-container { display: flex; flex-wrap: wrap; gap: 6px; }
        .tag { font-size: 11px; padding: 4px 8px; border-radius: 4px; font-weight: 500; }
        .txt-green { color: var(--accent-green); }
        .txt-red { color: var(--accent-red); }
        .tag-green { background-color: rgba(74, 222, 128, 0.15); color: var(--accent-green); }
        .tag-red { background-color: rgba(248, 113, 113, 0.15); color: var(--accent-red); }
        .tag-blue { background-color: rgba(96, 165, 250, 0.15); color: var(--accent-blue); }
        .metric-title { font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.05em; margin-bottom: 4px; font-weight: 600; }
        .metric-label { font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.05em; margin-bottom: 4px; font-weight: 600; }
        .metric-value { font-size: 1rem; font-weight: 800; color: var(--text-primary); }
        .metric-value.good { color: var(--accent-green); }
        .text-red { color: var(--accent-red); }
        .tracking-section { margin-top: 2.5rem; }
        .tracking-header { font-size: 1.25rem; font-weight: 700; color: var(--text-primary); margin-bottom: 1.25rem; border-bottom: 2px solid var(--border-color); padding-bottom: 0.5rem; }
        .metrics-row { display: flex; gap: 0.75rem; margin-top: 1.25rem; }
        .nav-bar { display: flex; gap: 10px; margin-bottom: 25px; overflow-x: auto; padding-bottom: 5px; }
        .nav-pill { padding: 8px 16px; background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: 20px; color: var(--text-secondary); text-decoration: none; font-size: 13px; font-weight: 500; transition: all 0.2s; white-space: nowrap; }
        .nav-pill:hover, .nav-pill.active { background-color: var(--bg-card-secondary); color: var(--text-primary); border-color: var(--text-primary); }
        .glow-green { box-shadow: 0 0 15px rgba(74, 222, 128, 0.15); border: 1px solid rgba(74, 222, 128, 0.3); }
        .glow-blue { box-shadow: 0 0 15px rgba(96, 165, 250, 0.15); border: 1px solid rgba(96, 165, 250, 0.3); }
        @media (max-width: 600px) { .summary-grid { grid-template-columns: repeat(2, 1fr); } .stat-box:last-child { grid-column: span 2; } }
    """
