#!/usr/bin/env python3
"""MLB Master Model - Sharp Plus Version
Includes: Strikeout Props, Pitching Outs Props, H+R+RBI Props, and Total Bases Props.
Features: CourtSide Analytics Styling, Automated Tracking, Kelly Criterion.
"""

import pandas as pd
import numpy as np
from scipy.stats import poisson, norm
from datetime import datetime, timedelta
import os
import json
import time
import pytz
import requests
import difflib
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')
ODDS_BASE    = 'https://api.the-odds-api.com/v4'

# --- CONFIGURATION ---
SEASON = 2026
MIN_INN = 50  # Minimum innings for pitchers
MIN_PA = 150  # Minimum plate appearances for batters
BANKROLL = 10000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TRACKING_FILE = os.path.join(SCRIPT_DIR, "mlb_master_model_tracking.json")
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "mlb_master_model.html")
RESULTS_CACHE = os.path.join(SCRIPT_DIR, "mlb_today_results.json")

PROP_PAGES = {
    'Player Props - Strikeouts':    {'label': 'Strikeouts',    'emoji': '⚡', 'file': os.path.join(SCRIPT_DIR, 'mlb_strikeouts.html')},
    'Player Props - Pitching Outs': {'label': 'Pitching Outs', 'emoji': '🎯', 'file': os.path.join(SCRIPT_DIR, 'mlb_pitching_outs.html')},
    'Player Props - Hits Allowed':  {'label': 'Hits Allowed',  'emoji': '🛡️', 'file': os.path.join(SCRIPT_DIR, 'mlb_hits_allowed.html')},
    'Player Props - H+R+RBI':       {'label': 'H+R+RBI',       'emoji': '💥', 'file': os.path.join(SCRIPT_DIR, 'mlb_hrbi.html')},
    'Player Props - Total Bases':   {'label': 'Total Bases',   'emoji': '💪', 'file': os.path.join(SCRIPT_DIR, 'mlb_total_bases.html')},
    'Team Props - Moneyline':       {'label': 'Moneyline',     'emoji': '🎰', 'file': os.path.join(SCRIPT_DIR, 'mlb_ml.html')},
    'Team Props - Run Line':        {'label': 'Run Line',      'emoji': '📏', 'file': os.path.join(SCRIPT_DIR, 'mlb_spreads.html')},
    'Team Props - Total Runs':      {'label': 'Total Runs',    'emoji': '🏃', 'file': os.path.join(SCRIPT_DIR, 'mlb_totals.html')},
}

# Constants
MIN_EDGE      = 0.08   # 8% edge (strikeouts only)
HRBI_MIN_EDGE = 0.15
OUTS_MIN_EDGE = 0.15
HA_MIN_EDGE   = 0.15
TB_MIN_EDGE   = 0.08
ML_MIN_EDGE   = 0.05   # moneyline
RL_MIN_EDGE   = 0.06   # run line
TOT_MIN_EDGE  = 0.05   # totals
HOME_FIELD_ADV = 0.03  # 3% home-field advantage
KELLY_MULTIPLIER = 0.5

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


def _calc_mlb_perf(picks, n):
    subset = picks[:n]
    wins = sum(1 for p in subset if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in subset if p.get('status', '').lower() == 'loss')
    total = wins + losses
    profit = 0.0
    for p in subset:
        s = p.get('status', '').lower()
        odds = p.get('odds_dec', 1.91)
        if s == 'win':
            profit += odds - 1
        elif s == 'loss':
            profit -= 1.0
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (profit / total * 100) if total > 0 else 0
    return {'record': f"{wins}-{losses}", 'win_rate': win_rate, 'profit': profit, 'roi': roi}


def _calc_mlb_by_type(completed):
    types = {
        'Player Props - Strikeouts':  'Strikeouts',
        'Player Props - Pitching Outs': 'Pitching Outs',
        'Player Props - Hits Allowed': 'Hits Allowed',
        'Player Props - H+R+RBI':     'H+R+RBI',
        'Player Props - Total Bases':  'Total Bases',
        'Team Props - Moneyline':     'Moneyline',
        'Team Props - Run Line':      'Run Line',
        'Team Props - Total Runs':    'Total Runs',
    }
    result = {}
    for raw_type, label in types.items():
        subset = [p for p in completed if p.get('type') == raw_type]
        wins = sum(1 for p in subset if p.get('status', '').lower() == 'win')
        losses = sum(1 for p in subset if p.get('status', '').lower() == 'loss')
        total = wins + losses
        profit = 0.0
        for p in subset:
            s = p.get('status', '').lower()
            if s == 'win':
                profit += p.get('odds_dec', 1.91) - 1
            elif s == 'loss':
                profit -= 1.0
        win_rate = (wins / total * 100) if total > 0 else 0
        roi = (profit / total * 100) if total > 0 else 0
        result[label] = {'record': f"{wins}-{losses}", 'total': total,
                         'profit': profit, 'win_rate': win_rate, 'roi': roi}
    return result


# ==========================================
# 2. DATA INGESTION ENGINE
# ==========================================

_MLB_STATS_BASE = 'https://statsapi.mlb.com/api/v1/stats'

# Full team name → abbreviation used by schedule API
_TEAM_NAME_TO_ABBR = {
    'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
    'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
    'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
    'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
    'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
    'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
    'New York Yankees': 'NYY', 'Oakland Athletics': 'ATH', 'Philadelphia Phillies': 'PHI',
    'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
    'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB',
    'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
}


def _fetch_mlb_stats(group, season, limit=500, min_pa=0):
    """Fetch season stats from MLB Stats API (free, no key, no rate limits)."""
    params = f"stats=season&group={group}&season={season}&sportId=1&limit={limit}"
    if min_pa:
        params += f"&minPA={min_pa}"
    resp = requests.get(f"{_MLB_STATS_BASE}?{params}", timeout=15)
    resp.raise_for_status()
    return resp.json().get('stats', [{}])[0].get('splits', [])


def _fetch_mlb_game_odds():
    """Fetch h2h, spreads, totals for all upcoming MLB games from The Odds API.
    Returns {(home_abbr, away_abbr): {h2h, spreads, totals, game_time}}.
    """
    if not ODDS_API_KEY:
        print(f"{Colors.YELLOW}No ODDS_API_KEY — skipping ML/Spreads/Totals{Colors.END}")
        return {}
    try:
        resp = requests.get(
            f"{ODDS_BASE}/sports/baseball_mlb/odds",
            params={'apiKey': ODDS_API_KEY, 'regions': 'us',
                    'markets': 'h2h,spreads,totals', 'oddsFormat': 'american'},
            timeout=15,
        )
        resp.raise_for_status()
        events = resp.json()
    except Exception as e:
        print(f"{Colors.YELLOW}MLB odds fetch error: {e}{Colors.END}")
        return {}

    priority = {'fanduel': 0, 'draftkings': 1, 'betmgm': 2, 'caesars': 3}
    lookup = {}

    for event in events:
        home_full = event.get('home_team', '')
        away_full = event.get('away_team', '')
        home = _TEAM_NAME_TO_ABBR.get(home_full, home_full[:3].upper())
        away = _TEAM_NAME_TO_ABBR.get(away_full, away_full[:3].upper())

        gd = {'h2h': {}, 'spreads': {}, 'totals': {}, 'game_time': event.get('commence_time', '')}

        books = sorted(event.get('bookmakers', []), key=lambda b: priority.get(b.get('key', ''), 99))
        for book in books:
            for market in book.get('markets', []):
                mk = market.get('key')
                if mk == 'h2h' and not gd['h2h']:
                    for oc in market.get('outcomes', []):
                        abbr = _TEAM_NAME_TO_ABBR.get(oc['name'], oc['name'][:3].upper())
                        gd['h2h'][abbr] = int(oc['price'])
                elif mk == 'spreads' and not gd['spreads']:
                    for oc in market.get('outcomes', []):
                        abbr = _TEAM_NAME_TO_ABBR.get(oc['name'], oc['name'][:3].upper())
                        gd['spreads'][abbr] = (int(oc['price']), float(oc.get('point', -1.5)))
                elif mk == 'totals' and not gd['totals']:
                    for oc in market.get('outcomes', []):
                        side = oc['name'].lower()
                        gd['totals'][side] = (int(oc['price']), float(oc.get('point', 8.5)))

        lookup[(home, away)] = gd

    print(f"{Colors.GREEN}  MLB game odds loaded: {len(lookup)} games{Colors.END}")
    return lookup


