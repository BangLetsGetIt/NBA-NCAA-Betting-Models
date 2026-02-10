
import sys
import os
import json
from datetime import datetime
import pytz

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Monkeypatch grading logic to filter dates
import nba_points_props_model

original_grade = nba_points_props_model.grade_pending_picks

def patch_grade_pending_picks():
    # We will manually load tracking data, filter for recent dates, and then run the original logic logic?
    # No, grade_pending_picks loads from file.
    # We can modify the `pending_picks` list by mocking `load_tracking_data`?
    
    real_load = nba_points_props_model.load_tracking_data
    
    def mocked_load():
        data = real_load()
        # Filter pending picks to only include 2026 ones
        picks = data.get('picks', [])
        
        # Keep non-pending as is
        # Keep pending ONLY if date >= 2026-01-20
        
        filtered_picks = []
        for p in picks:
            if p.get('status') != 'pending':
                filtered_picks.append(p)
                continue
                
            game_time = p.get('game_time', '')
            if '2026-01' in game_time:
                 filtered_picks.append(p)
            # Else ignore old pending picks for this run
        
        data['picks'] = filtered_picks
        return data
        
    # We also need to save back to the REAL file, but preserving the ignored picks?
    # If we filter them out of 'picks', save_tracking_data will delete them!
    # So checking inside the loop is better.
    # But I can't edit the loop without editing code.
    pass

# Alternative: Write a custom grader loop here using the imported functions
from nba_points_props_model import load_tracking_data, save_tracking_data, fetch_all_player_stats_for_date, fetch_completed_teams_for_date, Colors

def fast_grade():
    print("🚀 FAST GRADING (Jan 2026 Only)...")
    tracking_data = load_tracking_data()
    pending_picks = [p for p in tracking_data['picks'] if p.get('status') == 'pending']
    
    # Filter for Jan 2026, starting from 21st
    target_picks = [p for p in pending_picks if '2026-01' in p.get('game_time', '') and int(p.get('game_time', '').split('T')[0].split('-')[-1]) >= 21]
    
    if not target_picks:
        print("No pending picks for Jan 2026.")
        return

    print(f"Found {len(target_picks)} pending picks for Jan 2026.")
    
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
        completed_teams = fetch_completed_teams_for_date(date_str)
        
        if not daily_stats:
            print(f"No stats for {date_str}")
            continue
            
        for pick in picks:
            player_name = pick.get('player')
            
            # Use the Alias logic (copied/imported from model handled naturally if using helper functions?)
            # Wait, the alias logic is INSIDE `grade_pending_picks` which we are re-writing here.
            # So we must RE-IMPLEMENT the alias logic here.
            
            player_key = player_name.lower()
            aliases = {
                "moe wagner": "moritz wagner",
                "mo wagner": "moritz wagner",
                "kelly oubre jr.": "kelly oubre jr", # Normalize Jr.
                "michael porter jr.": "michael porter jr",
                "c.j. mccollum": "cj mccollum",
            }
            lookup_key = aliases.get(player_key, player_key)
            
            actual_pts = daily_stats.get(lookup_key)
            
            # Fuzzy fallback
            if actual_pts is None:
                for p_name, pts in daily_stats.items():
                    p_parts = p_name.split()
                    name_parts = player_key.split()
                    if len(p_parts) >= 2 and len(name_parts) >= 2:
                        if name_parts[0] == p_parts[0] and name_parts[-1] == p_parts[-1]:
                            actual_pts = pts
                            break
            
            if actual_pts is not None:
                # Grade it!
                prop_line = pick.get('prop_line')
                bet_type = pick.get('bet_type')
                if bet_type == 'over':
                    is_win = actual_pts > prop_line
                else:
                    is_win = actual_pts < prop_line
                
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
                pick['actual_pts'] = actual_pts
                pick['profit_loss'] = profit_loss
                pick['updated_at'] = datetime.now().isoformat()
                graded_count += 1
                print(f"  GRADED: {player_name} -> {status} ({actual_pts} pts)")
    
    if graded_count > 0:
        save_tracking_data(tracking_data)
        print(f"Saved {graded_count} graded picks.")

if __name__ == "__main__":
    fast_grade()
