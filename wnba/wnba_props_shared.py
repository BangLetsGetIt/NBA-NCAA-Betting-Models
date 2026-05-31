#!/usr/bin/env python3
"""WNBA Props Shared Engine
Stats: ESPN WNBA box scores (free, no key)
Odds:  The Odds API - basketball_wnba (existing key)
Props: Points, Rebounds, Assists
"""

import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta

import pytz
import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(SCRIPT_DIR), '.env'))

ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')
ESPN_BASE = 'https://site.api.espn.com/apis/site/v2/sports/basketball/wnba'
ODDS_BASE = 'https://api.the-odds-api.com/v4'

SEASON_START = '2026-05-01'   # scan from here to build averages
RECENT_GAMES = 10
CACHE_TTL_HOURS = 4

# ── Prop configurations ───────────────────────────────────────────────────────

PROP_CONFIGS = {
    "points": {
        "market_key": "player_points",
        "stat_col": "PTS",
        "prop_unit": "PTS",
        "display_name": "Points",
        "html_file": "wnba_points_props.html",
        "tracking_file": "wnba_points_props_tracking.json",
        "stats_cache": "wnba_player_stats_cache.json",
        "min_edge": 1.5,
        "top_plays": 10,
    },
    "rebounds": {
        "market_key": "player_rebounds",
        "stat_col": "REB",
        "prop_unit": "REB",
        "display_name": "Rebounds",
        "html_file": "wnba_rebounds_props.html",
        "tracking_file": "wnba_rebounds_props_tracking.json",
        "stats_cache": "wnba_player_stats_cache.json",
        "min_edge": 1.0,
        "top_plays": 8,
    },
    "assists": {
        "market_key": "player_assists",
        "stat_col": "AST",
        "prop_unit": "AST",
        "display_name": "Assists",
        "html_file": "wnba_assists_props.html",
        "tracking_file": "wnba_assists_props_tracking.json",
        "stats_cache": "wnba_player_stats_cache.json",
        "min_edge": 0.8,
        "top_plays": 6,
    },
}

WNBA_TEAM_ABBREVS = {
    'Atlanta Dream': 'atl', 'Chicago Sky': 'chi', 'Connecticut Sun': 'con',
    'Dallas Wings': 'dal', 'Golden State Valkyries': 'gsv', 'Indiana Fever': 'ind',
    'Las Vegas Aces': 'lv', 'Los Angeles Sparks': 'la', 'Minnesota Lynx': 'min',
    'New York Liberty': 'ny', 'Phoenix Mercury': 'phx', 'Portland Fire': 'por',
    'Seattle Storm': 'sea', 'Toronto Tempo': 'tor', 'Washington Mystics': 'was',
}

SHORT_NAMES = {v: k.split()[-1] for k, v in WNBA_TEAM_ABBREVS.items()}


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


# ── ESPN helpers ──────────────────────────────────────────────────────────────

_espn_box_cache: dict = {}   # date_str -> (player_stats, completed_teams)

def _fetch_espn_date(date_str: str):
    """Return (player_stats_dict, completed_teams_set) for a date.
    player_stats_dict: {player_name_lower: {PTS, REB, AST, MIN, team}}
    """
    if date_str in _espn_box_cache:
        return _espn_box_cache[date_str]

    date_compact = date_str.replace('-', '')
    player_stats = {}
    completed_teams = set()

    try:
        sb = requests.get(f"{ESPN_BASE}/scoreboard?dates={date_compact}", timeout=10).json()
    except Exception as e:
        print(f"  ESPN scoreboard error {date_str}: {e}")
        _espn_box_cache[date_str] = ({}, set())
        return {}, set()

    for event in sb.get('events', []):
        game_id = event.get('id')
        comps = event.get('competitions', [{}])[0]
        is_complete = comps.get('status', {}).get('type', {}).get('completed', False)

        for comp in comps.get('competitors', []):
            tname = comp.get('team', {}).get('displayName', '')
            if is_complete and tname:
                completed_teams.add(tname)

        if not game_id or not is_complete:
            continue

        try:
            box = requests.get(f"{ESPN_BASE}/summary?event={game_id}", timeout=10).json()
            for team_block in box.get('boxscore', {}).get('players', []):
                tname = team_block.get('team', {}).get('displayName', '')
                for stat_group in team_block.get('statistics', []):
                    labels = stat_group.get('labels', [])
                    for athlete in stat_group.get('athletes', []):
                        name = athlete.get('athlete', {}).get('displayName', '')
                        if not name:
                            continue
                        raw = athlete.get('stats', [])
                        row = {'team': tname}
                        for i, lbl in enumerate(labels):
                            if i >= len(raw):
                                continue
                            v = raw[i]
                            try:
                                if lbl == '3PT' and '-' in str(v):
                                    row['3PT'] = int(str(v).split('-')[0])
                                elif lbl in ('PTS', 'REB', 'AST', 'OREB', 'DREB',
                                             'STL', 'BLK', 'TO', 'PF'):
                                    row[lbl] = int(float(v)) if v not in ('', '--', None) else 0
                                elif lbl == 'MIN':
                                    row['MIN'] = float(v) if v not in ('', '--', None) else 0.0
                            except (ValueError, TypeError):
                                row[lbl] = 0
                        player_stats[name.lower()] = row
            time.sleep(0.2)
        except Exception as e:
            print(f"  Box score error game {game_id}: {e}")

    result = (player_stats, completed_teams)
    _espn_box_cache[date_str] = result
    return result


