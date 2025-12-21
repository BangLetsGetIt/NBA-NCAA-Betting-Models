#!/usr/bin/env python3
"""
NFL ANYTIME TOUCHDOWN MODEL - COURTSIDE ANALYTICS EDITION
Optimized for +EV with Sharp Betting Logic & Advanced Tracking
"""

import json
import os
import re
import math
from datetime import datetime, timedelta
import pytz
import requests
from dotenv import load_dotenv
from jinja2 import Template

# Import grader for automated tracking
from props_grader import grade_props_tracking_file

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('ODDS_API_KEY')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "atd_model_output.html")
TRACKING_FILE = os.path.join(SCRIPT_DIR, "atd_model_tracking.json")

# Model Parameters - SHARP +EV (Relaxed Dec 20, 2024)
MIN_EDGE_THRESHOLD = 0.05  # 5% minimum edge (was 8%)
SHARP_EDGE_THRESHOLD = 0.08  # 8%+ edge for "SHARP BET" (was 10%)
KELLY_FRACTION = 0.25  # Conservative Kelly (1/4 Kelly)
MIN_CONFIDENCE = 0.65  # Confidence required
CURRENT_SEASON = "2024" # Adjust as needed

# Defense Ratings (Position specific - Lower is better for Defense)
DEFENSE_TD_RATINGS = {
    # Elite defenses
    "SF": {"RB": 0.65, "WR": 0.70, "TE": 0.75}, "BAL": {"RB": 0.70, "WR": 0.72, "TE": 0.78},
    "BUF": {"RB": 0.72, "WR": 0.75, "TE": 0.80}, "PHI": {"RB": 0.75, "WR": 0.78, "TE": 0.82},
    "DAL": {"RB": 0.77, "WR": 0.80, "TE": 0.85}, "CLE": {"RB": 0.78, "WR": 0.82, "TE": 0.86},
    "KC": {"RB": 0.85, "WR": 0.87, "TE": 0.90}, "DET": {"RB": 0.87, "WR": 0.85, "TE": 0.88},
    "MIA": {"RB": 0.88, "WR": 0.90, "TE": 0.92}, "CIN": {"RB": 0.90, "WR": 0.88, "TE": 0.90},
    # Average
    "SEA": {"RB": 0.95, "WR": 0.95, "TE": 0.95}, "LAC": {"RB": 0.98, "WR": 0.97, "TE": 0.96},
    "TB": {"RB": 1.00, "WR": 1.00, "TE": 1.00}, "ATL": {"RB": 1.02, "WR": 1.00, "TE": 0.98},
    "HOU": {"RB": 1.05, "WR": 1.03, "TE": 1.00},
    # Weak
    "GB": {"RB": 1.10, "WR": 1.12, "TE": 1.15}, "MIN": {"RB": 1.12, "WR": 1.10, "TE": 1.12},
    "ARI": {"RB": 1.15, "WR": 1.18, "TE": 1.20}, "LV": {"RB": 1.18, "WR": 1.20, "TE": 1.22},
    "IND": {"RB": 1.20, "WR": 1.22, "TE": 1.25}, "CHI": {"RB": 1.22, "WR": 1.25, "TE": 1.28},
    "NO": {"RB": 1.25, "WR": 1.28, "TE": 1.30}, "NE": {"RB": 1.28, "WR": 1.30, "TE": 1.32},
    "TEN": {"RB": 1.30, "WR": 1.32, "TE": 1.35},
    # Default
    "LAR": {"RB": 1.0, "WR": 1.0, "TE": 1.0}, "JAX": {"RB": 1.0, "WR": 1.0, "TE": 1.0},
    "DEN": {"RB": 1.0, "WR": 1.0, "TE": 1.0}, "PIT": {"RB": 1.0, "WR": 1.0, "TE": 1.0},
    "WAS": {"RB": 1.0, "WR": 1.0, "TE": 1.0}, "NYG": {"RB": 1.0, "WR": 1.0, "TE": 1.0},
    "NYJ": {"RB": 1.0, "WR": 1.0, "TE": 1.0}, "CAR": {"RB": 1.0, "WR": 1.0, "TE": 1.0},
}

# ANSI Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

# =============================================================================
# TRACKING SYSTEM
# =============================================================================

def load_tracking_data():
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'picks': []}
    return {'picks': []}

