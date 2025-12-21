import json
import os
from datetime import datetime

# Define the mapping of tracking files to their stats cache and key names
CONFIG = [
    # NFL Props
    {
        'tracking': 'nfl/nfl_passing_yards_props_tracking.json',
        'cache': 'nfl/nfl_player_passing_yards_stats_cache.json',
        'keys': {'season': 'season_pass_yds_avg', 'recent': 'recent_pass_yds_avg'}
    },
    {
        'tracking': 'nfl/nfl_rushing_yards_props_tracking.json',
        'cache': 'nfl/nfl_player_rushing_yards_stats_cache.json',
        'keys': {'season': 'season_rush_yds_avg', 'recent': 'recent_rush_yds_avg'}
    },
    {
        'tracking': 'nfl/nfl_receiving_yards_props_tracking.json',
        'cache': 'nfl/nfl_player_receiving_yards_stats_cache.json',
        'keys': {'season': 'season_rec_yds_avg', 'recent': 'recent_rec_yds_avg'}
    },
    {
        'tracking': 'nfl/nfl_receptions_props_tracking.json',
        'cache': 'nfl/nfl_player_receptions_stats_cache.json',
        'keys': {'season': 'season_rec_avg', 'recent': 'recent_rec_avg'}
    },
    # NBA Props
    {
        'tracking': 'nba/nba_points_props_tracking.json',
        'cache': 'nba/nba_player_points_stats_cache.json',
        'keys': {'season': 'season_pts_avg', 'recent': 'recent_pts_avg'}
    },
    {
        'tracking': 'nba/nba_assists_props_tracking.json',
        'cache': 'nba/nba_player_assists_stats_cache.json',
        'keys': {'season': 'season_ast_avg', 'recent': 'recent_ast_avg'}
    },
    {
        'tracking': 'nba/nba_rebounds_props_tracking.json',
        'cache': 'nba/nba_player_rebounds_stats_cache.json',
        'keys': {'season': 'season_reb_avg', 'recent': 'recent_reb_avg'}
    },
    {
        'tracking': 'nba/nba_3pt_props_tracking.json',
        'cache': 'nba/nba_player_3pt_stats_cache.json',
        'keys': {'season': 'season_3pm_avg', 'recent': 'recent_3pm_avg'}
    }
]

def backfill():
    print("🚀 Starting Global Stats Backfill...")
    total_updated = 0
    
    for entry in CONFIG:
        tracking_path = entry['tracking']
        cache_path = entry.get('cache')
        keys = entry.get('keys')
        
        if not os.path.exists(tracking_path):
            continue
            
        with open(tracking_path, 'r') as f:
            tracking_data = json.load(f)
            
        # Calculate Team Records from graded picks in this file (Fallback for Team Bets)
        team_records = {}
        all_picks = tracking_data.get('picks', [])
        for p in all_picks:
            team = p.get('team') or p.get('player')
            status = p.get('status', '').lower()
            if team and status in ['win', 'won', 'loss', 'lost']:
                if team not in team_records:
                    team_records[team] = {'w': 0, 'l': 0}
                if status in ['win', 'won']:
                    team_records[team]['w'] += 1
                else:
                    team_records[team]['l'] += 1

        # Load Cache if exists
        cache_data = {}
        if cache_path and os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
        updated_in_file = 0
        for pick in all_picks:
            if pick.get('status') == 'pending':
                player = pick.get('player')
                
                # 1. Try Player Cache Match
                if cache_path and player in cache_data:
                    stats = cache_data[player]
                    s_avg = stats.get(keys['season'], 0)
                    r_avg = stats.get(keys['recent'], 0)
                    
                    if pick.get('season_avg', 0) == 0:
                        pick['season_avg'] = s_avg
                    if pick.get('recent_avg', 0) == 0:
                        pick['recent_avg'] = r_avg
                    updated_in_file += 1
                
                # 2. Try Team Record Fallback (for Main/Spread lines or if player not in cache)
                team = pick.get('team') or pick.get('player')
                if team in team_records:
                    rec = team_records[team]
                    pick['season_record'] = f"{rec['w']}-{rec['l']}"
                    # If it's a team bet and no stats, use record as a substitute or additional info
                    if pick.get('season_avg', 0) == 0:
                         # We don't want to show 0.0 for team bets, so we'll just rely on season_record in the HTML
                         pass
                    updated_in_file += 1
                    
        if updated_in_file > 0:
            with open(tracking_path, 'w') as f:
                json.dump(tracking_data, f, indent=2)
            print(f"✅ Updated {updated_in_file} picks in {tracking_path}")
            total_updated += updated_in_file
            
    # Also add Main models to CONFIG (for team records only)
    print("\n📦 Processing Main models for team records...")
    MAINS = [
        'nba/nba_picks_tracking.json',
        'nfl/nfl_picks_tracking.json',
        'ncaa/ncaab_picks_tracking.json',
        'soccer/soccer_picks_tracking.json'
    ]
    for path in MAINS:
        if not os.path.exists(path): continue
        with open(path, 'r') as f:
            data = json.load(f)
        
        team_records = {}
        picks = data.get('picks', []) if isinstance(data, dict) else data
        if not isinstance(picks, list): continue
            
        for p in picks:
            team = p.get('team') or p.get('player')
            status = p.get('status', '').lower()
            if team and status in ['win', 'won', 'loss', 'lost']:
                if team not in team_records: team_records[team] = {'w': 0, 'l': 0}
                if status in ['win', 'won']: team_records[team]['w'] += 1
                else: team_records[team]['l'] += 1
        
        updated = 0
        for p in picks:
            if p.get('status') == 'pending':
                team = p.get('team') or p.get('player')
                if team in team_records:
                    rec = team_records[team]
                    p['season_record'] = f"{rec['w']}-{rec['l']}"
                    updated += 1
        
        if updated > 0:
            with open(path, 'w') as f:
                json.dump(data if isinstance(data, dict) else {'picks': picks}, f, indent=2)
            print(f"✅ Updated {updated} team records in {path}")
            total_updated += updated

    print(f"\n✨ Global Backfill complete. Total items updated: {total_updated}")


if __name__ == '__main__':
    backfill()
