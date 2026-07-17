#!/usr/bin/env python3
"""WNBA Team Model — Moneyline, Spread, Totals
ESPN team stats + The Odds API. Outputs wnba_ml.html, wnba_spreads.html, wnba_totals.html
"""

import json
import os
import sys
from datetime import datetime, timedelta

import pytz
import requests
from dotenv import load_dotenv
from scipy.stats import norm

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(SCRIPT_DIR), '.env'))

ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')
ESPN_BASE    = 'https://site.api.espn.com/apis/site/v2/sports/basketball/wnba'
ODDS_BASE    = 'https://api.the-odds-api.com/v4'

HOME_ADV     = 3.2   # home court advantage in points
SPREAD_STD   = 11.0  # std dev of final score margin
TOTAL_STD    = 12.0  # std dev of combined score
KELLY_MULT   = 0.5

ML_MIN_EDGE  = 0.05
RL_MIN_EDGE  = 0.06
TOT_MIN_EDGE = 0.05

TRACKING_FILE = os.path.join(SCRIPT_DIR, 'wnba_team_tracking.json')
OUTPUT_HTML   = os.path.join(SCRIPT_DIR, 'wnba_model_output.html')  # kept for grader compat

OUTPUT_FILES = {
    'ml':      os.path.join(SCRIPT_DIR, 'wnba_ml.html'),
    'spreads': os.path.join(SCRIPT_DIR, 'wnba_spreads.html'),
    'totals':  os.path.join(SCRIPT_DIR, 'wnba_totals.html'),
}

TEAM_ABBREVS = {
    'Atlanta Dream':          'atl',
    'Chicago Sky':            'chi',
    'Connecticut Sun':        'con',
    'Dallas Wings':           'dal',
    'Golden State Valkyries': 'gsv',
    'Indiana Fever':          'ind',
    'Las Vegas Aces':         'lv',
    'Los Angeles Sparks':     'la',
    'Minnesota Lynx':         'min',
    'New York Liberty':       'ny',
    'Phoenix Mercury':        'phx',
    'Portland Fire':          'por',
    'Seattle Storm':          'sea',
    'Toronto Tempo':          'tor',
    'Washington Mystics':     'was',
}


class Colors:
    GREEN = "\033[92m"
    RED   = "\033[91m"
    CYAN  = "\033[96m"
    YELLOW = "\033[93m"
    END   = "\033[0m"


# ── ESPN helpers ──────────────────────────────────────────────────────────────

def fetch_team_stats() -> dict:
    """Return {team_name: {ppg, papg}} from ESPN WNBA standings (single API call)."""
    try:
        resp = requests.get(
            'https://site.api.espn.com/apis/v2/sports/basketball/wnba/standings',
            timeout=10,
        ).json()
    except Exception as e:
        print(f"{Colors.YELLOW}ESPN standings fetch failed: {e}{Colors.END}")
        return {}

    team_stats = {}
    for conf in resp.get('children', []):
        for entry in conf.get('standings', {}).get('entries', []):
            name = entry.get('team', {}).get('displayName', '')
            if not name:
                continue
            stats = entry.get('stats', [])
            ppg  = next((float(s['value']) for s in stats if s.get('name') == 'avgPointsFor'),  85.0)
            papg = next((float(s['value']) for s in stats if s.get('name') == 'avgPointsAgainst'), 85.0)
            team_stats[name] = {'ppg': ppg, 'papg': papg}

    print(f"{Colors.GREEN}  ESPN standings loaded: {len(team_stats)} teams{Colors.END}")
    return team_stats


def fetch_schedule(date_str: str) -> list:
    """Return list of {home_team, away_team, game_time, event_id} for date_str."""
    date_compact = date_str.replace('-', '')
    try:
        sb = requests.get(
            f"{ESPN_BASE}/scoreboard", params={'dates': date_compact}, timeout=10
        ).json()
    except Exception as e:
        print(f"{Colors.YELLOW}ESPN scoreboard error: {e}{Colors.END}")
        return []

    games = []
    for event in sb.get('events', []):
        comps = event.get('competitions', [{}])[0]
        competitors = comps.get('competitors', [])
        home = next((c for c in competitors if c.get('homeAway') == 'home'), None)
        away = next((c for c in competitors if c.get('homeAway') == 'away'), None)
        if not home or not away:
            continue
        games.append({
            'home_team': home.get('team', {}).get('displayName', ''),
            'away_team': away.get('team', {}).get('displayName', ''),
            'game_time': event.get('date', ''),
            'event_id':  event.get('id', ''),
        })

    return games