def save_tracking_data(data):
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def track_new_picks(recommendations):
    """Track new picks that aren't already pending/completed"""
    data = load_tracking_data()
    existing_ids = set(p['pick_id'] for p in data['picks'])
    
    new_picks_count = 0
    current_time = datetime.now(pytz.timezone('US/Eastern')).isoformat()
    
    for rec in recommendations:
        # ATD usually valid for the whole game, so ID is player + date
        game_date = rec['commence_time'][:10]
        pick_id = f"{rec['player']}_ATD_{game_date}"
        
        if pick_id not in existing_ids:
            new_pick = {
                'pick_id': pick_id,
                'player': rec['player'],
                'pick_type': 'Anytime TD',
                'bet_type': 'over', # ATD is implicitly an 'over 0.5'
                'prop_line': 0.5,
                'odds': rec['best_odds'],
                'opening_odds': rec['best_odds'],
                'bookmaker': rec.get('best_book', 'Generic'),
                'edge': rec['edge'],
                'ai_score': rec['model_prob'] * 10, # Proxy score
                'ev': rec['ev'],
                'kelly_pct': rec['kelly_pct'],
                'team': rec['team'],
                'opponent': rec['opponent'],
                'game_date': rec['commence_time'],
                'game_time': rec['commence_time'],
                'date_placed': current_time,
                'status': 'pending',
                'result': None,
                'profit_loss': 0,
                'bet_size_units': rec.get('kelly_pct', 0.05) * 100 # Tracking unit size? Or just 1.0
            }
            # For consistent tracking, we'll assume 1 unit plays or fraction of bankroll logic?
            # Let's stick to simple units for display, but store kelly for detail.
            new_pick['bet_size_units'] = 1.0 
            
            data['picks'].append(new_pick)
            new_picks_count += 1
            existing_ids.add(pick_id)
            
    if new_picks_count > 0:
        save_tracking_data(data)
        print(f"{Colors.GREEN}✓ Tracked {new_picks_count} new picks{Colors.END}")

def backfill_profit_loss():
    tracking_data = load_tracking_data()
    updated = 0
    for pick in tracking_data['picks']:
        if pick.get('status') in ['win', 'loss'] and 'profit_loss' not in pick:
            odds = pick.get('opening_odds') or pick.get('odds', -110)
            if pick.get('status') == 'win':
                if odds > 0: profit_loss = int(odds)
                else: profit_loss = int((100.0 / abs(odds)) * 100)
            else:
                profit_loss = -100
            pick['profit_loss'] = profit_loss
            updated += 1
    if updated > 0: save_tracking_data(tracking_data)

def calculate_tracking_stats(data):
    picks = data.get('picks', [])
    completed = [p for p in picks if p['status'] in ['win', 'loss']]
    
    wins = sum(1 for p in completed if p['status'] == 'win')
    
    total_profit_cents = 0
    for p in completed:
        val = p.get('profit_loss')
        if val is not None: total_profit_cents += val
        
    
    total_profit_units = total_profit_cents / 100.0
    roi_pct = (total_profit_units / len(completed) * 100) if completed else 0.0
    win_rate = (wins / len(completed) * 100) if completed else 0.0
    
    # CLV Calc
    clv_wins = 0
    clv_total = 0
    for p in completed:
        opening = p.get('opening_odds', 0)
        closing = p.get('closing_odds', p.get('latest_odds', 0))
        if opening != 0 and closing != 0:
            clv_total += 1
            if opening > closing:
                clv_wins += 1
                
    clv_rate = (clv_wins / clv_total * 100) if clv_total > 0 else 0.0
    
    # --- Daily Stats ---
    from datetime import datetime, timedelta
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    today_str = now_et.strftime('%Y-%m-%d')
    yesterday_str = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def calc_daily(target_date):
        d_picks = []
        for p in completed:
            gt = p.get('game_time', '')
            if not gt: continue
            try:
                dt_utc = datetime.fromisoformat(gt.replace('Z', '+00:00'))
                dt_et = dt_utc.astimezone(et_tz)
                if dt_et.strftime('%Y-%m-%d') == target_date:
                    d_picks.append(p)
            except:
                continue
        
        d_wins = sum(1 for p in d_picks if p.get('status') == 'win')
        d_losses = sum(1 for p in d_picks if p.get('status') == 'loss')
        d_profit_cents = 0
        for p in d_picks:
            val = p.get('profit_loss')
            if val is not None: d_profit_cents += val
            else:
                odds = p.get('opening_odds') or p.get('odds', -110)
                if p.get('status') == 'win':
                    if odds > 0: d_profit_cents += int(odds)
                    else: d_profit_cents += int((100.0 / abs(odds)) * 100)
                else: d_profit_cents -= 100
        
        d_profit = d_profit_cents / 100.0
        d_roi = (d_profit / len(d_picks) * 100) if d_picks else 0.0
        return {'record': f"{d_wins}-{d_losses}", 'profit': d_profit, 'roi': d_roi}
    
    return {
        'wins': wins, 'losses': len(completed) - wins, 'total': len(completed),
        'win_rate': round(win_rate, 1),
        'profit': round(total_profit_units, 2),
        'roi': round(roi_pct, 1),
        'clv_rate': round(clv_rate, 1),
        'today': calc_daily(today_str),
        'yesterday': calc_daily(yesterday_str)
    }

