#!/usr/bin/env python3

import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

COLORS = {
    "bg": "#000000",
    "card": "#1a1a1a",
    "bet_box": "#262626",
    "win": "#10b981",
    "loss": "#ef4444",
    "text": "#ffffff",
    "secondary": "#94a3b8",
    "accent": "#3b82f6",
    "void": "#9ca3af"
}

SPORT_ORDER = ["NBA", "MLB", "WNBA", "NCAAB", "UFC", "Soccer", "Other"]

SPORT_EMOJI = {
    "NBA": "🏀",
    "MLB": "⚾",
    "WNBA": "🏀",
    "NCAAB": "🏀",
    "UFC": "🥊",
    "Soccer": "⚽",
    "Other": "🎯",
}

class DailyRecapGenerator:
    def __init__(self, target_date):
        self.base_dir = Path("/Users/rico/Dev/sports-models")
        self.target_date = target_date
        self.all_picks = []
        self.tracking_files = [
            "nba/nba_picks_tracking.json",
            "nba/nba_points_props_tracking.json",
            "nba/nba_rebounds_props_tracking.json",
            "nba/nba_assists_props_tracking.json",
            "nba/nba_3pt_props_tracking.json",
            "nba/nba_pra_props_tracking.json",
            "nba/nba_points_rebounds_props_tracking.json",
            "nba/nba_points_assists_props_tracking.json",
            "nba/nba_rebounds_assists_props_tracking.json",
            "ncaa/ncaab_picks_tracking.json",
            "ncaa/cbb_points_props_tracking.json",
            "ncaa/cbb_assists_props_tracking.json",
            "ncaa/cbb_rebounds_props_tracking.json",
            "ncaa/cbb_pra_props_tracking.json",
            "ncaa/cbb_points_rebounds_props_tracking.json",
            "ncaa/cbb_points_assists_props_tracking.json",
            "ncaa/cbb_rebounds_assists_props_tracking.json",
            "ncaa/cbb_3pt_props_tracking.json",
            "soccer/soccer_picks_tracking.json",
            "wnba/wnba_model_tracking.json",
            "wnba/wnba_props_tracking.json",
            "wnba/wnba_points_props_tracking.json",
            "wnba/wnba_rebounds_props_tracking.json",
            "wnba/wnba_assists_props_tracking.json",
            "wnba/wnba_3pt_props_tracking.json",
            "wnba/wnba_pra_props_tracking.json",
            "wnba/wnba_points_rebounds_props_tracking.json",
            "wnba/wnba_points_assists_props_tracking.json",
            "wnba/wnba_rebounds_assists_props_tracking.json",
            "ufc/data/ufc_picks.json",
            "mlb/mlb_master_model_tracking.json",
            "best_plays_tracking.json",
        ]

    def get_sport(self, file_path):
        if 'nba' in file_path: return 'NBA'
        if 'ncaa' in file_path or 'cbb' in file_path: return 'NCAAB'
        if 'soccer' in file_path: return 'Soccer'
        if 'ufc' in file_path: return 'UFC'
        if 'wnba' in file_path: return 'WNBA'
        if 'mlb' in file_path: return 'MLB'
        return 'Other'

    def get_prop_label(self, file_path, pick=None):
        fp = file_path.lower()

        if 'best_plays' in fp:
            return 'Best Plays'

        if 'mlb' in fp and pick:
            t = pick.get('type', '')
            if ' - ' in t:
                return t.split(' - ', 1)[1]
            return t or 'MLB Picks'

        if 'nba' in fp or 'ncaa' in fp or 'cbb' in fp:
            if 'pra' in fp: return 'PRA'
            if 'points_rebounds_assists' in fp: return 'PRA'
            if 'points_rebounds' in fp: return 'Pts+Reb'
            if 'points_assists' in fp: return 'Pts+Ast'
            if 'rebounds_assists' in fp: return 'Reb+Ast'
            if 'points' in fp: return 'Points'
            if 'rebounds' in fp: return 'Rebounds'
            if 'assists' in fp: return 'Assists'
            if '3pt' in fp: return '3-Pointers'
            return 'Game Picks'

        if 'wnba' in fp:
            return 'Props' if 'props' in fp else 'Game Picks'

        if 'ufc' in fp:
            return 'Fight Picks'

        if 'soccer' in fp:
            return 'Match Picks'

        return 'Picks'

    def load_data(self):
        print(f"Loading data for date: {self.target_date}")
        daily_picks = []

        for file_path in self.tracking_files:
            full_path = self.base_dir / file_path
            if not full_path.exists():
                continue
            try:
                with open(full_path, 'r') as f:
                    data = json.load(f)
                if isinstance(data, dict) and 'picks' in data:
                    picks = data['picks']
                elif isinstance(data, list):
                    picks = data
                else:
                    continue

                for pick in picks:
                    pick_date_str = ""

                    def parse_iso(date_str):
                        try:
                            if 'T' in date_str:
                                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                et_dt = dt - timedelta(hours=5)
                                return et_dt.strftime('%Y-%m-%d')
                            else:
                                return date_str
                        except:
                            return ""

                    if pick.get('game_time'):
                        pick_date_str = parse_iso(pick.get('game_time'))
                    elif pick.get('game_date'):
                        pick_date_str = parse_iso(pick.get('game_date'))
                    elif pick.get('date'):
                        pick_date_str = pick.get('date')
                    elif pick.get('created_at'):
                        pick_date_str = pick['created_at'][:10]

                    if pick_date_str == self.target_date:
                        pick['sport'] = self.get_sport(file_path)
                        pick['prop_label'] = self.get_prop_label(file_path, pick)
                        pick['file_path'] = file_path
                        self.normalize_pick(pick)
                        daily_picks.append(pick)

            except Exception as e:
                print(f"Error loading {file_path}: {e}")

        original_count = len(daily_picks)

        # Deduplication
        unique_picks_map = {}
        for pick in daily_picks:
            player = pick.get('player', pick.get('team', 'Unknown'))
            prop = pick.get('prop_line', '')
            btype = pick.get('bet_type', '')
            gtime = pick.get('game_time', '')

            is_props_pick = pick.get('player') or 'prop' in pick.get('prop_label', '').lower()
            if is_props_pick and pick.get('sport') in ('NBA', 'NCAAB'):
                model = pick.get('prop_label', 'unknown')
                key = f"{player}_{model}_{btype}_{gtime}"
            else:
                if pick.get('id') and not pick.get('pick_id'):
                    key = pick['id']
                elif pick.get('pick_id'):
                    raw_id = pick['pick_id']
                    if 'T' in raw_id:
                        parts = raw_id.rsplit('_', 1)
                        if len(parts) == 2:
                            prefix, suffix = parts
                            idx = prefix.rfind('_')
                            if idx > 0:
                                teams = prefix[:idx]
                                ts = prefix[idx+1:]
                                try:
                                    from datetime import datetime as dt_parse
                                    utc_dt = dt_parse.fromisoformat(ts.replace('Z', '+00:00'))
                                    et_dt = utc_dt - timedelta(hours=5)
                                    date_only = et_dt.strftime('%Y-%m-%d')
                                except:
                                    date_only = ts.split('T')[0]
                                key = f"{teams}_{date_only}_{suffix}"
                            else:
                                key = raw_id
                        else:
                            key = raw_id
                    else:
                        key = raw_id
                else:
                    key = f"{pick.get('team')}_{pick.get('opponent')}_{pick.get('prop_label')}_{pick.get('pick_text')}"

            if key in unique_picks_map:
                existing = unique_picks_map[key]
                if existing.get('status') == 'pending' and pick.get('status') != 'pending':
                    unique_picks_map[key] = pick
                elif pick.get('last_updated') and existing.get('last_updated'):
                    if pick['last_updated'] > existing['last_updated']:
                        unique_picks_map[key] = pick
            else:
                unique_picks_map[key] = pick

        self.all_picks.extend(list(unique_picks_map.values()))
        print(f"Found {len(self.all_picks)} unique picks for {self.target_date} (from {original_count} raw)")

    def normalize_pick(self, pick):
        status = pick.get('status', 'pending').lower()
        if status in ('won', 'win'): pick['status'] = 'win'
        elif status in ('lost', 'loss'): pick['status'] = 'loss'
        elif status == 'void': pick['status'] = 'void'
        elif status == 'push': pick['status'] = 'push'
        else: pick['status'] = 'pending'

        if 'profit_loss' not in pick:
            if 'profit' in pick:
                pick['profit_loss'] = float(pick['profit']) * 100
            elif pick['status'] in ['win', 'loss']:
                units = float(pick.get('recommended_bet_size_unit', 1))
                odds = float(pick.get('odds', -110))
                if pick['status'] == 'win':
                    if odds > 0: profit = (odds / 100) * units * 100
                    else: profit = (100 / abs(odds)) * units * 100
                    pick['profit_loss'] = profit
                elif pick['status'] == 'loss':
                    pick['profit_loss'] = -(units * 100)
            else:
                pick['profit_loss'] = 0

    def calculate_stats(self):
        # by_sport_prop: {sport: {prop_label: {wins, losses, pushes, voids, units, picks}}}
        by_sport_prop = defaultdict(lambda: defaultdict(
            lambda: {'wins': 0, 'losses': 0, 'pushes': 0, 'voids': 0, 'units': 0.0, 'picks': []}
        ))
        by_sport = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pushes': 0, 'voids': 0, 'units': 0.0})
        total = {'wins': 0, 'losses': 0, 'pushes': 0, 'voids': 0, 'units': 0.0}

        for pick in self.all_picks:
            status = pick.get('status', 'pending')
            sport = pick['sport']
            prop_label = pick['prop_label']

            by_sport_prop[sport][prop_label]['picks'].append(pick)

            if status not in ('win', 'loss', 'push', 'void'):
                continue

            pl = float(pick.get('profit_loss', 0)) / 100.0

            for d in (total, by_sport[sport], by_sport_prop[sport][prop_label]):
                if status == 'win': d['wins'] += 1
                elif status == 'loss': d['losses'] += 1
                elif status == 'push': d['pushes'] += 1
                elif status == 'void': d['voids'] += 1
                d['units'] += pl

        return {
            'total': total,
            'by_sport': dict(by_sport),
            'by_sport_prop': {s: dict(p) for s, p in by_sport_prop.items()},
        }

    def _record_str(self, d, show_units=True):
        w, l, p, v = d['wins'], d['losses'], d['pushes'], d['voids']
        u = d['units']
        void_part = f' <span style="font-size:0.8em;color:{COLORS["void"]}">({v}v)</span>' if v else ''
        push_part = f'-{p}' if p else ''
        rec = f"{w}-{l}{push_part}{void_part}"
        if show_units:
            u_color = COLORS['win'] if u >= 0 else COLORS['loss']
            rec += f' <span style="color:{u_color};font-size:0.9em">({u:+.2f}u)</span>'
        return rec

    def generate_html(self, stats):
        total = stats['total']
        by_sport_prop = stats['by_sport_prop']
        by_sport = stats['by_sport']

        u_color = COLORS['win'] if total['units'] >= 0 else COLORS['loss']

        sport_sections_html = ''
        for sport in SPORT_ORDER:
            if sport not in by_sport_prop:
                continue
            sp_data = by_sport[sport]
            prop_map = by_sport_prop[sport]
            emoji = SPORT_EMOJI.get(sport, '')
            sp_record = self._record_str(sp_data, show_units=True)

            prop_sections = ''
            for prop_label, pd in sorted(prop_map.items()):
                def sort_key(p):
                    s = p.get('status', 'pending')
                    return {'win': 0, 'push': 1, 'void': 2, 'loss': 3}.get(s, 4)

                sorted_picks = sorted(pd['picks'], key=sort_key)
                cards = ''.join(self.render_pick_card(p) for p in sorted_picks)

                completed = [p for p in sorted_picks if p.get('status') in ('win','loss','push','void')]
                if completed:
                    prop_rec = self._record_str(pd, show_units=False)
                    u_col = COLORS['win'] if pd['units'] >= 0 else COLORS['loss']
                    prop_units = f'<span style="color:{u_col}">({pd["units"]:+.2f}u)</span>'
                    header_right = f'{prop_rec} {prop_units}'
                else:
                    header_right = '<span style="color:#94a3b8;font-size:0.85em">Pending</span>'

                prop_sections += f"""
        <div class="prop-section">
            <div class="prop-title">
                <span>{prop_label}</span>
                <span>{header_right}</span>
            </div>
            <div class="picks-grid">{cards}</div>
        </div>"""

            sport_sections_html += f"""
        <div class="sport-section">
            <div class="sport-header">
                <span>{emoji} {sport}</span>
                <span class="sport-record">{sp_record}</span>
            </div>
            {prop_sections}
        </div>"""

        total_void_part = f' <span style="font-size:0.65em;color:{COLORS["void"]}">({total["voids"]}v)</span>' if total['voids'] else ''
        push_part = f'-{total["pushes"]}' if total['pushes'] else ''
        total_record = f'{total["wins"]}-{total["losses"]}{push_part}{total_void_part}'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Recap - {self.target_date}</title>
    <style>
        body {{
            background-color: {COLORS['bg']};
            color: {COLORS['text']};
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 1px solid {COLORS['bet_box']};
            padding-bottom: 20px;
        }}
        .date-badge {{
            background-color: {COLORS['bet_box']};
            color: {COLORS['secondary']};
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.9em;
            display: inline-block;
            margin-bottom: 10px;
        }}
        h1 {{ margin: 10px 0; font-size: 2rem; }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background-color: {COLORS['card']};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid {COLORS['bet_box']};
        }}
        .stat-value {{ font-size: 2rem; font-weight: bold; display: block; }}
        .stat-label {{
            color: {COLORS['secondary']};
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .sport-section {{
            margin-bottom: 40px;
            border: 1px solid {COLORS['bet_box']};
            border-radius: 12px;
            overflow: hidden;
        }}
        .sport-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #1e293b;
            padding: 14px 18px;
            font-size: 1.2rem;
            font-weight: bold;
            border-bottom: 1px solid {COLORS['bet_box']};
        }}
        .sport-record {{ font-size: 1rem; font-weight: normal; }}
        .prop-section {{ padding: 16px 18px; border-top: 1px solid {COLORS['bet_box']}; }}
        .prop-section:first-of-type {{ border-top: none; }}
        .prop-title {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 12px;
            color: {COLORS['secondary']};
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.85rem;
        }}
        .picks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 12px;
        }}
        .pick-card {{
            background-color: {COLORS['card']};
            border-radius: 8px;
            padding: 14px;
            border: 1px solid {COLORS['bet_box']};
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .pick-card.win {{ border-top: 3px solid {COLORS['win']}; }}
        .pick-card.loss {{ border-top: 3px solid {COLORS['loss']}; }}
        .pick-card.push {{ border-top: 3px solid {COLORS['accent']}; }}
        .pick-card.void {{ border-top: 3px solid {COLORS['void']}; }}
        .pick-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 0.8em;
            color: {COLORS['secondary']};
        }}
        .player-name {{ font-size: 1rem; font-weight: bold; margin-bottom: 4px; }}
        .matchup {{ font-size: 0.85em; color: {COLORS['secondary']}; margin-bottom: 10px; }}
        .pick-details {{
            background-color: {COLORS['bet_box']};
            padding: 8px 10px;
            border-radius: 6px;
            margin-bottom: 10px;
        }}
        .pick-line {{ font-weight: bold; display: block; margin-bottom: 3px; font-size: 0.95em; }}
        .pick-odds {{ font-size: 0.85em; color: {COLORS['secondary']}; }}
        .pick-result {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 8px;
            border-top: 1px solid {COLORS['bet_box']};
            margin-top: auto;
        }}
        .result-score {{ font-family: monospace; font-size: 0.85em; color: {COLORS['secondary']}; }}
        .badge {{
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .badge-win {{ background-color: rgba(16,185,129,0.2); color: {COLORS['win']}; }}
        .badge-loss {{ background-color: rgba(239,68,68,0.2); color: {COLORS['loss']}; }}
        .badge-push {{ background-color: rgba(59,130,246,0.2); color: {COLORS['accent']}; }}
        .badge-void {{ background-color: rgba(156,163,175,0.2); color: {COLORS['void']}; }}
        .badge-pending {{ background-color: rgba(148,163,184,0.15); color: {COLORS['secondary']}; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <span class="date-badge">{self.target_date}</span>
            <h1>Daily Recap</h1>
        </div>
        <div class="summary-grid">
            <div class="stat-card">
                <span class="stat-value">{total_record}</span>
                <span class="stat-label">Daily Record</span>
            </div>
            <div class="stat-card">
                <span class="stat-value" style="color:{u_color}">{total['units']:+.2f}u</span>
                <span class="stat-label">Total Profit</span>
            </div>
        </div>
        {sport_sections_html}
    </div>
</body>
</html>"""

    def render_pick_card(self, pick):
        status = pick.get('status', 'pending')
        card_class = f"pick-card {status}"
        badge_class = f"badge-{status}"

        player = pick.get('player') or pick.get('selection')
        team = pick.get('team')
        opponent = pick.get('opponent')

        text = pick.get('pick') or pick.get('pick_text') or pick.get('type') or "Unknown Pick"
        text = text.replace("✅ BET:", "").replace("❌ BET:", "").strip()

        matchup = ""
        if team and opponent:
            matchup = f"{team} vs {opponent}"
        elif pick.get('matchup'):
            matchup = pick.get('matchup')
        elif pick.get('home_team') and pick.get('away_team'):
            matchup = f"{pick['away_team']} @ {pick['home_team']}"

        header_text = player if player else text

        line_text = ""
        if pick.get('bet_type') and pick.get('prop_line'):
            bet_type = pick['bet_type'].upper()
            line = pick['prop_line']
            unit = ""
            fp = pick.get('file_path', '').lower()
            if 'points' in fp: unit = "Pts"
            elif 'rebounds' in fp: unit = "Reb"
            elif 'assists' in fp: unit = "Ast"
            elif '3pt' in fp: unit = "3PT"
            line_text = f"{bet_type} {line} {unit}"
        elif pick.get('line'):
            line_text = pick['line']
        else:
            line_text = text

        odds = pick.get('odds') or pick.get('odds_str')
        odds_text = f"{odds}" if odds else ""
        try:
            if odds and float(str(odds).replace('+', '')) > 0 and not str(odds).startswith('+'):
                odds_text = f"+{odds}"
        except (ValueError, TypeError):
            pass

        result_display = ""
        actual_val = None
        if pick.get('actual_pts') is not None: actual_val = pick['actual_pts']
        elif pick.get('actual_reb') is not None: actual_val = pick['actual_reb']
        elif pick.get('actual_ast') is not None: actual_val = pick['actual_ast']
        elif pick.get('actual_3pm') is not None: actual_val = pick['actual_3pm']

        if actual_val is not None:
            result_display = f"Actual: {actual_val}"
            if pick.get('status') == 'void' and actual_val == 0:
                result_display = "DNP"
        elif pick.get('actual_score'):
            score_str = pick['actual_score']
            for t in [team, opponent, pick.get('home_team'), pick.get('away_team')]:
                if t:
                    score_str = score_str.replace(t, "")
            result_display = score_str.replace(",", "-").strip()
        elif pick.get('actual_home_score') and pick.get('actual_away_score'):
            result_display = f"{pick['actual_away_score']}-{pick['actual_home_score']}"
        elif pick.get('result') == 'DNP':
            result_display = "DNP"
        elif pick.get('result') and status != 'pending':
            r = pick['result']
            if len(r) < 60:
                result_display = r

        game_time = pick.get('game_time', '')
        time_display = game_time[11:16] + ' ET' if game_time and 'T' in game_time else ''

        return f"""
        <div class="{card_class}">
            <div>
                <div class="pick-header">
                    <span>{pick.get('sport', '')}</span>
                    <span>{time_display}</span>
                </div>
                <div class="player-name">{header_text}</div>
                <div class="matchup">{matchup}</div>
                <div class="pick-details">
                    <span class="pick-line">{line_text}</span>
                    <span class="pick-odds">Odds: {odds_text}</span>
                </div>
            </div>
            <div class="pick-result">
                <span class="result-score">{result_display}</span>
                <span class="badge {badge_class}">{status.upper()}</span>
            </div>
        </div>"""


def find_most_recent_completed_date():
    base_dir = Path("/Users/rico/Dev/sports-models")
    tracking_files = [
        "nba/nba_picks_tracking.json",
        "nba/nba_points_props_tracking.json",
        "nba/nba_rebounds_props_tracking.json",
        "nba/nba_assists_props_tracking.json",
        "nba/nba_3pt_props_tracking.json",
        "nba/nba_pra_props_tracking.json",
        "nba/nba_points_rebounds_props_tracking.json",
        "nba/nba_points_assists_props_tracking.json",
        "nba/nba_rebounds_assists_props_tracking.json",
        "ncaa/ncaab_picks_tracking.json",
        "ncaa/cbb_points_props_tracking.json",
        "ncaa/cbb_3pt_props_tracking.json",
        "soccer/soccer_picks_tracking.json",
        "wnba/wnba_model_tracking.json",
        "mlb/mlb_master_model_tracking.json",
        "best_plays_tracking.json",
    ]

    import pytz
    et_tz = pytz.timezone('US/Eastern')
    latest_date = None
    yesterday_str = (datetime.now(et_tz) - timedelta(days=1)).strftime('%Y-%m-%d')

    for rel_path in tracking_files:
        fpath = base_dir / rel_path
        if not fpath.exists():
            continue
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            picks = data.get('picks', data) if isinstance(data, dict) else data
            for pick in picks:
                if pick.get('status', 'pending').lower() not in ('win', 'loss', 'void', 'push'):
                    continue
                date_str = None
                for field in ('game_date', 'game_time', 'date', 'tracked_at'):
                    val = pick.get(field, '')
                    if not val:
                        continue
                    try:
                        if 'T' in val or 'Z' in val:
                            dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                            date_str = dt.astimezone(et_tz).strftime('%Y-%m-%d')
                        else:
                            date_str = val[:10]
                        break
                    except Exception:
                        continue
                if date_str and date_str <= yesterday_str and (latest_date is None or date_str > latest_date):
                    latest_date = date_str
        except Exception:
            continue

    return latest_date or (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')


def main():
    parser = argparse.ArgumentParser(description='Generate Daily Recap Report')
    parser.add_argument('--date', type=str, default=None)
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()

    if args.date is None:
        args.date = find_most_recent_completed_date()
        print(f"Auto-detected recap date: {args.date}")

    if args.output is None:
        args.output = f"daily_recap_{args.date}.html"

    generator = DailyRecapGenerator(args.date)
    generator.load_data()
    stats = generator.calculate_stats()
    html = generator.generate_html(stats)

    with open(args.output, 'w') as f:
        f.write(html)

    with open(Path("/Users/rico/Dev/sports-models") / "daily_recap.html", 'w') as f:
        f.write(html)

    print(f"Report generated: {args.output}")

if __name__ == "__main__":
    main()