# ── Season stats builder ──────────────────────────────────────────────────────

def _build_season_stats(cache_file: str):
    """Build per-player season stats by scraping ESPN box scores since SEASON_START.
    Returns {player_lower: {season_pts, season_reb, season_ast, recent_pts, recent_reb,
                            recent_ast, games_played, team, minutes}}.
    Uses a shared cache file since all prop types need the same underlying data.
    """
    if os.path.exists(cache_file):
        age_h = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))).total_seconds() / 3600
        if age_h < CACHE_TTL_HOURS:
            with open(cache_file) as f:
                return json.load(f)

    print(f"\n{Colors.CYAN}Building WNBA season stats from ESPN box scores...{Colors.END}")
    et_tz = pytz.timezone('US/Eastern')
    today = datetime.now(et_tz).date()
    yesterday = today - timedelta(days=1)

    start = datetime.strptime(SEASON_START, '%Y-%m-%d').date()

    # Accumulate per-player game logs: {player_lower: [stat_row, ...]}
    game_logs: dict = defaultdict(list)

    d = start
    while d <= yesterday:
        date_str = d.strftime('%Y-%m-%d')
        player_day, _ = _fetch_espn_date(date_str)
        for name, row in player_day.items():
            # Skip players who clearly didn't play (DNP = 0 min, 0 everything)
            if row.get('MIN', 0) == 0 and row.get('PTS', 0) == 0:
                continue
            game_logs[name].append(row)
        d += timedelta(days=1)

    # Build averages
    season_stats = {}
    for player, logs in game_logs.items():
        if not logs:
            continue
        gp = len(logs)
        avg = lambda col: round(sum(r.get(col, 0) for r in logs) / gp, 2)
        recent = logs[-RECENT_GAMES:]
        rp = len(recent)
        ravg = lambda col: round(sum(r.get(col, 0) for r in recent) / rp, 2) if rp else avg(col)

        season_stats[player] = {
            'season_pts': avg('PTS'),
            'season_reb': avg('REB'),
            'season_ast': avg('AST'),
            'recent_pts': ravg('PTS'),
            'recent_reb': ravg('REB'),
            'recent_ast': ravg('AST'),
            'games_played': gp,
            'team': logs[-1].get('team', ''),
            'minutes': avg('MIN'),
        }

    with open(cache_file, 'w') as f:
        json.dump(season_stats, f, indent=2)
    print(f"{Colors.GREEN}✓ Built stats for {len(season_stats)} players ({(yesterday - start).days + 1} days scanned){Colors.END}")
    return season_stats


# ── Odds API helpers ──────────────────────────────────────────────────────────