def calculate_recent_performance(picks_list, count):
    completed = [p for p in picks_list if p.get('status', '').lower() in ['win', 'loss']]
    completed.sort(key=lambda x: x.get('game_time', ''), reverse=True)
    recent = completed[:count]
    
    wins = sum(1 for p in recent if p.get('status') == 'win')
    losses = sum(1 for p in recent if p.get('status') == 'loss')
    
    p_cents = sum(p.get('profit_loss', 0) for p in recent)
    p_units = p_cents / 100.0
    
    return {
        'record': f"{wins}-{losses}",
        'profit': p_units
    }

def calculate_player_stats(player_name, tracking_data):
    if not tracking_data: return None
    player_picks = [p for p in tracking_data['picks'] 
                   if p.get('player') == player_name and p.get('status') in ['win', 'loss']]
    if not player_picks: return None
    
    wins = sum(1 for p in player_picks if p['status'] == 'win')
    losses = sum(1 for p in player_picks if p['status'] == 'loss')
    p_cents = sum(p.get('profit_loss', 0) for p in player_picks)
    roi = (p_cents/100.0) / len(player_picks) * 100
    
    return {'season_record': f"{wins}-{losses}", 'player_roi': round(roi, 1)}

# =============================================================================
# CORE UTILS
# =============================================================================

def american_to_decimal(american_odds):
    return (american_odds / 100) + 1 if american_odds > 0 else (100 / abs(american_odds)) + 1

def american_to_implied_prob(american_odds):
    return 100 / (american_odds + 100) if american_odds > 0 else abs(american_odds) / (abs(american_odds) + 100)

def calculate_kelly_bet_size(prob, odds, fraction=KELLY_FRACTION):
    decimal_odds = american_to_decimal(odds)
    q = 1 - prob
    b = decimal_odds - 1
    if prob <= 0 or b <= 0: return 0
    kelly = (prob * b - q) / b
    return max(0, min(kelly * fraction, 0.05)) # Cap at 5%

def calculate_expected_value(prob, odds):
    # EV = (Prob_Win * Profit) - (Prob_Loss * Bet_Size)
    # Using bet size of 1 unit
    decimal_odds = american_to_decimal(odds)
    profit = decimal_odds - 1
    prob_loss = 1 - prob
    
    ev = (prob * profit) - (prob_loss * 1)
    return ev

# =============================================================================
# DATA LOGIC
# =============================================================================

def fetch_atd_odds():
    """Fetch both Anytime TD and First TD odds from sportsbooks"""
    print(f"\n💰 Fetching TD odds from sportsbooks (ATTD + First TD)...")
    if not API_KEY: return []
    
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events"
    try:
        r = requests.get(url, params={'apiKey': API_KEY}, timeout=10)
        r.raise_for_status()
        raw_events = r.json()
        
        # Filter past games
        events = []
        current_time_utc = datetime.now(pytz.utc)
        for event in raw_events:
            try:
                ct = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
                if ct > current_time_utc:
                    events.append(event)
            except: 
                continue
                
        print(f"  Found {len(events)} upcoming games (filtered from {len(raw_events)})")
    except Exception as e:
        print(f"{Colors.RED}Odds fetch failed: {e}{Colors.END}")
        return []
        
    all_offers = []
    
    # TD market types to fetch
    td_markets = ['player_anytime_td', 'player_first_td']
    
    for i, event in enumerate(events):
         game_id = event['id']
         commence_time = event['commence_time']
         home = event['home_team']
         away = event['away_team']
         
         print(f"  [{i+1}/{len(events)}] {away[:15]} @ {home[:15]}...", end=' ', flush=True)
         
         # Fetch specific odds - use single market (comma-separated returns 422)
         o_url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/{game_id}/odds"
         try:
             orsp = requests.get(o_url, params={
                 'apiKey': API_KEY, 
                 'regions': 'us', 
                 'markets': 'player_anytime_td',  # Single market only
                 'oddsFormat': 'american'
             }, timeout=10)
             if orsp.status_code != 200:
                 print(f"Skip (status {orsp.status_code})")
                 continue
             odata = orsp.json()
             
             game_offers = 0
             for book in odata.get('bookmakers', []):
                 bk_name = book['title']
                 for m in book.get('markets', []):
                     market_key = m['key']
                     if market_key in td_markets:
                         market_type = 'ATTD' if market_key == 'player_anytime_td' else 'First TD'
                         for out in m['outcomes']:
                             if out['name'] == 'Over': continue
                             name = out['description'] if 'description' in out else out['name']
                             
                             all_offers.append({
                                 'player': name,
                                 'bookmaker': bk_name,
                                 'odds': out['price'],
                                 'market_type': market_type,
                                 'team': 'UNK',
                                 'home_team': home,
                                 'away_team': away,
                                 'commence_time': commence_time
                             })
                             game_offers += 1
             print(f"{game_offers} offers")
         except Exception as e:
             print(f"Error: {e}")
             continue
         
    attd_count = sum(1 for o in all_offers if o.get('market_type') == 'ATTD')
    first_td_count = sum(1 for o in all_offers if o.get('market_type') == 'First TD')
    print(f"  Fetched {attd_count} ATTD offers, {first_td_count} First TD offers")
    return all_offers