def get_data():
    print("1. Fetching Stats from MLB Stats API...")

    # --- Pitching ---
    pitching = None
    try:
        splits = _fetch_mlb_stats('pitching', SEASON)
        if not splits:
            raise ValueError("empty response")
        rows = []
        for sp in splits:
            st = sp.get('stat', {})
            name = sp.get('player', {}).get('fullName', '')
            team_full = sp.get('team', {}).get('name', '')
            team_abbr = _TEAM_NAME_TO_ABBR.get(team_full, team_full[:3].upper())
            bf = float(st.get('battersFaced') or 1)
            era = float(st.get('era') or 4.50)
            ip_str = st.get('inningsPitched', '0')
            try:
                ip = float(ip_str)
            except (ValueError, TypeError):
                ip = 0.0
            gs = int(st.get('gamesStarted') or 0)
            rows.append({
                'Name': name,
                'Team': team_abbr,
                'SIERA': era,
                'xFIP':  era,
                'K/9':   float(st.get('strikeoutsPer9Inn') or 8.0),
                'BB/9':  float(st.get('walksPer9Inn') or 3.0),
                'HR/9':  float(st.get('homeRunsPer9') or 1.2),
                'H/9':   float(st.get('hitsPer9Inn') or 8.5),
                'K%':    float(st.get('strikeOuts') or 0) / bf,
                'BB%':   float(st.get('baseOnBalls') or 0) / bf,
                'IP_per_GS': round(ip / gs, 2) if gs > 0 else 5.0,
            })
        pitching = pd.DataFrame(rows)
        print(f"   Pitching stats loaded: {len(pitching)} pitchers.")
    except Exception as e:
        print(f"{Colors.RED}Error: Pitching stats unavailable ({e}). Cannot run model.{Colors.END}")
        pitching = pd.DataFrame(columns=[
            'Name', 'Team', 'SIERA', 'xFIP', 'K/9', 'BB/9',
            'HR/9', 'H/9', 'K%', 'BB%', 'IP_per_GS'
        ])

    # --- Batting ---
    batting = None
    try:
        splits = _fetch_mlb_stats('hitting', SEASON, min_pa=50)
        if not splits:
            raise ValueError("empty response")
        rows = []
        for sp in splits:
            st = sp.get('stat', {})
            name = sp.get('player', {}).get('fullName', '')
            team_full = sp.get('team', {}).get('name', '')
            team_abbr = _TEAM_NAME_TO_ABBR.get(team_full, team_full[:3].upper())
            pa = float(st.get('plateAppearances') or 1)
            avg = float(st.get('avg') or 0.250)
            slg = float(st.get('slg') or 0.400)
            ops = float(st.get('ops') or 0.720)
            rows.append({
                'Name': name,
                'Team': team_abbr,
                'wRC+': round((ops / 0.720) * 100, 1),
                'ISO':  round(slg - avg, 3),
                'SLG':  slg,
                'AVG':  avg,
                'K%':   float(st.get('strikeOuts') or 0) / pa,
                'BB%':  float(st.get('baseOnBalls') or 0) / pa,
                'brl_percent': 6.0,
            })
        batting = pd.DataFrame(rows)
        print(f"   Batting stats loaded: {len(batting)} batters.")
    except Exception as e:
        print(f"{Colors.RED}Error: Batting stats unavailable ({e}). Cannot run model.{Colors.END}")
        batting = pd.DataFrame(columns=[
            'Name', 'Team', 'wRC+', 'ISO', 'SLG', 'AVG', 'K%', 'BB%', 'brl_percent'
        ])

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
    avg_innings = float(pitcher.get('IP_per_GS', 5.5) or 5.5)
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

def calculate_pitching_outs_probability(pitcher, opp_k_rate, line):
    """Models outs recorded by a starting pitcher using normal distribution."""
    base_outs = pitcher.get('IP_per_GS', 5.0) * 3

    # Higher K/9 → pitchers stay in longer (fewer balls in play)
    k9 = pitcher.get('K/9', 8.0)
    k_adj = (k9 - 9.0) * 0.15

    # Higher BB/9 → higher pitch counts → exits earlier
    bb9 = pitcher.get('BB/9', 3.0)
    bb_adj = -(bb9 - 3.0) * 0.20

    # High opponent K% means more strikeouts → pitcher extends outing
    opp_k_adj = (opp_k_rate - 0.22) * 5.0

    exp_outs = max(6.0, min(27.0, base_outs + k_adj + bb_adj + opp_k_adj))

    # Normal distribution — ~3 outs std dev (≈1 inning spread is typical)
    std_outs = 3.0
    prob_over = float(1 - norm.cdf(line, loc=exp_outs, scale=std_outs))
    return exp_outs, prob_over


def calculate_total_bases_probability(batter, pitcher, line=1.5):
    """Estimate P(total bases > line) using batter SLG × avg ABs, adjusted for pitcher xFIP."""
    import math
    avg_ab_per_game = 4.0  # top-order bats (wRC+>=100) average ~4 ABs/game
    slg = float(batter.get('SLG', 0.400) or 0.400)
    xfip = float(pitcher.get('xFIP', 4.20) or 4.20)
    league_avg_xfip = 4.20
    pitcher_adj = xfip / league_avg_xfip
    exp_tb = slg * avg_ab_per_game * pitcher_adj
    exp_tb = max(exp_tb, 0.01)
    # Poisson: P(TB > line) = 1 - sum P(TB=k) for k=0..floor(line)
    cutoff = int(line)
    prob_under = sum((exp_tb**k * math.exp(-exp_tb)) / math.factorial(k) for k in range(cutoff + 1))
    prob = max(0.0, min(1.0, 1.0 - prob_under))
    return round(exp_tb, 2), prob


def calculate_game_probabilities(pitcher_home, pitcher_away, home_wrc, away_wrc):
    """Pythagorean expectation from expected runs per team.
    Returns (home_win_prob, away_win_prob, expected_total, home_exp_r, away_exp_r).
    """
    home_era = float(pitcher_home.get('SIERA', 4.50) or 4.50)
    away_era = float(pitcher_away.get('SIERA', 4.50) or 4.50)
    home_exp_r = max(1.5, min((home_wrc / 100) * 4.5 * (away_era / 4.20), 9.0))
    away_exp_r = max(1.5, min((away_wrc / 100) * 4.5 * (home_era / 4.20), 9.0))
    exp = 1.83  # Pythagorean exponent for baseball
    denom = home_exp_r**exp + away_exp_r**exp
    raw = (home_exp_r**exp / denom) if denom > 0 else 0.5
    home_win_prob = min(max(raw + HOME_FIELD_ADV, 0.30), 0.75)
    away_win_prob = 1.0 - home_win_prob
    return home_win_prob, away_win_prob, home_exp_r + away_exp_r, home_exp_r, away_exp_r


def calculate_run_line_probability(exp_r_team, exp_r_opp):
    """P(team covers -1.5) and P(team covers +1.5) using normal distribution over run margin."""
    exp_margin = exp_r_team - exp_r_opp
    margin_std = 3.0
    prob_fav = float(1 - norm.cdf(1.5,  loc=exp_margin, scale=margin_std))  # win by 2+
    prob_dog = float(1 - norm.cdf(-1.5, loc=exp_margin, scale=margin_std))  # win or lose by 1
    return prob_fav, prob_dog


def calculate_totals_probability(expected_total, line):
    """P(total runs over/under line) using normal distribution."""
    total_std = 2.8
    prob_over  = float(1 - norm.cdf(line, loc=expected_total, scale=total_std))
    prob_under = float(norm.cdf(line, loc=expected_total, scale=total_std))
    return prob_over, prob_under


def calculate_hits_allowed_probability(pitcher, opp_team_avg, ip_per_gs, line):
    """Estimate P(hits allowed < line) using pitcher H/9 adjusted for opponent AVG and expected IP."""
    import math
    h9 = float(pitcher.get('H/9', 8.5) or 8.5)
    league_avg_avg = 0.248
    opp_adj = opp_team_avg / league_avg_avg
    exp_hits = (h9 / 9.0) * ip_per_gs * opp_adj
    exp_hits = max(exp_hits, 0.01)
    # We bet UNDER — P(hits <= floor(line))
    cutoff = int(line)
    prob_under = sum((exp_hits**k * math.exp(-exp_hits)) / math.factorial(k) for k in range(cutoff + 1))
    prob_under = max(0.0, min(1.0, prob_under))
    return round(exp_hits, 2), prob_under


def kelly_criterion(true_prob, decimal_odds):
    b = decimal_odds - 1
    q = 1 - true_prob
    f = (b * true_prob - q) / b
    return max(0, f)

# ==========================================
# 4. HTML GENERATION (CourtSide Analytics)
# ==========================================

ESPN_MLB_SLUGS = {
    'AZ': 'ari', 'ATH': 'oak', 'CWS': 'chw', 'WSH': 'wsh',
    'TB': 'tb', 'SD': 'sd', 'SF': 'sf', 'KC': 'kc',
    'NYY': 'nyy', 'NYM': 'nym', 'LAD': 'lad', 'LAA': 'laa',
    'CHC': 'chc',
}

def team_logo_url(abbr):
    slug = ESPN_MLB_SLUGS.get(abbr, abbr.lower())
    return f"https://a.espncdn.com/i/teamlogos/mlb/500/{slug}.png"

def fmt_game_time(game_time_str):
    if not game_time_str:
        return ''
    try:
        import pytz as _pytz
        gt = str(game_time_str).replace('Z', '+00:00')
        dt = datetime.fromisoformat(gt).astimezone(_pytz.timezone('US/Eastern'))
        day = dt.strftime('%a, %b %-d')
        t = dt.strftime('%-I:%M %p ET')
        return f"{day} • {t}"
    except Exception:
        return str(game_time_str)[:10]

