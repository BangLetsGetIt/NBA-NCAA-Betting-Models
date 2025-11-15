#!/usr/bin/env python
"""
NBA API Column Checker
Run this to see what columns are actually returned by the NBA API
"""

from nba_api.stats.endpoints import leaguedashteamstats
import time

print("=" * 70)
print("NBA API COLUMN CHECKER")
print("=" * 70)

try:
    print("\n1. Fetching SEASON stats...")
    season_stats = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense='Advanced',
        season='2025-26',
        timeout=30
    )
    season_df = season_stats.get_data_frames()[0]
    
    print(f"   ✓ Fetched {len(season_df)} teams")
    print(f"\n   Available columns ({len(season_df.columns)} total):")
    for i, col in enumerate(season_df.columns, 1):
        print(f"   {i:2d}. {col}")
    
    print(f"\n   First team data:")
    if not season_df.empty:
        first_team = season_df.iloc[0]
        print(f"   Team Name: {first_team.get('TEAM_NAME', 'N/A')}")
        print(f"   Team ID: {first_team.get('TEAM_ID', 'N/A')}")
        print(f"   NET_RATING: {first_team.get('NET_RATING', 'N/A')}")
        print(f"   PACE: {first_team.get('PACE', 'N/A')}")
        print(f"   OFF_RATING: {first_team.get('OFF_RATING', 'N/A')}")
        print(f"   DEF_RATING: {first_team.get('DEF_RATING', 'N/A')}")
    
    time.sleep(0.6)
    
    print("\n2. Fetching LAST 10 GAMES stats...")
    form_stats = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense='Advanced',
        season='2025-26',
        last_n_games=10,
        timeout=30
    )
    form_df = form_stats.get_data_frames()[0]
    
    print(f"   ✓ Fetched {len(form_df)} teams")
    print(f"   Columns same as season: {list(season_df.columns) == list(form_df.columns)}")
    
    time.sleep(0.6)
    
    print("\n3. Fetching HOME splits...")
    home_stats = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense='Advanced',
        season='2025-26',
        location_nullable='Home',
        timeout=30
    )
    home_df = home_stats.get_data_frames()[0]
    
    print(f"   ✓ Fetched {len(home_df)} teams")
    print(f"   Columns same as season: {list(season_df.columns) == list(home_df.columns)}")
    
    time.sleep(0.6)
    
    print("\n4. Fetching ROAD splits...")
    road_stats = leaguedashteamstats.LeagueDashTeamStats(
        measure_type_detailed_defense='Advanced',
        season='2025-26',
        location_nullable='Road',
        timeout=30
    )
    road_df = road_stats.get_data_frames()[0]
    
    print(f"   ✓ Fetched {len(road_df)} teams")
    print(f"   Columns same as season: {list(season_df.columns) == list(road_df.columns)}")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nKey columns for the model:")
    key_cols = ['TEAM_NAME', 'TEAM_ID', 'NET_RATING', 'PACE', 'OFF_RATING', 'DEF_RATING']
    for col in key_cols:
        exists = col in season_df.columns
        status = "✓" if exists else "✗"
        print(f"  {status} {col}")
    
    print("\n✓ API is working correctly!")
    print("\nIf the model is failing, the column names above show what's actually available.")
    print("The fixed model should handle these variations automatically.\n")

except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nPossible issues:")
    print("  - No internet connection")
    print("  - NBA API is down")
    print("  - Invalid season parameter")
    print("  - nba_api package needs update: pip install --upgrade nba_api")

print("=" * 70)
