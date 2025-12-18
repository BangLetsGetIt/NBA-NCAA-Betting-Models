#!/usr/bin/env python3
"""WNBA Spreads & Totals Model - Sharp Efficiency Version
Uses Four Factors + Pace Analysis to predict Spreads and Totals.
Outputs HTML matching CourtSide Analytics NBA standards.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
import random
from jinja2 import Template

# --- CONFIGURATION ---
SEASON = 2025
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKING_FILE = os.path.join(SCRIPT_DIR, "wnba_model_tracking.json")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "wnba_model_output.html")

# Constants
HOME_COURT_ADV = 3.2 
KELLY_MULTIPLIER = 0.5 

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"

# ==========================================
# 1. TRACKING SYSTEM
# ==========================================
def load_tracking_data():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'picks': [], 'summary': {}}
    return {'picks': [], 'summary': {}}

def save_tracking_data(data):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def track_picks(new_picks):
    data = load_tracking_data()
    existing_ids = {p['id'] for p in data['picks']}
    
    count = 0
    for p in new_picks:
        if p['id'] not in existing_ids:
            p['status'] = 'Pending'
            p['result'] = None
            p['profit_loss'] = 0
            # Mock historical outcome for demonstration if needed
            # p['status'] = random.choice(['Win', 'Loss'])
            # p['profit_loss'] = 100 if p['status']=='Win' else -110
            
            p['created_at'] = datetime.now().isoformat()
            data['picks'].append(p)
            count += 1
            
    if count > 0:
        save_tracking_data(data)
        print(f"{Colors.GREEN}Tracked {count} new picks.{Colors.END}")

def get_stats():
    # Returns stats object matching the NBA model's expectations: 
    # {record, win_rate, profit, roi} + recent splits
    data = load_tracking_data()
    completed = [p for p in data['picks'] if p.get('status', '').lower() in ['win', 'loss']]
    
    def calc_metrics(picks_subset):
        wins = sum(1 for p in picks_subset if p.get('status', '').lower() == 'win')
        losses = sum(1 for p in picks_subset if p.get('status', '').lower() == 'loss')
        pushes = sum(1 for p in picks_subset if p.get('status', '').lower() == 'push')
        total = wins + losses + pushes
        profit = sum(p.get('profit_loss', 0) for p in picks_subset) / 100.0
        risked = total * 1.1 # approx units risked
        roi = (profit / risked * 100) if risked > 0 else 0.0
        win_rate = (wins / total * 100) if total > 0 else 0.0
        return {
            'record': f"{wins}-{losses}-{pushes}",
            'win_rate': win_rate,
            'profit': profit,
            'roi': roi,
            'count': total
        }

    season = calc_metrics(completed)
    # Mocking Last 10/20/50 since we might not have enough data yet
    last_10 = calc_metrics(completed[:10])
    last_20 = calc_metrics(completed[:20])
    last_50 = calc_metrics(completed[:50])
    
    # --- Daily Stats ---
    from datetime import datetime, timedelta
    import pytz
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    today_str = now_et.strftime('%Y-%m-%d')
    yesterday_str = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def calc_daily(target_date):
        d_picks = []
        for p in completed:
            gt = p.get('created_at', '') # WNBA model uses created_at
            if not gt: continue
            try:
                dt_utc = datetime.fromisoformat(gt) # created_at is likely ISO
                # Assuming created_at is local or UTC, handle conversion if needed
                # For this model, let's assume it's roughly comparable
                if dt_utc.strftime('%Y-%m-%d') == target_date:
                     d_picks.append(p)
            except:
                continue
        return calc_metrics(d_picks)

    today_stats = calc_daily(today_str)
    yesterday_stats = calc_daily(yesterday_str)
    
    return season, last_10, last_20, last_50, today_stats, yesterday_stats

# ==========================================
# 2. MODEL ENGINE
# ==========================================
def predict_game(home, away):
    est_poss = (home['pace'] + away['pace']) / 2
    home_proj = ((home['ortg'] + away['drtg']) / 2) * (est_poss / 100) + (HOME_COURT_ADV / 2)
    away_proj = ((away['ortg'] + home['drtg']) / 2) * (est_poss / 100) - (HOME_COURT_ADV / 2)
    total_proj = home_proj + away_proj
    margin_proj = home_proj - away_proj
    return home_proj, away_proj, margin_proj, total_proj

# ==========================================
# 3. HTML GENERATION
# ==========================================
def generate_html(results, stats_tuple):
    season_stats, last_10, last_20, last_50, today_stats, yesterday_stats = stats_tuple
    timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p ET')
    
    # Map WNBA team names to abbreviations for Logos
    team_abbr_map = {
        'Las Vegas Aces': 'LVA', 'New York Liberty': 'NYL', 'Connecticut Sun': 'CON',
        'Seattle Storm': 'SEA', 'Dallas Wings': 'DAL', 'Washington Mystics': 'WAS',
        'Minnesota Lynx': 'MIN', 'Atlanta Dream': 'ATL', 'Phoenix Mercury': 'PHO',
        'Indiana Fever': 'IND', 'Los Angeles Sparks': 'LAS', 'Chicago Sky': 'CHI'
    }

    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics WNBA Picks</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #121212;
            --bg-card: #1c1c1e;
            --bg-metric: #2c2c2e;
            --text-primary: #ffffff;
            --text-secondary: #8e8e93;
            --accent-green: #34c759;
            --accent-red: #ff3b30;
            --border-color: #333333;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 2rem;
        }

        .container {
            max-width: 850px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        header h1 {
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }

        .date-sub {
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 500;
        }

        .prop-card {
            background-color: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255,255,255,0.05);
        }

        /* Header Section */
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .team-logos-container {
            display: flex;
            align-items: center;
            gap: 8px;
            position: relative;
        }

        .team-logo {
            width: 44px;
            height: 44px;
            object-fit: contain;
            /* background: #fff; Removed per user request */
            border-radius: 50%;
        }

        .matchup-info h2 {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .matchup-sub {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .game-time-badge {
            background-color: var(--bg-metric);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        /* Bet Section */
        .bet-row {
            margin-bottom: 1.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .bet-row:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }

        .main-pick {
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
            letter-spacing: -0.01em;
        }
        
        .main-pick.green { color: var(--accent-green); }

        .model-context {
            color: var(--text-secondary);
            font-size: 0.95rem;
            font-weight: 500;
        }

        .edge-val {
            color: var(--accent-green);
            font-weight: 600;
            margin-left: 6px;
        }

        /* Metrics Row */
        .metrics-row {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
        }

        .metric-box {
            background-color: var(--bg-metric);
            border-radius: 8px;
            padding: 0.8rem 1.5rem;
            text-align: center;
            flex: 1;
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

        .metric-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 600;
        }
        
        /* Stats */
        .text-red { color: var(--accent-red); }
        .text-green { color: var(--accent-green); }

        @media (max-width: 768px) {
            body { padding: 1rem; }
            .metrics-row { flex-direction: column; gap: 0.5rem; }
            .metric-box { padding: 0.8rem 0.5rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>CourtSide Analytics WNBA</h1>
                <div class="date-sub">Generated: {{ timestamp }}</div>
            </div>
            <div style="text-align: right;">
                <div class="metric-title">SEASON RECORD</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                    {{ season_stats.record }} ({{ "%.1f"|format(season_stats.win_rate) }}%)
                </div>
                <div style="font-size: 0.9rem; color: {{ 'var(--accent-green)' if season_stats.profit > 0 else 'var(--accent-red)' }};">
                     {{ "%+.1f"|format(season_stats.profit) }}u
                </div>
            </div>
        </header>

        {% for r in results %}
        {% set home_abbr = team_abbr_map.get(r.home_team, 'wnba')|lower %}
        {% set away_abbr = team_abbr_map.get(r.away_team, 'wnba')|lower %}
        
        <div class="prop-card">
            <div class="card-header">
                <div class="header-left">
                    <div class="team-logos-container">
                        <img src="https://a.espncdn.com/i/teamlogos/wnba/500/{{ away_abbr }}.png" 
                             alt="{{ r.away_team }}" 
                             class="team-logo away-logo"
                             onerror="this.src='https://a.espncdn.com/i/teamlogos/wnba/500/wnba.png'">
                        <img src="https://a.espncdn.com/i/teamlogos/wnba/500/{{ home_abbr }}.png" 
                             alt="{{ r.home_team }}" 
                             class="team-logo home-logo"
                             onerror="this.src='https://a.espncdn.com/i/teamlogos/wnba/500/wnba.png'">
                    </div>
                    <div class="matchup-info">
                        <h2>{{ r.Matchup }}</h2>
                        <div class="matchup-sub">{{ r.home_team }} Home Game</div>
                    </div>
                </div>
                <!-- <div class="game-time-badge">7:00 PM ET</div> -->
            </div>

            <!-- SPREAD BET BLOCK -->
            <div class="bet-row">
                {% if '✅' in r['ATS Pick'] %}
                <div class="main-pick green">{{ r['ATS Pick'].replace('✅ BET: ', '') }}</div>
                {% else %}
                <div class="main-pick" style="color:var(--text-secondary);">{{ r['Market Spread'] }}</div>
                {% endif %}
                
                <div class="model-context">
                    Model: {{ r['Model Spread'] }}
                    <span class="edge-val">Edge: {{ "%+.1f"|format(r.spread_edge) }}</span>
                </div>
            </div>

            <!-- TOTAL BET BLOCK -->
            <div class="bet-row" style="border-bottom: none;">
                {% if '✅' in r['Total Pick'] %}
                    {% if 'OVER' in r['Total Pick'] %}
                    <div class="main-pick green">OVER {{ r['Market Total'] }}</div>
                    {% else %}
                    <div class="main-pick green">UNDER {{ r['Market Total'] }}</div>
                    {% endif %}
                {% else %}
                <div class="main-pick" style="color:var(--text-secondary);">O/U {{ r['Market Total'] }}</div>
                {% endif %}
                
                <div class="model-context">
                    Model: {{ r['Model Total'] }}
                    <span class="edge-val">Edge: {{ "%+.1f"|format(r.total_edge|abs) }}</span>
                </div>
            </div>

            <!-- METRICS ROW -->
            <div class="metrics-row">
                <div class="metric-box">
                    <div class="metric-title">WIN % (EST)</div>
                    <div class="metric-value good">{{ 50 + (r.spread_edge|abs * 2)|int }}%</div>
                </div>
                <div class="metric-box">
                    <div class="metric-title">PREDICTED</div>
                    <div class="metric-value">{{ r['Predicted Score'] }}</div>
                </div>
            </div>

        </div>
        {% endfor %}
        
        <!-- DAILY PERFORMANCE -->
        <div class="prop-card" style="padding: 1.5rem; text-align:center;">
             <div class="metric-title" style="margin-bottom:1rem; font-size:1rem;">DAILY PERFORMANCE</div>
             <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div style="border-right: 1px solid var(--border-color);">
                    <div class="metric-label" style="font-size:0.8rem; margin-bottom:5px;">TODAY</div>
                    <div class="metric-value">{{ today_stats.record }}</div>
                    <div class="metric-value {{ 'good' if today_stats.profit > 0 else 'text-red' }}" style="font-size:1rem;">
                         {{ "%+.1f"|format(today_stats.profit) }}u
                    </div>
                </div>
                <div>
                    <div class="metric-label" style="font-size:0.8rem; margin-bottom:5px;">YESTERDAY</div>
                    <div class="metric-value">{{ yesterday_stats.record }}</div>
                    <div class="metric-value {{ 'good' if yesterday_stats.profit > 0 else 'text-red' }}" style="font-size:1rem;">
                         {{ "%+.1f"|format(yesterday_stats.profit) }}u
                    </div>
                </div>
             </div>
        </div>

        <!-- TRACKING FOOTER -->
        <div class="prop-card" style="padding: 1.5rem; text-align:center;">
             <div class="metric-title" style="margin-bottom:1rem; font-size:1rem;">RECENT PERFORMANCE (LAST 10)</div>
             <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div>
                    <div class="metric-label">Record</div>
                    <div class="metric-value">{{ last_10.record }}</div>
                </div>
                <div>
                    <div class="metric-label">Profit</div>
                    <div class="metric-value {{ 'good' if last_10.profit > 0 else 'text-red' }}">
                        {{ "%+.1f"|format(last_10.profit) }}u
                    </div>
                </div>
             </div>
        </div>

    </div>
</body>
</html>
    """
    
    template = Template(template_str)
    html_output = template.render(
        results=results,
        timestamp=timestamp,
        team_abbr_map=team_abbr_map,
        season_stats=season_stats,
        last_10=last_10,
        today_stats=today_stats,
        yesterday_stats=yesterday_stats
    )
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html_output)
    print(f"\n{Colors.GREEN}Report generated: {OUTPUT_HTML}{Colors.END}")

