import json
from collections import defaultdict
import os
import sys
from datetime import datetime

# HTML Constants & CSS - Updated to match Prop_Model_Design.md
HTML_HEADER = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics - Performance Deep Dive</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Palette from Prop_Model_Design.md */
            --bg-black: #000000;
            --card-gray: #1a1a1a;
            --box-gray: #262626;
            --text-white: #ffffff;
            --text-slate: #94a3b8;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-blue: #3b82f6; /* Keeping blue for neutral/info */
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-black);
            color: var(--text-white);
            margin: 0;
            padding: 24px;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* Typography */
        h1, h2, h3 { margin: 0; color: var(--text-white); }
        
        .header {
            text-align: center;
            margin-bottom: 48px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--box-gray);
        }
        
        .brand-title {
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
            background: linear-gradient(135deg, var(--text-white) 0%, var(--text-slate) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .subtitle {
            color: var(--text-slate);
            font-size: 1rem;
            font-weight: 500;
        }
        
        /* Cards */
        .section {
            background-color: var(--card-gray);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            border: 1px solid var(--box-gray);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
        }
        
        .section-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-white);
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .section-title::before {
            content: '';
            display: block;
            width: 4px;
            height: 24px;
            background-color: var(--accent-green);
            border-radius: 2px;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
        }
        
        .stat-card {
            background-color: var(--bg-black);
            border: 1px solid var(--box-gray);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: transform 0.2s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            border-color: var(--text-slate);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 4px;
        }
        
        .stat-label {
            color: var(--text-slate);
            font-size: 0.875rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        /* Tables */
        .table-container {
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 0.95rem;
        }
        
        th {
            text-align: left;
            padding: 16px;
            color: var(--text-slate);
            font-weight: 600;
            border-bottom: 1px solid var(--box-gray);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }
        
        td {
            padding: 16px;
            border-bottom: 1px solid var(--box-gray);
            color: var(--text-white);
        }
        
        tr:last-child td { border-bottom: none; }
        
        tr:hover td {
            background-color: rgba(255, 255, 255, 0.02);
        }
        
        /* Utilities */
        .text-green { color: var(--accent-green); }
        .text-red { color: var(--accent-red); }
        .font-bold { font-weight: 700; }
        
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }
        
        .badge-hot {
            background-color: rgba(16, 185, 129, 0.2);
            color: var(--accent-green);
        }
        
        .badge-cold {
            background-color: rgba(239, 68, 68, 0.2);
            color: var(--accent-red);
        }
        
        .profit-value {
            font-family: 'DM Mono', monospace; /* Monospace for numbers alignment */
            font-weight: 700;
        }
        
        .two-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }
        
        @media (max-width: 768px) {
            .two-columns { grid-template-columns: 1fr; }
            .brand-title { font-size: 2rem; }
            .stat-value { font-size: 1.5rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="brand-title">CourtSide Analytics</h1>
            <p class="subtitle">NCAAB Performance Intelligence Report • Generated {date}</p>
        </div>
"""

HTML_FOOTER = """
    </div>
</body>
</html>
"""

def generate_report():
    # Load Data from Multiple Sources
    base_dir = '/Users/rico/sports-models/nba'
    files = {
        'Main Model': 'nba_picks_tracking.json',
        'Points Props': 'nba_points_props_tracking.json',
        'Rebounds Props': 'nba_rebounds_props_tracking.json',
        'Assists Props': 'nba_assists_props_tracking.json',
        '3PT Props': 'nba_3pt_props_tracking.json'
    }
    
    all_picks = []
    
    for source, filename in files.items():
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            with open(path, 'r') as f:
                try:
                    data = json.load(f)
                    # Handle different list names if necessary, usually 'picks' or 'history'
                    # Standardizing on 'picks' based on earlier checks
                    picks = data.get('picks', [])
                    for p in picks:
                        p['source'] = source # Tag the source
                        # Normalize pick_type for props if missing
                        if 'Props' in source and 'pick_type' not in p:
                            p['pick_type'] = 'prop'
                        all_picks.append(p)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        else:
            print(f"Warning: {filename} not found")

    # Sort and Filter
    decided_picks = [p for p in all_picks if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    # Sort by date descending
    def get_date(x): return x.get('game_date') or x.get('date_logged') or ''
    decided_picks.sort(key=get_date, reverse=True)
    
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    html = HTML_HEADER.replace("{date}", current_time).replace("NCAAB", "NBA")
    
    # --- HELPER: Calculate Profit in Units ---
    def get_unit_profit(pick):
        status = pick.get('status', '').lower()
        raw_profit = pick.get('profit', 0)
        
        # If profit logic is missing, infer standard -110 / -100
        if raw_profit == 0:
            if status == 'win': raw_profit = 91.0 
            elif status == 'loss': raw_profit = -100.0
        
        # FIX: The raw profit is in dollars (e.g. 91.0). Convert to Units (Divide by 100)
        return float(raw_profit) / 100.0

    # --- 1. KEY HIGHLIGHTS ---
    wins = sum(1 for p in decided_picks if p['status']=='win')
    losses = sum(1 for p in decided_picks if p['status']=='loss')
    pushes = sum(1 for p in decided_picks if p['status']=='push')
    total = len(decided_picks)
    
    total_profit_units = sum(get_unit_profit(p) for p in decided_picks)
    win_rate = (wins / (wins+losses) * 100) if (wins+losses) > 0 else 0
    
    profit_class = "text-green" if total_profit_units > 0 else "text-red"
    sign = "+" if total_profit_units > 0 else ""
    
    html += f"""
        <div class="section">
            <h2 class="section-title">Executive Summary (All Models)</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{total:,}</div>
                    <div class="stat-label">Total Bets Tracked</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{wins}-{losses}-{pushes}</div>
                    <div class="stat-label">Overall Record</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{win_rate:.1f}%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {profit_class}">{sign}{total_profit_units:.2f}u</div>
                    <div class="stat-label">Net Profit (Units)</div>
                </div>
            </div>
        </div>
    """

    # --- 2. ROLLING TRENDS ---
    html += """
        <div class="section">
            <h2 class="section-title">🔥 Trend Analysis</h2>
            <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Window</th>
                        <th>Record</th>
                        <th>Win Rate</th>
                        <th>Profit (Units)</th>
                        <th>Trend</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    windows = [10, 20, 50, 100, 200]
    for w in windows:
        if len(decided_picks) >= w:
            sample = decided_picks[:w]
            w_wins = sum(1 for p in sample if p['status'] == 'win')
            w_losses = sum(1 for p in sample if p['status'] == 'loss')
            w_pushes = sum(1 for p in sample if p['status'] == 'push')
            
            w_profit = sum(get_unit_profit(p) for p in sample)
            w_wr = (w_wins/(w_wins+w_losses)*100) if (w_wins+w_losses)>0 else 0
            
            badge = ""
            if w_wr >= 55: badge = '<span class="badge badge-hot">HOT</span>'
            elif w_wr < 48: badge = '<span class="badge badge-cold">COLD</span>'
            else: badge = '<span class="badge" style="background:#334155; color:#94a3b8">NORMAL</span>'
            
            p_class = 'text-green' if w_profit > 0 else 'text-red'
            p_sign = "+" if w_profit > 0 else ""
            
            html += f"""
                <tr>
                    <td class="font-bold">Last {w} Bets</td>
                    <td>{w_wins}-{w_losses}-{w_pushes}</td>
                    <td>{w_wr:.1f}%</td>
                    <td class="{p_class} profit-value">{p_sign}{w_profit:.2f}u</td>
                    <td>{badge}</td>
                </tr>
            """
    html += "</tbody></table></div></div>"
    
    # --- 3. CATEGORY BREAKDOWN ---
    # Enhanced for NBA Props
    categories = {
        'Spreads (Main)': lambda p: p.get('source') == 'Main Model' and 'spread' in p.get('pick_type', '').lower(),
        'Totals (Main)': lambda p: p.get('source') == 'Main Model' and 'total' in p.get('pick_type', '').lower(),
        'Player Props (All)': lambda p: 'Props' in p.get('source', ''),
        '🏀 Points': lambda p: 'Points' in p.get('source', ''),
        '🎯 3-Pointers': lambda p: '3PT' in p.get('source', ''),
        '🤝 Assists': lambda p: 'Assists' in p.get('source', ''),
        '💪 Rebounds': lambda p: 'Rebounds' in p.get('source', ''),
    }
    
    html += """
        <div class="section">
            <h2 class="section-title">💰 Profitability by Market</h2>
            <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Market Segment</th>
                        <th>Record</th>
                        <th>Win Rate</th>
                        <th>Profit (Units)</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for name, func in categories.items():
        cat_picks = [p for p in decided_picks if func(p)]
        if not cat_picks: continue # Skip empty categories
        
        c_wins = sum(1 for p in cat_picks if p['status']=='win')
        c_losses = sum(1 for p in cat_picks if p['status']=='loss')
        c_pushes = sum(1 for p in cat_picks if p['status']=='push')
        
        c_profit = sum(get_unit_profit(p) for p in cat_picks)
        c_wr = (c_wins/(c_wins+c_losses)*100) if (c_wins+c_losses)>0 else 0
        p_class = 'text-green' if c_profit > 0 else 'text-red'
        p_sign = "+" if c_profit > 0 else ""
        
        row_style = ""
        # Highlight Logic
        if "Spreads" in name: icon = "📊"
        elif "Totals" in name: icon = "↕️"
        elif "Props" in name: icon = "👤"
        elif "Points" in name: icon = "🏀"
        else: icon = "🔹"
            
        html += f"""
            <tr style="{row_style}">
                <td style="font-weight: 500;">{icon} {name}</td>
                <td>{c_wins}-{c_losses}-{c_pushes}</td>
                <td>{c_wr:.1f}%</td>
                <td class="{p_class} profit-value">{p_sign}{c_profit:.2f}u</td>
            </tr>
        """
        
    html += "</tbody></table></div></div>"

    # --- 4. TEAMS (Main Model Only) ---
    # We filter only Main Model Spreads/Totals for Team Analysis to keep "Fade/Follow" logic pure
    main_model_picks = [p for p in decided_picks if p.get('source') == 'Main Model']
    
    team_stats = defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0,
        'fav_w': 0, 'fav_l': 0, 'fav_p': 0,
        'dog_w': 0, 'dog_l': 0, 'dog_p': 0
    })
    
    for p in main_model_picks:
        # FIX: JSON key is 'pick', but some legacy might be 'pick_text'
        pick_text = (p.get('pick') or p.get('pick_text') or '').upper()
        home = p.get('home_team', '')
        away = p.get('away_team', '')
        
        # Determine which team was bet on
        bet_team = "Unknown"
        if home.upper() in pick_text: bet_team = home
        elif away.upper() in pick_text: bet_team = away
        else: continue
        
        s = team_stats[bet_team]
        
        # Update General
        if p['status'] == 'win': s['wins'] += 1
        elif p['status'] == 'loss': s['losses'] += 1
        elif p['status'] == 'push': s['pushes'] += 1
        s['profit'] += get_unit_profit(p)
        
        # Determine Fav/Dog Status based on pick text
        # Look for "+" or "-" associated with the spread
        # Examples: "Team +5.5", "Team -3.0", "Team PK"
        is_dog = False
        is_fav = False
        
        if "+" in pick_text:
            is_dog = True
        elif "-" in pick_text:
            is_fav = True
        # If 'PK' or neither, we skip the specific breakdown or assume one (optional)
        
        if is_dog:
            if p['status'] == 'win': s['dog_w'] += 1
            elif p['status'] == 'loss': s['dog_l'] += 1
            elif p['status'] == 'push': s['dog_p'] += 1
        elif is_fav:
            if p['status'] == 'win': s['fav_w'] += 1
            elif p['status'] == 'loss': s['fav_l'] += 1
            elif p['status'] == 'push': s['fav_p'] += 1
        
    team_list = []
    for team, stats in team_stats.items():
        total = stats['wins'] + stats['losses'] + stats['pushes']
        if total >= 5:
            wr = stats['wins'] / (stats['wins'] + stats['losses']) * 100 if (stats['wins'] + stats['losses']) > 0 else 0
            
            # Format Split Records
            fav_r = f"{stats['fav_w']}-{stats['fav_l']}-{stats['fav_p']}"
            dog_r = f"{stats['dog_w']}-{stats['dog_l']}-{stats['dog_p']}"
            
            team_list.append({
                'team': team, 
                'record': f"{stats['wins']}-{stats['losses']}-{stats['pushes']}", 
                'wr': wr, 
                'profit': stats['profit'],
                'fav_rec': fav_r,
                'dog_rec': dog_r
            })
            
            if team == 'Valparaiso Beacons':
                pass
            
    best_teams = sorted(team_list, key=lambda x: x['profit'], reverse=True)[:20]
    worst_teams = sorted(team_list, key=lambda x: x['profit'])[:20]

    # Helpers for totals
    def calc_totals(teams):
        w = sum(int(t['record'].split('-')[0]) for t in teams)
        l = sum(int(t['record'].split('-')[1]) for t in teams)
        p = sum(int(t['record'].split('-')[2]) for t in teams)
        prof = sum(t['profit'] for t in teams)
        return w, l, p, prof

    bw, bl, bp, bprof = calc_totals(best_teams)
    ww, wl, wp, wprof = calc_totals(worst_teams)
    
    html += '<div class="two-columns">'
    
    # Best Teams Column
    html += f"""
        <div class="section">
            <h2 class="section-title">✅ Auto-Bet Teams (Top 20)</h2>
            <div style="background: rgba(16, 185, 129, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-slate); text-transform: uppercase; font-weight: 600;">Combined Record</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-white);">{bw}-{bl}-{bp}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.75rem; color: var(--text-slate); text-transform: uppercase; font-weight: 600;">Total Profit</div>
                    <div style="font-size: 1.1rem; font-weight: 700;" class="text-green">+{bprof:.2f}u</div>
                </div>
            </div>
            <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Team</th>
                        <th>Record</th>
                        <th>Snippet (Fav / Dog)</th>
                        <th>Profit</th>
                    </tr>
                </thead>
                <tbody>
    """
    for t in best_teams:
        html += f"""<tr>
            <td style="color:var(--accent-green); font-weight:600">{t['team']}</td>
            <td>{t['record']}</td>
            <td style="font-size:0.8rem; color:var(--text-slate)">
                Fav: {t['fav_rec']} <br>
                Dog: {t['dog_rec']}
            </td>
            <td class="text-green profit-value">+{t['profit']:.2f}u</td>
        </tr>"""
    html += "</tbody></table></div></div>"
    
    # Worst Teams Column (Fade Logic)
    # We invert the record and profit for these teams
    fade_teams = []
    for t in worst_teams:
        # Parse current record
        rec_parts = t['record'].split('-')
        w = int(rec_parts[0])
        l = int(rec_parts[1])
        p = int(rec_parts[2])
        
        # Invert for Fade
        fade_w = l
        fade_l = w
        # Push remains push
        
        # Recalculate Profit: (Wins * 0.91) - (Losses * 1.00)
        # Note: We use 0.9091 (1/1.1) or just 0.91? The get_unit_profit uses 0.91.
        fade_profit = (fade_w * 0.91) - (fade_l * 1.0)
        
        fade_teams.append({
            'team': t['team'],
            'record': f"{fade_w}-{fade_l}-{p}",
            'profit': fade_profit,
            'fav_rec': t['fav_rec'], # These are snippets, maybe complex to invert display, keeping as reference
            'dog_rec': t['dog_rec']
        })
        
    # Calc totals for Fade
    fw = sum(int(t['record'].split('-')[0]) for t in fade_teams)
    fl = sum(int(t['record'].split('-')[1]) for t in fade_teams)
    fp = sum(int(t['record'].split('-')[2]) for t in fade_teams)
    fprof = sum(t['profit'] for t in fade_teams)

    html += f"""
        <div class="section">
            <h2 class="section-title">📉 Fade This Team (Bottom 20)</h2>
            <div style="background: rgba(16, 185, 129, 0.1); padding: 12px; border-radius: 8px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.75rem; color: var(--text-slate); text-transform: uppercase; font-weight: 600;">Fade Record</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-white);">{fw}-{fl}-{fp}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.75rem; color: var(--text-slate); text-transform: uppercase; font-weight: 600;">Fade Profit</div>
                    <div style="font-size: 1.1rem; font-weight: 700;" class="text-green">+{fprof:.2f}u</div>
                </div>
            </div>
            <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Team</th>
                        <th>Record (If Faded)</th>
                        <th>Snippet (Fav / Dog)</th>
                        <th>Profit</th>
                    </tr>
                </thead>
                <tbody>
    """
    for t in fade_teams:
        html += f"""<tr>
            <td style="color:var(--accent-red); font-weight:600">{t['team']}</td>
            <td>{t['record']}</td>
            <td style="font-size:0.8rem; color:var(--text-slate)">
                Fav: {t['fav_rec']} <br>
                Dog: {t['dog_rec']}
            </td>
            <td class="text-green profit-value">+{t['profit']:.2f}u</td>
        </tr>"""
    html += "</tbody></table></div></div></div>"
    
    html += HTML_FOOTER
    
    output_path = '/Users/rico/sports-models/nba/nba_analysis_report.html'
    with open(output_path, 'w') as f:
        f.write(html)
        
    print(f"HTML Report generated at: {output_path}")

if __name__ == "__main__":
    generate_report()