def load_player_data_manual():
    """
    Expanded player database for TD props (Dec 20, 2024)
    Includes 45+ players with TD scoring potential
    """
    players = [
        # === ELITE RBs (High TD Volume) ===
        {"name": "Christian McCaffrey", "pos": "RB", "team": "SF", "tds": 14, "games": 8, "rz_share": 0.45},
        {"name": "Derrick Henry", "pos": "RB", "team": "BAL", "tds": 13, "games": 10, "rz_share": 0.42},
        {"name": "Saquon Barkley", "pos": "RB", "team": "PHI", "tds": 11, "games": 10, "rz_share": 0.38},
        {"name": "Bijan Robinson", "pos": "RB", "team": "ATL", "tds": 11, "games": 10, "rz_share": 0.36},
        {"name": "Jahmyr Gibbs", "pos": "RB", "team": "DET", "tds": 11, "games": 10, "rz_share": 0.30},
        {"name": "Josh Jacobs", "pos": "RB", "team": "GB", "tds": 10, "games": 10, "rz_share": 0.35},
        {"name": "Alvin Kamara", "pos": "RB", "team": "NO", "tds": 9, "games": 10, "rz_share": 0.32},
        {"name": "Kyren Williams", "pos": "RB", "team": "LAR", "tds": 8, "games": 10, "rz_share": 0.34},
        {"name": "James Cook", "pos": "RB", "team": "BUF", "tds": 8, "games": 10, "rz_share": 0.30},
        {"name": "Jonathan Taylor", "pos": "RB", "team": "IND", "tds": 7, "games": 9, "rz_share": 0.35},
        {"name": "De'Von Achane", "pos": "RB", "team": "MIA", "tds": 7, "games": 8, "rz_share": 0.28},
        {"name": "Aaron Jones", "pos": "RB", "team": "MIN", "tds": 6, "games": 10, "rz_share": 0.25},
        {"name": "Tony Pollard", "pos": "RB", "team": "TEN", "tds": 6, "games": 10, "rz_share": 0.30},
        {"name": "Isiah Pacheco", "pos": "RB", "team": "KC", "tds": 5, "games": 8, "rz_share": 0.30},
        {"name": "Breece Hall", "pos": "RB", "team": "NYJ", "tds": 5, "games": 10, "rz_share": 0.28},
        {"name": "David Montgomery", "pos": "RB", "team": "DET", "tds": 8, "games": 10, "rz_share": 0.30},
        {"name": "Rhamondre Stevenson", "pos": "RB", "team": "NE", "tds": 5, "games": 10, "rz_share": 0.32},
        {"name": "Joe Mixon", "pos": "RB", "team": "HOU", "tds": 6, "games": 9, "rz_share": 0.30},
        
        # === ELITE WRs (TD Threats) ===
        {"name": "Ja'Marr Chase", "pos": "WR", "team": "CIN", "tds": 9, "games": 10, "rz_share": 0.30},
        {"name": "Amon-Ra St. Brown", "pos": "WR", "team": "DET", "tds": 9, "games": 10, "rz_share": 0.28},
        {"name": "CeeDee Lamb", "pos": "WR", "team": "DAL", "tds": 6, "games": 10, "rz_share": 0.25},
        {"name": "Tyreek Hill", "pos": "WR", "team": "MIA", "tds": 6, "games": 10, "rz_share": 0.22},
        {"name": "A.J. Brown", "pos": "WR", "team": "PHI", "tds": 6, "games": 9, "rz_share": 0.22},
        {"name": "Justin Jefferson", "pos": "WR", "team": "MIN", "tds": 5, "games": 10, "rz_share": 0.20},
        {"name": "Davante Adams", "pos": "WR", "team": "NYJ", "tds": 5, "games": 10, "rz_share": 0.22},
        {"name": "Stefon Diggs", "pos": "WR", "team": "HOU", "tds": 5, "games": 10, "rz_share": 0.20},
        {"name": "DeVonta Smith", "pos": "WR", "team": "PHI", "tds": 4, "games": 10, "rz_share": 0.18},
        {"name": "Mike Evans", "pos": "WR", "team": "TB", "tds": 6, "games": 10, "rz_share": 0.25},
        {"name": "Chris Godwin", "pos": "WR", "team": "TB", "tds": 5, "games": 8, "rz_share": 0.22},
        {"name": "Puka Nacua", "pos": "WR", "team": "LAR", "tds": 4, "games": 8, "rz_share": 0.20},
        {"name": "Nico Collins", "pos": "WR", "team": "HOU", "tds": 5, "games": 8, "rz_share": 0.25},
        {"name": "Malik Nabers", "pos": "WR", "team": "NYG", "tds": 4, "games": 10, "rz_share": 0.22},
        {"name": "Jaylen Waddle", "pos": "WR", "team": "MIA", "tds": 4, "games": 10, "rz_share": 0.18},
        {"name": "DK Metcalf", "pos": "WR", "team": "SEA", "tds": 4, "games": 10, "rz_share": 0.20},
        {"name": "Terry McLaurin", "pos": "WR", "team": "WAS", "tds": 5, "games": 10, "rz_share": 0.22},
        {"name": "Keenan Allen", "pos": "WR", "team": "CHI", "tds": 3, "games": 10, "rz_share": 0.18},
        {"name": "Ladd McConkey", "pos": "WR", "team": "LAC", "tds": 4, "games": 10, "rz_share": 0.20},
        
        # === ELITE TEs ===
        {"name": "George Kittle", "pos": "TE", "team": "SF", "tds": 7, "games": 9, "rz_share": 0.23},
        {"name": "Travis Kelce", "pos": "TE", "team": "KC", "tds": 6, "games": 10, "rz_share": 0.20},
        {"name": "Trey McBride", "pos": "TE", "team": "ARI", "tds": 4, "games": 10, "rz_share": 0.18},
        {"name": "Mark Andrews", "pos": "TE", "team": "BAL", "tds": 4, "games": 10, "rz_share": 0.18},
        {"name": "Brock Bowers", "pos": "TE", "team": "LV", "tds": 3, "games": 10, "rz_share": 0.15},
        {"name": "Sam LaPorta", "pos": "TE", "team": "DET", "tds": 4, "games": 10, "rz_share": 0.15},
        {"name": "Evan Engram", "pos": "TE", "team": "JAX", "tds": 3, "games": 10, "rz_share": 0.15},
        {"name": "Dallas Goedert", "pos": "TE", "team": "PHI", "tds": 3, "games": 9, "rz_share": 0.12},
    ]
    return players