def fetch_game_odds() -> dict:
    """Fetch h2h, spreads, totals for all upcoming WNBA games.
    Returns {(home_name, away_name): {h2h, spreads, totals, game_time}}
    """
    if not ODDS_API_KEY:
        print(f"{Colors.YELLOW}No ODDS_API_KEY — skipping team odds{Colors.END}")
        return {}

    try:
        resp = requests.get(
            f"{ODDS_BASE}/sports/basketball_wnba/odds",
            params={
                'apiKey':      ODDS_API_KEY,
                'regions':     'us',
                'markets':     'h2h,spreads,totals',
                'oddsFormat':  'american',
            },
            timeout=15,
        )
        resp.raise_for_status()
        events = resp.json()
    except Exception as e:
        print(f"{Colors.YELLOW}WNBA odds fetch error: {e}{Colors.END}")
        return {}

    priority = {'fanduel': 0, 'draftkings': 1, 'betmgm': 2, 'caesars': 3}
    lookup = {}

    for event in events:
        home_full = event.get('home_team', '')
        away_full = event.get('away_team', '')
        gd = {
            'h2h':      {},
            'spreads':  {},
            'totals':   {},
            'game_time': event.get('commence_time', ''),
        }

        books = sorted(
            event.get('bookmakers', []),
            key=lambda b: priority.get(b.get('key', ''), 99),
        )
        for book in books:
            for market in book.get('markets', []):
                mk = market.get('key')
                if mk == 'h2h' and not gd['h2h']:
                    for oc in market.get('outcomes', []):
                        gd['h2h'][oc['name']] = int(oc['price'])
                elif mk == 'spreads' and not gd['spreads']:
                    for oc in market.get('outcomes', []):
                        gd['spreads'][oc['name']] = (int(oc['price']), float(oc.get('point', 0)))
                elif mk == 'totals' and not gd['totals']:
                    for oc in market.get('outcomes', []):
                        side = oc['name'].lower()
                        gd['totals'][side] = (int(oc['price']), float(oc.get('point', 165.0)))

        lookup[(home_full, away_full)] = gd

    print(f"{Colors.GREEN}  WNBA game odds loaded: {len(lookup)} games{Colors.END}")
    return lookup


# ── Prediction model ──────────────────────────────────────────────────────────

def predict_game(home_stats: dict, away_stats: dict) -> tuple:
    """Return (home_proj, away_proj, expected_margin, expected_total)."""
    h_ppg  = home_stats.get('ppg',  83.0)
    h_papg = home_stats.get('papg', 83.0)
    a_ppg  = away_stats.get('ppg',  83.0)
    a_papg = away_stats.get('papg', 83.0)

    home_proj = (h_ppg + a_papg) / 2 + HOME_ADV / 2
    away_proj = (a_ppg + h_papg) / 2 - HOME_ADV / 2

    expected_margin = home_proj - away_proj
    expected_total  = home_proj + away_proj
    return round(home_proj, 1), round(away_proj, 1), round(expected_margin, 1), round(expected_total, 1)


def win_probability(expected_margin: float) -> float:
    """P(home wins) from expected margin using normal spread distribution."""
    return float(1 - norm.cdf(0, loc=expected_margin, scale=SPREAD_STD))


def spread_probability(expected_margin: float, point: float) -> float:
    """P(team covers spread). point is from that team's perspective (negative = fav)."""
    return float(1 - norm.cdf(-point, loc=expected_margin, scale=SPREAD_STD))


def total_probability(expected_total: float, line: float, direction: str) -> float:
    if direction == 'over':
        return float(1 - norm.cdf(line, loc=expected_total, scale=TOTAL_STD))
    return float(norm.cdf(line, loc=expected_total, scale=TOTAL_STD))


def kelly(prob: float, dec_odds: float) -> float:
    edge = prob * dec_odds - 1
    denom = dec_odds - 1
    return max(0.0, edge / denom * KELLY_MULT) if denom > 0 else 0.0


