"""
MLB Player Performance Report
Reads mlb_master_model_tracking.json and generates a player hit-rate leaderboard.
"""
import json
import os
import requests
from collections import defaultdict
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKING_FILE = os.path.join(SCRIPT_DIR, "mlb_master_model_tracking.json")
OUTPUT_HTML   = os.path.join(SCRIPT_DIR, "mlb_player_report.html")
MIN_PICKS     = 3   # minimum graded picks to appear on leaderboard

PROP_LABELS = {
    'Player Props - Strikeouts':    'Strikeouts',
    'Player Props - H+R+RBI':       'H+R+RBI',
    'Player Props - Home Run':      'Home Run',
    'Player Props - Pitching Outs': 'Pitching Outs',
    'First 5 Innings ML':           'F5 ML',
}

TYPE_COLORS = {
    'Strikeouts':    '#3b82f6',
    'H+R+RBI':       '#10b981',
    'Home Run':      '#f59e0b',
    'Pitching Outs': '#8b5cf6',
    'F5 ML':         '#ec4899',
}

# ESPN CDN slug overrides (abbr → slug)
_ESPN_SLUGS = {
    'ARI': 'ari', 'ATL': 'atl', 'BAL': 'bal', 'BOS': 'bos',
    'CHC': 'chc', 'CWS': 'chw', 'CIN': 'cin', 'CLE': 'cle',
    'COL': 'col', 'DET': 'det', 'HOU': 'hou', 'KC':  'kc',
    'LAA': 'laa', 'LAD': 'lad', 'MIA': 'mia', 'MIL': 'mil',
    'MIN': 'min', 'NYM': 'nym', 'NYY': 'nyy', 'ATH': 'oak',
    'PHI': 'phi', 'PIT': 'pit', 'SD':  'sd',  'SF':  'sf',
    'SEA': 'sea', 'STL': 'stl', 'TB':  'tb',  'TEX': 'tex',
    'TOR': 'tor', 'WSH': 'wsh',
}


def team_logo_url(abbr):
    if not abbr:
        return ''
    slug = _ESPN_SLUGS.get(abbr.upper(), abbr.lower())
    return f"https://a.espncdn.com/i/teamlogos/mlb/500/{slug}.png"


def build_player_team_map(picks):
    """Extract player→team from tracking picks; fill gaps from MLB Stats API."""
    mapping = {}
    for p in picks:
        name = p.get('selection', '').strip()
        team = (p.get('pitcher_team') or p.get('batting_team') or
                p.get('away_team') or p.get('home_team'))
        if name and team:
            mapping[name] = team

    # Fill remaining players from MLB Stats API (free, no key)
    try:
        r = requests.get(
            'https://statsapi.mlb.com/api/v1/sports/1/players?season=2026',
            timeout=10
        )
        if r.status_code == 200:
            for player in r.json().get('people', []):
                full_name = player.get('fullName', '')
                abbr = (player.get('currentTeam') or {}).get('abbreviation', '')
                if full_name and abbr and full_name not in mapping:
                    mapping[full_name] = abbr
    except Exception:
        pass

    return mapping


def load_picks():
    with open(TRACKING_FILE) as f:
        data = json.load(f)
    return data.get('picks', [])


def build_player_stats(picks, team_map):
    players = defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'pushes': 0,
        'profit': 0.0,
        'team': '',
        'by_type': defaultdict(lambda: {'wins': 0, 'losses': 0, 'pushes': 0}),
        'lines': [],
    })

    for p in picks:
        status = p.get('status', '').lower()
        if status not in ('win', 'loss', 'push'):
            continue

        name  = p.get('selection', '').strip()
        ptype = PROP_LABELS.get(p.get('type', ''), p.get('type', 'Other'))
        if not name or ptype == 'F5 ML':
            continue

        players[name]['by_type'][ptype]['wins'   if status == 'win'  else
                                        'losses' if status == 'loss' else
                                        'pushes'] += 1

        if status == 'win':
            players[name]['wins'] += 1
        elif status == 'loss':
            players[name]['losses'] += 1
        else:
            players[name]['pushes'] += 1

        players[name]['profit'] += float(p.get('profit', 0))
        players[name]['lines'].append(p.get('line', ''))
        if not players[name]['team']:
            players[name]['team'] = team_map.get(name, '')

    return players


def qualify(stats):
    total = stats['wins'] + stats['losses']
    return total >= MIN_PICKS


def win_rate(stats):
    total = stats['wins'] + stats['losses']
    return stats['wins'] / total if total else 0


def record_str(w, l, p=0):
    s = f"{w}-{l}"
    if p:
        s += f"-{p}"
    return s


def build_type_summary(picks):
    summary = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0.0})
    for p in picks:
        status = p.get('status', '').lower()
        if status not in ('win', 'loss', 'push'):
            continue
        label = PROP_LABELS.get(p.get('type', ''), 'Other')
        summary[label]['wins'   if status == 'win'  else
                        'losses' if status == 'loss' else
                        'pushes'] += 1
        summary[label]['profit'] += float(p.get('profit', 0))
    return summary