def _get_wnba_props(market_key: str):
    """Fetch WNBA player props for all upcoming games.
    Returns list of {player, team, opponent, prop_line, over_price, under_price,
                     home_team, away_team, game_time}.
    """
    if not ODDS_API_KEY:
        print(f"{Colors.RED}No ODDS_API_KEY set{Colors.END}")
        return []

    # Step 1: get events
    try:
        events_resp = requests.get(
            f"{ODDS_BASE}/sports/basketball_wnba/events",
            params={'apiKey': ODDS_API_KEY},
            timeout=10,
        ).json()
    except Exception as e:
        print(f"{Colors.RED}Odds API events error: {e}{Colors.END}")
        return []

    if not isinstance(events_resp, list):
        print(f"{Colors.YELLOW}No WNBA events: {events_resp}{Colors.END}")
        return []

    all_props = []
    for event in events_resp:
        event_id = event.get('id')
        home_team = event.get('home_team', '')
        away_team = event.get('away_team', '')
        commence_time = event.get('commence_time', '')

        try:
            odds_resp = requests.get(
                f"{ODDS_BASE}/sports/basketball_wnba/events/{event_id}/odds",
                params={
                    'apiKey': ODDS_API_KEY,
                    'regions': 'us',
                    'markets': market_key,
                    'oddsFormat': 'american',
                },
                timeout=10,
            ).json()
        except Exception as e:
            print(f"  Odds fetch error event {event_id}: {e}")
            continue

        bookmakers = odds_resp.get('bookmakers', [])
        if not bookmakers:
            continue

        # Priority: fanduel > draftkings > others
        priority = {'fanduel': 0, 'draftkings': 1}
        bookmakers.sort(key=lambda b: priority.get(b.get('key', ''), 99))

        for book in bookmakers:
            found = False
            for market in book.get('markets', []):
                if market.get('key') != market_key:
                    continue
                found = True
                grouped = {}
                for outcome in market.get('outcomes', []):
                    pn = (outcome.get('description') or '').strip()
                    point = outcome.get('point')
                    if not pn or point is None:
                        continue
                    side = (outcome.get('name') or '').lower()
                    price = outcome.get('price', -110)
                    key = (pn, float(point))
                    if key not in grouped:
                        grouped[key] = {
                            'player': pn,
                            'prop_line': float(point),
                            'over_price': None,
                            'under_price': None,
                            'home_team': home_team,
                            'away_team': away_team,
                            'game_time': commence_time,
                        }
                    if side == 'over':
                        grouped[key]['over_price'] = price
                    elif side == 'under':
                        grouped[key]['under_price'] = price
                all_props.extend(grouped.values())
                break
            if found:
                break

        time.sleep(0.15)

    # Attach team/opponent for each player
    team_lookup = {}
    for p in all_props:
        pn_lower = p['player'].lower()
        if pn_lower not in team_lookup:
            team_lookup[pn_lower] = (p['home_team'], p['away_team'])

    return all_props


# ── EV / scoring ─────────────────────────────────────────────────────────────

def _calculate_ev(season_avg: float, recent_avg: float, prop_line: float,
                  odds: int, bet_type: str):
    """Return (ev_pct, true_prob_pct)."""
    if odds is None:
        odds = -110
    if odds > 0:
        implied = 100 / (odds + 100)
    else:
        implied = abs(odds) / (abs(odds) + 100)

    edge = (season_avg - prop_line) if bet_type == 'over' else (prop_line - season_avg)
    edge_factor = min(abs(edge) / 2.0, 1.0)

    recent_factor = 0.0
    if bet_type == 'over' and recent_avg > season_avg:
        recent_factor = min((recent_avg - season_avg) / 2.0, 0.08)
    elif bet_type == 'under' and recent_avg < season_avg:
        recent_factor = min((season_avg - recent_avg) / 2.0, 0.08)

    true_prob = 0.50 + (edge_factor * 0.18) + recent_factor
    true_prob = min(max(true_prob, 0.40), 0.70)

    if odds > 0:
        ev = (true_prob * (odds / 100)) - (1 - true_prob)
    else:
        ev = (true_prob * (100 / abs(odds))) - (1 - true_prob)

    return round(ev * 100, 2), round(true_prob * 100, 1)


# ── Main engine ───────────────────────────────────────────────────────────────