def dec_odds(american: int) -> float:
    return (1 + 100 / abs(american)) if american < 0 else (1 + american / 100)


def fmt_time(iso: str) -> str:
    if not iso:
        return ''
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        et = dt.astimezone(pytz.timezone('US/Eastern'))
        return et.strftime('%-I:%M %p ET')
    except Exception:
        return ''


def logo_url(team_name: str) -> str:
    abbr = TEAM_ABBREVS.get(team_name, '')
    if abbr:
        return f"https://a.espncdn.com/i/teamlogos/wnba/500/{abbr}.png"
    return "https://a.espncdn.com/i/teamlogos/wnba/500/wnba.png"


# ── Tracking ──────────────────────────────────────────────────────────────────

def load_tracking():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {'picks': []}


def save_tracking(data):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def track_picks(picks: list):
    td = load_tracking()
    existing = {p['id'] for p in td['picks']}
    added = 0
    for p in picks:
        if p['id'] not in existing:
            p.setdefault('status', 'pending')
            p.setdefault('result', None)
            p.setdefault('profit_loss', 0)
            p['tracked_at'] = datetime.now().isoformat()
            td['picks'].append(p)
            added += 1
    if added:
        save_tracking(td)
        print(f"{Colors.GREEN}  Tracked {added} new picks{Colors.END}")


def get_stats(kind: str = None):
    """Compute tracking stats. Pass kind='ml'/'spreads'/'totals' for per-type stats."""
    td = load_tracking()
    all_picks = td.get('picks', [])
    if kind:
        all_picks = [p for p in all_picks if p.get('kind') == kind]
    completed = [p for p in all_picks
                 if p.get('status', '').lower() in ('win', 'loss', 'push')]

    def calc(subset):
        wins   = sum(1 for p in subset if p.get('status', '').lower() == 'win')
        losses = sum(1 for p in subset if p.get('status', '').lower() == 'loss')
        pushes = sum(1 for p in subset if p.get('status', '').lower() == 'push')
        profit = sum(float(p.get('profit_loss', 0)) for p in subset) / 100.0
        total  = wins + losses
        wr     = (wins / total * 100) if total > 0 else 0.0
        return {'record': f"{wins}-{losses}-{pushes}", 'win_rate': wr,
                'profit': profit, 'count': wins + losses + pushes}

    season  = calc(completed)
    last_10 = calc(completed[-10:])
    return season, last_10


def _get_active_picks() -> list:
    """Load today's pending picks from the tracking file for HTML display."""
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    td = load_tracking()
    active = []
    for p in td.get('picks', []):
        if p.get('status', 'pending') != 'pending':
            continue
        gt = p.get('game_time', '')
        if gt:
            try:
                dt = datetime.fromisoformat(gt.replace('Z', '+00:00'))
                dt_et = dt.astimezone(et_tz)
                # Show picks for today and tomorrow
                if dt_et.date() < now_et.date():
                    continue
            except Exception:
                pass
        active.append(p)
    return active


# ── HTML ──────────────────────────────────────────────────────────────────────