def analyze_opportunities(odds_list, players_stats):
    """
    Analyze ALL players with TD odds - not just those in manual database.
    Uses odds-based probability estimation for players without stats.
    """
    # Map known stats (optional enhancement)
    stat_map = {n['name']: n for n in players_stats}
    
    opportunities = []
    
    # Filter past games first
    current_time = datetime.now(pytz.utc)
    valid_odds = []
    
    for o in odds_list:
        ct_str = o.get('commence_time')
        if ct_str:
            try:
                ct_dt = datetime.fromisoformat(ct_str.replace('Z', '+00:00'))
                if ct_dt < current_time:
                    continue
            except:
                pass
        valid_odds.append(o)
    
    # Group odds by player to find best price
    grouped = {}
    for o in valid_odds:
        p = o['player']
        if p not in grouped: grouped[p] = []
        grouped[p].append(o)
    
    print(f"  Analyzing {len(grouped)} unique players...")
        
    for player_name, offers in grouped.items():
        # Determine best odds across all books
        best_offer = max(offers, key=lambda x: x['odds'])
        best_odds = best_offer['odds']
        
        # Skip extreme longshots (+2000 or worse) and heavy favorites (-200 or better)
        if best_odds > 2000 or best_odds < -200:
            continue
        
        home = best_offer['home_team'] 
        away = best_offer['away_team']
        matchup = f"{away} @ {home}"
        
        # Get stats if available, otherwise estimate from position/odds
        stats = stat_map.get(player_name)
        
        if stats:
            # Use known stats
            team = stats['team']
            pos = stats['pos']
            td_rate = (stats['tds'] / max(1, stats['games']))
            rz_share = stats['rz_share']
            
            # Calculate model probability
            raw_prob = (td_rate * 0.4 + rz_share * 0.6)
            
        else:
            # DYNAMIC ESTIMATION: Use odds + book consensus for unknown players
            # The key insight: if MULTIPLE books offer similar odds, the true prob is close to implied
            # But if one book is an outlier, there's potential value
            
            team = "UNK"
            pos = "UNK"
            
            # Calculate consensus implied probability from all offers
            all_implied = [american_to_implied_prob(o['odds']) for o in offers]
            consensus_prob = sum(all_implied) / len(all_implied)
            
            # The best odds will have lower implied prob than consensus
            best_implied = american_to_implied_prob(best_odds)
            
            # Model probability = consensus (market wisdom) with slight boost for discrepancy
            # If best odds are significantly better than consensus, trust market less
            prob_boost = max(0, consensus_prob - best_implied) * 0.5  # Half-credit the discrepancy
            raw_prob = consensus_prob + prob_boost
            
            rz_share = 0.0  # Unknown
        
        # Apply opponent adjustment if we know team
        opponent = away if team in home or home.startswith(team[:3]) else home
        def_ratings = DEFENSE_TD_RATINGS.get(opponent[:3].upper(), {"RB": 1.0, "WR": 1.0, "TE": 1.0})
        pos_mult = def_ratings.get(pos, 1.0)
        
        # Final model probability
        model_prob = min(0.65, max(0.08, raw_prob * pos_mult))  # Clamp to realistic range
        
        implied_val = american_to_implied_prob(best_odds)
        edge = model_prob - implied_val
        ev = calculate_expected_value(model_prob, best_odds)
        kelly = calculate_kelly_bet_size(model_prob, best_odds)
        
        # Lower threshold for unknown players to catch more value
        min_edge = MIN_EDGE_THRESHOLD if stats else 0.03  # 3% edge for unknowns
        
        if ev > 0 and edge >= min_edge:
            opportunities.append({
                'player': player_name,
                'team': team,
                'opponent': opponent,
                'pos': pos,
                'best_odds': best_odds,
                'best_book': best_offer['bookmaker'],
                'model_prob': round(model_prob, 3),
                'implied_prob': round(implied_val, 3),
                'edge': round(edge, 3),
                'ev': round(ev, 3),
                'kelly_pct': round(kelly, 3),
                'commence_time': best_offer['commence_time'],
                'matchup': matchup,
                'num_books': len(offers)  # Track how many books have this player
            })
    
    # Sort by EV (best plays first)
    opportunities.sort(key=lambda x: x['ev'], reverse=True)
    
    print(f"  Found {len(opportunities)} +EV opportunities")
    return opportunities