def render_team_card(res):
    """Card for ML / Run Line / Total Runs picks."""
    bet_type = res['type']
    home     = res.get('home_team', '')
    away     = res.get('away_team', '')
    matchup  = res.get('matchup', f"{away} @ {home}")
    gt       = fmt_game_time(res.get('game_time', ''))

    home_logo = team_logo_url(home)
    away_logo = team_logo_url(away)

    home_era  = res.get('home_era', '—')
    away_era  = res.get('away_era', '—')
    home_exp  = res.get('home_exp_r', '—')
    away_exp  = res.get('away_exp_r', '—')
    home_wrc  = res.get('home_wrc', '—')
    away_wrc  = res.get('away_wrc', '—')
    home_sp   = res.get('home_pitcher', '—')
    away_sp   = res.get('away_pitcher', '—')

    if bet_type == 'Team Props - Total Runs':
        direction  = res.get('direction', 'over').upper()
        tot_line   = res.get('tot_line', '—')
        exp_total  = res.get('expected_total', '—')
        headline   = f"{direction} {tot_line} RUNS"
        subtext    = f"Model expects <strong>{exp_total}</strong> total runs"
        badge_col  = '#4ade80' if direction == 'OVER' else '#f87171'
    elif bet_type == 'Team Props - Run Line':
        bet_team  = res.get('bet_team', '')
        point     = res.get('point', -1.5)
        pt_str    = f"{point:+.1f}" if isinstance(point, (int, float)) else str(point)
        headline  = f"{bet_team} {pt_str}"
        subtext   = f"Model win prob: <strong>{res['prob']:.1%}</strong>"
        badge_col = '#60a5fa'
    else:  # Moneyline
        bet_team  = res.get('bet_team', '')
        headline  = f"{bet_team} ML"
        subtext   = f"Model win prob: <strong>{res['prob']:.1%}</strong>"
        badge_col = '#4ade80'

    edge_pct = res['edge']
    tags_html  = ''
    if edge_pct > 0.10:
        tags_html += '<span class="tag tag-green">High Value</span>'
    tags_html += f'<span class="tag tag-blue">Score: {res["score"]:.1f}</span>'

    return f"""
        <div class="prop-card glow-green">
            <div class="card-header">
                <div class="header-left">
                    <img src="{away_logo}" alt="" class="team-logo" onerror="this.style.display='none'">
                    <div style="font-size:14px;color:#94a3b8;padding:0 6px">@</div>
                    <img src="{home_logo}" alt="" class="team-logo" onerror="this.style.display='none'">
                    <div class="player-info" style="margin-left:8px">
                        <h2>{matchup}</h2>
                        <div class="matchup-info">{away_sp} vs {home_sp}</div>
                    </div>
                </div>
                <div class="game-meta">
                    <div class="bet-type-badge">{bet_type.replace('Team Props - ','')}</div>
                    {f'<div class="game-date-time">{gt}</div>' if gt else ''}
                </div>
            </div>
            <div class="card-body">
                <div class="bet-main-row">
                    <div class="bet-selection">
                        <span class="txt-green" style="font-size:20px;font-weight:800">{headline}</span>
                        <span class="bet-odds">{res['odds_str']}</span>
                    </div>
                </div>
                <div class="model-subtext">{subtext}</div>
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-title">{away} Exp R</div>
                        <div class="stat-val">{away_exp}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-title">{home} Exp R</div>
                        <div class="stat-val">{home_exp}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-title">{away} wRC+</div>
                        <div class="stat-val">{away_wrc}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-title">{home} wRC+</div>
                        <div class="stat-val">{home_wrc}</div>
                    </div>
                </div>
                <div class="metrics-grid">
                    <div class="metric-item"><span class="metric-lbl">WIN %</span><span class="metric-val txt-green">{res['prob']:.0%}</span></div>
                    <div class="metric-item"><span class="metric-lbl">EDGE</span><span class="metric-val txt-green">+{edge_pct:.1%}</span></div>
                    <div class="metric-item"><span class="metric-lbl">KELLY</span><span class="metric-val">{res['wager']}</span></div>
                </div>
                <div class="tags-container">{tags_html}</div>
            </div>
        </div>"""


def render_card(res):
    bet_type = res['type']
    # Route team props to dedicated renderer
    if bet_type.startswith('Team Props'):
        return render_team_card(res)

    is_batter = bet_type in ('Player Props - H+R+RBI', 'Player Props - Home Run', 'Player Props - Total Bases')
    is_tb = bet_type == 'Player Props - Total Bases'
    is_k = bet_type == 'Player Props - Strikeouts'
    is_f5 = bet_type == 'First 5 Innings ML'
    is_outs = bet_type == 'Player Props - Pitching Outs'
    is_ha = bet_type == 'Player Props - Hits Allowed'

    # --- Logo & team ---
    if is_batter:
        logo = team_logo_url(res.get('batting_team', ''))
    elif is_k or is_outs or is_ha:
        logo = team_logo_url(res.get('pitcher_team', ''))
    elif is_f5:
        logo = team_logo_url(res.get('away_team', ''))
    else:
        logo = ''

    game_time_str = fmt_game_time(res.get('game_time', ''))

    # --- Bet direction / line display ---
    if is_f5:
        direction = res['selection']
        line_display = ''
    elif is_k:
        direction = 'OVER'
        line_display = res['line'].replace('Over ', '')
    elif is_outs:
        direction = 'OVER'
        line_display = res['line'].replace('Over ', '')
    elif is_ha:
        direction = 'UNDER'
        line_display = res['line'].replace('Under ', '')
    elif bet_type == 'Player Props - Home Run':
        direction = 'TO HIT HR'
        line_display = '+200'
    elif is_tb:
        direction = 'OVER'
        line_display = f"1.5 Total Bases  (Exp: {res.get('exp_tb', '?')})"
    else:
        direction = 'OVER'
        exp = res.get('exp_val')
        line_display = f"1.5 H+R+RBI  (Exp: {exp})" if exp else res['line']

    # --- Model subtext ---
    if is_f5:
        subtext = f"Win Probability: <strong>{res['prob']:.1%}</strong>"
    elif is_k:
        subtext = f"Model Expects: <strong>{res.get('exp_k', '?')} Ks</strong>"
    elif is_outs:
        ip_est = round(res.get('exp_outs', 0) / 3, 1)
        subtext = f"Model Expects: <strong>{res.get('exp_outs', '?')} Outs</strong> (~{ip_est} IP)"
    elif is_ha:
        subtext = f"Model Expects: <strong>{res.get('exp_hits', '?')} Hits Allowed</strong>"
    elif bet_type == 'Player Props - Home Run':
        subtext = f"HR Probability: <strong>{res['prob']:.1%}</strong>"
    elif is_tb:
        subtext = f"Model Expects: <strong>{res.get('exp_tb', '?')} Total Bases</strong>"
    else:
        subtext = f"Model Expects: <strong>{res.get('exp_val', '?')} H+R+RBI</strong>"

    # --- Stats row ---
    if is_tb:
        stats_row = f"""
            <div class="stats-row">
                <div class="stat-item"><div class="stat-title">wRC+</div><div class="stat-val">{int(res.get('batter_wrc', 0))}</div></div>
                <div class="stat-item"><div class="stat-title">SLG</div><div class="stat-val">{res.get('batter_slg', 0):.3f}</div></div>
                <div class="stat-item"><div class="stat-title">xFIP</div><div class="stat-val">{res.get('pitcher_xfip', '—')}</div></div>
            </div>"""
    elif is_batter:
        stats_row = f"""
            <div class="stats-row">
                <div class="stat-item"><div class="stat-title">wRC+</div><div class="stat-val">{int(res.get('batter_wrc', 0))}</div></div>
                <div class="stat-item"><div class="stat-title">Barrel%</div><div class="stat-val">{res.get('batter_barrel', 0):.1f}%</div></div>
            </div>"""
    elif is_k:
        stats_row = f"""
            <div class="stats-row">
                <div class="stat-item"><div class="stat-title">SIERA</div><div class="stat-val">{res.get('pitcher_siera', '—')}</div></div>
                <div class="stat-item"><div class="stat-title">K/9</div><div class="stat-val">{res.get('pitcher_k9', '—')}</div></div>
                <div class="stat-item"><div class="stat-title">Opp K%</div><div class="stat-val">{res.get('opp_k_rate', 0):.1f}%</div></div>
            </div>"""
    elif is_outs:
        stats_row = f"""
            <div class="stats-row">
                <div class="stat-item"><div class="stat-title">IP/Start</div><div class="stat-val">{res.get('pitcher_ip_per_gs', '—')}</div></div>
                <div class="stat-item"><div class="stat-title">K/9</div><div class="stat-val">{res.get('pitcher_k9', '—')}</div></div>
                <div class="stat-item"><div class="stat-title">BB/9</div><div class="stat-val">{res.get('pitcher_bb9', '—')}</div></div>
                <div class="stat-item"><div class="stat-title">Opp K%</div><div class="stat-val">{res.get('opp_k_rate', 0):.1f}%</div></div>
            </div>"""
    elif is_ha:
        stats_row = f"""
            <div class="stats-row">
                <div class="stat-item"><div class="stat-title">H/9</div><div class="stat-val">{res.get('pitcher_h9', '—')}</div></div>
                <div class="stat-item"><div class="stat-title">IP/Start</div><div class="stat-val">{res.get('pitcher_ip_per_gs', '—')}</div></div>
                <div class="stat-item"><div class="stat-title">SIERA</div><div class="stat-val">{res.get('pitcher_siera', '—')}</div></div>
                <div class="stat-item"><div class="stat-title">Opp AVG</div><div class="stat-val">{res.get('opp_avg', 0):.3f}</div></div>
            </div>"""
    elif is_f5:
        stats_row = f"""
            <div class="stats-row">
                <div class="stat-item"><div class="stat-title">{res.get('away_pitcher_name','Away SP')}</div><div class="stat-val">SIERA {res.get('away_pitcher_siera','—')}</div></div>
                <div class="stat-item"><div class="stat-title">{res.get('home_pitcher_name','Home SP')}</div><div class="stat-val">SIERA {res.get('home_pitcher_siera','—')}</div></div>
            </div>"""
    else:
        stats_row = ''

    # --- Pitcher matchup section (batter props only) ---
    if (is_batter or is_tb) and res.get('pitcher_name'):
        p = res['pitcher_name']
        siera = res.get('pitcher_siera', '—')
        xfip = res.get('pitcher_xfip', '—')
        hr9 = res.get('pitcher_hr9', '—')
        pitcher_section = f"""
            <div class="pitcher-matchup">
                <div class="pitcher-vs">vs. {p}</div>
                <div class="pitcher-stats">
                    <span>SIERA&nbsp;{siera}</span>
                    <span>xFIP&nbsp;{xfip}</span>
                    <span>HR/9&nbsp;{hr9}</span>
                </div>
            </div>"""
    else:
        pitcher_section = ''

    # --- Tags ---
    tags_html = ''
    if res['edge'] > 0.1:
        tags_html += '<span class="tag tag-green">High Value</span>'
    if res.get('kel', 0) > 0.05:
        tags_html += '<span class="tag tag-green">Max Bet</span>'
    tags_html += f'<span class="tag tag-blue">Score: {res["score"]:.1f}</span>'

    logo_html = f'<img src="{logo}" alt="" class="team-logo" onerror="this.style.display=\'none\'">' if logo else ''
    odds_display = res['odds_str'] if is_f5 else res['odds_str']

    return f"""
        <div class="prop-card glow-green">
            <div class="card-header">
                <div class="header-left">
                    {logo_html}
                    <div class="player-info">
                        <h2>{res['selection']}</h2>
                        <div class="matchup-info">{res['matchup']}</div>
                    </div>
                </div>
                <div class="game-meta">
                    <div class="bet-type-badge">{bet_type.replace('Player Props - ','').replace('First 5 Innings ','F5 ')}</div>
                    {f'<div class="game-date-time">{game_time_str}</div>' if game_time_str else ''}
                </div>
            </div>
            <div class="card-body">
                <div class="bet-main-row">
                    <div class="bet-selection">
                        <span class="txt-green">{direction}</span>
                        {f'<span class="line">{line_display}</span>' if line_display else ''}
                        <span class="bet-odds">{odds_display}</span>
                    </div>
                </div>
                <div class="model-subtext">{subtext}</div>
                {stats_row}
                {pitcher_section}
                <div class="metrics-grid">
                    <div class="metric-item"><span class="metric-lbl">WIN %</span><span class="metric-val txt-green">{res['prob']:.0%}</span></div>
                    <div class="metric-item"><span class="metric-lbl">EV</span><span class="metric-val txt-green">+{res['edge']:.1%}</span></div>
                    <div class="metric-item"><span class="metric-lbl">KELLY</span><span class="metric-val">{res['wager']}</span></div>
                </div>
                <div class="tags-container">{tags_html}</div>
            </div>
        </div>"""