# ==========================================
# 4. EXECUTION
# ==========================================
def main():
    teams = {
        'LVA': {'name': 'Las Vegas Aces', 'ortg': 108.5, 'drtg': 97.5, 'pace': 98.0},
        'NYL': {'name': 'New York Liberty', 'ortg': 107.0, 'drtg': 98.0, 'pace': 96.5},
        'CON': {'name': 'Connecticut Sun', 'ortg': 103.0, 'drtg': 96.0, 'pace': 95.0},
        'SEA': {'name': 'Seattle Storm', 'ortg': 101.0, 'drtg': 102.0, 'pace': 97.0},
        'IND': {'name': 'Indiana Fever', 'ortg': 104.5, 'drtg': 105.0, 'pace': 99.0},
        'CHI': {'name': 'Chicago Sky', 'ortg': 100.0, 'drtg': 103.0, 'pace': 96.0}
    }
    
    games = [
        {'home': 'LVA', 'away': 'NYL', 'spread': -2.5, 'total': 172.5},
        {'home': 'CON', 'away': 'SEA', 'spread': -6.5, 'total': 158.5},
        {'home': 'IND', 'away': 'CHI', 'spread': -4.5, 'total': 168.0}
    ]
    
    results = []
    new_picks = []
    
    print("\n--- ANALYZING GAMES ---")
    
    for g in games:
        h_team = teams[g['home']]
        a_team = teams[g['away']]
        
        hp, ap, margin, total = predict_game(h_team, a_team)
        
        # Prepare Result Dict for Template
        res = {
            'home_team': h_team['name'],
            'away_team': a_team['name'],
            'Matchup': f"{a_team['name']} @ {h_team['name']}",
            'Predicted Score': f"{h_team['name']} {int(hp)} - {a_team['name']} {int(ap)}",
            'Market Spread': f"{h_team['name']} {g['spread']}",
            'Model Spread': f"{h_team['name']} {-margin:.1f}", # Margin is Home - Away. Spread is usually Home -X. So if Margin is 5, Fair spread is -5.
            'Market Total': str(g['total']),
            'Model Total': f"{total:.1f}",
            'spread_edge': 0,
            'total_edge': total - g['total'], # Positive means model > market (Over)
            'ATS Pick': '',
            'Total Pick': ''
        }
        
        # Spread Logic
        # Market: Home -2.5. Model: Home wins by 5 (Fair -5).
        # We want to buy Home -2.5 because -2.5 > -5.
        # Calc edge: Fair Spread - Market Spread?
        # Let's say Edge = Points of value.
        # If Model Margin = 5. Market Spread = -2.5 (Home wins by 2.5).
        # We cover by 2.5 points. Edge = 2.5.
        
        # Simplify:
        model_margin = hp - ap # 5.0
        market_margin = -g['spread'] # 2.5 (implied victory margin)
        
        # If model expects 5 pt win, and market expects 2.5 pt win.
        # Home covers -2.5.
        spread_edge = 0
        if model_margin > market_margin:
            # Likes Home
            spread_edge = model_margin - market_margin
            res['ATS Pick'] = f"✅ BET: {h_team['name']} {g['spread']}"
            
            # Track
            if spread_edge > 1.0:
                 new_picks.append({
                    'id': f"SPD_{g['home']}_{g['away']}_{datetime.now().strftime('%Y%m%d')}",
                    'type': 'Spread', 
                    'selection': res['ATS Pick'],
                    'profit_loss': 0 # pending
                })

        elif model_margin < market_margin:
            # Likes Away
            spread_edge = market_margin - model_margin
            res['ATS Pick'] = f"✅ BET: {a_team['name']} +{-g['spread']}" # simplified
            
            # Track
            if spread_edge > 1.0:
                 new_picks.append({
                    'id': f"SPD_{g['home']}_{g['away']}_{datetime.now().strftime('%Y%m%d')}",
                    'type': 'Spread', 
                    'selection': res['ATS Pick'],
                    'profit_loss': 0 # pending
                })

        res['spread_edge'] = spread_edge
        
        # Total Logic
        total_edge = total - g['total']
        res['total_edge'] = total_edge
        
        if total_edge > 3.0:
            res['Total Pick'] = f"✅ BET: OVER {g['total']}"
            new_picks.append( {'id': f"TOT_{g['home']}_{g['away']}_{datetime.now().strftime('%Y%m%d')}", 'type': 'Total', 'selection': f"OVER {g['total']}"})
        elif total_edge < -3.0:
            res['Total Pick'] = f"✅ BET: UNDER {g['total']}"
            new_picks.append( {'id': f"TOT_{g['home']}_{g['away']}_{datetime.now().strftime('%Y%m%d')}", 'type': 'Total', 'selection': f"UNDER {g['total']}"})

        results.append(res)

    track_picks(new_picks)
    stats = get_stats()
    generate_html(results, stats)

if __name__ == "__main__":
    main()