class WNBAPropsEngine:
    def __init__(self, prop_type: str):
        if prop_type not in PROP_CONFIGS:
            raise ValueError(f"Unknown prop type: {prop_type}. Valid: {list(PROP_CONFIGS)}")

        self.prop_type = prop_type
        cfg = PROP_CONFIGS[prop_type]

        self.market_key = cfg['market_key']
        self.stat_col = cfg['stat_col']
        self.prop_unit = cfg['prop_unit']
        self.display_name = cfg['display_name']
        self.min_edge = cfg['min_edge']
        self.top_plays = cfg['top_plays']

        self.html_file = os.path.join(SCRIPT_DIR, cfg['html_file'])
        self.tracking_file = os.path.join(SCRIPT_DIR, cfg['tracking_file'])
        self.stats_cache = os.path.join(SCRIPT_DIR, cfg['stats_cache'])

        self.season_key = f"season_{self.stat_col.lower()}"
        self.recent_key = f"recent_{self.stat_col.lower()}"

    # ── Tracking ──────────────────────────────────────────────────────────────

    def load_tracking(self):
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file) as f:
                return json.load(f)
        return {'picks': []}

    def save_tracking(self, data):
        with open(self.tracking_file, 'w') as f:
            json.dump(data, f, indent=2)

    def track_picks(self, plays: list):
        td = self.load_tracking()
        new_count = 0
        for play in plays:
            bet_type = play['bet_type']
            pick_id = f"{play['player']}_{play['prop_line']}_{bet_type}_{play['game_time']}"

            existing = next(
                (p for p in td['picks']
                 if p.get('player') == play['player']
                 and p.get('bet_type') == bet_type
                 and p.get('game_time') == play.get('game_time')),
                None
            )
            if existing:
                if existing.get('odds') != play.get('odds'):
                    existing['odds'] = play['odds']
                    existing['last_updated'] = datetime.now(pytz.timezone('US/Eastern')).isoformat()
            else:
                td['picks'].append({
                    'pick_id': pick_id,
                    'player': play['player'],
                    'prop_line': play['prop_line'],
                    'bet_type': bet_type,
                    'prop_unit': self.prop_unit,
                    'team': play.get('team', ''),
                    'opponent': play.get('opponent', ''),
                    'odds': play['odds'],
                    'game_time': play['game_time'],
                    'season_avg': play.get('season_avg'),
                    'recent_avg': play.get('recent_avg'),
                    'ev': play.get('ev'),
                    'edge': play.get('edge'),
                    'status': 'pending',
                    'tracked_at': datetime.now(pytz.timezone('US/Eastern')).isoformat(),
                })
                new_count += 1

        if new_count:
            self.save_tracking(td)
            print(f"{Colors.GREEN}✓ Tracked {new_count} new picks{Colors.END}")
        return new_count

    # ── Grading ───────────────────────────────────────────────────────────────

    def grade_pending(self):
        td = self.load_tracking()
        pending = [p for p in td['picks'] if p.get('status') == 'pending']
        if not pending:
            print(f"{Colors.GREEN}✓ No pending {self.display_name} picks{Colors.END}")
            return 0

        print(f"\n{Colors.CYAN}Grading {len(pending)} pending {self.display_name} picks...{Colors.END}")
        et_tz = pytz.timezone('US/Eastern')
        graded = 0

        by_date = defaultdict(list)
        for pick in pending:
            gt = pick.get('game_time', '')
            if not gt:
                continue
            try:
                dt = datetime.fromisoformat(gt.replace('Z', '+00:00'))
                hours_ago = (datetime.now(pytz.UTC) - dt.astimezone(pytz.UTC)).total_seconds() / 3600
                if hours_ago < 1:
                    continue
                if hours_ago > 7 * 24:
                    pick['status'] = 'void'
                    pick['result'] = 'Stale — voided'
                    graded += 1
                    continue
                game_date = dt.astimezone(et_tz).strftime('%Y-%m-%d')
                by_date[game_date].append(pick)
            except Exception:
                continue

        for date_str, picks in by_date.items():
            day_stats, completed_teams = _fetch_espn_date(date_str)
            if not day_stats:
                continue

            for pick in picks:
                player = pick.get('player', '')
                lookup = player.lower()
                stat_row = day_stats.get(lookup)

                # Fuzzy match on last name if exact miss
                if stat_row is None:
                    parts = lookup.split()
                    if len(parts) >= 2:
                        for pn, row in day_stats.items():
                            pp = pn.split()
                            if len(pp) >= 2 and pp[-1] == parts[-1] and pp[0][0] == parts[0][0]:
                                stat_row = row
                                break

                team = pick.get('team', '')
                game_final = team in completed_teams or not team

                if stat_row is None:
                    if game_final:
                        pick['status'] = 'void'
                        pick['result'] = 'DNP'
                        pick['profit_loss'] = 0
                        graded += 1
                    continue

                actual = stat_row.get(self.stat_col, 0)
                prop_line = pick.get('prop_line', 0)
                bet_type = pick.get('bet_type', 'over')

                # Determine if result can be graded (game over or early clinch)
                can_grade = game_final
                if not can_grade:
                    if bet_type == 'over' and actual > prop_line:
                        can_grade = True
                    elif bet_type == 'under' and actual < prop_line - 1:
                        can_grade = True

                if not can_grade:
                    continue

                is_win = (actual > prop_line) if bet_type == 'over' else (actual < prop_line)
                is_push = actual == prop_line

                odds = pick.get('odds', -110)
                if is_push:
                    status, result, pl = 'push', 'PUSH', 0
                elif is_win:
                    pl = int(odds) if odds > 0 else int((100.0 / abs(odds)) * 100)
                    status, result = 'win', 'WIN'
                else:
                    pl = -100
                    status, result = 'loss', 'LOSS'

                pick['status'] = status
                pick['result'] = result
                pick[f'actual_{self.prop_unit.lower()}'] = actual
                pick['profit_loss'] = pl
                pick['graded_at'] = datetime.now(et_tz).isoformat()

                color = Colors.GREEN if is_win else (Colors.YELLOW if is_push else Colors.RED)
                print(f"  {color}{result}{Colors.END}: {player} — {actual} {self.prop_unit} "
                      f"(line {prop_line}, {bet_type.upper()}) | {pl/100:+.2f}u")
                graded += 1

        if graded:
            self.save_tracking(td)
            print(f"{Colors.GREEN}✓ Graded {graded} picks{Colors.END}")
        return graded

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_player_stats(self):
        return _build_season_stats(self.stats_cache)

    # ── Analysis ──────────────────────────────────────────────────────────────

    def analyze(self, props: list, player_stats: dict):
        print(f"\n{Colors.CYAN}Analyzing {len(props)} {self.display_name} props...{Colors.END}")
        plays = []
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(pytz.UTC)

        for prop in props:
            player = prop['player']
            gt = prop.get('game_time', '')
            if gt:
                try:
                    dt = datetime.fromisoformat(gt.replace('Z', '+00:00'))
                    if dt.astimezone(pytz.UTC) < (now - timedelta(hours=12)):
                        continue
                except Exception:
                    pass

            # Find player in stats
            pdata = player_stats.get(player.lower())
            if pdata is None:
                # Fuzzy: first initial + last name
                parts = player.lower().split()
                if len(parts) >= 2:
                    for pn, pd in player_stats.items():
                        pp = pn.split()
                        if len(pp) >= 2 and pp[-1] == parts[-1] and pp[0][0] == parts[0][0]:
                            pdata = pd
                            break
            if pdata is None:
                continue

            season_avg = pdata.get(self.season_key, 0)
            recent_avg = pdata.get(self.recent_key, season_avg)
            if season_avg == 0:
                continue

            prop_line = prop['prop_line']
            home = prop['home_team']
            away = prop['away_team']
            team = home  # default — will check rosters below

            # Determine which team the player is on
            for tname, rows in []:  # placeholder; we'll use pdata team
                pass
            player_team = pdata.get('team', '')

            # Over side
            if prop.get('over_price') is not None:
                edge = round(season_avg - prop_line, 2)
                if edge >= self.min_edge:
                    ev, prob = _calculate_ev(season_avg, recent_avg, prop_line,
                                             prop['over_price'], 'over')
                    if ev > 0:
                        plays.append({
                            'player': player,
                            'team': player_team,
                            'opponent': away if player_team == home else home,
                            'prop_line': prop_line,
                            'bet_type': 'over',
                            'prop': f"OVER {prop_line} {self.prop_unit}",
                            'odds': prop['over_price'],
                            'season_avg': season_avg,
                            'recent_avg': recent_avg,
                            'edge': edge,
                            'ev': ev,
                            'true_prob': prob,
                            'game_time': gt,
                            'home_team': home,
                            'away_team': away,
                        })

            # Under side
            if prop.get('under_price') is not None:
                edge = round(prop_line - season_avg, 2)
                if edge >= self.min_edge:
                    ev, prob = _calculate_ev(season_avg, recent_avg, prop_line,
                                             prop['under_price'], 'under')
                    if ev > 0:
                        plays.append({
                            'player': player,
                            'team': player_team,
                            'opponent': away if player_team == home else home,
                            'prop_line': prop_line,
                            'bet_type': 'under',
                            'prop': f"UNDER {prop_line} {self.prop_unit}",
                            'odds': prop['under_price'],
                            'season_avg': season_avg,
                            'recent_avg': recent_avg,
                            'edge': edge,
                            'ev': ev,
                            'true_prob': prob,
                            'game_time': gt,
                            'home_team': home,
                            'away_team': away,
                        })

        plays.sort(key=lambda x: x['ev'], reverse=True)
        over_plays = [p for p in plays if p['bet_type'] == 'over'][:self.top_plays]
        under_plays = [p for p in plays if p['bet_type'] == 'under'][:self.top_plays]
        print(f"{Colors.GREEN}✓ {len(over_plays)} over plays, {len(under_plays)} under plays{Colors.END}")
        return over_plays, under_plays

    # ── Tracking stats ────────────────────────────────────────────────────────

    def calc_tracking_stats(self, td: dict):
        picks = td.get('picks', [])
        completed = [p for p in picks if p.get('status') in ('win', 'loss', 'push', 'void')]
        wins = sum(1 for p in completed if p.get('status') == 'win')
        losses = sum(1 for p in completed if p.get('status') == 'loss')
        pushes = sum(1 for p in completed if p.get('status') == 'push')
        units = sum(float(p.get('profit_loss', 0)) / 100 for p in completed)

        et_tz = pytz.timezone('US/Eastern')
        today = datetime.now(et_tz).date()
        last10_dates = sorted({
            datetime.fromisoformat(p['game_time'].replace('Z', '+00:00'))
            .astimezone(et_tz).strftime('%Y-%m-%d')
            for p in completed if p.get('game_time')
        })[-10:]
        l10 = [p for p in completed if p.get('game_time') and
               datetime.fromisoformat(p['game_time'].replace('Z', '+00:00'))
               .astimezone(et_tz).strftime('%Y-%m-%d') in last10_dates]
        l10_wins = sum(1 for p in l10 if p.get('status') == 'win')
        l10_losses = sum(1 for p in l10 if p.get('status') == 'loss')
        l10_units = sum(float(p.get('profit_loss', 0)) / 100 for p in l10)

        return {
            'wins': wins, 'losses': losses, 'pushes': pushes, 'units': units,
            'l10_wins': l10_wins, 'l10_losses': l10_losses, 'l10_units': l10_units,
            'total_graded': len(completed),
        }

    # ── Display picks ─────────────────────────────────────────────────────────

    def get_active_plays(self, td: dict):
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        plays = []
        for p in td.get('picks', []):
            gt = p.get('game_time', '')
            if not gt:
                continue
            try:
                dt = datetime.fromisoformat(gt.replace('Z', '+00:00')).astimezone(et_tz)
                if dt.date() < now.date():
                    continue
                if dt.date() == now.date() and p.get('status') != 'pending':
                    continue
                if dt < now and dt.date() == now.date():
                    continue
            except Exception:
                continue
            if p.get('status') != 'pending':
                continue
            plays.append({
                'player': p['player'],
                'prop': f"{p['bet_type'].upper()} {p['prop_line']} {self.prop_unit}",
                'bet_type': p['bet_type'],
                'prop_line': p['prop_line'],
                'game_time': gt,
                'team': p.get('team', ''),
                'opponent': p.get('opponent', ''),
                'odds': p.get('odds', -110),
                'season_avg': p.get('season_avg', 0),
                'recent_avg': p.get('recent_avg', 0),
                'edge': p.get('edge', 0),
                'ev': p.get('ev', 0),
            })
        plays.sort(key=lambda x: x['ev'], reverse=True)
        return plays

    # ── HTML ──────────────────────────────────────────────────────────────────

    def generate_html(self, over_plays, under_plays, stats, td):
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        date_str = now.strftime('%B %d, %Y')

        wins, losses = stats['wins'], stats['losses']
        units = stats['units']
        win_rate = round(wins / (wins + losses) * 100, 1) if (wins + losses) else 0.0
        units_color = '#4ade80' if units >= 0 else '#f87171'

        l10_w, l10_l = stats['l10_wins'], stats['l10_losses']
        l10_units = stats['l10_units']
        l10_color = '#4ade80' if l10_units >= 0 else '#f87171'

        nav_html = _build_nav(self.prop_type)

        over_html = ''.join(self._render_card(p, 'over') for p in over_plays) or \
                    '<p style="color:#666;text-align:center;padding:20px">No over plays today</p>'
        under_html = ''.join(self._render_card(p, 'under') for p in under_plays) or \
                     '<p style="color:#666;text-align:center;padding:20px">No under plays today</p>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WNBA {self.display_name} Props</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{_get_css()}</style>
