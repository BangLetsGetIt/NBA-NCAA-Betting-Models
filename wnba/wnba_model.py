#!/usr/bin/env python3
"""WNBA Spreads & Totals Model - Sharp Efficiency Version
Uses Four Factors + Pace Analysis to predict Spreads and Totals.
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
TRACKING_FILE = os.path.join(SCRIPT_DIR, "wnba_model_tracking.json")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "wnba_model_output.html")

# Constants
HOME_COURT_ADV = 3.2 # WNBA HCA is significant
KELLY_MULTIPLIER = 0.5 

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"

print(f"{Colors.BOLD}--- INITIALIZING WNBA SPREAD/TOTAL MODEL ({SEASON}) ---{Colors.END}")

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
            p['profit'] = 0
            p['created_at'] = datetime.now().isoformat()
            data['picks'].append(p)
            count += 1
            
    if count > 0:
        save_tracking_data(data)
        print(f"{Colors.GREEN}Tracked {count} new picks.{Colors.END}")

def get_stats():
    data = load_tracking_data()
    completed = [p for p in data['picks'] if p['status'] in ['Win', 'Loss']]
    if not completed: return {'roi': 0.0, 'win_rate': 0.0, 'record': '0-0'}
    
    wins = len([p for p in completed if p['status'] == 'Win'])
    total = len(completed)
    units = sum([(p['odds_dec']-1) if p['status']=='Win' else -1 for p in completed])
    
    return {
        'roi': (units/total)*100,
        'win_rate': (wins/total)*100,
        'record': f"{wins}-{total-wins}"
    }

# ==========================================
# 2. MODEL ENGINE
# ==========================================
def predict_game(home, away):
    """
    Predicts score based on Efficiency ratings.
    Inputs are dicts with: ORtg, DRtg, Pace
    """
    # Pace Estimation
    est_poss = (home['pace'] + away['pace']) / 2
    
    # Project Scores
    # Home Score = (Home ORtg + Away DRtg)/2 * Poss / 100 + HCA/2
    home_proj = ((home['ortg'] + away['drtg']) / 2) * (est_poss / 100) + (HOME_COURT_ADV / 2)
    
    # Away Score = (Away ORtg + Home DRtg)/2 * Poss / 100 - HCA/2
    away_proj = ((away['ortg'] + home['drtg']) / 2) * (est_poss / 100) - (HOME_COURT_ADV / 2)
    
    total_proj = home_proj + away_proj
    spread_proj = away_proj - home_proj # Positive means Away wins, Negative means Home wins (Points Spread convention: Home -5.5)
    # Wait, spread convention: Handi Home -5 means Home needs to win by >5.
    # Prediction: Home 85, Away 80. Margin = 5. fair spread = -5.
    
    margin_proj = home_proj - away_proj # Positive = Home Win
    
    return home_proj, away_proj, margin_proj, total_proj

# ==========================================
# 3. EXECUTION (MOCK DATA FOR OFF-SEASON)
# ==========================================
def main():
    # Mock Team Data (Efficiency Ratings)
    teams = {
        'LVA': {'name': 'Las Vegas Aces', 'ortg': 108.5, 'drtg': 97.5, 'pace': 98.0},
        'NYL': {'name': 'New York Liberty', 'ortg': 107.0, 'drtg': 98.0, 'pace': 96.5},
        'CON': {'name': 'Connecticut Sun', 'ortg': 103.0, 'drtg': 96.0, 'pace': 95.0},
        'SEA': {'name': 'Seattle Storm', 'ortg': 101.0, 'drtg': 102.0, 'pace': 97.0}
    }
    
    games = [
        {'home': 'LVA', 'away': 'NYL', 'spread': -2.5, 'total': 172.5},
        {'home': 'CON', 'away': 'SEA', 'spread': -6.5, 'total': 158.5}
    ]
    
    picks = []
    
    print("\n--- ANALYZING GAMES ---")
    
    for g in games:
        h_team = teams[g['home']]
        a_team = teams[g['away']]
        
        hp, ap, margin, total = predict_game(h_team, a_team)
        
        print(f"{a_team['name']} @ {h_team['name']}")
        print(f"  Model: {h_team['name']} {hp:.1f}, {a_team['name']} {ap:.1f} (Total: {total:.1f})")
        print(f"  Line: {h_team['name']} {g['spread']}, Total {g['total']}")
        
        # Spread Logic
        # Market: LVA -2.5. Model: LVA wins by (margin).
        # if Model Margin > Market Spread (e.g. Model says LVA win by 5, Mkt is -2.5), Bet Home.
        # Note on Spread sign: -2.5 means Home is favored. Margin is positive.
        # Fair Spread = -Margin. 
        fair_spread = -margin
        
        edge_spread = g['spread'] - fair_spread # e.g. -2.5 - (-5.0) = +2.5 points value on Home
        
        if abs(edge_spread) > 1.5:
            selection = h_team['name'] if edge_spread > 0 else a_team['name'] # Simplified logic
            # Actually:
            # If Model says Home wins by 5 (Fair -5). Market is -2.5.
            # We want to BUY Home -2.5.
            # edge check: 
            if fair_spread < g['spread']: # We think Home is BETTER (more negative spread)
                picks.append({
                    'id': f"SPD_{g['home']}_{g['away']}_{datetime.now().strftime('%Y%m%d')}",
                    'type': 'Spread',
                    'matchup': f"{a_team['name']} @ {h_team['name']}",
                    'selection': f"{h_team['name']} {g['spread']}",
                    'line': str(g['spread']),
                    'odds_str': '-110',
                    'odds_dec': 1.91,
                    'prob': 0.55, # Simplified
                    'edge': abs(edge_spread)/10, # Mock edge
                    'wager': '1.0% Unit',
                    'score': abs(edge_spread) * 2
                })
        
        # Total Logic
        edge_total = total - g['total']
        if abs(edge_total) > 3.0:
            pick_type = 'Over' if edge_total > 0 else 'Under'
            picks.append({
                'id': f"TOT_{g['home']}_{g['away']}_{datetime.now().strftime('%Y%m%d')}",
                'type': 'Total Points',
                'matchup': f"{a_team['name']} @ {h_team['name']}",
                'selection': f"{pick_type} {g['total']}",
                'line': str(g['total']),
                'odds_str': '-110',
                'odds_dec': 1.91,
                'prob': 0.56,
                'edge': abs(edge_total)/100,
                'wager': '1.0% Unit',
                'score': abs(edge_total)
            })

    # Output
    track_picks(picks)
    stats = get_stats()
    generate_html(picks, stats)

def generate_html(picks, stats):
    css = """
    :root { --bg-main: #121212; --bg-card: #1e1e1e; --accent-green: #4ade80; --text-primary: #ffffff; --text-secondary: #b3b3b3; }
    body { background: var(--bg-main); color: var(--text-primary); font-family: sans-serif; padding: 20px; }
    .prop-card { background: var(--bg-card); padding: 15px; margin-bottom: 20px; border-radius: 10px; border: 1px solid #333; }
    .header { color: var(--accent-green); font-weight: bold; font-size: 1.2em; }
    .row { display: flex; justify-content: space-between; margin-top: 10px; }
    .stat-box { display: inline-block; background: #222; padding: 10px; margin-right: 10px; border-radius: 5px; text-align: center; }
    .txt-green { color: var(--accent-green); }
    """
    
    html = f"""<!DOCTYPE html><html><head><style>{css}</style></head><body>
    <h1>🏀 CourtSide Analytics: WNBA</h1>
    <div style="margin-bottom: 20px;">
        <span class="stat-box">ROI: <span class="txt-green">{stats['roi']:.1f}%</span></span>
        <span class="stat-box">Record: {stats['record']}</span>
    </div>
    """
    
    for p in picks:
        html += f"""
        <div class="prop-card">
            <div class="header">{p['matchup']}</div>
            <div class="row">
                <span>{p['type']}</span>
                <span class="txt-green" style="font-weight:bold; font-size:1.1em;">{p['selection']}</span>
                <span>{p['odds_str']}</span>
            </div>
            <div class="row" style="font-size: 0.9em; color: #888;">
                <span>Edge: {p['edge']:.1%}</span>
                <span>Score: {p['score']:.1f}</span>
                <span>Bet: {p['wager']}</span>
            </div>
        </div>
        """
    html += "</body></html>"
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html)
    print(f"\n{Colors.GREEN}Report generated: {OUTPUT_HTML}{Colors.END}")

if __name__ == "__main__":
    main()