_CSS = """
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
    .prop-card { background:var(--bg-card); border-radius:16px; overflow:hidden;
                 margin-bottom:20px; border:1px solid var(--border-color);
                 box-shadow:0 4px 6px -1px rgba(0,0,0,.2); }
    .card-header { padding:12px 16px; display:flex; justify-content:space-between;
                   align-items:center; background:var(--bg-card-secondary);
                   border-bottom:1px solid var(--border-color); }
    .header-left { display:flex; align-items:center; gap:10px; }
    .team-logo { width:40px; height:40px; border-radius:50%; object-fit:contain; }
    .team-logo-sm { width:28px; height:28px; border-radius:50%; object-fit:contain; }
    .player-info h2 { margin:0; font-size:15px; line-height:1.2; }
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
    .metrics-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px;
                    margin-bottom:12px; }
    .metric-item { background:var(--bg-card-secondary); border-radius:8px;
                   padding:8px; text-align:center; }
    .metric-lbl { font-size:10px; color:var(--text-secondary); text-transform:uppercase;
                  letter-spacing:.05em; margin-bottom:3px; font-weight:600; }
    .metric-val { font-size:16px; font-weight:700; }
    .stats-row { display:grid; grid-template-columns:repeat(2,1fr); gap:8px;
                 margin-bottom:12px; }
    .stat-item { background:var(--bg-card-secondary); border-radius:8px; padding:8px;
                 text-align:center; }
    .stat-title { font-size:10px; color:var(--text-secondary); text-transform:uppercase;
                  margin-bottom:3px; font-weight:600; }
    .stat-val { font-size:15px; font-weight:700; }
    .tags-container { display:flex; flex-wrap:wrap; gap:6px; }
    .tag { font-size:11px; padding:4px 8px; border-radius:4px; font-weight:500; }
    .tag-green { background:rgba(74,222,128,.15); color:var(--accent-green); }
    .tag-blue  { background:rgba(96,165,250,.15); color:var(--accent-blue); }
    .tag-red   { background:rgba(248,113,113,.15); color:var(--accent-red); }
    .txt-green { color:var(--accent-green); }
    .txt-red   { color:var(--accent-red); }
    .txt-blue  { color:var(--accent-blue); }
    .glow-green { box-shadow:0 0 15px rgba(74,222,128,.15);
                  border:1px solid rgba(74,222,128,.3) !important; }
    .glow-blue  { box-shadow:0 0 15px rgba(96,165,250,.15);
                  border:1px solid rgba(96,165,250,.3) !important; }
    .nav-bar { display:flex; gap:8px; margin-bottom:25px; overflow-x:auto;
               padding-bottom:5px; flex-wrap:nowrap; }
    .nav-pill { padding:7px 14px; background:var(--bg-card);
                border:1px solid var(--border-color); border-radius:20px;
                color:var(--text-secondary); text-decoration:none;
                font-size:12px; font-weight:500; white-space:nowrap; }
    .nav-pill:hover, .nav-pill.active { background:var(--bg-card-secondary);
                                        color:var(--text-primary);
                                        border-color:var(--text-primary); }
    .no-picks { color:#666; text-align:center; padding:30px;
                font-size:14px; background:var(--bg-card);
                border-radius:16px; border:1px solid var(--border-color); }
    @media(max-width:600px){
        .summary-grid{grid-template-columns:repeat(2,1fr);}
        .stat-box:last-child{grid-column:span 2;}
        .metrics-grid{grid-template-columns:repeat(3,1fr);}
    }
"""

_NAV_LINKS = [
    ('ml',      'wnba_ml.html',                    'Moneyline'),
    ('spreads',  'wnba_spreads.html',               'Spreads'),
    ('totals',   'wnba_totals.html',                'Totals'),
    ('points',   'wnba_points_props.html',          'Points'),
    ('rebounds', 'wnba_rebounds_props.html',        'Rebounds'),
    ('assists',  'wnba_assists_props.html',         'Assists'),
    ('threes',   'wnba_3pt_props.html',             '3-Pointers'),
    ('pra',      'wnba_pra_props.html',             'PRA'),
]


def _nav_html(active: str) -> str:
    pills = ''.join(
        f'<a href="{href}" class="nav-pill{" active" if key == active else ""}">{label}</a>'
        for key, href, label in _NAV_LINKS
    )
    return f'<nav class="nav-bar">{pills}</nav>'