</head>
<body>
<div class="container">
  {nav_html}
  <header>
    <div>
      <h1>🏀 WNBA {self.display_name} Props</h1>
      <div class="date-sub">{date_str} · Powered by The Odds API + ESPN</div>
    </div>
  </header>

  <div class="summary-grid">
    <div class="stat-box">
      <div class="stat-label">Season Record</div>
      <div class="stat-value">{wins}-{losses}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Win Rate</div>
      <div class="stat-value" style="color:{'#4ade80' if win_rate >= 55 else '#f87171'}">{win_rate}%</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Total Units</div>
      <div class="stat-value" style="color:{units_color}">{units:+.2f}u</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Last 10 Days</div>
      <div class="stat-value">{l10_w}-{l10_l}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">L10 Units</div>
      <div class="stat-value" style="color:{l10_color}">{l10_units:+.2f}u</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Graded Picks</div>
      <div class="stat-value">{stats['total_graded']}</div>
    </div>
  </div>

  <div class="section-title" style="color:#4ade80">
    ▲ OVER PLAYS <span class="highlight">{len(over_plays)} today</span>
  </div>
  {over_html}

  <div class="section-title" style="color:#f87171;margin-top:30px">
    ▼ UNDER PLAYS <span class="highlight">{len(under_plays)} today</span>
  </div>
  {under_html}