def generate_html(results, stats, tracking_data=None):
    if not results and os.path.exists(RESULTS_CACHE):
        try:
            import json as _json
            with open(RESULTS_CACHE) as _f:
                results = _json.load(_f)
        except Exception:
            pass
    css = """
    :root {
        --bg-main: #0a0a0a;
        --bg-card: #1a1a1a;
        --bg-card-secondary: #222222;
        --text-primary: #ffffff;
        --text-secondary: #94a3b8;
        --accent-green: #4ade80;
        --accent-red: #f87171;
        --accent-blue: #60a5fa;
        --border-color: #2a2a2a;
        --glow-green: rgba(74,222,128,0.15);
    }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 20px; font-family: 'Inter', system-ui, sans-serif;
           background-color: var(--bg-main); color: var(--text-primary); }
    .container { max-width: 820px; margin: 0 auto; }

    header { display: flex; justify-content: space-between; align-items: center;
             margin-bottom: 28px; border-bottom: 1px solid var(--border-color); padding-bottom: 18px; }
    h1 { margin: 0; font-size: 22px; font-weight: 800; }
    .subheader { font-size: 15px; font-weight: 600; margin-top: 2px; }
    .date-sub { color: var(--text-secondary); font-size: 13px; margin-top: 4px; }

    .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 30px; }
    .stat-box { background: var(--bg-card); border-radius: 12px; padding: 16px;
                text-align: center; border: 1px solid var(--border-color); }
    .stat-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase;
                  letter-spacing: .5px; margin-bottom: 6px; }
    .stat-value { font-size: 22px; font-weight: 700; }
    .txt-green { color: var(--accent-green); }
    .txt-red   { color: var(--accent-red); }

    /* ---- Card ---- */
    .prop-card { background: var(--bg-card); border-radius: 16px; overflow: hidden;
                 margin-bottom: 18px; border: 1px solid var(--border-color);
                 box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    .prop-card.glow-green { border-color: rgba(74,222,128,0.25); }

    .card-header { padding: 14px 18px; background: var(--bg-card-secondary);
                   display: flex; justify-content: space-between; align-items: center;
                   border-bottom: 1px solid var(--border-color); gap: 10px; }
    .header-left { display: flex; align-items: center; gap: 12px; }
    .team-logo { width: 44px; height: 44px; object-fit: contain; flex-shrink: 0; }
    .player-info h2 { margin: 0; font-size: 17px; font-weight: 700; line-height: 1.2; }
    .matchup-info { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }
    .game-meta { text-align: right; flex-shrink: 0; }
    .bet-type-badge { font-size: 11px; font-weight: 700; text-transform: uppercase;
                      color: var(--accent-blue); letter-spacing: .4px; }
    .game-date-time { font-size: 12px; color: var(--text-secondary); margin-top: 3px; }

    .card-body { padding: 18px; }

    /* ---- Bet row ---- */
    .bet-main-row { margin-bottom: 10px; }
    .bet-selection { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
    .txt-green { color: var(--accent-green); }
    .bet-selection .txt-green { font-size: 20px; font-weight: 800; }
    .line { font-size: 18px; font-weight: 600; color: var(--text-primary); }
    .bet-odds { font-size: 16px; color: var(--text-secondary); font-weight: 500; margin-left: auto; }

    .model-subtext { font-size: 13px; color: var(--text-secondary); margin-bottom: 14px; }
    .model-subtext strong { color: var(--text-primary); }

    /* ---- Stats row ---- */
    .stats-row { display: flex; gap: 10px; margin-bottom: 12px; }
    .stat-item { background: var(--bg-main); border-radius: 8px; padding: 10px 14px; flex: 1; }
    .stat-title { font-size: 11px; color: var(--text-secondary); text-transform: uppercase;
                  letter-spacing: .4px; margin-bottom: 4px; }
    .stat-val { font-size: 16px; font-weight: 700; }

    /* ---- Pitcher matchup ---- */
    .pitcher-matchup { background: rgba(96,165,250,0.07); border: 1px solid rgba(96,165,250,0.2);
                       border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; }
    .pitcher-vs { font-size: 13px; font-weight: 700; color: var(--accent-blue); margin-bottom: 6px; }
    .pitcher-stats { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary); }
    .pitcher-stats span strong { color: var(--text-primary); }

    /* ---- Metrics ---- */
    .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
    .metric-item { background: var(--bg-main); padding: 10px; border-radius: 8px; text-align: center; }
    .metric-lbl { display: block; font-size: 10px; color: var(--text-secondary);
                  text-transform: uppercase; letter-spacing: .4px; margin-bottom: 4px; }
    .metric-val { font-size: 15px; font-weight: 700; }

    /* ---- Tags ---- */
    .tags-container { display: flex; flex-wrap: wrap; gap: 6px; }
    .tag { font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; }
    .tag-green { background: rgba(74,222,128,0.12); color: var(--accent-green); }
    .tag-blue  { background: rgba(96,165,250,0.12); color: var(--accent-blue); }

    .no-bets { text-align: center; color: var(--text-secondary); padding: 40px; font-style: italic; }
    footer { text-align: center; font-size: 12px; color: var(--text-secondary); margin-top: 40px; padding-top: 20px;
             border-top: 1px solid var(--border-color); }

    .tracking-section { margin-top: 2.5rem; }
    .tracking-header { font-size: 15px; font-weight: 700; margin-bottom: 1rem;
                       padding-bottom: 0.5rem; border-bottom: 1px solid var(--border-color); }
    .perf-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .perf-card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);
                 padding: 1.2rem; flex: 1; min-width: 140px; }
    .perf-title { font-size: 0.7rem; text-transform: uppercase; color: var(--text-secondary);
                  letter-spacing: 0.05em; font-weight: 700; text-align: center; margin-bottom: 0.8rem; }
    .perf-grid-inner { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; text-align: center; }
    .perf-label { font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary);
                  letter-spacing: 0.05em; margin-bottom: 2px; }
    .perf-value { font-size: 0.95rem; font-weight: 800; }
    .type-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
    .type-card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color); padding: 1rem; }
    .type-name { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
                 margin-bottom: 0.7rem; color: var(--accent-blue); }
    .type-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; }
    .type-stat { text-align: center; }
    .type-stat-lbl { font-size: 0.6rem; text-transform: uppercase; color: var(--text-secondary); }
    .type-stat-val { font-size: 0.9rem; font-weight: 700; }
    """

    roi_class = 'txt-green' if stats['roi'] > 0 else 'txt-red'
    cards_html = ''.join(render_card(r) for r in results) if results else '<div class="no-bets">No high-value plays found for today.</div>'

    performance_html = ''
    if tracking_data:
        all_picks = tracking_data.get('picks', [])
        completed = [p for p in all_picks if p.get('status', '').lower() in ('win', 'loss')]
        completed.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        today_str = datetime.now().strftime('%Y%m%d')
        yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

        def _pick_game_date(p):
            pid = p.get('id', '')
            return pid.split('_')[-1] if pid else ''

        today_done = [p for p in completed if _pick_game_date(p) == today_str]
        yest_done = [p for p in completed if _pick_game_date(p) == yesterday_str]

        def _day_stats(picks):
            w = sum(1 for p in picks if p.get('status', '').lower() == 'win')
            l = sum(1 for p in picks if p.get('status', '').lower() == 'loss')
            tot = w + l
            profit = sum((p.get('odds_dec', 1.91) - 1) if p.get('status', '').lower() == 'win' else -1.0
                         for p in picks)
            roi = (profit / tot * 100) if tot > 0 else 0
            return {'record': f"{w}-{l}", 'profit': profit, 'roi': roi}

        t = _day_stats(today_done)
        y = _day_stats(yest_done)
        tc = 'txt-green' if t['profit'] > 0 else ('txt-red' if t['profit'] < 0 else '')
        yc = 'txt-green' if y['profit'] > 0 else ('txt-red' if y['profit'] < 0 else '')

        l10 = _calc_mlb_perf(completed, 10)
        l20 = _calc_mlb_perf(completed, 20)
        l50 = _calc_mlb_perf(completed, 50)
        by_type = _calc_mlb_by_type(completed)

        def _cc(val, threshold=0):
            return 'txt-green' if val > threshold else ('txt-red' if val < 0 else '')

        type_cards_html = ''
        for label, d in by_type.items():
            type_cards_html += f'''
            <div class="type-card">
                <div class="type-name">{label}</div>
                <div class="type-stats">
                    <div class="type-stat"><div class="type-stat-lbl">Record</div><div class="type-stat-val">{d["record"]}</div></div>
                    <div class="type-stat"><div class="type-stat-lbl">Win %</div><div class="type-stat-val {_cc(d["win_rate"], 50)}">{d["win_rate"]:.0f}%</div></div>
                    <div class="type-stat"><div class="type-stat-lbl">Profit</div><div class="type-stat-val {_cc(d["profit"])}">{d["profit"]:+.1f}u</div></div>
                    <div class="type-stat"><div class="type-stat-lbl">ROI</div><div class="type-stat-val {_cc(d["roi"])}">{d["roi"]:+.1f}%</div></div>
                </div>
            </div>'''

        performance_html = f'''
    <div class="tracking-section">
        <div class="tracking-header">Daily Performance</div>
        <div class="perf-row">
            <div class="perf-card">
                <div class="perf-title">Today</div>
                <div style="text-align:center;">
                    <div style="font-size:1.1rem;font-weight:700;">{t["record"]}</div>
                    <div class="{tc}" style="font-weight:600;">{t["profit"]:+.1f}u</div>
                    <div style="font-size:0.8rem;color:var(--text-secondary);">{t["roi"]:.1f}% ROI</div>
                </div>
            </div>
            <div class="perf-card">
                <div class="perf-title">Yesterday</div>
                <div style="text-align:center;">
                    <div style="font-size:1.1rem;font-weight:700;">{y["record"]}</div>
                    <div class="{yc}" style="font-weight:600;">{y["profit"]:+.1f}u</div>
                    <div style="font-size:0.8rem;color:var(--text-secondary);">{y["roi"]:.1f}% ROI</div>
                </div>
            </div>
        </div>
    </div>
    <div class="tracking-section">
        <div class="tracking-header">Recent Form</div>
        <div class="perf-row">
            <div class="perf-card">
                <div class="perf-title">Last 10</div>
                <div class="perf-grid-inner">
                    <div><div class="perf-label">Record</div><div class="perf-value">{l10["record"]}</div></div>
                    <div><div class="perf-label">Win %</div><div class="perf-value {_cc(l10["win_rate"], 50)}">{l10["win_rate"]:.0f}%</div></div>
                    <div><div class="perf-label">Profit</div><div class="perf-value {_cc(l10["profit"])}">{l10["profit"]:+.1f}u</div></div>
                    <div><div class="perf-label">ROI</div><div class="perf-value {_cc(l10["roi"])}">{l10["roi"]:+.1f}%</div></div>
                </div>
            </div>
            <div class="perf-card">
                <div class="perf-title">Last 20</div>
                <div class="perf-grid-inner">
                    <div><div class="perf-label">Record</div><div class="perf-value">{l20["record"]}</div></div>
                    <div><div class="perf-label">Win %</div><div class="perf-value {_cc(l20["win_rate"], 50)}">{l20["win_rate"]:.0f}%</div></div>
                    <div><div class="perf-label">Profit</div><div class="perf-value {_cc(l20["profit"])}">{l20["profit"]:+.1f}u</div></div>
                    <div><div class="perf-label">ROI</div><div class="perf-value {_cc(l20["roi"])}">{l20["roi"]:+.1f}%</div></div>
                </div>
            </div>
            <div class="perf-card">
                <div class="perf-title">Last 50</div>
                <div class="perf-grid-inner">
                    <div><div class="perf-label">Record</div><div class="perf-value">{l50["record"]}</div></div>
                    <div><div class="perf-label">Win %</div><div class="perf-value {_cc(l50["win_rate"], 50)}">{l50["win_rate"]:.0f}%</div></div>
                    <div><div class="perf-label">Profit</div><div class="perf-value {_cc(l50["profit"])}">{l50["profit"]:+.1f}u</div></div>
                    <div><div class="perf-label">ROI</div><div class="perf-value {_cc(l50["roi"])}">{l50["roi"]:+.1f}%</div></div>
                </div>
            </div>
        </div>
    </div>
    <div class="tracking-section">
        <div class="tracking-header">MLB Model Performance — By Bet Type</div>
        <div class="type-grid">{type_cards_html}</div>
    </div>'''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics — MLB</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
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
            <div class="stat-value {roi_class}">{stats['roi']:.1f}%</div>
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
        {cards_html}
    </div>
    {performance_html}
    <footer>
        Model based on SIERA, xFIP, wRC+ &amp; Statcast Data. Always bet responsibly.
    </footer>
