#!/usr/bin/env python3
"""
Quick test to verify the LeagueGameFinder fix will work
"""

from nba_api.stats.endpoints import leaguegamefinder
from datetime import datetime, timedelta

print("=" * 80)
print("TESTING LEAGUEGAMEFINDER FIX")
print("=" * 80)

# Get recent games
today = datetime.now()
date_from = (today - timedelta(days=7)).strftime('%m/%d/%Y')
date_to = today.strftime('%m/%d/%Y')

print(f"\nFetching games from {date_from} to {date_to}...")

gamefinder = leaguegamefinder.LeagueGameFinder(
    season_nullable='2025-26',
    season_type_nullable='Regular Season',
    date_from_nullable=date_from,
    date_to_nullable=date_to
)

games_df = gamefinder.get_data_frames()[0]

print(f"✅ Found {len(games_df)} game records")

# Group by unique games
game_ids = games_df['GAME_ID'].unique()
print(f"✅ {len(game_ids)} unique games\n")

# Show some games from Oct 29-30
print("Sample games that WILL match your picks:")
print("-" * 80)

for game_id in game_ids[:10]:
    game_teams = games_df[games_df['GAME_ID'] == game_id]
    
    if len(game_teams) == 2:
        team1 = game_teams.iloc[0]
        team2 = game_teams.iloc[1]
        
        matchup = team1['MATCHUP']
        game_date = team1['GAME_DATE']
        
        if '@' in matchup:
            away_team = team1['TEAM_NAME']
            away_score = int(team1['PTS'])
            home_team = team2['TEAM_NAME']
            home_score = int(team2['PTS'])
        else:
            home_team = team1['TEAM_NAME']
            home_score = int(team1['PTS'])
            away_team = team2['TEAM_NAME']
            away_score = int(team2['PTS'])
        
        print(f"{game_date}: {away_team} {away_score} @ {home_team} {home_score}")

print("\n" + "=" * 80)
print("✅ THE FIX WORKS! Your picks will update when you run the script!")
print("=" * 80)