def _render_pick_card(pick: dict) -> str:
    home    = pick['home_team']
    away    = pick['away_team']
    matchup = f"{away} @ {home}"
    gt      = fmt_time(pick.get('game_time', ''))
    kind    = pick['kind']

    home_logo = logo_url(home)
    away_logo = logo_url(away)

    h_proj = pick['home_proj']
    a_proj = pick['away_proj']
    margin = pick['expected_margin']

    if kind == 'ml':
        team     = pick['bet_team']
        headline = f"{team} ML"
        sub      = (f"Model: <strong>{home} {h_proj}</strong> – "
                    f"<strong>{away} {a_proj}</strong>"
                    f" (margin {margin:+.1f})")
        glow     = 'glow-green'
        color    = 'txt-green'
    elif kind == 'spreads':
        team  = pick['bet_team']
        point = pick['point']
        pt_s  = f"{point:+.1f}" if isinstance(point, float) else str(point)
        headline = f"{team} {pt_s}"
        sub   = (f"Model margin: <strong>{margin:+.1f}</strong> · "
                 f"Proj: <strong>{home} {h_proj} – {away} {a_proj}</strong>")
        glow  = 'glow-blue'
        color = 'txt-blue'
    else:  # totals
        direction  = pick['direction'].upper()
        tot_line   = pick['tot_line']
        exp_total  = pick['expected_total']
        headline   = f"{direction} {tot_line}"
        sub        = f"Model total: <strong>{exp_total:.1f}</strong> (line {tot_line})"
        glow       = 'glow-green' if direction == 'OVER' else 'glow-blue'
        color      = 'txt-green' if direction == 'OVER' else 'txt-red'

    prob    = pick['prob']
    edge    = pick['edge']
    kel_pct = pick['kelly']

    tags = ''
    if edge > 0.10:
        tags += '<span class="tag tag-green">High Value</span>'
    tags += f'<span class="tag tag-blue">Edge: +{edge:.1%}</span>'

    return f"""
<div class="prop-card {glow}">
  <div class="card-header">
    <div class="header-left">
      <img src="{away_logo}" class="team-logo" onerror="this.style.display='none'">
      <span style="color:#666;font-size:12px;padding:0 4px">@</span>
      <img src="{home_logo}" class="team-logo" onerror="this.style.display='none'">
      <div class="player-info" style="margin-left:6px">
        <h2>{matchup}</h2>
        <div class="matchup-info">WNBA · Team Props</div>
      </div>
    </div>
    {'<div class="game-date-time">' + gt + '</div>' if gt else ''}
  </div>
  <div class="card-body">
    <div class="bet-main-row">
      <span class="bet-selection {color}">{headline}</span>
      <span class="bet-odds">{pick['odds_str']}</span>
    </div>
    <div class="model-subtext">{sub}</div>
    <div class="metrics-grid">
      <div class="metric-item">
        <div class="metric-lbl">Win %</div>
        <div class="metric-val txt-green">{prob:.0%}</div>
      </div>
      <div class="metric-item">
        <div class="metric-lbl">Edge</div>
        <div class="metric-val txt-green">+{edge:.1%}</div>
      </div>
      <div class="metric-item">
        <div class="metric-lbl">Kelly</div>
        <div class="metric-val">{kel_pct:.1%}</div>
      </div>
    </div>
    <div class="stats-row">
      <div class="stat-item">
        <div class="stat-title">{home} PPG</div>
        <div class="stat-val">{pick.get('home_ppg', '—')}</div>
      </div>
      <div class="stat-item">
        <div class="stat-title">{away} PPG</div>
        <div class="stat-val">{pick.get('away_ppg', '—')}</div>
      </div>
    </div>
    <div class="tags-container">{tags}</div>
  </div>
</div>"""


def _page_header(active_key: str, title: str, subtitle: str, kind: str) -> str:
    """Render nav + header + summary stats for one page. Stats are type-specific."""
    season, last_10 = get_stats(kind)
    units_color = '#4ade80' if season['profit'] >= 0 else '#f87171'
    l10_color   = '#4ade80' if last_10['profit'] >= 0 else '#f87171'
    date_str = datetime.now().strftime('%B %d, %Y')
    return f"""
  {_nav_html(active_key)}
  <header>
    <div>
      <h1>🏀 WNBA {title}</h1>
      <div class="date-sub">{date_str} · {subtitle}</div>
    </div>
  </header>
  <div class="summary-grid">
    <div class="stat-box">
      <div class="stat-label">Season</div>
      <div class="stat-value">{season['record']}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Win Rate</div>
      <div class="stat-value" style="color:{'#4ade80' if season['win_rate'] >= 55 else '#f87171'}">{season['win_rate']:.1f}%</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Units</div>
      <div class="stat-value" style="color:{units_color}">{season['profit']:+.2f}u</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">L10 Record</div>
      <div class="stat-value">{last_10['record']}</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">L10 Units</div>
      <div class="stat-value" style="color:{l10_color}">{last_10['profit']:+.2f}u</div>
    </div>
    <div class="stat-box">
      <div class="stat-label">Graded</div>
      <div class="stat-value">{season['count']}</div>
    </div>
  </div>"""


def _wrap_html(active_key: str, title: str, subtitle: str, kind: str, body: str) -> str:
    hdr = _page_header(active_key, title, subtitle, kind)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WNBA {title}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head>