# =============================================================================
# HTML GENERATION (CourtSide Style)
# =============================================================================

def get_team_logo(team_abbr):
    # Basic mapping
    mapping = {'SF': 'sf', 'BAL': 'bal', 'PHI': 'phi', 'KC': 'kc', 
               'DET': 'det', 'MIA': 'mia', 'CIN': 'cin', 'BUF': 'buf'} 
    # Fallback usually works with lower case
    code = mapping.get(team_abbr, team_abbr.lower())
    return f"https://a.espncdn.com/i/teamlogos/nfl/500/{code}.png"

def format_date(iso_str):
    try:
        dt = datetime.fromisoformat(str(iso_str).replace('Z', '+00:00'))
        return dt.strftime('%a, %b %d • %-I:%M %p ET')
    except: return iso_str

def generate_html_output(plays, stats, tracking_data):
    # Sort securely
    plays.sort(key=lambda x: x.get('edge', 0), reverse=True)
    
    # Tracking Stats
    completed = [p for p in tracking_data['picks'] if p.get('status') in ['win', 'loss']]
    last_10 = calculate_recent_performance(completed, 10)
    last_20 = calculate_recent_performance(completed, 20)
    last_50 = calculate_recent_performance(completed, 50)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CourtSide Analytics - NFL ATD</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #121212; --bg-card: #1e1e1e; --bg-card-secondary: #2a2a2a;
            --text-primary: #ffffff; --text-secondary: #b3b3b3;
            --accent-green: #4ade80; --accent-red: #f87171; --accent-gold: #fbbf24;
            --border-color: #333333;
        }}
        body {{ margin:0; padding:20px; font-family:'Inter', sans-serif; background-color:var(--bg-main); color:var(--text-primary); }}
        .container {{ max-width:800px; margin:0 auto; }}
        header {{ display:flex; justify-content:space-between; border-bottom:1px solid var(--border-color); padding-bottom:15px; margin-bottom:25px; }}
        h1 {{ font-size:24px; font-weight:700; margin:0; }}
        .header-stats {{ text-align:right; }}
        .prop-card {{ background-color:var(--bg-card); border-radius:16px; border:1px solid var(--border-color); margin-bottom:20px; overflow:hidden; }}
        .card-header {{ background-color:var(--bg-card-secondary); padding:15px 20px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-color); }}
        .team-logo {{ width:45px; height:45px; border-radius:50%; object-fit:contain; }}
        .card-body {{ padding:20px; }}
        .metrics-grid {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin-top:15px; }}
        .metric-item {{ background:var(--bg-main); padding:10px; border-radius:8px; text-align:center; }}
        .metric-val {{ font-weight:700; font-size:16px; }}
        .metric-lbl {{ font-size:11px; color:var(--text-secondary); text-transform:uppercase; }}
        .txt-green {{ color:var(--accent-green); }}
        .txt-gold {{ color:var(--accent-gold); }}
        .txt-red {{ color:var(--accent-red); }}
        .bet-main {{ font-size:22px; font-weight:800; }}
        .odds-badge {{ font-size:18px; color:var(--text-secondary); margin-left:8px; }}
        .player-stats {{ background:var(--bg-card-secondary); padding:10px; border-radius:8px; display:flex; justify-content:space-between; margin-top:15px; border:1px solid var(--border-color); }}
        .section-title {{ font-size:18px; margin:30px 0 15px 0; font-weight:600; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>CourtSide Analytics</h1>
            <div style="color:var(--text-secondary); margin-top:5px;">NFL Anytime Touchdown • Sharp +EV</div>
        </div>
        <div class="header-stats">
            <div style="font-size:11px; color:var(--text-secondary);">SEASON RECORD</div>
            <div style="font-size:20px; font-weight:700; color:var(--accent-green);">
                {stats['wins']}-{stats['losses']} ({stats['win_rate']}%)
            </div>
            <div style="color:{'var(--accent-green)' if stats['profit'] > 0 else 'var(--accent-red)'}">
                {stats['profit']:+.2f}u
            </div>
            <div style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 4px;">CLV: {stats.get('clv_rate', 0)}%</div>
        </div>
    </header>

    <div class="section-title">🔥 Top ATD Picks</div>
"""
    
    for play in plays:
        p_stats = calculate_player_stats(play['player'], tracking_data)
        roi_str = f"{p_stats['player_roi']:+.1f}%" if p_stats else "N/A"
        rec_str = p_stats['season_record'] if p_stats else "0-0"
        
        edge_val = play.get('edge', 0.0)
        
        sharp_tag = ""
        if edge_val > SHARP_EDGE_THRESHOLD:
            sharp_tag = "<span style='background:#064e3b; color:#34d399; padding:2px 6px; border-radius:4px; font-size:10px; margin-left:8px;'>SHARP</span>"
            
        play_pos = play.get('pos', 'RB/WR') # Default pos
        play_matchup = play.get('matchup', '')
        play_time = play.get('commence_time', '')
        play_odds = play.get('best_odds', play.get('odds', '-110'))
        play_book = play.get('best_book', play.get('bookmaker', 'Sportsbook'))
        
        model_prob = play.get('model_prob', 0.0)
        implied_prob = play.get('implied_prob', 0.0)
        kelly_pct = play.get('kelly_pct', 0.0)
        
        html += f"""
        <div class="prop-card">
            <div class="card-header">
                <div style="display:flex; align-items:center; gap:12px;">
                    <img src="{get_team_logo(play.get('team', 'NFL'))}" class="team-logo">
                    <div>
                        <div style="font-size:18px; font-weight:700;">{play['player']} <span style="font-size:12px; color:var(--text-secondary);">({play_pos})</span>{sharp_tag}</div>
                        <div style="font-size:13px; color:var(--text-secondary);">{play_matchup}</div>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:12px; font-weight:500; background:#333; padding:4px 8px; border-radius:4px;">{format_date(play_time)}</div>
                </div>
            </div>
            <div class="card-body">
                <div class="bet-main">
                    <span class="txt-gold">ANYTIME TD</span>
                    <span class="odds-badge">{play_odds}</span>
                    <span style="font-size:12px; color:var(--text-secondary); margin-left:10px;">@ {play_book}</span>
                </div>
                
                <div class="metrics-grid">
                    <div class="metric-item">
                        <div class="metric-lbl">Model Prob</div>
                        <div class="metric-val">{(model_prob*100):.1f}%</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-lbl">Implied</div>
                        <div class="metric-val">{(implied_prob*100):.1f}%</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-lbl">Edge</div>
                        <div class="metric-val txt-green">+{edge_val:.1%}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-lbl">Kelly</div>
                        <div class="metric-val txt-gold">{(kelly_pct*100):.1f}%</div>
                    </div>
                </div>
                
                <div class="player-stats">
                    <div style="text-align:center; flex:1;">
                        <div class="metric-lbl">Player Season</div>
                        <div style="font-weight:700;">{rec_str}</div>
                    </div>
                    <div style="width:1px; background:var(--border-color);"></div>
                    <div style="text-align:center; flex:1;">
                        <div class="metric-lbl">Player ROI</div>
                        <div style="font-weight:700; color:{'var(--accent-green)' if p_stats and p_stats['player_roi']>0 else 'var(--text-primary)'};">{roi_str}</div>
                    </div>
                </div>
            </div>
        </div>
        """
        
    
    # --- Daily Performance Tracking HTML ---
    daily_tracking_html = ""
    if stats and 'today' in stats:
        t_stats = stats['today']
        y_stats = stats.get('yesterday', {'record':'0-0', 'profit':0, 'roi':0})
        
        def get_track_class(val): return 'var(--accent-green)' if val > 0 else 'var(--accent-red)'
        
        daily_tracking_html = f"""
        <div class="section-title">📅 Daily Performance</div>
        <div class="metrics-grid" style="grid-template-columns: repeat(2, 1fr);">
            <!-- Today -->
            <div class="prop-card" style="padding: 1rem; margin:0;">
                <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">TODAY</div>
                <div style="text-align:center;">
                    <div style="font-weight:700; font-size:1.1rem;">{t_stats['record']}</div>
                    <div style="color:{get_track_class(t_stats['profit'])}; font-weight:700;">{t_stats['profit']:+.1f}u</div>
                    <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">{t_stats['roi']:.1f}% ROI</div>
                </div>
            </div>
            <!-- Yesterday -->
            <div class="prop-card" style="padding: 1rem; margin:0;">
                <div style="font-size:0.75rem; color:var(--text-secondary); text-align:center; margin-bottom:0.5rem;">YESTERDAY</div>
                <div style="text-align:center;">
                    <div style="font-weight:700; font-size:1.1rem;">{y_stats['record']}</div>
                    <div style="color:{get_track_class(y_stats['profit'])}; font-weight:700;">{y_stats['profit']:+.1f}u</div>
                     <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">{y_stats['roi']:.1f}% ROI</div>
                </div>
            </div>
        </div>
        """
        html += daily_tracking_html

    html += f"""
    <div class="section-title">📊 Recent Performance</div>
    <div class="metrics-grid" style="grid-template-columns:repeat(3,1fr);">
        <div class="prop-card" style="padding:15px; margin:0; text-align:center;">
            <div class="metric-lbl">Last 10</div>
            <div style="font-size:14px; font-weight:700; margin-top:5px;">{last_10['record']}</div>
            <div style="color:{'var(--accent-green)' if last_10['profit']>0 else 'var(--accent-red)'}; font-weight:700;">{last_10['profit']:+.2f}u</div>
        </div>
        <div class="prop-card" style="padding:15px; margin:0; text-align:center;">
            <div class="metric-lbl">Last 20</div>
            <div style="font-size:14px; font-weight:700; margin-top:5px;">{last_20['record']}</div>
            <div style="color:{'var(--accent-green)' if last_20['profit']>0 else 'var(--accent-red)'}; font-weight:700;">{last_20['profit']:+.2f}u</div>
        </div>
        <div class="prop-card" style="padding:15px; margin:0; text-align:center;">
            <div class="metric-lbl">Last 50</div>
            <div style="font-size:14px; font-weight:700; margin-top:5px;">{last_50['record']}</div>
            <div style="color:{'var(--accent-green)' if last_50['profit']>0 else 'var(--accent-red)'}; font-weight:700;">{last_50['profit']:+.2f}u</div>
        </div>
    </div>
</div>
</body>
</html>
    """
    
    with open(OUTPUT_HTML, 'w') as f: f.write(html)
    print(f"\n✅ HTML saved: {OUTPUT_HTML}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    print(f"{Colors.BOLD}🏈 NFL Anytime TD Model - CourtSide Analytics{Colors.END}")
    
    # 1. Grade picks
    print(f"\n{Colors.CYAN}--- Grading Pending Picks ---{Colors.END}")
    try:
        updated = grade_props_tracking_file(TRACKING_FILE, stat_kind='anytime_td')
        print(f"Graded {updated} picks.")
        backfill_profit_loss()
    except Exception as e:
        print(f"{Colors.YELLOW}Grading skipped/failed: {e}{Colors.END}")
        
    # 2. Analyze
    odds = fetch_atd_odds()
    stats = load_player_data_manual()
    
    if not odds:
        print("No odds available.")
        # Still gen html for tracking
        t_data = load_tracking_data()
        ts = calculate_tracking_stats(t_data)
        generate_html_output([], ts, t_data)
        return
        
    plays = analyze_opportunities(odds, stats)
    
    print(f"\nFound {len(plays)} value plays.")
    
    # Track
    track_new_picks(plays)
    
    # Stats & Output
    t_data = load_tracking_data()
    ts = calculate_tracking_stats(t_data)
    generate_html_output(plays, ts, t_data)

if __name__ == "__main__":
    main()
