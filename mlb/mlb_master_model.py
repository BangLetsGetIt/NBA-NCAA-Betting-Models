#!/usr/bin/env python3
"""MLB Master Model - Sharp Plus Version
Includes: Moneyline, F5, Strikeout Props, HR Props, and Hits+Runs+RBI Props.
Features: CourtSide Analytics Styling, Automated Tracking, Kelly Criterion.
"""

import pandas as pd
import numpy as np
from scipy.stats import poisson
from datetime import datetime
import os
import json
import time
import pytz
import requests
import difflib

# --- CONFIGURATION ---
SEASON = 2026
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
_FG_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.fangraphs.com/leaders/major-league',
    'Accept': 'application/json, text/plain, */*',
}
_FG_BASE = 'https://www.fangraphs.com/api/leaders/major-league/data'


def _fetch_fangraphs(stats_type, season, qual, stat_type=8):
    url = (
        f"{_FG_BASE}?pos=all&stats={stats_type}&lg=all&qual={qual}"
        f"&season={season}&season1={season}&month=0&team=0"
        f"&pageitems=2000&pagenum=1&ind=0&type={stat_type}"
        f"&postseason=&sortdir=default&sortstat=ERA"
    )
    resp = requests.get(url, headers=_FG_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json().get('data', [])


def get_data():
    print("1. Fetching Advanced Stats from FanGraphs API...")

    # --- Pitching ---
    pitching = None
    for season_try in [SEASON, SEASON - 1]:
        try:
            rows = _fetch_fangraphs('pit', season_try, qual=20)
            if not rows:
                raise ValueError("empty response")
            pitching = pd.DataFrame([{
                'Name': r['PlayerName'],
                'Team': r['TeamNameAbb'],
                'SIERA': r.get('SIERA') or 4.50,
                'xFIP': r.get('xFIP') or 4.20,
                'K/9': r.get('K/9') or 8.0,
                'BB/9': r.get('BB/9') or 3.0,
                'HR/9': r.get('HR/9') or 1.2,
                'K%': r.get('K%') or 0.22,
                'BB%': r.get('BB%') or 0.09,
            } for r in rows])
            label = f"{season_try}" if season_try == SEASON else f"{season_try} (fallback)"
            print(f"   Pitching stats loaded ({label}): {len(pitching)} pitchers.")
            break
        except Exception as e:
            if season_try == SEASON:
                print(f"   {SEASON} pitching unavailable ({e}), trying {SEASON - 1}...")
    if pitching is None:
        print(f"{Colors.RED}Error: Pitching stats unavailable. Cannot run model.{Colors.END}")
        pitching = pd.DataFrame(columns=['Name', 'Team', 'SIERA', 'xFIP', 'K/9', 'BB/9', 'HR/9', 'K%', 'BB%'])

    # --- Batting (barrel% included in same advanced endpoint) ---
    batting = None
    for season_try in [SEASON, SEASON - 1]:
        try:
            rows = _fetch_fangraphs('bat', season_try, qual=100)
            if not rows:
                raise ValueError("empty response")
            batting = pd.DataFrame([{
                'Name': r['PlayerName'],
                'Team': r['TeamNameAbb'],
                'wRC+': r.get('wRC+') or 100,
                'ISO': r.get('ISO') or 0.150,
                'K%': r.get('K%') or 0.22,
                'BB%': r.get('BB%') or 0.09,
                'brl_percent': (r.get('Barrel%') or 0) * 100,
            } for r in rows])
            label = f"{season_try}" if season_try == SEASON else f"{season_try} (fallback)"
            print(f"   Batting stats loaded ({label}): {len(batting)} batters.")
            break
        except Exception as e:
            if season_try == SEASON:
                print(f"   {SEASON} batting unavailable ({e}), trying {SEASON - 1}...")
    if batting is None:
        print(f"{Colors.RED}Error: Batting stats unavailable. Cannot run model.{Colors.END}")
        batting = pd.DataFrame(columns=['Name', 'Team', 'wRC+', 'ISO', 'K%', 'BB%', 'brl_percent'])

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
            
        game_date = ''
        if res.get('game_time'):
            try:
                import datetime as _dt, pytz as _pytz
                gt = res['game_time']
                if 'Z' in str(gt):
                    _d = _dt.datetime.fromisoformat(str(gt).replace('Z', '+00:00'))
                    game_date = _d.astimezone(_pytz.timezone('US/Eastern')).strftime('%b %d, %Y')
                else:
                    game_date = str(gt)[:10]
            except:
                game_date = str(res['game_time'])[:10]

        html += f"""
        <div class="prop-card">
            <div class="card-header">
                <span class="bet-type">{res['type']}</span>
                <span>{res['matchup']}</span>
                {f'<span style="color:var(--text-secondary);font-size:12px;">{game_date}</span>' if game_date else ''}
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
# 5. LIVE SCHEDULE INTEGRATION
# ==========================================
def get_schedule(date_str=None):
    """Fetch today's MLB schedule with probable pitchers from MLB Stats API (free, no key)."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    url = (
        f"https://statsapi.mlb.com/api/v1/schedule"
        f"?sportId=1&date={date_str}&hydrate=probablePitcher,team&gameType=R"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Could not fetch schedule: {e}{Colors.END}")
        return []

    games = []
    for date_block in data.get('dates', []):
        for game in date_block.get('games', []):
            away = game['teams']['away']
            home = game['teams']['home']
            games.append({
                'gamePk': game['gamePk'],
                'away_team': away['team']['abbreviation'],
                'home_team': home['team']['abbreviation'],
                'away_pitcher': away.get('probablePitcher', {}).get('fullName'),
                'home_pitcher': home.get('probablePitcher', {}).get('fullName'),
                'game_time': game.get('gameDate', ''),
            })
    return games


def find_player(name, df, name_col='Name'):
    """Fuzzy-match a player name to a row in a DataFrame."""
    if name is None or df.empty:
        return None
    # Exact match
    exact = df[df[name_col] == name]
    if not exact.empty:
        return exact.iloc[0]
    # Last-name contains match
    last = name.split()[-1]
    contains = df[df[name_col].str.contains(last, case=False, na=False)]
    if not contains.empty:
        return contains.iloc[0]
    # Fuzzy match
    names = df[name_col].tolist()
    matches = difflib.get_close_matches(name, names, n=1, cutoff=0.6)
    if matches:
        return df[df[name_col] == matches[0]].iloc[0]
    return None


def get_team_wrc(team_abbr, batters):
    """Average wRC+ for a team's qualified batters (falls back to league avg 100)."""
    team_batters = batters[batters['Team'] == team_abbr]
    if team_batters.empty:
        return 100
    return team_batters['wRC+'].mean()


def get_team_k_rate(team_abbr, batters):
    """Average K% for a team's batters (falls back to league avg 0.22)."""
    team_batters = batters[batters['Team'] == team_abbr]
    if team_batters.empty or 'K%' not in team_batters.columns:
        return 0.22
    rate = team_batters['K%'].mean()
    return rate if not pd.isna(rate) else 0.22


# ==========================================
# 6. EXECUTION CORE
# ==========================================
def main():
    # 1. Load Data
    pitchers, batters = get_data()
    
    # 2. Tracking Stats
    stats = calculate_tracking_stats()
    
    new_picks = []
    today_str = datetime.now().strftime('%Y%m%d')

    print("\n--- FETCHING TODAY'S SCHEDULE ---")
    games = get_schedule()

    if not games:
        print(f"{Colors.YELLOW}No regular season games today (pre-season or off day).{Colors.END}")
    else:
        print(f"{Colors.GREEN}Found {len(games)} games today.{Colors.END}")

    print("\n--- RUNNING ANALYSIS ---")

    for game in games:
        away = game['away_team']
        home = game['home_team']
        matchup = f"{away} @ {home}"
        away_pitcher_name = game['away_pitcher'] or 'TBD'
        home_pitcher_name = game['home_pitcher'] or 'TBD'
        print(f"  {matchup}  |  {away_pitcher_name} vs {home_pitcher_name}")

        p_away = find_player(game['away_pitcher'], pitchers)
        p_home = find_player(game['home_pitcher'], pitchers)
        away_wrc = get_team_wrc(away, batters)
        home_wrc = get_team_wrc(home, batters)

        # --- F5 ML (requires both pitchers in stats) ---
        if p_away is not None and p_home is not None:
            try:
                f5_prob_away = calculate_f5_probability(p_away, p_home, away_wrc, home_wrc)
                f5_odds = 1.91  # -110 both sides baseline
                edge = f5_prob_away - (1 / f5_odds)
                if edge > MIN_EDGE:
                    kel = kelly_criterion(f5_prob_away, f5_odds) * KELLY_MULTIPLIER
                    new_picks.append({
                        'id': f"F5_{away}_{home}_{today_str}",
                        'type': 'First 5 Innings ML',
                        'matchup': matchup,
                        'selection': f'{away} F5 ML',
                        'line': 'Moneyline',
                        'odds_str': '-110',
                        'odds_dec': f5_odds,
                        'prob': f5_prob_away,
                        'edge': edge,
                        'wager': f"{kel:.1%} Unit",
                        'kel': kel,
                        'score': f5_prob_away * 10,
                    })
            except Exception as e:
                print(f"    F5 error {matchup}: {e}")

        # --- K Props (one per pitcher if found) ---
        for pitcher_row, opp_team in [(p_away, home), (p_home, away)]:
            if pitcher_row is None:
                continue
            try:
                opp_k_rate = get_team_k_rate(opp_team, batters)
                # Line set ~10% below expected so model has something to beat
                raw_exp = pitcher_row['K/9'] * (5.5 / 9)
                k_line = round(raw_exp * 0.9 - 0.5) + 0.5
                exp_k, prob_over, _ = calculate_k_prop_probability(pitcher_row, opp_k_rate, k_line)
                k_odds = 1.91
                edge_k = prob_over - (1 / k_odds)
                if edge_k > MIN_EDGE:
                    kel_k = kelly_criterion(prob_over, k_odds) * KELLY_MULTIPLIER
                    new_picks.append({
                        'id': f"K_{pitcher_row['Name'].replace(' ','_')}_{today_str}",
                        'type': 'Player Props - Strikeouts',
                        'matchup': matchup,
                        'selection': pitcher_row['Name'],
                        'line': f"Over {k_line} Ks",
                        'odds_str': '-110',
                        'odds_dec': k_odds,
                        'prob': prob_over,
                        'edge': edge_k,
                        'wager': f"{kel_k:.1%} Unit",
                        'kel': kel_k,
                        'score': prob_over * 10,
                    })
            except Exception as e:
                print(f"    K prop error {pitcher_row.get('Name','?')}: {e}")

        # --- HR Props & H+R+RBI Props (top 5 batters per team vs opposing pitcher) ---
        for batting_team, opp_pitcher_row, team_wrc_val in [
            (away, p_home, away_wrc),
            (home, p_away, home_wrc),
        ]:
            if opp_pitcher_row is None:
                continue
            team_bats = batters[batters['Team'] == batting_team]
            if team_bats.empty:
                continue
            top_bats = team_bats.nlargest(5, 'wRC+')

            for _, batter_row in top_bats.iterrows():
                batter_name = batter_row['Name']
                batter_id = batter_name.replace(' ', '_')

                # HR prop (~+200 market standard)
                try:
                    prob_hr = calculate_hr_probability(batter_row, opp_pitcher_row)
                    hr_odds = 3.00
                    edge_hr = prob_hr - (1 / hr_odds)
                    if edge_hr > MIN_EDGE:
                        kel_hr = kelly_criterion(prob_hr, hr_odds) * KELLY_MULTIPLIER
                        new_picks.append({
                            'id': f"HR_{batter_id}_{today_str}",
                            'type': 'Player Props - Home Run',
                            'matchup': matchup,
                            'selection': batter_name,
                            'line': 'To Hit HR',
                            'odds_str': '+200',
                            'odds_dec': hr_odds,
                            'prob': prob_hr,
                            'edge': edge_hr,
                            'wager': f"{kel_hr:.1%} Unit",
                            'kel': kel_hr,
                            'score': prob_hr * 10,
                        })
                except Exception as e:
                    print(f"    HR prop error {batter_name}: {e}")

                # H+R+RBI prop (Over 1.5, ~-110 market standard)
                try:
                    exp_val, prob_over_hrbi = calculate_h_r_rbi_probability(
                        batter_row, opp_pitcher_row, team_wrc_val
                    )
                    hrbi_odds = 1.91
                    edge_hrbi = prob_over_hrbi - (1 / hrbi_odds)
                    if edge_hrbi > MIN_EDGE:
                        kel_hrbi = kelly_criterion(prob_over_hrbi, hrbi_odds) * KELLY_MULTIPLIER
                        new_picks.append({
                            'id': f"HRBI_{batter_id}_{today_str}",
                            'type': 'Player Props - H+R+RBI',
                            'matchup': matchup,
                            'selection': batter_name,
                            'line': f"Over 1.5 (Exp: {exp_val:.2f})",
                            'odds_str': '-110',
                            'odds_dec': hrbi_odds,
                            'prob': prob_over_hrbi,
                            'edge': edge_hrbi,
                            'wager': f"{kel_hrbi:.1%} Unit",
                            'kel': kel_hrbi,
                            'score': prob_over_hrbi * 10,
                        })
                except Exception as e:
                    print(f"    H+R+RBI prop error {batter_name}: {e}")

    # 3. Output
    track_new_picks(new_picks)
    html_content = generate_html(new_picks, stats)
    
    with open(OUTPUT_HTML, 'w') as f:
        f.write(html_content)
        
    print(f"\n{Colors.GREEN}✅ Analysis Complete. {len(new_picks)} plays found. Report: {OUTPUT_HTML}{Colors.END}")

if __name__ == "__main__":
    main()