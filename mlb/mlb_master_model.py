#!/usr/bin/env python3
"""MLB Master Model - Sharp Plus Version
Includes: Moneyline, F5, Strikeout Props, HR Props, and Hits+Runs+RBI Props.
Features: CourtSide Analytics Styling, Automated Tracking, Kelly Criterion.
"""

import pandas as pd
import numpy as np
from pybaseball import pitching_stats, batting_stats, statcast_batter_exitvelo_barrels
from scipy.stats import poisson
from datetime import datetime
import os
import json
import time
import pytz

# --- CONFIGURATION ---
SEASON = 2025
MIN_INN = 50  # Minimum innings for pitchers
MIN_PA = 150  # Minimum plate appearances for batters
BANKROLL = 10000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKING_FILE = os.path.join(SCRIPT_DIR, "mlb_master_model_tracking.json")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "mlb_master_model.html")

# Constants
MIN_EDGE = 0.05  # 5% edge required to bet
KELLY_MULTIPLIER = 0.5  # Half-Kelly for safety

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"

print(f"{Colors.BOLD}--- INITIALIZING COURT-SIDE ANALYTICS MLB MODEL ({SEASON}) ---{Colors.END}")

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

def track_new_picks(new_picks):
    tracking_data = load_tracking_data()
    current_ids = {p['id'] for p in tracking_data['picks']}
    
    added_count = 0
    for pick in new_picks:
        if pick['id'] not in current_ids:
            # Add metadata for tracking
            pick['status'] = 'Pending'
            pick['result'] = None
            pick['profit'] = 0
            pick['created_at'] = datetime.now().isoformat()
            tracking_data['picks'].append(pick)
            added_count += 1
            
    if added_count > 0:
        save_tracking_data(tracking_data)
        print(f"{Colors.GREEN}Successfully tracked {added_count} new picks.{Colors.END}")

def calculate_tracking_stats():
    """Calculate ROI and Record from tracked picks."""
    data = load_tracking_data()
    picks = data.get('picks', [])
    
    completed = [p for p in picks if p['status'] in ['Win', 'Loss']]
    if not completed:
        return {'wins': 0, 'losses': 0, 'win_rate': 0.0, 'roi': 0.0, 'profit': 0.0}
        
    wins = len([p for p in completed if p['status'] == 'Win'])
    losses = len([p for p in completed if p['status'] == 'Loss'])
    total = wins + losses
    
    # Simple unit tracking (assuming 1 unit per bet for ROI calc if bet_amount missing)
    net_units = 0
    for p in completed:
        odds = p.get('odds_dec', 1.91)
        if p['status'] == 'Win':
            net_units += (odds - 1)
        else:
            net_units -= 1
            
    roi = (net_units / total) * 100 if total > 0 else 0
    win_rate = (wins / total) * 100 if total > 0 else 0
    
    return {
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'roi': roi,
        'profit': net_units
    }

# ==========================================
# 2. DATA INGESTION ENGINE
# ==========================================
def get_data():
    print("1. Fetching Advanced Stats from FanGraphs & Statcast...")
    
    # Pitching: SIERA, xFIP, K/9
    try:
        pitching = pitching_stats(SEASON, qual=MIN_INN)
        pitching = pitching[['Name', 'Team', 'SIERA', 'xFIP', 'K/9', 'BB/9', 'HR/9', 'K%', 'BB%']]
    except:
        print(f"{Colors.YELLOW}Warning: Pitching stats fetch failed (Off-season?). Using Mock Data.{Colors.END}")
        # Mock Data Structure
        pitching = pd.DataFrame({
            'Name': ['Gerrit Cole', 'Tyler Glasnow', 'Zack Wheeler'],
            'Team': ['NYY', 'LAD', 'PHI'],
            'SIERA': [3.10, 2.95, 3.20],
            'xFIP': [3.20, 2.80, 3.15],
            'K/9': [10.5, 11.5, 9.8],
            'HR/9': [1.0, 0.9, 0.8]
        })

    # Batting: wRC+, ISO
    try:
        batting = batting_stats(SEASON, qual=MIN_PA)
        batting = batting[['Name', 'Team', 'wRC+', 'ISO', 'K%', 'BB%']]
        
        # Statcast Barrels
        try:
            barrels = statcast_batter_exitvelo_barrels(SEASON, MIN_PA)
            barrels = barrels[['last_name, first_name', 'brl_percent']]
            barrels['Name'] = barrels['last_name, first_name'].apply(lambda x: f"{x.split(', ')[1]} {x.split(', ')[0]}")
            batting = batting.merge(barrels[['Name', 'brl_percent']], on='Name', how='left').fillna(0)
        except:
            print("   ! Statcast Barrel data unavailable, using ISO proxy.")
            batting['brl_percent'] = batting['ISO'] * 10 
    except:
        print(f"{Colors.YELLOW}Warning: Batting stats fetch failed. Using Mock Data.{Colors.END}")
        batting = pd.DataFrame({
            'Name': ['Aaron Judge', 'Shohei Ohtani', 'Juan Soto'],
            'Team': ['NYY', 'LAD', 'NYY'],
            'wRC+': [160, 155, 150],
            'ISO': [0.300, 0.280, 0.250],
            'brl_percent': [20.0, 18.0, 15.0],
            'K%': [0.25, 0.22, 0.18]
        })

    return pitching, batting