def render_player_card(name, stats, rank, best=True):
    w, l, pu = stats['wins'], stats['losses'], stats['pushes']
    total = w + l
    rate  = win_rate(stats)
    profit = stats['profit']
    color  = '#10b981' if best else '#ef4444'
    rank_bg = 'rgba(16,185,129,0.15)' if best else 'rgba(239,68,68,0.15)'

    logo_url = team_logo_url(stats.get('team', ''))
    logo_html = (f'<img src="{logo_url}" class="team-logo" alt="{stats["team"]}">'
                 if logo_url else '<div class="team-logo-placeholder"></div>')

    by_type_html = ''
    for ptype, ts in sorted(stats['by_type'].items()):
        tw, tl = ts['wins'], ts['losses']
        tt = tw + tl
        if tt == 0:
            continue
        tr = tw / tt
        tc = TYPE_COLORS.get(ptype, '#94a3b8')
        by_type_html += f"""
        <div class="type-chip">
            <span class="chip-dot" style="background:{tc}"></span>
            <span class="chip-label">{ptype}</span>
            <span class="chip-record">{tw}-{tl}</span>
            <span class="chip-rate" style="color:{tc}">{tr:.0%}</span>
        </div>"""

    return f"""
    <div class="player-card">
        <div class="player-rank" style="background:{rank_bg}; color:{color}">#{rank}</div>
        {logo_html}
        <div class="player-info">
            <div class="player-name">{name}</div>
            <div class="player-types">{by_type_html}</div>
        </div>
        <div class="player-stats">
            <div class="stat-block">
                <span class="stat-val" style="color:{color}">{rate:.0%}</span>
                <span class="stat-lbl">Hit Rate</span>
            </div>
            <div class="stat-block">
                <span class="stat-val">{record_str(w, l, pu)}</span>
                <span class="stat-lbl">Record</span>
            </div>
            <div class="stat-block">
                <span class="stat-val" style="color:{'#10b981' if profit >= 0 else '#ef4444'}">{profit:+.2f}u</span>
                <span class="stat-lbl">Profit</span>
            </div>
        </div>
    </div>"""


def render_type_card(label, ts):
    w, l, pu = ts['wins'], ts['losses'], ts['pushes']
    total = w + l
    rate  = w / total if total else 0
    profit = ts['profit']
    color  = TYPE_COLORS.get(label, '#94a3b8')
    bar_w  = int(rate * 100)
    return f"""
    <div class="type-card">
        <div class="type-header">
            <span class="type-dot" style="background:{color}"></span>
            <span class="type-name">{label}</span>
            <span class="type-record">{record_str(w, l, pu)}</span>
        </div>
        <div class="type-bar-bg">
            <div class="type-bar-fill" style="width:{bar_w}%; background:{color}"></div>
        </div>
        <div class="type-footer">
            <span style="color:{color}; font-weight:700">{rate:.1%} hit rate</span>
            <span style="color:{'#10b981' if profit >= 0 else '#ef4444'}">{profit:+.2f}u</span>
        </div>
    </div>"""


def generate_html(players, type_summary, picks):
    now_str = datetime.now().strftime('%B %d, %Y')

    qualified = {n: s for n, s in players.items() if qualify(s)}
    sorted_all = sorted(qualified.items(), key=lambda x: (win_rate(x[1]), x[1]['profit']), reverse=True)

    top_players  = sorted_all[:10]
    fade_players = sorted_all[-10:][::-1]

    total_graded = sum(p.get('status', '') in ('Win','Loss','Push') for p in picks)
    total_w = sum(1 for p in picks if p.get('status') == 'Win')
    total_l = sum(1 for p in picks if p.get('status') == 'Loss')
    overall_rate = total_w / (total_w + total_l) if (total_w + total_l) else 0

    top_html  = ''.join(render_player_card(n, s, i+1, best=True)  for i,(n,s) in enumerate(top_players))
    fade_html = ''.join(render_player_card(n, s, i+1, best=False) for i,(n,s) in enumerate(fade_players))

    type_order = ['H+R+RBI', 'Strikeouts', 'Pitching Outs', 'Home Run']
    type_html  = ''.join(render_type_card(t, type_summary[t]) for t in type_order if t in type_summary)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MLB Player Report – CourtSide Analytics</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #0a0a0a;
    --card: #1a1a1a;
    --box: #262626;
    --text: #ffffff;
    --muted: #94a3b8;
    --green: #10b981;
    --red: #ef4444;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); padding: 24px; }}
.container {{ max-width: 1100px; margin: 0 auto; }}