</div>
</body>
</html>"""

    def _render_card(self, play, bet_type):
        player = play['player']
        team = play.get('team', '')
        opponent = play.get('opponent', '')
        odds = play.get('odds', -110)
        season_avg = play.get('season_avg', 0)
        recent_avg = play.get('recent_avg', 0)
        edge = play.get('edge', 0)
        ev = play.get('ev', 0)
        prop_line = play.get('prop_line', 0)
        gt = play.get('game_time', '')

        odds_str = f"+{odds}" if odds > 0 else str(odds)
        color_class = 'txt-green' if bet_type == 'over' else 'txt-red'
        glow_class = 'glow-green' if bet_type == 'over' else 'glow-blue'

        abbr = WNBA_TEAM_ABBREVS.get(team, '')
        logo = (f"https://a.espncdn.com/i/teamlogos/wnba/500/{abbr}.png"
                if abbr else "https://a.espncdn.com/i/teamlogos/wnba/500/wnba.png")

        opp_short = SHORT_NAMES.get(WNBA_TEAM_ABBREVS.get(opponent, ''), opponent)

        time_str = ''
        if gt:
            try:
                et_tz = pytz.timezone('US/Eastern')
                dt = datetime.fromisoformat(gt.replace('Z', '+00:00')).astimezone(et_tz)
                time_str = dt.strftime('%a %I:%M %p').lstrip('0')
            except Exception:
                pass

        edge_tag = f'<span class="tag tag-green">Edge: +{edge:.1f}</span>' if edge > 0 else \
                   f'<span class="tag tag-red">Edge: {edge:.1f}</span>'
        ev_tag = f'<span class="tag tag-blue">EV: {ev:+.1f}%</span>'

        return f"""
