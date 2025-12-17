#!/usr/bin/env python3
"""WNBA Player Props Model - Efficiency Driven
Targets: Points, Rebounds, Assists.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
import random

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
        p.update({'status': 'Pending', 'result': None, 'profit': 0, 'created_at': datetime.now().isoformat()})
        data['picks'].append(p)
    if new:
        save_tracking(data)
        print(f"{Colors.GREEN}Tracked {len(new)} prop bets.{Colors.END}")

# ==========================================
# 2. LOGIC
# ==========================================
def analyze_props():
    print("--- ANALYZING WNBA PLAYER PROPS ---")
    
    # Mock Data for Breanna Stewart & A'ja Wilson
    players = [
        {'name': 'A\'ja Wilson', 'team': 'LVA', 'pts_proj': 24.5, 'reb_proj': 12.2, 'ast_proj': 2.5},
        {'name': 'Breanna Stewart', 'team': 'NYL', 'pts_proj': 21.8, 'reb_proj': 9.5, 'ast_proj': 4.2},
        {'name': 'Caitlin Clark', 'team': 'IND', 'pts_proj': 22.5, 'reb_proj': 5.5, 'ast_proj': 8.5} # 2025 Hype
    ]
    
    market = [
        {'player': 'A\'ja Wilson', 'prop': 'Points', 'line': 22.5, 'odds': -110},
        {'player': 'Breanna Stewart', 'prop': 'Rebounds', 'line': 10.5, 'odds': -115},
        {'player': 'Caitlin Clark', 'prop': 'Assists', 'line': 7.5, 'odds': -105}
    ]
    
    picks = []
    
    for m in market:
        try:
            p_data = next(p for p in players if p['name'] == m['player'])
            
            # Logic Map
            proj = 0
            if m['prop'] == 'Points': proj = p_data['pts_proj']
            elif m['prop'] == 'Rebounds': proj = p_data['reb_proj']
            elif m['prop'] == 'Assists': proj = p_data['ast_proj']
            
            # Determine Edge
            diff = proj - m['line']
            
            if abs(diff) > 1.0: # Significant Edge
                side = 'Over' if diff > 0 else 'Under'
                
                # Check line direction
                if (side == 'Over' and diff > 0) or (side == 'Under' and diff < 0):
                    picks.append({
                        'id': f"{m['player'][:3]}_{m['prop']}_{datetime.now().strftime('%Y%m%d')}",
                        'type': f"Player {m['prop']}",
                        'matchup': f"{p_data['team']} vs OPP",
                        'selection': f"{m['player']} {side} {m['line']}",
                        'line': str(m['line']),
                        'odds_str': str(m['odds']),
                        'odds_dec': 1.91,
                        'prob': 0.58,
                        'edge': abs(diff)/m['line'],
                        'wager': '1.0% Unit',
                        'score': abs(diff) * 1.5
                    })
        except: continue
        
    track_props(picks)
    generate_html(picks)

def generate_html(picks):
    css = """
    :root { --bg-main: #121212; --bg-card: #1e1e1e; --accent-blue: #60a5fa; --text-primary: #ffffff; }
    body { background: var(--bg-main); color: var(--text-primary); font-family: sans-serif; padding: 20px; }
    .prop-card { background: var(--bg-card); padding: 15px; margin-bottom: 20px; border-radius: 10px; border: 1px solid #333; }
    .header { color: var(--accent-blue); font-weight: bold; font-size: 1.1em; }
    .row { display: flex; justify-content: space-between; margin-top: 10px; }
    .txt-blue { color: var(--accent-blue); }
    """
    
    html = f"""<!DOCTYPE html><html><head><style>{css}</style></head><body>
    <h1>🏀 CourtSide WNBA: Player Props</h1>
    """
    
    for p in picks:
        html += f"""
        <div class="prop-card">
            <div class="header">{p['matchup']}</div>
            <div class="row">
                <span>{p['type']}</span>
                <span class="txt-blue" style="font-weight:bold;">{p['selection']}</span>
                <span>{p['odds_str']}</span>
            </div>
             <div class="row" style="font-size: 0.9em; color: #888;">
                <span>Proj Edge: {p['edge']:.1%}</span>
                <span>Score: {p['score']:.1f}</span>
            </div>
        </div>
        """
    html += "</body></html>"
    with open(OUTPUT_HTML, 'w') as f: f.write(html)
    print(f"\n{Colors.GREEN}Props Report: {OUTPUT_HTML}{Colors.END}")

if __name__ == "__main__":
    analyze_props()