</div>
</body>
</html>"""


_MLB_CSS = """
    :root {
        --bg-main: #0a0a0a; --bg-card: #1a1a1a; --bg-card-secondary: #222222;
        --text-primary: #ffffff; --text-secondary: #94a3b8;
        --accent-green: #4ade80; --accent-red: #f87171; --accent-blue: #60a5fa;
        --border-color: #2a2a2a;
    }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 20px; font-family: 'Inter', system-ui, sans-serif;
           background-color: var(--bg-main); color: var(--text-primary); }
    .container { max-width: 820px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center;
             margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 18px; }
    h1 { margin: 0; font-size: 22px; font-weight: 800; }
    .subheader { font-size: 15px; font-weight: 600; margin-top: 2px; }
    .date-sub { color: var(--text-secondary); font-size: 13px; margin-top: 4px; }
    .nav-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }
    .nav-link { padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;
                text-decoration: none; border: 1px solid var(--border-color);
                color: var(--text-secondary); background: var(--bg-card); transition: all 0.15s; }
    .nav-link:hover { color: var(--text-primary); border-color: var(--accent-blue); }
    .nav-link.active { color: var(--accent-blue); border-color: var(--accent-blue);
                       background: rgba(96,165,250,0.1); }
    .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 30px; }
    .stat-box { background: var(--bg-card); border-radius: 12px; padding: 16px;
                text-align: center; border: 1px solid var(--border-color); }
    .stat-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase;
                  letter-spacing: .5px; margin-bottom: 6px; }
    .stat-value { font-size: 22px; font-weight: 700; }
    .txt-green { color: var(--accent-green); }
    .txt-red   { color: var(--accent-red); }
    .prop-card { background: var(--bg-card); border-radius: 16px; overflow: hidden;
                 margin-bottom: 18px; border: 1px solid var(--border-color);
                 box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
    .prop-card.glow-green { border-color: rgba(74,222,128,0.25); }
    .card-header { padding: 14px 18px; background: var(--bg-card-secondary);
                   display: flex; justify-content: space-between; align-items: center;
                   border-bottom: 1px solid var(--border-color); gap: 10px; }
    .header-left { display: flex; align-items: center; gap: 12px; }
    .team-logo { width: 44px; height: 44px; object-fit: contain; flex-shrink: 0; }
    .player-info h2 { margin: 0; font-size: 17px; font-weight: 700; line-height: 1.2; }
    .matchup-info { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }
    .game-meta { text-align: right; flex-shrink: 0; }
    .bet-type-badge { font-size: 11px; font-weight: 700; text-transform: uppercase;
                      color: var(--accent-blue); letter-spacing: .4px; }
    .game-date-time { font-size: 12px; color: var(--text-secondary); margin-top: 3px; }
    .card-body { padding: 18px; }
    .bet-main-row { margin-bottom: 10px; }
    .bet-selection { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
    .bet-selection .txt-green { font-size: 20px; font-weight: 800; }
    .line { font-size: 18px; font-weight: 600; color: var(--text-primary); }
    .bet-odds { font-size: 16px; color: var(--text-secondary); font-weight: 500; margin-left: auto; }
    .model-subtext { font-size: 13px; color: var(--text-secondary); margin-bottom: 14px; }
    .model-subtext strong { color: var(--text-primary); }
    .stats-row { display: flex; gap: 10px; margin-bottom: 12px; }
    .stat-item { background: var(--bg-main); border-radius: 8px; padding: 10px 14px; flex: 1; }
    .stat-title { font-size: 11px; color: var(--text-secondary); text-transform: uppercase;
                  letter-spacing: .4px; margin-bottom: 4px; }
    .stat-val { font-size: 16px; font-weight: 700; }
    .pitcher-matchup { background: rgba(96,165,250,0.07); border: 1px solid rgba(96,165,250,0.2);
                       border-radius: 8px; padding: 10px 14px; margin-bottom: 14px; }
    .pitcher-vs { font-size: 13px; font-weight: 700; color: var(--accent-blue); margin-bottom: 6px; }
    .pitcher-stats { display: flex; gap: 16px; font-size: 12px; color: var(--text-secondary); }
    .pitcher-stats span strong { color: var(--text-primary); }
    .metrics-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px; }
    .metric-item { background: var(--bg-main); padding: 10px; border-radius: 8px; text-align: center; }
    .metric-lbl { display: block; font-size: 10px; color: var(--text-secondary);
                  text-transform: uppercase; letter-spacing: .4px; margin-bottom: 4px; }
    .metric-val { font-size: 15px; font-weight: 700; }
    .tags-container { display: flex; flex-wrap: wrap; gap: 6px; }
    .tag { font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; }
    .tag-green { background: rgba(74,222,128,0.12); color: var(--accent-green); }
    .tag-blue  { background: rgba(96,165,250,0.12); color: var(--accent-blue); }
    .no-bets { text-align: center; color: var(--text-secondary); padding: 40px; font-style: italic; }
    footer { text-align: center; font-size: 12px; color: var(--text-secondary); margin-top: 40px;
             padding-top: 20px; border-top: 1px solid var(--border-color); }
    .tracking-section { margin-top: 2.5rem; }
    .tracking-header { font-size: 15px; font-weight: 700; margin-bottom: 1rem;
                       padding-bottom: 0.5rem; border-bottom: 1px solid var(--border-color); }
    .perf-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .perf-card { background: var(--bg-card); border-radius: 12px; border: 1px solid var(--border-color);
                 padding: 1.2rem; flex: 1; min-width: 140px; }
    .perf-title { font-size: 0.7rem; text-transform: uppercase; color: var(--text-secondary);
                  letter-spacing: 0.05em; font-weight: 700; text-align: center; margin-bottom: 0.8rem; }
    .perf-grid-inner { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; text-align: center; }
    .perf-label { font-size: 0.65rem; text-transform: uppercase; color: var(--text-secondary);
                  letter-spacing: 0.05em; margin-bottom: 2px; }
    .perf-value { font-size: 0.95rem; font-weight: 800; }
    /* hub-specific */
    .hub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; margin-bottom: 30px; }
    .hub-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px;
                padding: 20px; text-decoration: none; color: inherit; display: block;
                transition: border-color 0.15s, transform 0.15s; }
    .hub-card:hover { border-color: var(--accent-blue); transform: translateY(-2px); }
    .hub-card-emoji { font-size: 28px; margin-bottom: 10px; }
    .hub-card-label { font-size: 14px; font-weight: 700; margin-bottom: 12px; }
    .hub-card-record { font-size: 22px; font-weight: 800; margin-bottom: 4px; }
    .hub-card-meta { font-size: 12px; color: var(--text-secondary); }