# ==========================================
# 3. PROBABILITY ENGINES
# ==========================================

def calculate_f5_probability(pitcher_a, pitcher_b, lineup_a_wrc, lineup_b_wrc):
    """Calculates Win Probability for First 5 Innings."""
    # Lower SIERA is better. Score = (5.00 - SIERA)*0.6 + (wRC+/100)*0.4
    score_a = (5.00 - pitcher_a['SIERA']) * 0.6 + (lineup_a_wrc / 100) * 0.4
    score_b = (5.00 - pitcher_b['SIERA']) * 0.6 + (lineup_b_wrc / 100) * 0.4
    
    total_score = score_a + score_b
    win_prob_a = score_a / total_score
    return win_prob_a

def calculate_k_prop_probability(pitcher, opp_lineup_k_rate, line=5.5):
    """Uses Poisson for K Props."""
    avg_innings = 5.5
    opp_k_factor = opp_lineup_k_rate / 0.22 # 22% is league avg
    expected_ks = (pitcher['K/9'] * (avg_innings / 9)) * opp_k_factor
    
    prob_over = 1 - poisson.cdf(line, expected_ks)
    prob_under = poisson.cdf(line, expected_ks)
    return expected_ks, prob_over, prob_under

def calculate_hr_probability(batter, pitcher):
    """Simplified HR Probability utilizing Barrel Rate."""
    base_prob = 0.035
    batter_mod = batter['brl_percent'] / 6.0 
    pitcher_mod = pitcher['HR/9'] / 1.2
    estimated_prob = base_prob * batter_mod * pitcher_mod
    prob_hr_game = 1 - (1 - estimated_prob) ** 4
    return prob_hr_game

def calculate_h_r_rbi_probability(batter, pitcher, team_wrc):
    """
    New Prop: Hits + Runs + RBIs
    Based on Batter wRC+, Pitcher xFIP, and Team Strength (for R/RBI context).
    Average H+R+RBI is approx 1.8-2.2 for good hitters.
    """
    # 1. Base Expectation based on wRC+ (100 = 1.5, 150 = 2.2 approx)
    base_exp = 1.5 * (batter['wRC+'] / 100)
    
    # 2. Pitcher Modifier (xFIP)
    # xFIP 3.00 is tough (0.8x), 5.00 is easy (1.2x)
    pitcher_factor = (pitcher['xFIP'] / 4.00) 
    
    # 3. Team Context (Batter needs teammates on base for RBI, or to drive him in for R)
    team_factor = (team_wrc / 100)
    
    expected_val = base_exp * pitcher_factor * team_factor
    
    # Standard line is usually 1.5. Calculate prob of hitting >= 2
    # Prob(X >= 2) = 1 - Prob(X <= 1)
    prob_over_1_5 = 1 - poisson.cdf(1, expected_val)
    
    return expected_val, prob_over_1_5

def kelly_criterion(true_prob, decimal_odds):
    b = decimal_odds - 1
    q = 1 - true_prob
    f = (b * true_prob - q) / b
    return max(0, f)