.header {{ text-align: center; margin-bottom: 40px; padding-bottom: 24px; border-bottom: 1px solid var(--box); }}
.brand {{ font-size: 2rem; font-weight: 800; letter-spacing: -0.02em;
    background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
.sub {{ color: var(--muted); font-size: 0.95rem; margin-top: 6px; }}

.summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 32px; }}
.summary-card {{ background: var(--card); border: 1px solid var(--box); border-radius: 12px; padding: 20px; text-align: center; }}
.summary-val {{ font-size: 2rem; font-weight: 800; }}
.summary-lbl {{ font-size: 0.8rem; color: var(--muted); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }}

.section {{ background: var(--card); border: 1px solid var(--box); border-radius: 16px; padding: 24px; margin-bottom: 24px; }}
.section-title {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }}
.section-title .bar {{ width: 4px; height: 20px; border-radius: 2px; }}

.player-card {{ display: flex; align-items: center; gap: 16px; padding: 14px 0;
    border-bottom: 1px solid var(--box); }}
.player-card:last-child {{ border-bottom: none; }}
.player-rank {{ width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-weight: 800; font-size: 0.85rem; flex-shrink: 0; }}
.team-logo {{ width: 36px; height: 36px; object-fit: contain; flex-shrink: 0; }}
.team-logo-placeholder {{ width: 36px; height: 36px; flex-shrink: 0; }}
.player-info {{ flex: 1; min-width: 0; }}
.player-name {{ font-weight: 700; font-size: 1rem; margin-bottom: 6px; }}
.player-types {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.type-chip {{ display: flex; align-items: center; gap: 4px; background: var(--box);
    border-radius: 20px; padding: 3px 10px; font-size: 0.75rem; }}
.chip-dot {{ width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }}
.chip-label {{ color: var(--muted); }}
.chip-record {{ font-weight: 600; margin-left: 2px; }}
.chip-rate {{ font-weight: 700; margin-left: 4px; }}
.player-stats {{ display: flex; gap: 20px; flex-shrink: 0; }}
.stat-block {{ text-align: center; }}
.stat-val {{ display: block; font-size: 1.1rem; font-weight: 800; }}
.stat-lbl {{ display: block; font-size: 0.7rem; color: var(--muted); text-transform: uppercase; margin-top: 2px; }}

.type-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
.type-card {{ background: var(--box); border-radius: 12px; padding: 16px; }}
.type-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }}
.type-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
.type-name {{ font-weight: 700; flex: 1; }}
.type-record {{ color: var(--muted); font-size: 0.85rem; }}
.type-bar-bg {{ background: #333; border-radius: 4px; height: 6px; margin-bottom: 10px; }}
.type-bar-fill {{ height: 6px; border-radius: 4px; transition: width 0.3s; }}
.type-footer {{ display: flex; justify-content: space-between; font-size: 0.85rem; font-weight: 600; }}

@media (max-width: 640px) {{
    .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .type-grid {{ grid-template-columns: 1fr; }}
    .player-stats {{ gap: 12px; }}
}}
</style>
</head>
<body>
<div class="container">

<div class="header">
    <div class="brand">⚾ MLB Player Report</div>
    <div class="sub">CourtSide Analytics &bull; {now_str} &bull; Min. {MIN_PICKS} graded picks</div>
</div>

<div class="summary-grid">
    <div class="summary-card">
        <div class="summary-val">{total_graded}</div>
        <div class="summary-lbl">Graded Picks</div>
    </div>
    <div class="summary-card">
        <div class="summary-val" style="color:{'var(--green)' if overall_rate >= 0.5 else 'var(--red)'}">
            {overall_rate:.1%}
        </div>
        <div class="summary-lbl">Overall Hit Rate</div>
    </div>
    <div class="summary-card">
        <div class="summary-val">{len(qualified)}</div>
        <div class="summary-lbl">Qualified Players</div>
    </div>
</div>

<div class="section">
    <div class="section-title">
        <span class="bar" style="background:var(--green)"></span>
        🔥 Top Players — Fade the Under
    </div>
    {top_html if top_html else '<p style="color:var(--muted)">Not enough data yet.</p>'}
</div>

<div class="section">
    <div class="section-title">
        <span class="bar" style="background:var(--red)"></span>
        ❄️ Fade These Players
    </div>
    {fade_html if fade_html else '<p style="color:var(--muted)">Not enough data yet.</p>'}
</div>

<div class="section">
    <div class="section-title">
        <span class="bar" style="background:#3b82f6"></span>
        📊 By Prop Type
    </div>
    <div class="type-grid">
        {type_html}
    </div>
</div>

</div>
</body>
</html>"""


def main():
    picks = load_picks()
    team_map = build_player_team_map(picks)
    players = build_player_stats(picks, team_map)
    type_summary = build_type_summary(picks)
    html = generate_html(players, type_summary, picks)
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)
    print(f"✅ MLB Player Report: {OUTPUT_HTML}")


if __name__ == '__main__':
    main()