"""


def _nav_html(active_key=None):
    links = '<a href="mlb_master_model.html" class="nav-link">⚾ Hub</a>'
    for pt_key, info in PROP_PAGES.items():
        fname = os.path.basename(info['file'])
        active = 'active' if pt_key == active_key else ''
        links += f'<a href="{fname}" class="nav-link {active}">{info["emoji"]} {info["label"]}</a>'
    return f'<div class="nav-bar">{links}</div>'


def _perf_html_for_picks(completed):
    def _pick_game_date(p):
        pid = p.get('id', '')
        return pid.split('_')[-1] if pid else ''

    today_str = datetime.now().strftime('%Y%m%d')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    today_done = [p for p in completed if _pick_game_date(p) == today_str]
    yest_done  = [p for p in completed if _pick_game_date(p) == yesterday_str]

    def _day_stats(picks):
        w = sum(1 for p in picks if p.get('status','').lower() == 'win')
        l = sum(1 for p in picks if p.get('status','').lower() == 'loss')
        tot = w + l
        profit = sum((p.get('odds_dec', 1.91) - 1) if p.get('status','').lower() == 'win' else -1.0
                     for p in picks)
        roi = (profit / tot * 100) if tot > 0 else 0
        return {'record': f"{w}-{l}", 'profit': profit, 'roi': roi}

    def _cc(val, threshold=0):
        return 'txt-green' if val > threshold else ('txt-red' if val < 0 else '')

    t = _day_stats(today_done)
    y = _day_stats(yest_done)
    tc = _cc(t['profit'])
    yc = _cc(y['profit'])
    l10 = _calc_mlb_perf(completed, 10)
    l20 = _calc_mlb_perf(completed, 20)
    l50 = _calc_mlb_perf(completed, 50)

    return f'''
    <div class="tracking-section">
        <div class="tracking-header">Daily Performance</div>
        <div class="perf-row">
            <div class="perf-card">
                <div class="perf-title">Today</div>
                <div style="text-align:center;">
                    <div style="font-size:1.1rem;font-weight:700;">{t["record"]}</div>
                    <div class="{tc}" style="font-weight:600;">{t["profit"]:+.1f}u</div>
                    <div style="font-size:0.8rem;color:var(--text-secondary);">{t["roi"]:.1f}% ROI</div>
                </div>
            </div>
            <div class="perf-card">
                <div class="perf-title">Yesterday</div>
                <div style="text-align:center;">
                    <div style="font-size:1.1rem;font-weight:700;">{y["record"]}</div>
                    <div class="{yc}" style="font-weight:600;">{y["profit"]:+.1f}u</div>
                    <div style="font-size:0.8rem;color:var(--text-secondary);">{y["roi"]:.1f}% ROI</div>
                </div>
            </div>
        </div>
    </div>
    <div class="tracking-section">
        <div class="tracking-header">Recent Form</div>
        <div class="perf-row">
            <div class="perf-card">
                <div class="perf-title">Last 10</div>
                <div class="perf-grid-inner">
                    <div><div class="perf-label">Record</div><div class="perf-value">{l10["record"]}</div></div>
                    <div><div class="perf-label">Win %</div><div class="perf-value {_cc(l10["win_rate"],50)}">{l10["win_rate"]:.0f}%</div></div>
                    <div><div class="perf-label">Profit</div><div class="perf-value {_cc(l10["profit"])}">{l10["profit"]:+.1f}u</div></div>
                    <div><div class="perf-label">ROI</div><div class="perf-value {_cc(l10["roi"])}">{l10["roi"]:+.1f}%</div></div>
                </div>
            </div>
            <div class="perf-card">
                <div class="perf-title">Last 20</div>
                <div class="perf-grid-inner">
                    <div><div class="perf-label">Record</div><div class="perf-value">{l20["record"]}</div></div>
                    <div><div class="perf-label">Win %</div><div class="perf-value {_cc(l20["win_rate"],50)}">{l20["win_rate"]:.0f}%</div></div>
                    <div><div class="perf-label">Profit</div><div class="perf-value {_cc(l20["profit"])}">{l20["profit"]:+.1f}u</div></div>
                    <div><div class="perf-label">ROI</div><div class="perf-value {_cc(l20["roi"])}">{l20["roi"]:+.1f}%</div></div>
                </div>
            </div>
            <div class="perf-card">
                <div class="perf-title">Last 50</div>
                <div class="perf-grid-inner">
                    <div><div class="perf-label">Record</div><div class="perf-value">{l50["record"]}</div></div>
                    <div><div class="perf-label">Win %</div><div class="perf-value {_cc(l50["win_rate"],50)}">{l50["win_rate"]:.0f}%</div></div>
                    <div><div class="perf-label">Profit</div><div class="perf-value {_cc(l50["profit"])}">{l50["profit"]:+.1f}u</div></div>
                    <div><div class="perf-label">ROI</div><div class="perf-value {_cc(l50["roi"])}">{l50["roi"]:+.1f}%</div></div>
                </div>
            </div>
        </div>
    </div>'''


def generate_prop_html(prop_type_key, all_results, tracking_data):
    info = PROP_PAGES[prop_type_key]
    label = info['label']
    emoji = info['emoji']

    # Filter today's picks to this prop type
    if not all_results and os.path.exists(RESULTS_CACHE):
        try:
            with open(RESULTS_CACHE) as _f:
                all_results = json.load(_f)
        except Exception:
            all_results = []
    results = [r for r in all_results if r.get('type') == prop_type_key]

    # Filter tracking to this prop type
    all_picks = tracking_data.get('picks', [])
    completed = [p for p in all_picks
                 if p.get('type') == prop_type_key and p.get('status','').lower() in ('win','loss')]
    completed.sort(key=lambda x: x.get('created_at',''), reverse=True)

    # Overall stats for this type
    wins = sum(1 for p in completed if p['status'].lower() == 'win')
    losses = len(completed) - wins
    total = wins + losses
    profit = sum((p.get('odds_dec',1.91)-1) if p['status'].lower()=='win' else -1.0 for p in completed)
    roi = (profit / total * 100) if total > 0 else 0.0
    win_rate = (wins / total * 100) if total > 0 else 0.0
    roi_class = 'txt-green' if roi > 0 else 'txt-red'

    cards_html = (''.join(render_card(r) for r in results)
                  if results else '<div class="no-bets">No high-value plays found for today.</div>')
    perf_html = _perf_html_for_picks(completed) if completed else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics — MLB {label}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>{_MLB_CSS}</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">{emoji} MLB {label}</div>
            <div class="date-sub">{datetime.now().strftime('%B %d, %Y')} • Alpha V2.0</div>
        </div>
    </header>
    {_nav_html(prop_type_key)}
    <div class="summary-grid">
        <div class="stat-box">
            <div class="stat-label">Season ROI</div>
            <div class="stat-value {roi_class}">{roi:.1f}%</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Win Rate</div>
            <div class="stat-value">{win_rate:.1f}%</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Record</div>
            <div class="stat-value">{wins}-{losses}</div>
        </div>
    </div>
    <div class="picks-section">
        {cards_html}
    </div>
    {perf_html}
    <footer>
        Model based on SIERA, xFIP, wRC+ &amp; Statcast Data. Always bet responsibly.
    </footer>
</div>
</body>
</html>"""


def generate_hub_html(tracking_data):
    all_picks = tracking_data.get('picks', [])
    completed = [p for p in all_picks if p.get('status','').lower() in ('win','loss')]

    # Overall stats
    wins = sum(1 for p in completed if p['status'].lower() == 'win')
    losses = len(completed) - wins
    total = wins + losses
    profit = sum((p.get('odds_dec',1.91)-1) if p['status'].lower()=='win' else -1.0 for p in completed)
    roi = (profit / total * 100) if total > 0 else 0.0
    win_rate = (wins / total * 100) if total > 0 else 0.0
    roi_class = 'txt-green' if roi > 0 else 'txt-red'

    # Per-prop cards
    by_type = _calc_mlb_by_type(completed)
    hub_cards = ''
    for pt_key, info in PROP_PAGES.items():
        label = info['label']
        emoji = info['emoji']
        fname = os.path.basename(info['file'])
        d = by_type.get(label, {'record': '0-0', 'win_rate': 0, 'profit': 0, 'roi': 0})
        rec_color = '#4ade80' if d['win_rate'] >= 55 else ('#f87171' if d['win_rate'] < 50 and d['win_rate'] > 0 else '#ffffff')
        roi_c = '#4ade80' if d['roi'] > 0 else ('#f87171' if d['roi'] < 0 else '#ffffff')
        hub_cards += f'''
        <a href="{fname}" class="hub-card">
            <div class="hub-card-emoji">{emoji}</div>
            <div class="hub-card-label">{label}</div>
            <div class="hub-card-record" style="color:{rec_color};">{d["record"]}</div>
            <div class="hub-card-meta">
                {d["win_rate"]:.0f}% Win &nbsp;|&nbsp;
                <span style="color:{roi_c};">{d["roi"]:+.1f}% ROI</span>
            </div>
        </a>'''

    nav = '<div class="nav-bar">' + ''.join(
        f'<a href="{os.path.basename(i["file"])}" class="nav-link">{i["emoji"]} {i["label"]}</a>'
        for i in PROP_PAGES.values()
    ) + '</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics — MLB</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>{_MLB_CSS}</style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div class="subheader">⚾ MLB Models</div>
            <div class="date-sub">{datetime.now().strftime('%B %d, %Y')} • Alpha V2.0</div>
        </div>
    </header>
    {nav}
    <div class="summary-grid">
        <div class="stat-box">
            <div class="stat-label">Season ROI</div>
            <div class="stat-value {roi_class}">{roi:.1f}%</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Win Rate</div>
            <div class="stat-value">{win_rate:.1f}%</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Overall Record</div>
            <div class="stat-value">{wins}-{losses}</div>
        </div>
    </div>
    <div class="hub-grid">
        {hub_cards}
    </div>
    <footer>
        Model based on SIERA, xFIP, wRC+ &amp; Statcast Data. Always bet responsibly.
    </footer>
