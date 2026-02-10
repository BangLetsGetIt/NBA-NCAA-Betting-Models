
import sys
import os
import json
from datetime import datetime
import pytz

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Rebounds Model
from nba_rebounds_props_model import load_tracking_data, save_tracking_data, fetch_all_player_stats_for_date, fetch_completed_teams_for_date, Colors

def fast_grade_rebs():
    print("🚀 FAST GRADING REBOUNDS (Jan 2026 Only)...")
    tracking_data = load_tracking_data()
    pending_picks = [p for p in tracking_data['picks'] if p.get('status') == 'pending']
    
    # Filter for Jan 2026
    target_picks = [p for p in pending_picks if '2026-01' in p.get('game_time', '')]
    
    if not target_picks:
        print("No pending picks for Jan 2026.")
        return

    print(f"Found {len(target_picks)} pending rebound picks for Jan 2026.")
    
    # Group by date
    picks_by_date = {}
    for p in target_picks:
        gt_str = p.get('game_time', '')
        dt_utc = datetime.fromisoformat(gt_str.replace('Z', '+00:00'))
        dt_et = dt_utc.astimezone(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
        if dt_et not in picks_by_date:
            picks_by_date[dt_et] = []
        picks_by_date[dt_et].append(p)
        
    graded_count = 0
    
    for date_str, picks in picks_by_date.items():
        print(f"Processing {date_str}...")
        daily_stats = fetch_all_player_stats_for_date(date_str)
        # completed_teams = fetch_completed_teams_for_date(date_str) # Not needed if we trust stats? 
        # But DNP logic uses it.
        
        if not daily_stats:
            print(f"No stats for {date_str}")
            continue
            
        for pick in picks:
            player_name = pick.get('player')
            
            player_key = player_name.lower()
            aliases = {
                "moe wagner": "moritz wagner",
                "mo wagner": "moritz wagner",
                "kelly oubre jr.": "kelly oubre jr", # Normalize Jr.
                "michael porter jr.": "michael porter jr",
                "c.j. mccollum": "cj mccollum",
            }
            lookup_key = aliases.get(player_key, player_key)
            
            actual_reb = daily_stats.get(lookup_key)
            
            # Fuzzy fallback
            if actual_reb is None:
                for p_name, reb in daily_stats.items():
                    p_parts = p_name.split()
                    name_parts = player_key.split()
                    if len(p_parts) >= 2 and len(name_parts) >= 2:
                        if name_parts[0] == p_parts[0] and name_parts[-1] == p_parts[-1]:
                            actual_reb = reb
                            break
            
            if actual_reb is not None:
                # Grade it!
                prop_line = pick.get('prop_line')
                bet_type = pick.get('bet_type')
                if bet_type == 'over':
                    is_win = actual_reb > prop_line
                else:
                    is_win = actual_reb < prop_line
                
                odds = pick.get('opening_odds') or pick.get('odds', -110)
                if is_win:
                    if odds > 0: profit_loss = int(odds)
                    else: profit_loss = int((100.0 / abs(odds)) * 100)
                    status = 'win'
                    result = 'WIN'
                else:
                    profit_loss = -100
                    status = 'loss'
                    result = 'LOSS'
                
                pick['status'] = status
                pick['result'] = result
                pick['actual_reb'] = actual_reb
                pick['profit_loss'] = profit_loss
                pick['updated_at'] = datetime.now().isoformat()
                graded_count += 1
                print(f"  GRADED: {player_name} -> {status} ({actual_reb} reb)")
    
    if graded_count > 0:
        save_tracking_data(tracking_data)
        print(f"Saved {graded_count} graded rebound picks.")

if __name__ == "__main__":
    fast_grade_rebs()
