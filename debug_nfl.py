import nflreadpy as nfl
import json
import os
import pandas as pd

def debug_nfl_sched():
    print("Loading stats/schedules for 2025...")
    sched = nfl.load_schedules([2025])
    try:
        sched = sched.to_pandas()
    except:
        pass
        
    print(f"Schedule Columns: {list(sched.columns)}")
    print(f"Sample Gamedays: {list(sched['gameday'].head().astype(str))}")
    
    # Check today's games
    today = "2025-12-21"
    
    # Check stats for those games
    print("\nLoading player stats for 2025...")
    stats = nfl.load_player_stats([2025])
    try:
        stats_df = stats.to_pandas()
    except:
        stats_df = stats
        
    print(f"Stats Columns: {list(stats_df.columns)}")
    
    week_16_stats = stats_df[stats_df['week'] == 16]
    print(f"Total stats rows for Week 16: {len(week_16_stats)}")
    
    if not week_16_stats.empty:
        # Check for Josh Allen
        josh = week_16_stats[week_16_stats['player_display_name'].str.contains('Josh Allen', na=False)]
        if not josh.empty:
            print("Found Josh Allen stats!")
            print(josh[['player_display_name', 'team', 'passing_yards']].to_dict())
        else:
            print("Josh Allen not found.")
            
        # Check for Joe Burrow
        joe = week_16_stats[week_16_stats['player_display_name'].str.contains('Burrow', na=False)]
        if not joe.empty:
            print("Found Joe Burrow stats!")
            print(joe[['player_display_name', 'team', 'passing_yards']].to_dict())
        else:
            print("Joe Burrow not found.")
    else:
        print("No stats found for Week 16 yet.")

if __name__ == "__main__":
    debug_nfl_sched()