# ==========================================
# 4. HTML GENERATION (CourtSide Analytics)
# ==========================================
def generate_html(results, stats):
    """Generates the modern CourtSide Analytics HTML report."""
    
    # Helper for formatting
    def fmt_odds(odds_str):
        return odds_str

    # CSS Styles (CourtSide Dark Theme)
    css = """
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
        margin: 0; padding: 20px; font-family: 'Inter', sans-serif;
        background-color: var(--bg-main); color: var(--text-primary);
    }
    .container { max-width: 800px; margin: 0 auto; }
    header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 25px; border-bottom: 1px solid var(--border-color); padding-bottom: 15px;
    }
    h1 { margin: 0; font-size: 24px; font-weight: 700; margin-bottom: 5px; }
    .subheader { font-size: 18px; font-weight: 600; color: var(--text-primary); }
    .date-sub { color: var(--text-secondary); font-size: 14px; margin-top: 5px; }
    
    .summary-grid {
        display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 30px;
    }
    .stat-box {
        background-color: var(--bg-card); border-radius: 12px; padding: 15px;
        text-align: center; border: 1px solid var(--border-color);
    }
    .stat-label { font-size: 12px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 5px; }
    .stat-value { font-size: 20px; font-weight: 700; }
    .txt-green { color: var(--accent-green); }
    .txt-red { color: var(--accent-red); }
    
    .prop-card {
        background-color: var(--bg-card); border-radius: 16px; overflow: hidden;
        margin-bottom: 20px; border: 1px solid var(--border-color);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
    }
    .card-header {
        padding: 15px 20px; background-color: var(--bg-card-secondary);
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid var(--border-color);
    }
    .card-body { padding: 20px; }
    .bet-main-row { margin-bottom: 15px; display: flex; align-items: baseline; gap: 10px; }
    .bet-type { font-size: 14px; color: var(--text-secondary); text-transform: uppercase; font-weight: 600; }
    .bet-selection { font-size: 22px; font-weight: 800; color: var(--accent-green); }
    .bet-line { font-size: 20px; color: var(--text-primary); margin-left: 5px; }
    .bet-odds { font-size: 18px; color: var(--text-secondary); font-weight: 500; margin-left: auto; }
    
    .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .metric-item { background-color: var(--bg-main); padding: 10px; border-radius: 8px; text-align: center; }
    .metric-lbl { display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }
    .metric-val { font-size: 16px; font-weight: 700; }
    
    .tags-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 15px; }
    .tag { font-size: 11px; padding: 4px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; }
    .tag-green { background-color: rgba(74, 222, 128, 0.15); color: var(--accent-green); }
    .tag-blue { background-color: rgba(96, 165, 250, 0.15); color: var(--accent-blue); }
    
    .no-bets { text-align: center; color: var(--text-secondary); padding: 30px; font-style: italic; }
    footer { text-align: center; font-size: 12px; color: var(--text-secondary); margin-top: 40px; }
    """

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics MLB</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>{css}</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">MLB Master Model</div>
            <div class="date-sub">{datetime.now().strftime('%B %d, %Y')} • Alpha V2.0</div>
        </div>
    </header>
    
    <div class="summary-grid">
        <div class="stat-box">
            <div class="stat-label">Season ROI</div>
            <div class="stat-value {'txt-green' if stats['roi'] > 0 else 'txt-red'}">{stats['roi']:.1f}%</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Win Rate</div>
            <div class="stat-value">{stats['win_rate']:.1f}%</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Record</div>
            <div class="stat-value">{stats['wins']}-{stats['losses']}</div>
        </div>
    </div>
    
    <div class="picks-section">
"""
    
    if not results:
        html += '<div class="no-bets">No high-value plays found for today.</div>'
    
    for res in results:
        # Determine tags
        tags_html = ""
        if res['edge'] > 0.1:
            tags_html += '<span class="tag tag-green">High Value</span>'
        if res.get('kel', 0) > 0.05:
            tags_html += '<span class="tag tag-green">Max Bet</span>'
            
        html += f"""
        <div class="prop-card">
            <div class="card-header">
                <span class="bet-type">{res['type']}</span>
                <span>{res['matchup']}</span>
            </div>
            <div class="card-body">
                <div class="bet-main-row">
                    <span class="bet-selection">{res['selection']}</span>
                    <span class="bet-line">{res['line']}</span>
                    <span class="bet-odds">{res['odds_str']}</span>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-item">
                        <span class="metric-lbl">MODEL PROB</span>
                        <span class="metric-val txt-green">{res['prob']:.1%}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">EDGE</span>
                        <span class="metric-val txt-green">+{res['edge']:.1%}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-lbl">KELLY BET</span>
                        <span class="metric-val">{res['wager']}</span>
                    </div>
                </div>
                
                <div class="tags-container">
                    {tags_html}
                    <span class="tag tag-blue">Model Score: {res['score']:.1f}</span>
                </div>
            </div>
        </div>
        """
        
    html += """
    </div>
    <footer>
        Model based on SIERA, xFIP, wRC+ & Statcast Data.<br>
        Always bet responsibly. Past performance doesn't guarantee future results.
    </footer>