</div>
</body>
</html>"""


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


def get_team_lineup_wrc(team_abbr, batters, n=5):
    """Average wRC+ of the top-N batters for a team — proxy for lineup context around the target batter."""
    team_batters = batters[batters['Team'] == team_abbr]
    if team_batters.empty:
        return 100
    top_n = team_batters.nlargest(n, 'wRC+')
    return top_n['wRC+'].mean()


def get_team_avg(team_abbr, batters):
    """Average batting AVG for a team's qualified batters (falls back to league avg .248)."""
    team_batters = batters[batters['Team'] == team_abbr]
    if team_batters.empty or 'AVG' not in team_batters.columns:
        return 0.248
    return team_batters['AVG'].mean()


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
    # Before noon ET → today's games haven't started, use today.
    # Noon ET or later → today's games are underway, look ahead to tomorrow.
    _et_now = datetime.now(pytz.timezone('US/Eastern'))
    if _et_now.hour < 12:
        target_date = _et_now
    else:
        target_date = _et_now + timedelta(days=1)
    today_str = target_date.strftime('%Y%m%d')
    target_date_str = target_date.strftime('%Y-%m-%d')

    print(f"\n--- FETCHING SCHEDULE FOR {target_date_str} ---")
    games = get_schedule(target_date_str)
    game_odds_lookup = _fetch_mlb_game_odds()

    if not games:
        print(f"{Colors.YELLOW}No regular season games on {target_date_str} (pre-season or off day).{Colors.END}")
    else:
        print(f"{Colors.GREEN}Found {len(games)} games on {target_date_str}.{Colors.END}")

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

        game_time = game.get('game_time', '')

        # --- K Props (one per pitcher if found) ---
        for pitcher_row, opp_team in [(p_away, home), (p_home, away)]:
            if pitcher_row is None:
                continue
            try:
                pitcher_team = away if opp_team == home else home
                opp_k_rate = get_team_k_rate(opp_team, batters)
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
                        'game_time': game_time,
                        'pitcher_team': pitcher_team,
                        'pitcher_siera': round(float(pitcher_row.get('SIERA', 0) or 0), 2),
                        'pitcher_xfip': round(float(pitcher_row.get('xFIP', 0) or 0), 2),
                        'pitcher_k9': round(float(pitcher_row.get('K/9', 0) or 0), 1),
                        'opp_k_rate': round(opp_k_rate * 100, 1),
                        'exp_k': round(exp_k, 1),
                    })
            except Exception as e:
                print(f"    K prop error {pitcher_row.get('Name','?')}: {e}")

        # --- Pitching Outs Props (one per pitcher if found) ---
        for pitcher_row, pitcher_name, opp_team in [
            (p_away, away_pitcher_name, home),
            (p_home, home_pitcher_name, away),
        ]:
            if pitcher_row is None:
                continue
            if float(pitcher_row.get('IP_per_GS', 0) or 0) < 5.5:
                continue  # skip short-stint / bulk-relief pitchers
            try:
                pitcher_team = away if opp_team == home else home
                opp_k_rate = get_team_k_rate(opp_team, batters)
                exp_outs, prob_over = calculate_pitching_outs_probability(pitcher_row, opp_k_rate, line=0)

                # Pick the standard line just below expected outs
                if exp_outs >= 20.0:
                    line_val = 18.5
                elif exp_outs >= 18.0:
                    line_val = 17.5
                elif exp_outs >= 16.0:
                    line_val = 15.5
                else:
                    line_val = 14.5

                exp_outs, prob_over = calculate_pitching_outs_probability(pitcher_row, opp_k_rate, line=line_val)
                outs_odds = 1.91
                edge_outs = prob_over - (1 / outs_odds)
                if edge_outs > OUTS_MIN_EDGE:
                    kel_outs = kelly_criterion(prob_over, outs_odds) * KELLY_MULTIPLIER
                    new_picks.append({
                        'id': f"OUTS_{pitcher_name.replace(' ','_')}_{today_str}",
                        'type': 'Player Props - Pitching Outs',
                        'matchup': matchup,
                        'selection': pitcher_name,
                        'line': f"Over {line_val} Outs",
                        'odds_str': '-110',
                        'odds_dec': outs_odds,
                        'prob': prob_over,
                        'edge': edge_outs,
                        'wager': f"{kel_outs:.1%} Unit",
                        'kel': kel_outs,
                        'score': prob_over * 10,
                        'game_time': game_time,
                        'pitcher_team': pitcher_team,
                        'pitcher_siera': round(float(pitcher_row.get('SIERA', 0) or 0), 2),
                        'pitcher_k9': round(float(pitcher_row.get('K/9', 0) or 0), 1),
                        'pitcher_bb9': round(float(pitcher_row.get('BB/9', 0) or 0), 1),
                        'pitcher_ip_per_gs': round(float(pitcher_row.get('IP_per_GS', 5.0) or 5.0), 2),
                        'exp_outs': round(exp_outs, 1),
                        'opp_k_rate': round(opp_k_rate * 100, 1),
                    })
            except Exception as e:
                print(f"    Pitching outs error {pitcher_name}: {e}")

        # --- Hits Allowed Props (Under, one per starter if found) ---
        for pitcher_row, pitcher_name, opp_team in [
            (p_away, away_pitcher_name, home),
            (p_home, home_pitcher_name, away),
        ]:
            if pitcher_row is None:
                continue
            ip_per_gs = float(pitcher_row.get('IP_per_GS', 0) or 0)
            h9 = float(pitcher_row.get('H/9', 99) or 99)
            if ip_per_gs < 5.5 or h9 > 8.0:
                continue  # only quality starters who limit hits
            try:
                pitcher_team = away if opp_team == home else home
                opp_avg = get_team_avg(opp_team, batters)
                exp_hits, prob_under = calculate_hits_allowed_probability(
                    pitcher_row, opp_avg, ip_per_gs, line=0
                )
                # Set line one step above expected hits
                if exp_hits <= 4.0:
                    line_val = 4.5
                elif exp_hits <= 5.0:
                    line_val = 5.5
                elif exp_hits <= 6.0:
                    line_val = 6.5
                else:
                    line_val = 7.5

                exp_hits, prob_under = calculate_hits_allowed_probability(
                    pitcher_row, opp_avg, ip_per_gs, line=line_val
                )
                ha_odds = 1.91
                edge_ha = prob_under - (1 / ha_odds)
                if edge_ha > HA_MIN_EDGE:
                    kel_ha = kelly_criterion(prob_under, ha_odds) * KELLY_MULTIPLIER
                    new_picks.append({
                        'id': f"HA_{pitcher_name.replace(' ','_')}_{today_str}",
                        'type': 'Player Props - Hits Allowed',
                        'matchup': matchup,
                        'selection': pitcher_name,
                        'line': f"Under {line_val} Hits",
                        'odds_str': '-110',
                        'odds_dec': ha_odds,
                        'prob': prob_under,
                        'edge': edge_ha,
                        'wager': f"{kel_ha:.1%} Unit",
                        'kel': kel_ha,
                        'score': prob_under * 10,
                        'game_time': game_time,
                        'pitcher_team': pitcher_team,
                        'pitcher_h9': round(float(pitcher_row.get('H/9', 0) or 0), 2),
                        'pitcher_siera': round(float(pitcher_row.get('SIERA', 0) or 0), 2),
                        'pitcher_xfip': round(float(pitcher_row.get('xFIP', 0) or 0), 2),
                        'pitcher_ip_per_gs': round(ip_per_gs, 2),
                        'opp_avg': round(opp_avg, 3),
                        'exp_hits': exp_hits,
                    })
            except Exception as e:
                print(f"    Hits allowed error {pitcher_name}: {e}")

        # --- H+R+RBI Props (top 5 qualified batters per team vs opposing pitcher) ---
        for batting_team, opp_pitcher_row in [
            (away, p_home),
            (home, p_away),
        ]:
            if opp_pitcher_row is None:
                continue
            team_bats = batters[batters['Team'] == batting_team]
            if team_bats.empty:
                continue
            lineup_wrc = get_team_lineup_wrc(batting_team, batters, n=5)
            top_bats = team_bats[team_bats['wRC+'] >= 100].nlargest(5, 'wRC+')

            for _, batter_row in top_bats.iterrows():
                batter_name = batter_row['Name']
                batter_id = batter_name.replace(' ', '_')
                batter_wrc = round(float(batter_row.get('wRC+', 100) or 100), 0)
                batter_barrel = round(float(batter_row.get('brl_percent', 0) or 0), 1)
                p_siera = round(float(opp_pitcher_row.get('SIERA', 0) or 0), 2)
                p_xfip = round(float(opp_pitcher_row.get('xFIP', 0) or 0), 2)
                p_hr9 = round(float(opp_pitcher_row.get('HR/9', 0) or 0), 2)
                p_name = opp_pitcher_row['Name']

                # H+R+RBI prop (Over 1.5, ~-110 market standard)
                try:
                    exp_val, prob_over_hrbi = calculate_h_r_rbi_probability(
                        batter_row, opp_pitcher_row, lineup_wrc
                    )
                    hrbi_odds = 1.91
                    edge_hrbi = prob_over_hrbi - (1 / hrbi_odds)
                    if edge_hrbi > HRBI_MIN_EDGE:
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
                            'game_time': game_time,
                            'batting_team': batting_team,
                            'batter_wrc': batter_wrc,
                            'batter_barrel': batter_barrel,
                            'pitcher_name': p_name,
                            'pitcher_siera': p_siera,
                            'pitcher_xfip': p_xfip,
                            'pitcher_hr9': p_hr9,
                            'exp_val': round(exp_val, 2),
                        })
                except Exception as e:
                    print(f"    H+R+RBI prop error {batter_name}: {e}")

                # Total Bases prop (Over 1.5, ~-110 market standard)
                try:
                    exp_tb, prob_over_tb = calculate_total_bases_probability(
                        batter_row, opp_pitcher_row, line=1.5
                    )
                    tb_odds = 1.91
                    edge_tb = prob_over_tb - (1 / tb_odds)
                    if edge_tb > TB_MIN_EDGE:
                        kel_tb = kelly_criterion(prob_over_tb, tb_odds) * KELLY_MULTIPLIER
                        new_picks.append({
                            'id': f"TB_{batter_id}_{today_str}",
                            'type': 'Player Props - Total Bases',
                            'matchup': matchup,
                            'selection': batter_name,
                            'line': f"Over 1.5 (Exp: {exp_tb:.2f})",
                            'odds_str': '-110',
                            'odds_dec': tb_odds,
                            'prob': prob_over_tb,
                            'edge': edge_tb,
                            'wager': f"{kel_tb:.1%} Unit",
                            'kel': kel_tb,
                            'score': prob_over_tb * 10,
                            'game_time': game_time,
                            'batting_team': batting_team,
                            'batter_wrc': batter_wrc,
                            'batter_barrel': batter_barrel,
                            'batter_slg': round(float(batter_row.get('SLG', 0.400) or 0.400), 3),
                            'pitcher_name': p_name,
                            'pitcher_siera': p_siera,
                            'pitcher_xfip': p_xfip,
                            'exp_tb': exp_tb,
                        })
                except Exception as e:
                    print(f"    Total Bases prop error {batter_name}: {e}")

    # --- Team Props (ML / Run Line / Totals) ---
    print("\n--- TEAM PROPS (ML / RUN LINE / TOTALS) ---")
    for game in games:
        away = game['away_team']
        home = game['home_team']
        matchup = f"{away} @ {home}"
        game_time = game.get('game_time', '')
        p_away = find_player(game['away_pitcher'], pitchers)
        p_home = find_player(game['home_pitcher'], pitchers)
        away_wrc = get_team_wrc(away, batters)
        home_wrc = get_team_wrc(home, batters)

        # look up game odds — try both key orders
        gd = game_odds_lookup.get((home, away)) or game_odds_lookup.get((away, home))
        if not gd:
            continue
        h2h     = gd.get('h2h', {})
        spreads = gd.get('spreads', {})
        totals  = gd.get('totals', {})

        if not h2h:
            continue

        try:
            home_win_prob, away_win_prob, expected_total, home_exp_r, away_exp_r = \
                calculate_game_probabilities(
                    p_home or {}, p_away or {}, home_wrc, away_wrc
                )

            home_exp_r_r = round(home_exp_r, 2)
            away_exp_r_r = round(away_exp_r, 2)
            exp_total_r  = round(expected_total, 2)
            home_era_val = round(float((p_home or {}).get('SIERA', 4.50) or 4.50), 2)
            away_era_val = round(float((p_away or {}).get('SIERA', 4.50) or 4.50), 2)
            home_sp_name = (p_home or {}).get('Name', 'TBD')
            away_sp_name = (p_away or {}).get('Name', 'TBD')
        except Exception as e:
            print(f"    Game prob error {matchup}: {e}")
            continue

        # --- Moneyline ---
        for bet_team, win_prob, odds_raw in [
            (home, home_win_prob, h2h.get(home)),
            (away, away_win_prob, h2h.get(away)),
        ]:
            if odds_raw is None:
                continue
            try:
                odds_dec = (1 + 100 / abs(odds_raw)) if odds_raw < 0 else (1 + odds_raw / 100)
                implied  = 1 / odds_dec
                edge     = win_prob - implied
                if edge > ML_MIN_EDGE:
                    kel = kelly_criterion(win_prob, odds_dec) * KELLY_MULTIPLIER
                    new_picks.append({
                        'id':             f"ML_{bet_team}_{today_str}",
                        'type':           'Team Props - Moneyline',
                        'matchup':        matchup,
                        'bet_team':       bet_team,
                        'home_team':      home,
                        'away_team':      away,
                        'selection':      f"{bet_team} ML",
                        'line':           'ML',
                        'odds_str':       str(odds_raw),
                        'odds_dec':       odds_dec,
                        'prob':           round(win_prob, 3),
                        'edge':           round(edge, 3),
                        'wager':          f"{kel:.1%} Unit",
                        'kel':            kel,
                        'score':          round(edge * 100, 1),
                        'game_time':      game_time,
                        'home_exp_r':     home_exp_r_r,
                        'away_exp_r':     away_exp_r_r,
                        'expected_total': exp_total_r,
                        'home_wrc':       home_wrc,
                        'away_wrc':       away_wrc,
                        'home_era':       home_era_val,
                        'away_era':       away_era_val,
                        'home_pitcher':   home_sp_name,
                        'away_pitcher':   away_sp_name,
                    })
                    print(f"    {Colors.GREEN}ML: {bet_team}  prob={win_prob:.1%}  edge={edge:+.1%}  odds={odds_raw}{Colors.END}")
            except Exception as e:
                print(f"    ML error {bet_team}: {e}")

        # --- Run Line ---
        for bet_team, exp_r_self, exp_r_opp, odds_entry in [
            (home, home_exp_r, away_exp_r, spreads.get(home)),
            (away, away_exp_r, home_exp_r, spreads.get(away)),
        ]:
            if odds_entry is None:
                continue
            try:
                rl_odds_raw, point = odds_entry
                prob_fav, prob_dog = calculate_run_line_probability(exp_r_self, exp_r_opp)
                # fav = negative spread (win by 2+); dog = positive spread (cover losing by 1)
                rl_prob = prob_fav if point < 0 else prob_dog
                rl_odds_dec = (1 + 100 / abs(rl_odds_raw)) if rl_odds_raw < 0 else (1 + rl_odds_raw / 100)
                implied = 1 / rl_odds_dec
                edge = rl_prob - implied
                if edge > RL_MIN_EDGE:
                    kel = kelly_criterion(rl_prob, rl_odds_dec) * KELLY_MULTIPLIER
                    new_picks.append({
                        'id':             f"RL_{bet_team}_{today_str}",
                        'type':           'Team Props - Run Line',
                        'matchup':        matchup,
                        'bet_team':       bet_team,
                        'home_team':      home,
                        'away_team':      away,
                        'selection':      f"{bet_team} {point:+.1f}",
                        'line':           f"{point:+.1f}",
                        'point':          point,
                        'odds_str':       str(rl_odds_raw),
                        'odds_dec':       rl_odds_dec,
                        'prob':           round(rl_prob, 3),
                        'edge':           round(edge, 3),
                        'wager':          f"{kel:.1%} Unit",
                        'kel':            kel,
                        'score':          round(edge * 100, 1),
                        'game_time':      game_time,
                        'home_exp_r':     home_exp_r_r,
                        'away_exp_r':     away_exp_r_r,
                        'expected_total': exp_total_r,
                        'home_wrc':       home_wrc,
                        'away_wrc':       away_wrc,
                        'home_era':       home_era_val,
                        'away_era':       away_era_val,
                        'home_pitcher':   home_sp_name,
                        'away_pitcher':   away_sp_name,
                    })
                    print(f"    {Colors.GREEN}RL: {bet_team} {point:+.1f}  prob={rl_prob:.1%}  edge={edge:+.1%}  odds={rl_odds_raw}{Colors.END}")
            except Exception as e:
                print(f"    RL error {bet_team}: {e}")

        # --- Totals ---
        for direction in ('over', 'under'):
            tot_entry = totals.get(direction)
            if tot_entry is None:
                continue
            try:
                tot_odds_raw, tot_line = tot_entry
                prob_over, prob_under = calculate_totals_probability(expected_total, tot_line)
                tot_prob = prob_over if direction == 'over' else prob_under
                tot_odds_dec = (1 + 100 / abs(tot_odds_raw)) if tot_odds_raw < 0 else (1 + tot_odds_raw / 100)
                implied = 1 / tot_odds_dec
                edge = tot_prob - implied
                if edge > TOT_MIN_EDGE:
                    kel = kelly_criterion(tot_prob, tot_odds_dec) * KELLY_MULTIPLIER
                    new_picks.append({
                        'id':             f"TOT_{direction.upper()}_{home}_{away}_{today_str}",
                        'type':           'Team Props - Total Runs',
                        'matchup':        matchup,
                        'direction':      direction,
                        'home_team':      home,
                        'away_team':      away,
                        'selection':      f"{direction.upper()} {tot_line}",
                        'line':           str(tot_line),
                        'tot_line':       tot_line,
                        'odds_str':       str(tot_odds_raw),
                        'odds_dec':       tot_odds_dec,
                        'prob':           round(tot_prob, 3),
                        'edge':           round(edge, 3),
                        'wager':          f"{kel:.1%} Unit",
                        'kel':            kel,
                        'score':          round(edge * 100, 1),
                        'game_time':      game_time,
                        'home_exp_r':     home_exp_r_r,
                        'away_exp_r':     away_exp_r_r,
                        'expected_total': exp_total_r,
                        'home_wrc':       home_wrc,
                        'away_wrc':       away_wrc,
                        'home_era':       home_era_val,
                        'away_era':       away_era_val,
                        'home_pitcher':   home_sp_name,
                        'away_pitcher':   away_sp_name,
                        'bet_team':       home,  # used by render_team_card for logo display
                    })
                    print(f"    {Colors.GREEN}TOT: {direction.upper()} {tot_line}  exp={expected_total:.2f}  edge={edge:+.1%}  odds={tot_odds_raw}{Colors.END}")
            except Exception as e:
                print(f"    Totals error {matchup} {direction}: {e}")

    # 3. Output
    track_new_picks(new_picks)
    with open(RESULTS_CACHE, 'w') as f:
        import json as _json
        _json.dump(new_picks, f)
    tracking_data = load_tracking_data()

    # Generate per-prop pages
    for pt_key, pt_info in PROP_PAGES.items():
        prop_html = generate_prop_html(pt_key, new_picks, tracking_data)
        with open(pt_info['file'], 'w') as f:
            f.write(prop_html)
        print(f"{Colors.CYAN}  → {os.path.basename(pt_info['file'])}{Colors.END}")

    # Hub page replaces mlb_master_model.html
    hub_html = generate_hub_html(tracking_data)
    with open(OUTPUT_HTML, 'w') as f:
        f.write(hub_html)

    print(f"\n{Colors.GREEN}✅ Analysis Complete. {len(new_picks)} plays found. Hub: {OUTPUT_HTML}{Colors.END}")

if __name__ == "__main__":
    main()