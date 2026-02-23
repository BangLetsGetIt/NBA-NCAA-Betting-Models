#!/usr/bin/env python3
"""
NBA Player Props Analysis Report - CourtSide Analytics
Shows top/worst performing players broken down by each prop type.
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE_DIR = Path(__file__).parent

PROP_FILES = {
    "points":           ("nba_points_props_tracking.json",          "Points",      "PTS",  "actual_pts"),
    "rebounds":         ("nba_rebounds_props_tracking.json",         "Rebounds",    "REB",  "actual_reb"),
    "assists":          ("nba_assists_props_tracking.json",          "Assists",     "AST",  "actual_ast"),
    "threes":           ("nba_3pt_props_tracking.json",             "3-Pointers",  "3PM",  "actual_3pm"),
    "pra":              ("nba_pra_props_tracking.json",              "PRA",         "PRA",  "actual_pra"),
    "points_rebounds":  ("nba_points_rebounds_props_tracking.json",  "P+R",         "P+R",  "actual_p+r"),
    "points_assists":   ("nba_points_assists_props_tracking.json",   "P+A",         "P+A",  "actual_p+a"),
    "rebounds_assists": ("nba_rebounds_assists_props_tracking.json", "R+A",         "R+A",  "actual_r+a"),
}

NBA_TEAMS = {
    'Atlanta Hawks': 'atl', 'Boston Celtics': 'bos', 'Brooklyn Nets': 'bkn',
    'Charlotte Hornets': 'cha', 'Chicago Bulls': 'chi', 'Cleveland Cavaliers': 'cle',
    'Dallas Mavericks': 'dal', 'Denver Nuggets': 'den', 'Detroit Pistons': 'det',
    'Golden State Warriors': 'gsw', 'Houston Rockets': 'hou', 'Indiana Pacers': 'ind',
    'LA Clippers': 'lac', 'Los Angeles Lakers': 'lal', 'Memphis Grizzlies': 'mem',
    'Miami Heat': 'mia', 'Milwaukee Bucks': 'mil', 'Minnesota Timberwolves': 'min',
    'New Orleans Pelicans': 'no', 'New York Knicks': 'ny', 'Oklahoma City Thunder': 'okc',
    'Orlando Magic': 'orl', 'Philadelphia 76ers': 'phi', 'Phoenix Suns': 'phx',
    'Portland Trail Blazers': 'por', 'Sacramento Kings': 'sac', 'San Antonio Spurs': 'sa',
    'Toronto Raptors': 'tor', 'Utah Jazz': 'utah', 'Washington Wizards': 'was',
}


def load_prop_picks(prop_key):
    """Load settled picks for a given prop type. Returns list of pick dicts."""
    filename, label, unit, actual_field = PROP_FILES[prop_key]
    path = BASE_DIR / filename
    if not path.exists():
        return []

    with open(path) as f:
        data = json.load(f)

    picks = data.get("picks", [])
    result = []
    for p in picks:
        if p.get("status") not in ("win", "loss"):
            continue
        player = p.get("player", "").strip()
        if not player:
            continue

        actual = p.get(actual_field)
        line = p.get("prop_line")
        bet_type = p.get("bet_type", "").lower()

        # Compute margin: positive = we beat the line, negative = we missed
        margin = None
        if actual is not None and line is not None:
            try:
                actual = float(actual)
                line = float(line)
                if bet_type == "over":
                    margin = actual - line
                elif bet_type == "under":
                    margin = line - actual
            except (TypeError, ValueError):
                pass

        result.append({
            "player": player,
            "team": p.get("team", ""),
            "status": p.get("status"),
            "bet_type": bet_type,
            "pl": float(p.get("profit_loss", 0)),
            "margin": margin,
            "line": line,
            "actual": actual,
            "game_time": p.get("game_time", ""),
        })

    return result


def aggregate_player_stats(picks):
    """
    Aggregate picks by player.
    Returns dict: player -> stats dict with wins, losses, over/under breakdown, P&L.
    """
    players = defaultdict(lambda: {
        "wins": 0, "losses": 0,
        "over_wins": 0, "over_losses": 0,
        "under_wins": 0, "under_losses": 0,
        "pl": 0.0,
        "margins": [],
        "team": "",
        "last_game": "",
    })

    for pick in picks:
        p = players[pick["player"]]
        if pick["status"] == "win":
            p["wins"] += 1
            if pick["bet_type"] == "over":
                p["over_wins"] += 1
            elif pick["bet_type"] == "under":
                p["under_wins"] += 1
        else:
            p["losses"] += 1
            if pick["bet_type"] == "over":
                p["over_losses"] += 1
            elif pick["bet_type"] == "under":
                p["under_losses"] += 1

        p["pl"] += pick["pl"]
        if pick["margin"] is not None:
            p["margins"].append(pick["margin"])
        if not p["team"] and pick["team"]:
            p["team"] = pick["team"]
        if pick["game_time"] and pick["game_time"] > p["last_game"]:
            p["last_game"] = pick["game_time"]

    # Finalize
    result = {}
    for name, s in players.items():
        total = s["wins"] + s["losses"]
        if total == 0:
            continue
        win_rate = s["wins"] / total
        avg_margin = sum(s["margins"]) / len(s["margins"]) if s["margins"] else None
        result[name] = {
            "wins": s["wins"],
            "losses": s["losses"],
            "total": total,
            "win_rate": win_rate,
            "over_wins": s["over_wins"],
            "over_losses": s["over_losses"],
            "under_wins": s["under_wins"],
            "under_losses": s["under_losses"],
            "pl": s["pl"] / 100.0,  # dollars -> units
            "avg_margin": avg_margin,
            "team": s["team"],
            "team_abbrev": NBA_TEAMS.get(s["team"], ""),
        }

    return result


def build_prop_sections():
    """Load and aggregate stats for all prop types."""
    sections = {}
    for prop_key, (filename, label, unit, _) in PROP_FILES.items():
        picks = load_prop_picks(prop_key)
        stats = aggregate_player_stats(picks)
        total_picks = len(picks)
        total_wins = sum(s["wins"] for s in stats.values())
        total_losses = sum(s["losses"] for s in stats.values())
        total_pl = sum(s["pl"] for s in stats.values())
        win_rate = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0
        sections[prop_key] = {
            "label": label,
            "unit": unit,
            "players": stats,
            "total_picks": total_picks,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "total_pl": total_pl,
            "win_rate": win_rate,
        }
    return sections


def player_row_html(rank, name, stats, is_worst=False):
    """Render a single player table row."""
    abbrev = stats["team_abbrev"]
    logo_html = ""
    if abbrev:
        logo_html = f'<img src="https://a.espncdn.com/i/teamlogos/nba/500/{abbrev}.png" style="width:22px;height:22px;border-radius:50%;vertical-align:middle;margin-right:6px;">'

    wr = stats["win_rate"]
    wr_class = "text-green" if wr >= 0.56 else "text-red" if wr < 0.45 else "text-slate"
    pl_class = "text-green" if stats["pl"] > 0 else "text-red" if stats["pl"] < 0 else "text-slate"
    pl_sign = "+" if stats["pl"] >= 0 else ""

    record = f'{stats["wins"]}-{stats["losses"]}'

    # Over/Under breakdown
    over_total = stats["over_wins"] + stats["over_losses"]
    under_total = stats["under_wins"] + stats["under_losses"]
    ou_parts = []
    if over_total > 0:
        ou_parts.append(f'<span style="color:#60a5fa">▲{stats["over_wins"]}-{stats["over_losses"]}</span>')
    if under_total > 0:
        ou_parts.append(f'<span style="color:#a78bfa">▼{stats["under_wins"]}-{stats["under_losses"]}</span>')
    ou_str = " / ".join(ou_parts) if ou_parts else "—"

    # Avg margin
    if stats["avg_margin"] is not None:
        margin_sign = "+" if stats["avg_margin"] >= 0 else ""
        margin_class = "text-green" if stats["avg_margin"] >= 0 else "text-red"
        margin_str = f'<span class="{margin_class}">{margin_sign}{stats["avg_margin"]:.1f}</span>'
    else:
        margin_str = "—"

    rank_color = "#10b981" if not is_worst else "#ef4444"

    return f"""<tr>
        <td style="color:{rank_color};font-weight:700;width:36px">{rank}</td>
        <td><div style="display:flex;align-items:center">{logo_html}<span style="font-weight:600">{name}</span></div></td>
        <td style="color:var(--text-slate);font-size:0.8rem">{stats["team"] or "—"}</td>
        <td style="font-weight:600">{record}</td>
        <td class="{wr_class}" style="font-weight:700">{wr*100:.1f}%</td>
        <td style="font-size:0.85rem">{ou_str}</td>
        <td>{margin_str}</td>
        <td class="{pl_class}" style="font-weight:700;font-family:monospace">{pl_sign}{stats["pl"]:.2f}u</td>
    </tr>"""


def prop_tab_content(prop_key, section, min_picks):
    """Render the content for a single prop tab."""
    players = section["players"]
    label = section["label"]
    unit = section["unit"]
    total_picks = section["total_picks"]
    win_rate = section["win_rate"]
    total_pl = section["total_pl"]
    total_wins = section["total_wins"]
    total_losses = section["total_losses"]

    # Filter by min picks
    eligible = {n: s for n, s in players.items() if s["total"] >= min_picks}
    if not eligible:
        return f'<div style="color:var(--text-slate);padding:20px">Not enough data yet (need {min_picks}+ picks per player).</div>'

    sorted_best = sorted(eligible.items(), key=lambda x: (x[1]["win_rate"], x[1]["total"]), reverse=True)
    sorted_worst = sorted(eligible.items(), key=lambda x: (x[1]["win_rate"], -x[1]["total"]))

    pl_class = "text-green" if total_pl > 0 else "text-red"
    pl_sign = "+" if total_pl >= 0 else ""
    wr_class = "text-green" if win_rate >= 0.52 else "text-red"

    summary_html = f"""<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px">
        <div class="mini-stat"><div class="mini-val">{total_picks}</div><div class="mini-lbl">Total Picks</div></div>
        <div class="mini-stat"><div class="mini-val">{total_wins}-{total_losses}</div><div class="mini-lbl">Record</div></div>
        <div class="mini-stat"><div class="mini-val {wr_class}">{win_rate*100:.1f}%</div><div class="mini-lbl">Win Rate</div></div>
        <div class="mini-stat"><div class="mini-val {pl_class}">{pl_sign}{total_pl:.1f}u</div><div class="mini-lbl">Total P&L</div></div>
    </div>"""

    th = """<tr>
        <th>#</th><th>Player</th><th>Team</th><th>Record</th>
        <th>Win %</th><th>Over / Under</th><th>Avg Margin</th><th>P&L</th>
    </tr>"""

    top10_rows = "\n".join(player_row_html(i + 1, n, s, False) for i, (n, s) in enumerate(sorted_best[:10]))
    worst10_rows = "\n".join(player_row_html(i + 1, n, s, True) for i, (n, s) in enumerate(sorted_worst[:10]))

    return f"""{summary_html}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div>
            <div class="table-header table-header-green">Top Performers</div>
            <div class="table-container">
                <table><thead>{th}</thead><tbody>{top10_rows}</tbody></table>
            </div>
        </div>
        <div>
            <div class="table-header table-header-red">Struggling Players</div>
            <div class="table-container">
                <table><thead>{th}</thead><tbody>{worst10_rows}</tbody></table>
            </div>
        </div>
    </div>"""


def overall_tab_content(sections, min_picks):
    """Render the 'All Props' overview tab."""
    # Aggregate across all prop types per player
    combined = defaultdict(lambda: {"wins": 0, "losses": 0, "pl": 0.0, "team": "", "props": defaultdict(lambda: [0, 0])})

    for prop_key, section in sections.items():
        label = section["label"]
        for name, s in section["players"].items():
            c = combined[name]
            c["wins"] += s["wins"]
            c["losses"] += s["losses"]
            c["pl"] += s["pl"]
            c["props"][label][0] += s["wins"]
            c["props"][label][1] += s["losses"]
            if not c["team"] and s["team"]:
                c["team"] = s["team"]

    eligible = []
    for name, c in combined.items():
        total = c["wins"] + c["losses"]
        if total < min_picks:
            continue
        wr = c["wins"] / total
        abbrev = NBA_TEAMS.get(c["team"], "")
        prop_tags = []
        for prop_label, (w, l) in sorted(c["props"].items(), key=lambda x: -(x[1][0]+x[1][1])):
            if w + l > 0:
                prop_tags.append(f'<span class="prop-tag">{prop_label} {w}-{l}</span>')
        eligible.append({
            "name": name,
            "wins": c["wins"],
            "losses": c["losses"],
            "total": total,
            "win_rate": wr,
            "pl": c["pl"],
            "team": c["team"],
            "abbrev": abbrev,
            "prop_tags": " ".join(prop_tags),
        })

    sorted_best = sorted(eligible, key=lambda x: (x["win_rate"], x["total"]), reverse=True)
    sorted_worst = sorted(eligible, key=lambda x: (x["win_rate"], -x["total"]))

    def row(rank, p, is_worst):
        logo = f'<img src="https://a.espncdn.com/i/teamlogos/nba/500/{p["abbrev"]}.png" style="width:22px;height:22px;border-radius:50%;vertical-align:middle;margin-right:6px;">' if p["abbrev"] else ""
        wr = p["win_rate"]
        wr_class = "text-green" if wr >= 0.56 else "text-red" if wr < 0.45 else "text-slate"
        pl_class = "text-green" if p["pl"] > 0 else "text-red" if p["pl"] < 0 else "text-slate"
        pl_sign = "+" if p["pl"] >= 0 else ""
        rank_color = "#10b981" if not is_worst else "#ef4444"
        return f"""<tr>
            <td style="color:{rank_color};font-weight:700;width:36px">{rank}</td>
            <td><div style="display:flex;align-items:center">{logo}<span style="font-weight:600">{p["name"]}</span></div></td>
            <td style="font-weight:600">{p["wins"]}-{p["losses"]}</td>
            <td class="{wr_class}" style="font-weight:700">{wr*100:.1f}%</td>
            <td style="font-size:0.8rem">{p["prop_tags"]}</td>
            <td class="{pl_class}" style="font-weight:700;font-family:monospace">{pl_sign}{p["pl"]:.2f}u</td>
        </tr>"""

    th = "<tr><th>#</th><th>Player</th><th>Record</th><th>Win %</th><th>Props Breakdown</th><th>P&L</th></tr>"
    top_rows = "\n".join(row(i + 1, p, False) for i, p in enumerate(sorted_best[:15]))
    worst_rows = "\n".join(row(i + 1, p, True) for i, p in enumerate(sorted_worst[:15]))

    total_picks = sum(s["total_picks"] for s in sections.values())
    total_wins = sum(s["total_wins"] for s in sections.values())
    total_losses = sum(s["total_losses"] for s in sections.values())
    total_pl = sum(s["total_pl"] for s in sections.values())
    wr = total_wins / (total_wins + total_losses) if (total_wins + total_losses) > 0 else 0
    wr_class = "text-green" if wr >= 0.52 else "text-red"
    pl_class = "text-green" if total_pl > 0 else "text-red"
    pl_sign = "+" if total_pl >= 0 else ""

    summary = f"""<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:24px">
        <div class="mini-stat"><div class="mini-val">{total_picks}</div><div class="mini-lbl">Total Props</div></div>
        <div class="mini-stat"><div class="mini-val">{len(eligible)}</div><div class="mini-lbl">Players Tracked</div></div>
        <div class="mini-stat"><div class="mini-val">{total_wins}-{total_losses}</div><div class="mini-lbl">Record</div></div>
        <div class="mini-stat"><div class="mini-val {wr_class}">{wr*100:.1f}%</div><div class="mini-lbl">Win Rate</div></div>
        <div class="mini-stat"><div class="mini-val {pl_class}">{pl_sign}{total_pl:.1f}u</div><div class="mini-lbl">Total P&L</div></div>
    </div>"""

    return f"""{summary}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
        <div>
            <div class="table-header table-header-green">Top Performers (All Props)</div>
            <div class="table-container"><table><thead>{th}</thead><tbody>{top_rows}</tbody></table></div>
        </div>
        <div>
            <div class="table-header table-header-red">Struggling Players (All Props)</div>
            <div class="table-container"><table><thead>{th}</thead><tbody>{worst_rows}</tbody></table></div>
        </div>
    </div>"""


def generate_html(sections, min_picks_main=5, min_picks_combo=2):
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # Build tab buttons and content
    tab_order = [
        ("all", "All Props"),
        ("points", "Points"),
        ("rebounds", "Rebounds"),
        ("assists", "Assists"),
        ("threes", "3-Pointers"),
        ("pra", "PRA"),
        ("points_rebounds", "P+R"),
        ("points_assists", "P+A"),
        ("rebounds_assists", "R+A"),
    ]
    combo_keys = {"pra", "points_rebounds", "points_assists", "rebounds_assists"}

    tab_buttons = []
    tab_contents = []

    for i, (key, label) in enumerate(tab_order):
        active = "active" if i == 0 else ""
        tab_buttons.append(f'<button class="tab-btn {active}" onclick="showTab(\'{key}\')" id="btn-{key}">{label}</button>')

        if key == "all":
            content = overall_tab_content(sections, min_picks=min_picks_main)
        else:
            min_p = min_picks_combo if key in combo_keys else min_picks_main
            content = prop_tab_content(key, sections[key], min_picks=min_p)

        display = "block" if i == 0 else "none"
        tab_contents.append(f'<div id="tab-{key}" class="tab-content" style="display:{display}">{content}</div>')

    tabs_html = "\n".join(tab_buttons)
    content_html = "\n".join(tab_contents)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <title>CourtSide Analytics - Player Props Analysis</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-black: #000000;
            --card-gray: #1a1a1a;
            --box-gray: #262626;
            --text-white: #ffffff;
            --text-slate: #94a3b8;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bg-black);
            color: var(--text-white);
            padding: 24px;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}

        /* Header */
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--box-gray);
        }}
        .brand-title {{
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .brand-subtitle {{ color: var(--text-slate); font-size: 1rem; margin-top: 6px; }}

        /* Tabs */
        .tabs {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }}
        .tab-btn {{
            background: var(--card-gray);
            border: 1px solid var(--box-gray);
            color: var(--text-slate);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 600;
            font-family: 'Inter', sans-serif;
            transition: all 0.15s;
        }}
        .tab-btn:hover {{ border-color: var(--text-slate); color: var(--text-white); }}
        .tab-btn.active {{
            background: var(--accent-green);
            border-color: var(--accent-green);
            color: #000;
        }}

        /* Card section */
        .card {{
            background: var(--card-gray);
            border: 1px solid var(--box-gray);
            border-radius: 16px;
            padding: 24px;
        }}

        /* Mini stats */
        .mini-stat {{
            background: var(--bg-black);
            border: 1px solid var(--box-gray);
            border-radius: 10px;
            padding: 16px;
            text-align: center;
        }}
        .mini-val {{ font-size: 1.5rem; font-weight: 700; }}
        .mini-lbl {{ color: var(--text-slate); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; margin-top: 4px; }}

        /* Table headers */
        .table-header {{
            font-size: 0.875rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 10px 0;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .table-header::before {{
            content: '';
            display: block;
            width: 4px;
            height: 18px;
            border-radius: 2px;
        }}
        .table-header-green {{ color: var(--accent-green); }}
        .table-header-green::before {{ background: var(--accent-green); }}
        .table-header-red {{ color: var(--accent-red); }}
        .table-header-red::before {{ background: var(--accent-red); }}

        /* Tables */
        .table-container {{ overflow-x: auto; border-radius: 8px; border: 1px solid var(--box-gray); }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            text-align: left;
            padding: 10px 14px;
            color: var(--text-slate);
            font-weight: 600;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid var(--box-gray);
            background: rgba(255,255,255,0.02);
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid #1f1f1f;
            font-size: 0.875rem;
            vertical-align: middle;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover td {{ background: rgba(255,255,255,0.02); }}

        /* Utilities */
        .text-green {{ color: var(--accent-green); }}
        .text-red {{ color: var(--accent-red); }}
        .text-slate {{ color: var(--text-slate); }}
        .prop-tag {{
            display: inline-block;
            background: var(--box-gray);
            color: var(--text-slate);
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 600;
            margin: 1px;
        }}

        .footer {{
            text-align: center;
            padding: 32px;
            color: var(--text-slate);
            font-size: 0.8rem;
        }}

        @media (max-width: 900px) {{
            .brand-title {{ font-size: 1.8rem; }}
            body {{ padding: 12px; }}
            [style*="grid-template-columns:1fr 1fr"] {{
                grid-template-columns: 1fr !important;
            }}
            [style*="grid-template-columns:repeat(4"] {{
                grid-template-columns: repeat(2,1fr) !important;
            }}
            [style*="grid-template-columns:repeat(5"] {{
                grid-template-columns: repeat(2,1fr) !important;
            }}
        }}
    </style>
</head>
<body>
<div class="container">

    <div class="header">
        <h1 class="brand-title">CourtSide Analytics</h1>
        <p class="brand-subtitle">Player Props Intelligence Report &bull; Generated {now}</p>
    </div>

    <div class="tabs">
        {tabs_html}
    </div>

    <div class="card">
        {content_html}
    </div>

    <div class="footer">
        CourtSide Analytics &bull; NBA Player Props Performance Report<br>
        <span style="font-size:0.75rem">▲ = Over bets &nbsp;&bull;&nbsp; ▼ = Under bets &nbsp;&bull;&nbsp; Avg Margin = avg units over/under the line when correct direction</span>
    </div>

</div>
<script>
    function showTab(key) {{
        document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
        document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
        document.getElementById('tab-' + key).style.display = 'block';
        document.getElementById('btn-' + key).classList.add('active');
    }}
</script>
</body>
</html>"""


def main():
    print("Loading NBA prop tracking data...")
    sections = build_prop_sections()

    for key, s in sections.items():
        print(f"  {s['label']}: {s['total_picks']} picks, {len(s['players'])} players, {s['win_rate']*100:.1f}% win rate")

    html = generate_html(sections, min_picks_main=5, min_picks_combo=2)

    output = BASE_DIR / "nba_player_props_analysis.html"
    with open(output, "w") as f:
        f.write(html)

    print(f"\nReport saved: {output}")


if __name__ == "__main__":
    main()
