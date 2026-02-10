
from nba_api.stats.endpoints import leaguedashplayerstats
from datetime import datetime

# Date of the game: 2026-01-26
target_date = "01/26/2026"  # Format for NBA API

try:
    print(f"Fetching stats for {target_date}...")
    stats = leaguedashplayerstats.LeagueDashPlayerStats(
        season="2025-26",
        date_from_nullable=target_date,
        date_to_nullable=target_date,
        measure_type_detailed_defense='Base',
        per_mode_detailed='PerGame',
        timeout=30
    )
    df = stats.get_data_frames()[0]
    
    # Search for Avdija
    wagners = df[df['PLAYER_NAME'].str.contains("Avdija", case=False)]
    
    if not wagners.empty:
        print("\nFound Wagners:")
        for _, row in wagners.iterrows():
            print(f"Name: {row['PLAYER_NAME']}, Points: {row['PTS']}, Rebounds: {row['REB']}, Assists: {row['AST']}")
    else:
        print("\nNo Wagners found.")
        
except Exception as e:
    print(f"Error: {e}")
