from nba_api.stats.endpoints import leaguedashteamstats
import pandas as pd

date_str = "2025-12-18" 
print(f"Fetching team stats for {date_str}...")

stats = leaguedashteamstats.LeagueDashTeamStats(
    date_from_nullable=date_str,
    date_to_nullable=date_str
).get_data_frames()[0]

if not stats.empty:
    print(f"Found {len(stats)} teams with stats.")
    print(stats[['TEAM_NAME', 'GP', 'W', 'L', 'PTS']].head())
else:
    print("No team stats found.")