</div>
</body>
</html>
"""
    return html

# ==========================================
# 5. EXECUTION CORE
# ==========================================
def main():
    # 1. Load Data
    pitchers, batters = get_data()
    
    # 2. Tracking Stats
    stats = calculate_tracking_stats()
    
    new_picks = []
    
    print("\n--- RUNNING ANALYSIS ---")
    
    # --- SIMULATION (Since we are likely off-season or just testing) ---
    # In production, iterate through today's schedule
    
    # GAME 1: NYY vs LAD
    try:
        p_nyy = pitchers[pitchers['Name'].str.contains("Cole")].iloc[0]
        p_lad = pitchers[pitchers['Name'].str.contains("Glasnow")].iloc[0]
        batter_judge = batters[batters['Name'].str.contains("Judge")].iloc[0]
        batter_ohtani = batters[batters['Name'].str.contains("Ohtani")].iloc[0]
        
        # Mocks
        odds_nyy_f5 = 2.05 # (+105)
        nyy_wrc = 115
        lad_wrc = 118
        
        # --- F5 BET ---
        f5_prob = calculate_f5_probability(p_nyy, p_lad, nyy_wrc, lad_wrc)
        # Assuming NYY is Selection
        edge = f5_prob - (1/odds_nyy_f5)
        if edge > 0.02: # Small threshold for demo
            kel = kelly_criterion(f5_prob, odds_nyy_f5) * KELLY_MULTIPLIER
            new_picks.append({
                'id': f"F5_NYY_LAD_{datetime.now().strftime('%Y%m%d')}",
                'type': 'First 5 Innings',
                'matchup': 'NYY @ LAD',
                'selection': 'NYY ML',
                'line': 'Moneyline',
                'odds_str': '+105',
                'odds_dec': 2.05,
                'prob': f5_prob,
                'edge': edge,
                'wager': f"{kel:.1%} Unit",
                'kel': kel,
                'score': f5_prob * 10 
            })
            
        # --- K PROP: Glasnow ---
        k_line = 7.5
        exp_k, prob_over, _ = calculate_k_prop_probability(p_lad, 0.21, k_line)
        k_odds = 1.91 # (-110)
        edge_k = prob_over - (1/k_odds)
        if edge_k > MIN_EDGE:
            kel_k = kelly_criterion(prob_over, k_odds) * KELLY_MULTIPLIER
            new_picks.append({
                'id': f"K_Glasnow_{datetime.now().strftime('%Y%m%d')}",
                'type': 'Player Props - Strikeouts',
                'matchup': 'NYY @ LAD',
                'selection': 'Tyler Glasnow',
                'line': f'Over {k_line} Ks',
                'odds_str': '-110',
                'odds_dec': 1.91,
                'prob': prob_over,
                'edge': edge_k,
                'wager': f"{kel_k:.1%} Unit",
                'kel': kel_k,
                'score': prob_over * 10
            })
            
        # --- HR PROP: Judge ---
        hr_prob = calculate_hr_probability(batter_judge, p_lad)
        hr_odds = 3.50 # (+250)
        edge_hr = hr_prob - (1/hr_odds)
        # Force add for demo if close
        if edge_hr > -0.1: 
            new_picks.append({
                'id': f"HR_Judge_{datetime.now().strftime('%Y%m%d')}",
                'type': 'Player Props - Home Run',
                'matchup': 'NYY @ LAD',
                'selection': 'Aaron Judge',
                'line': 'To Hit a HR',
                'odds_str': '+250',
                'odds_dec': 3.50,
                'prob': hr_prob,
                'edge': edge_hr,
                'wager': "0.2% Unit",
                'kel': 0.002,
                'score': hr_prob * 20 # Scale up for HRs
            })

        # --- H+R+RBI PROP: Ohtani (NEW) ---
        hrr_line = 1.5
        hrr_exp, hrr_prob = calculate_h_r_rbi_probability(batter_ohtani, p_nyy, nyy_wrc)
        hrr_odds = 1.87 # (-115)
        edge_hrr = hrr_prob - (1/hrr_odds)
        
        if edge_hrr > 0 or True: # Force for demo
             new_picks.append({
                'id': f"HRR_Ohtani_{datetime.now().strftime('%Y%m%d')}",
                'type': 'Player Props - H+R+RBI',
                'matchup': 'NYY @ LAD',
                'selection': 'Shohei Ohtani',
                'line': f'Over {hrr_line}',
                'odds_str': '-115',
                'odds_dec': 1.87,
                'prob': hrr_prob,
                'edge': edge_hrr,
                'wager': "1.0% Unit",
                'kel': 0.01,
                'score': hrr_prob * 10
            })
            
    except Exception as e:
        print(f"{Colors.RED}Simulation Error: {e}{Colors.END}")

    # 3. Output
    track_new_picks(new_picks)
    html_content = generate_html(new_picks, stats)
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html_content)
        
    print(f"\n{Colors.GREEN}✅ Analysis Complete. Report generated at: {OUTPUT_HTML}{Colors.END}")

if __name__ == "__main__":
    main()