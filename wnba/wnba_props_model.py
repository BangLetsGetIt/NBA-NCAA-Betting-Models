#!/usr/bin/env python3
"""WNBA Player Props Model - Efficiency Driven
Outputs HTML matching CourtSide Analytics NBA Props standards.
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
TRACKING_FILE = os.path.join(SCRIPT_DIR, "wnba_props_tracking.json")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "wnba_props_output.html")

class Colors:
    GREEN = "\033[92m"
    END = "\033[0m"

# ==========================================
# 1. TRACKING
# ==========================================
def load_tracking():
    if os.path.exists(TRACKING_FILE):
        try: return json.load(open(TRACKING_FILE))
        except: return {'picks': []}
    return {'picks': []}

def save_tracking(data):
    with open(TRACKING_FILE, 'w') as f: json.dump(data, f, indent=2)

def track_props(picks):
    data = load_tracking()
    ids = {p['id'] for p in data['picks']}
    new = [p for p in picks if p['id'] not in ids]
    for p in new:
        p.update({'status': 'Pending', 'result': None, 'profit_loss': 0, 'created_at': datetime.now().isoformat()})
        data['picks'].append(p)
    if new:
        save_tracking(data)
        print(f"{Colors.GREEN}Tracked {len(new)} prop bets.{Colors.END}")

def get_stats():
    data = load_tracking()
    completed = [p for p in data['picks'] if p.get('status', '').lower() in ['win', 'loss']]
    
    def calc(picks, limit=None):
        subset = picks[:limit] if limit else picks
        wins = sum(1 for p in subset if p['status'].lower()=='win')
        losses = sum(1 for p in subset if p['status'].lower()=='loss')
        profit = sum(p.get('profit_loss', 0) for p in subset) / 100.0
        total = wins + losses
        win_rate = (wins/total*100) if total else 0
        roi = (profit/(total*1.0)*100) if total > 0 else 0 # 1 unit per bet
        return {'record': f"{wins}-{losses}", 'win_rate': win_rate, 'profit': profit, 'roi': roi}
    
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
            gt = p.get('created_at', '') 
            if not gt: continue
            try:
                dt_utc = datetime.fromisoformat(gt)
                if dt_utc.strftime('%Y-%m-%d') == target_date:
                     d_picks.append(p)
            except:
                continue
        return calc(d_picks)

    today_stats = calc_daily(today_str)
    yesterday_stats = calc_daily(yesterday_str)

    return calc(completed), calc(completed, 10), calc(completed, 20), today_stats, yesterday_stats

# ==========================================
# 2. ANALYSIS
# ==========================================
def analyze_props():
    print("--- ANALYZING WNBA PLAYER PROPS ---")
    
    # Mock Data
    players = [
        {'name': 'A\'ja Wilson', 'team': 'LVA', 'opp': 'NYL', 'prop': 'Points', 'line': 22.5, 'proj': 26.5, 'odds': -110, 'avg': 24.5, 'last10': 25.8},
        {'name': 'Breanna Stewart', 'team': 'NYL', 'opp': 'LVA', 'prop': 'Rebounds', 'line': 10.5, 'proj': 12.0, 'odds': -115, 'avg': 9.5, 'last10': 11.2},
        {'name': 'Caitlin Clark', 'team': 'IND', 'opp': 'CHI', 'prop': 'Assists', 'line': 7.5, 'proj': 9.2, 'odds': -105, 'avg': 8.5, 'last10': 9.0},
        {'name': 'Angel Reese', 'team': 'CHI', 'opp': 'IND', 'prop': 'Rebounds', 'line': 12.5, 'proj': 14.5, 'odds': -110, 'avg': 13.1, 'last10': 13.5}
    ]
    
    picks = []
    
    for p in players:
        diff = p['proj'] - p['line']
        if abs(diff) > 1.0:
            side = 'OVER' if diff > 0 else 'UNDER'
            edge = abs(diff) / p['line']
            ai_score = 9.0 + (edge * 5) # Mock AI scoring
            
            picks.append({
                'id': f"{p['name'][:3]}_{p['prop']}_{side}_{datetime.now().strftime('%Y%m%d')}",
                'player': p['name'],
                'team': p['team'],
                'opponent': p['opp'],
                'prop_type': p['prop'],
                'selection': side,
                'line': p['line'],
                'odds': p['odds'],
                'proj': p['proj'],
                'edge_val': diff,
                'ai_score': min(10.0, ai_score),
                'ev': edge * 100 * 0.5, # Mock EV
                'win_prob': 55 + (edge * 20),
                'avg': p['avg'],
                'last10': p['last10']
            })
            
    track_props(picks)
    stats1, stats10, stats20, today_stats, yesterday_stats = get_stats()
    generate_html(picks, stats1, stats10, today_stats, yesterday_stats)

def generate_html(picks, season_stats, last10_stats, today_stats, yesterday_stats):
    timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p ET')
    
    template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics WNBA Props</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
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
        .txt-blue { color: var(--accent-blue); }
        
        .tag-green { background-color: rgba(74, 222, 128, 0.15); color: var(--accent-green); }
        .tag-blue { background-color: rgba(96, 165, 250, 0.15); color: var(--accent-blue); }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">WNBA Player Props</div>
            <div class="date-sub">Generated: {{ timestamp }}</div>
        </div>
        <div style="text-align: right;">
            <div class="metric-lbl">SEASON RECORD</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
                {{ season.record }} ({{ "%.1f"|format(season.win_rate) }}%)
            </div>
            <div style="font-size: 0.9rem; color: {{ 'var(--accent-green)' if season.profit > 0 else 'var(--accent-red)' }};">
                 {{ "%+.1f"|format(season.profit) }}u
            </div>
        </div>
    </header>

    {% for p in picks %}
    <div class="prop-card">
        <div class="card-header">
            <div class="header-left">
                <!-- Using WNBA Logo Placeholders -->
                <img src="https://a.espncdn.com/i/teamlogos/wnba/500/{{ p.team|lower }}.png" alt="Logo" class="team-logo"
                     onerror="this.src='https://a.espncdn.com/i/teamlogos/wnba/500/wnba.png'">
                <div class="player-info">
                    <h2>{{ p.player }}</h2>
                    <div class="matchup-info">{{ p.prop_type }} • {{ p.opponent }}</div>
                </div>
            </div>
        </div>
        <div class="card-body">
            <div class="bet-main-row">
                <div class="bet-selection">
                    <span class="{{ 'txt-green' if p.selection == 'OVER' else 'txt-red' }}">{{ p.selection }}</span> 
                    <span class="line">{{ p.line }}</span> 
                    <span class="bet-odds">{{ p.odds }}</span>
                </div>
            </div>
            <div class="model-subtext">
                Model Predicts: <strong>{{ p.proj }}</strong> (Edge: {{ "%+.1f"|format(p.edge_val) }})
            </div>
            <div class="metrics-grid">
                <div class="metric-item">
                    <span class="metric-lbl">AI SCORE</span>
                    <span class="metric-val txt-green">{{ "%.1f"|format(p.ai_score) }}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-lbl">EV</span>
                    <span class="metric-val txt-green">{{ "%.1f"|format(p.ev) }}%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-lbl">WIN %</span>
                    <span class="metric-val">{{ "%.0f"|format(p.win_prob) }}%</span>
                </div>
            </div>
            
            <div class="player-stats">
                <div class="player-stats-item">
                    <span class="player-stats-label">Season Avg</span>
                    <div class="player-stats-value">{{ p.avg }}</div>
                </div>
                <div class="player-stats-divider"></div>
                <div class="player-stats-item">
                    <span class="player-stats-label">Last 10</span>
                    <div class="player-stats-value">{{ p.last10 }}</div>
                </div>
            </div>

            <div class="tags-container">
                <span class="tag tag-green">🔥 Hot Trend</span>
                <span class="tag tag-blue">📊 Sharp Edge</span>
            </div>
        </div>
    </div>
    {% endfor %}

    <!-- DAILY PERFORMANCE -->
    <div class="prop-card" style="padding:1.5rem; text-align:center;">
        <div class="metric-lbl" style="font-size:1rem; margin-bottom:1rem;">DAILY PERFORMANCE</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
             <div style="border-right: 1px solid var(--border-color);">
                <div class="metric-lbl" style="font-size:0.8rem; margin-bottom:5px;">TODAY</div>
                <div class="metric-val">{{ today.record }}</div>
                <div class="metric-val {{ 'txt-green' if today.profit > 0 else 'txt-red' }}" style="font-size:1rem;">{{ "%+.1f"|format(today.profit) }}u</div>
             </div>
             <div>
                <div class="metric-lbl" style="font-size:0.8rem; margin-bottom:5px;">YESTERDAY</div>
                <div class="metric-val">{{ yesterday.record }}</div>
                <div class="metric-val {{ 'txt-green' if yesterday.profit > 0 else 'txt-red' }}" style="font-size:1rem;">{{ "%+.1f"|format(yesterday.profit) }}u</div>
             </div>
        </div>
    </div>

    <!-- TRACKING SECTION -->
    <div class="prop-card" style="padding:1.5rem; text-align:center;">
        <div class="metric-lbl" style="font-size:1rem; margin-bottom:1rem;">RECENT FORM (LAST 10)</div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
             <div>
                <div class="metric-lbl">Record</div>
                <div class="metric-val">{{ last10.record }}</div>
             </div>
             <div>
                <div class="metric-lbl">Profit</div>
                <div class="metric-val {{ 'txt-green' if last10.profit > 0 else 'txt-red' }}">{{ "%+.1f"|format(last10.profit) }}u</div>
             </div>
        </div>
    </div>
</div>

</body>
</html>
    """
    
    template = Template(template_str)
    html_output = template.render(
        picks=picks,
        timestamp=timestamp,
        season=season_stats,
        last10=last10_stats,
        today=today_stats,
        yesterday=yesterday_stats
    )
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html_output)
    print(f"\n{Colors.GREEN}Props Report: {OUTPUT_HTML}{Colors.END}")

if __name__ == "__main__":
    analyze_props()
