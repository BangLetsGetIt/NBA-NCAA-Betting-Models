
import json
import os
import pytz
from datetime import datetime, timedelta

SCRIPT_DIR = "/Users/rico/sports-models/nba"
TRACKING_FILE = os.path.join(SCRIPT_DIR, "nba_picks_tracking.json")

def load_picks_tracking():
    with open(TRACKING_FILE, 'r') as f:
        return json.load(f)

def run_debug():
    print("--- DEBUGGING DATE LOGIC ---")
    et_tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(et_tz)
    print(f"Current ET Time: {now_et}")
    
    today_str = now_et.strftime('%Y-%m-%d')
    yesterday_str = (now_et - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"Today Str: {today_str}")
    print(f"Yesterday Str: {yesterday_str}")
    
    data = load_picks_tracking()
    picks = data.get('picks', [])
    completed_picks = [p for p in picks if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    print(f"Total Completed Picks: {len(completed_picks)}")
    
    today_picks = []
    yesterday_picks = []
    
    for p in completed_picks:
        gd = p.get('game_date', '')
        if not gd: continue
        try:
            # Logic from nba_model_IMPROVED.py
            if 'Z' in gd:
                dt_utc = datetime.fromisoformat(gd.replace('Z', '+00:00'))
            else:
                dt_utc = datetime.fromisoformat(gd)
                
            dt_et = dt_utc.astimezone(et_tz)
            date_str = dt_et.strftime('%Y-%m-%d')
            
            if date_str == today_str:
                today_picks.append(p)
                print(f"FOUND TODAY PICK: {p['matchup']} ({gd})")
            elif date_str == yesterday_str:
                yesterday_picks.append(p)
        except Exception as e:
            print(f"Error parsing date {gd}: {e}")
            
    print(f"Today's Picks Count: {len(today_picks)}")
    print(f"Yesterday's Picks Count: {len(yesterday_picks)}")
    
    # Check pending picks dates
    pending_picks = [p for p in picks if p.get('status', '').lower() == 'pending']
    print(f"Pending Picks Count: {len(pending_picks)}")
    for p in pending_picks:
        gd = p.get('game_date', '')
        try:
            if 'Z' in gd: dt_utc = datetime.fromisoformat(gd.replace('Z', '+00:00'))
            else: dt_utc = datetime.fromisoformat(gd)
            dt_et = dt_utc.astimezone(et_tz)
            print(f"  Pending: {p['matchup']} - Game Date: {gd} -> ET: {dt_et}")
        except:
            pass

if __name__ == "__main__":
    run_debug()