<div class="prop-card {glow_class}">
  <div class="card-header">
    <div class="header-left">
      <img src="{logo}" class="team-logo" onerror="this.src='https://a.espncdn.com/i/teamlogos/wnba/500/wnba.png'" alt="">
      <div class="player-info">
        <h2>{player}</h2>
        <div class="matchup-info">{team or '?'} vs {opp_short or opponent}</div>
      </div>
    </div>
    <div class="game-meta">
      <div class="game-date-time">{time_str}</div>
    </div>
  </div>
  <div class="card-body">
    <div class="bet-main-row">
      <span class="bet-selection {color_class}">
        <span class="line">{'OVER' if bet_type == 'over' else 'UNDER'} {prop_line} {self.prop_unit}</span>
      </span>
      <span class="bet-odds">{odds_str}</span>
    </div>
    <div class="model-subtext">
      Season avg <strong>{season_avg}</strong> · Recent avg <strong>{recent_avg}</strong>
    </div>
    <div class="tags-container">
      {edge_tag}
      {ev_tag}
    </div>
  </div>
</div>"""

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self):
        print(f"\n{'='*70}")
        print(f"WNBA {self.display_name.upper()} PROPS MODEL")
        print(f"{'='*70}")

        self.grade_pending()

        player_stats = self.get_player_stats()
        print(f"{Colors.CYAN}Fetching {self.display_name} props from The Odds API...{Colors.END}")
        props = _get_wnba_props(self.market_key)
        print(f"{Colors.GREEN}✓ {len(props)} {self.display_name} props fetched{Colors.END}")

        over_plays, under_plays = self.analyze(props, player_stats)
        all_plays = over_plays + under_plays
        self.track_picks(all_plays)

        td = self.load_tracking()
        stats = self.calc_tracking_stats(td)

        active = self.get_active_plays(td)
        active_over = [p for p in active if p['bet_type'] == 'over']
        active_under = [p for p in active if p['bet_type'] == 'under']

        html = self.generate_html(active_over, active_under, stats, td)
        with open(self.html_file, 'w') as f:
            f.write(html)
        print(f"{Colors.GREEN}✓ HTML written: {self.html_file}{Colors.END}")

        print(f"\n{Colors.BOLD}{Colors.GREEN}✓ WNBA {self.display_name} model complete!{Colors.END}")


# ── Shared CSS + nav ─────────────────────────────────────────────────────────

def _build_nav(active_type: str):
    links = [
        ('points', 'wnba_points_props.html', '🏀 Points'),
        ('rebounds', 'wnba_rebounds_props.html', '💪 Rebounds'),
        ('assists', 'wnba_assists_props.html', '🎯 Assists'),
    ]
    pills = ''
    for key, href, label in links:
        cls = 'nav-pill active' if key == active_type else 'nav-pill'
        pills += f'<a href="{href}" class="{cls}">{label}</a>'
    return f'<nav class="nav-bar">{pills}</nav>'


def _get_css():
    return """
        :root {
            --bg-main: #121212; --bg-card: #1e1e1e; --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff; --text-secondary: #b3b3b3;
            --accent-green: #4ade80; --accent-red: #f87171; --accent-blue: #60a5fa;
            --border-color: #333333;
        }
        body { margin:0; padding:20px; font-family:'Inter',sans-serif;
               background:var(--bg-main); color:var(--text-primary);
               -webkit-font-smoothing:antialiased; }
        .container { max-width:650px; margin:0 auto; }
        header { display:flex; justify-content:space-between; align-items:center;
                 margin-bottom:25px; border-bottom:1px solid var(--border-color);
                 padding-bottom:15px; }
        h1 { margin:0; font-size:22px; font-weight:700; }
        .date-sub { color:var(--text-secondary); font-size:13px; margin-top:4px; }
        .summary-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:10px;
                        margin-bottom:25px; }
        .stat-box { background:var(--bg-card); border-radius:12px; padding:12px;
                    text-align:center; border:1px solid var(--border-color); }
        .stat-label { font-size:11px; color:var(--text-secondary);
                      text-transform:uppercase; margin-bottom:4px; }
        .stat-value { font-size:18px; font-weight:700; }
        .section-title { font-size:16px; margin-bottom:12px; display:flex;
                         align-items:center; font-weight:600; }
        .section-title .highlight { color:var(--accent-green); margin-left:8px;
                                    font-size:13px; font-weight:400; }
        .prop-card { background:var(--bg-card); border-radius:16px; overflow:hidden;
                     margin-bottom:20px; border:1px solid var(--border-color);
                     box-shadow:0 4px 6px -1px rgba(0,0,0,.2); }
        .card-header { padding:12px 16px; display:flex; justify-content:space-between;
                       align-items:center; background:var(--bg-card-secondary);
                       border-bottom:1px solid var(--border-color); }
        .header-left { display:flex; align-items:center; gap:10px; }
        .team-logo { width:40px; height:40px; border-radius:50%; object-fit:contain; }
        .player-info h2 { margin:0; font-size:16px; line-height:1.2; }
        .matchup-info { color:var(--text-secondary); font-size:12px; margin-top:2px; }
        .game-date-time { font-size:11px; color:var(--text-secondary); background:#333;
                          padding:4px 8px; border-radius:4px; font-weight:500;
                          white-space:nowrap; }
        .card-body { padding:16px; }
        .bet-main-row { margin-bottom:12px; }
        .bet-selection { font-size:20px; font-weight:800; }
        .bet-odds { font-size:16px; color:var(--text-secondary); font-weight:500;
                    margin-left:8px; }
        .model-subtext { color:var(--text-secondary); font-size:13px; margin-bottom:14px;
                         padding-bottom:12px; border-bottom:1px solid var(--border-color); }
        .model-subtext strong { color:var(--text-primary); }
        .tags-container { display:flex; flex-wrap:wrap; gap:6px; }
        .tag { font-size:11px; padding:4px 8px; border-radius:4px; font-weight:500; }
        .tag-green { background:rgba(74,222,128,.15); color:var(--accent-green); }
        .tag-red { background:rgba(248,113,113,.15); color:var(--accent-red); }
        .tag-blue { background:rgba(96,165,250,.15); color:var(--accent-blue); }
        .txt-green { color:var(--accent-green); }
        .txt-red { color:var(--accent-red); }
        .glow-green { box-shadow:0 0 15px rgba(74,222,128,.15);
                      border:1px solid rgba(74,222,128,.3); }
        .glow-blue { box-shadow:0 0 15px rgba(96,165,250,.15);
                     border:1px solid rgba(96,165,250,.3); }
        .nav-bar { display:flex; gap:10px; margin-bottom:25px; overflow-x:auto;
                   padding-bottom:5px; }
        .nav-pill { padding:8px 16px; background:var(--bg-card);
                    border:1px solid var(--border-color); border-radius:20px;
                    color:var(--text-secondary); text-decoration:none;
                    font-size:13px; font-weight:500; white-space:nowrap; }
        .nav-pill:hover, .nav-pill.active { background:var(--bg-card-secondary);
                                            color:var(--text-primary);
                                            border-color:var(--text-primary); }
        @media(max-width:600px){ .summary-grid{grid-template-columns:repeat(2,1fr);}
                                 .stat-box:last-child{grid-column:span 2;} }
    """