<body>
<div class="container">
{hdr}
<div class="section-title" style="margin-top:10px">{title}</div>
{body}
</div>
</body>
</html>"""


def generate_html(new_picks: list = None):
    """Generate wnba_ml.html, wnba_spreads.html, wnba_totals.html.
    Uses active pending picks from tracking for display; new_picks are merged in.
    """
    # Pull active picks from tracking file so pages stay populated after grading
    active = _get_active_picks()
    active_ids = {p['id'] for p in active}

    # Merge in any freshly generated picks not yet in tracking
    if new_picks:
        for p in new_picks:
            if p['id'] not in active_ids:
                active.append(p)

    no_picks = '<div class="no-picks">No qualifying picks today.</div>'

    ml_picks     = [p for p in active if p.get('kind') == 'ml']
    spread_picks = [p for p in active if p.get('kind') == 'spreads']
    total_picks  = [p for p in active if p.get('kind') == 'totals']

    ml_body = ''.join(_render_pick_card(p) for p in ml_picks) or no_picks
    with open(OUTPUT_FILES['ml'], 'w') as f:
        f.write(_wrap_html('ml', 'Moneyline', 'Win/Loss · Model vs Market', 'ml', ml_body))
    print(f"{Colors.CYAN}  → wnba_ml.html ({len(ml_picks)} picks){Colors.END}")

    sp_body = ''.join(_render_pick_card(p) for p in spread_picks) or no_picks
    with open(OUTPUT_FILES['spreads'], 'w') as f:
        f.write(_wrap_html('spreads', 'Spreads', 'ATS · Model vs Market', 'spreads', sp_body))
    print(f"{Colors.CYAN}  → wnba_spreads.html ({len(spread_picks)} picks){Colors.END}")

    tot_body = ''.join(_render_pick_card(p) for p in total_picks) or no_picks
    with open(OUTPUT_FILES['totals'], 'w') as f:
        f.write(_wrap_html('totals', 'Totals', 'Over/Under · Model vs Market', 'totals', tot_body))
    print(f"{Colors.CYAN}  → wnba_totals.html ({len(total_picks)} picks){Colors.END}")

    # Redirect stub for grader compat
    with open(OUTPUT_HTML, 'w') as f:
        f.write('<html><head><meta http-equiv="refresh" content="0;url=wnba_ml.html"></head>'
                '<body><a href="wnba_ml.html">Moneyline</a></body></html>')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    # Before noon ET → use today; noon+ → look at tomorrow
    if now_et.hour < 12:
        target = now_et
    else:
        target = now_et + timedelta(days=1)
    date_str = target.strftime('%Y-%m-%d')
    today_id = target.strftime('%Y%m%d')

    print(f"\n--- WNBA TEAM MODEL: {date_str} ---")

    print("Fetching team stats...")
    team_stats = fetch_team_stats()

    print("Fetching schedule...")
    schedule = fetch_schedule(date_str)
    print(f"{Colors.GREEN}  {len(schedule)} games on {date_str}{Colors.END}")

    print("Fetching game odds...")
    odds_lookup = fetch_game_odds()

    print("\n--- ANALYZING ---")
    picks = []

    for game in schedule:
        home = game['home_team']
        away = game['away_team']
        matchup = f"{away} @ {home}"
        game_time = game.get('game_time', '')

        # Look up odds — Odds API uses full team names
        gd = odds_lookup.get((home, away)) or odds_lookup.get((away, home))
        if not gd:
            print(f"  {matchup}: no odds found")
            continue

        h2h     = gd.get('h2h', {})
        spreads = gd.get('spreads', {})
        totals  = gd.get('totals', {})
        gt      = gd.get('game_time', game_time)

        if not h2h:
            continue

        h_stats = team_stats.get(home, {'ppg': 83.0, 'papg': 83.0})
        a_stats = team_stats.get(away, {'ppg': 83.0, 'papg': 83.0})

        h_proj, a_proj, exp_margin, exp_total = predict_game(h_stats, a_stats)
        home_win_p = win_probability(exp_margin)
        away_win_p = 1.0 - home_win_p

        print(f"  {matchup}: proj {home} {h_proj} - {away} {a_proj} "
              f"| margin {exp_margin:+.1f} | total {exp_total:.1f}")

        base = {
            'home_team':       home,
            'away_team':       away,
            'matchup':         matchup,
            'game_time':       gt,
            'home_proj':       h_proj,
            'away_proj':       a_proj,
            'expected_margin': exp_margin,
            'expected_total':  exp_total,
            'home_ppg':        round(h_stats['ppg'], 1),
            'away_ppg':        round(a_stats['ppg'], 1),
        }

        # --- Moneyline ---
        for team, win_p, odds_raw in [
            (home, home_win_p, h2h.get(home)),
            (away, away_win_p, h2h.get(away)),
        ]:
            if odds_raw is None:
                continue
            d = dec_odds(odds_raw)
            implied = 1 / d
            edge = win_p - implied
            if edge > ML_MIN_EDGE:
                k = kelly(win_p, d)
                pick = {**base,
                    'id':       f"WNBA_ML_{team.replace(' ','_')}_{today_id}",
                    'kind':     'ml',
                    'type':     'WNBA Moneyline',
                    'bet_team': team,
                    'selection': f"{team} ML",
                    'odds_str': f"{odds_raw:+d}" if odds_raw > 0 else str(odds_raw),
                    'odds_dec': d,
                    'prob':     round(win_p, 3),
                    'edge':     round(edge, 3),
                    'kelly':    k,
                    'status':   'pending',
                }
                picks.append(pick)
                print(f"    {Colors.GREEN}ML: {team}  prob={win_p:.1%}  edge={edge:+.1%}  {odds_raw}{Colors.END}")

        # --- Spreads ---
        for team, tm_margin, odds_entry in [
            (home, exp_margin, spreads.get(home)),
            (away, -exp_margin, spreads.get(away)),
        ]:
            if odds_entry is None:
                continue
            odds_raw, point = odds_entry
            cover_p = spread_probability(tm_margin, point)
            d = dec_odds(odds_raw)
            implied = 1 / d
            edge = cover_p - implied
            if edge > RL_MIN_EDGE:
                k = kelly(cover_p, d)
                pt_s = f"{point:+.1f}"
                pick = {**base,
                    'id':       f"WNBA_SPD_{team.replace(' ','_')}_{today_id}",
                    'kind':     'spreads',
                    'type':     'WNBA Spread',
                    'bet_team': team,
                    'point':    point,
                    'selection': f"{team} {pt_s}",
                    'odds_str': f"{odds_raw:+d}" if odds_raw > 0 else str(odds_raw),
                    'odds_dec': d,
                    'prob':     round(cover_p, 3),
                    'edge':     round(edge, 3),
                    'kelly':    k,
                    'status':   'pending',
                }
                picks.append(pick)
                print(f"    {Colors.GREEN}SPD: {team} {pt_s}  prob={cover_p:.1%}  edge={edge:+.1%}  {odds_raw}{Colors.END}")

        # --- Totals ---
        for direction in ('over', 'under'):
            tot_entry = totals.get(direction)
            if tot_entry is None:
                continue
            odds_raw, tot_line = tot_entry
            tot_p = total_probability(exp_total, tot_line, direction)
            d = dec_odds(odds_raw)
            implied = 1 / d
            edge = tot_p - implied
            if edge > TOT_MIN_EDGE:
                k = kelly(tot_p, d)
                pick = {**base,
                    'id':       f"WNBA_TOT_{direction.upper()}_{home.replace(' ','_')}_{today_id}",
                    'kind':     'totals',
                    'type':     'WNBA Total',
                    'direction': direction,
                    'tot_line':  tot_line,
                    'selection': f"{direction.upper()} {tot_line}",
                    'odds_str': f"{odds_raw:+d}" if odds_raw > 0 else str(odds_raw),
                    'odds_dec': d,
                    'prob':     round(tot_p, 3),
                    'edge':     round(edge, 3),
                    'kelly':    k,
                    'status':   'pending',
                }
                picks.append(pick)
                print(f"    {Colors.GREEN}TOT: {direction.upper()} {tot_line}  "
                      f"exp={exp_total:.1f}  edge={edge:+.1%}  {odds_raw}{Colors.END}")

    track_picks(picks)
    generate_html(picks)
    print(f"\n{Colors.GREEN}Done. {len(picks)} total team picks.{Colors.END}")


if __name__ == '__main__':
    main()
