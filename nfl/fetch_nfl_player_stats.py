#!/usr/bin/env python3
"""
NFL Player Stats Fetcher - Fully Automated using nflreadpy
Fetches player stats and populates cache files for NFL prop models
"""

import json
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Cache file paths
RECEPTIONS_CACHE = SCRIPT_DIR / "nfl_player_receptions_stats_cache.json"
RUSHING_YARDS_CACHE = SCRIPT_DIR / "nfl_player_rushing_yards_stats_cache.json"
RECEIVING_YARDS_CACHE = SCRIPT_DIR / "nfl_player_receiving_yards_stats_cache.json"
PASSING_YARDS_CACHE = SCRIPT_DIR / "nfl_player_passing_yards_stats_cache.json"

def get_current_season():
    """Get current NFL season year"""
    now = datetime.now()
    # NFL season starts in September
    if now.month >= 9:
        return now.year
    else:
        return now.year - 1

def fetch_all_stats():
    """Fetch all NFL player stats using nflreadpy"""
    print("=" * 70)
    print("NFL Player Stats Automated Fetcher")
    print("=" * 70)
    print()
    
    try:
        import nflreadpy as nfl
        print("✓ nflreadpy package loaded")
    except ImportError:
        print("✗ nflreadpy package not installed")
        print("  Install with: pip install nflreadpy")
        return False
    
    season = get_current_season()
    print(f"Fetching stats for {season} season...\n")
    
    try:
        # Load player stats for current season
        print("Loading player stats from nflreadpy...")
        player_stats = nfl.load_player_stats([season])
        
        # Convert to pandas if needed (nflreadpy uses polars)
        try:
            df = player_stats.to_pandas()
        except:
            # If it's already pandas or different format
            df = player_stats
        
        print(f"✓ Loaded {len(df)} player game records")
        print()
        
        # Process stats for each prop type
        receptions_stats = {}
        rushing_stats = {}
        receiving_stats = {}
        passing_stats = {}
        
        # Get unique players - use display_name for full names
        if 'player_display_name' in df.columns:
            player_col = 'player_display_name'
        elif 'player_name' in df.columns:
            player_col = 'player_name'
        elif 'player' in df.columns:
            player_col = 'player'
        else:
            print("✗ Could not find player name column")
            return False
        
        players = df[player_col].unique()
        print(f"Processing {len(players)} players...\n")
        
        for player_name in players:
            player_data = df[df[player_col] == player_name]
            
            if len(player_data) == 0:
                continue
            
            # Get team (use most recent)
            team_col = None
            for col in ['team', 'team_abbr', 'posteam', 'team_name']:
                if col in player_data.columns:
                    team_col = col
                    break
            
            team = player_data[team_col].iloc[-1] if team_col else 'UNK'
            games_played = len(player_data)
            
            # RECEPTIONS
            rec_col = None
            for col in ['receptions', 'rec', 'receptions_total']:
                if col in player_data.columns:
                    rec_col = col
                    break
            
            if rec_col:
                # Data is already per-game, so just take mean
                rec_avg = player_data[rec_col].mean() if games_played > 0 else 0
                recent_rec = player_data.tail(5)[rec_col].mean() if len(player_data) >= 5 else rec_avg
                
                if rec_avg > 0:
                    target_share = 0.20  # Estimate - would need team data for accurate
                    consistency = min(1.0, (rec_avg / 8.0) * 0.8)
                    
                    receptions_stats[player_name] = {
                        'season_rec_avg': round(rec_avg, 2),
                        'recent_rec_avg': round(recent_rec, 2),
                        'target_share': round(target_share, 2),
                        'consistency_score': round(consistency, 2),
                        'games_played': games_played,
                        'team': str(team)
                    }
            
            # RUSHING YARDS
            rush_yds_col = None
            for col in ['rushing_yards', 'rush_yds', 'rushing_yds', 'ry']:
                if col in player_data.columns:
                    rush_yds_col = col
                    break
            
            if rush_yds_col:
                # Data is already per-game, so just take mean
                rush_yds_avg = player_data[rush_yds_col].mean() if games_played > 0 else 0
                recent_rush_yds = player_data.tail(5)[rush_yds_col].mean() if len(player_data) >= 5 else rush_yds_avg
                
                if rush_yds_avg > 0:
                    carry_share = 0.20  # Estimate
                    consistency = min(1.0, (rush_yds_avg / 100.0) * 0.8)
                    
                    rushing_stats[player_name] = {
                        'season_rush_yds_avg': round(rush_yds_avg, 2),
                        'recent_rush_yds_avg': round(recent_rush_yds, 2),
                        'carry_share': round(carry_share, 2),
                        'consistency_score': round(consistency, 2),
                        'games_played': games_played,
                        'team': str(team)
                    }
            
            # RECEIVING YARDS
            rec_yds_col = None
            for col in ['receiving_yards', 'rec_yds', 'receiving_yds', 'recyds']:
                if col in player_data.columns:
                    rec_yds_col = col
                    break
            
            if rec_yds_col:
                # Data is already per-game, so just take mean
                rec_yds_avg = player_data[rec_yds_col].mean() if games_played > 0 else 0
                recent_rec_yds = player_data.tail(5)[rec_yds_col].mean() if len(player_data) >= 5 else rec_yds_avg
                
                if rec_yds_avg > 0:
                    target_share = 0.20  # Estimate
                    consistency = min(1.0, (rec_yds_avg / 100.0) * 0.8)
                    
                    receiving_stats[player_name] = {
                        'season_rec_yds_avg': round(rec_yds_avg, 2),
                        'recent_rec_yds_avg': round(recent_rec_yds, 2),
                        'target_share': round(target_share, 2),
                        'consistency_score': round(consistency, 2),
                        'games_played': games_played,
                        'team': str(team)
                    }
            
            # PASSING YARDS
            pass_yds_col = None
            for col in ['passing_yards', 'pass_yds', 'passing_yds', 'py']:
                if col in player_data.columns:
                    pass_yds_col = col
                    break
            
            if pass_yds_col:
                # Data is already per-game, so just take mean
                pass_yds_avg = player_data[pass_yds_col].mean() if games_played > 0 else 0
                recent_pass_yds = player_data.tail(5)[pass_yds_col].mean() if len(player_data) >= 5 else pass_yds_avg
                
                # Get pass attempts
                pass_att_col = None
                for col in ['attempts', 'pass_attempts', 'pass_att', 'att']:
                    if col in player_data.columns:
                        pass_att_col = col
                        break
                
                pass_att_avg = 0
                if pass_att_col:
                    # Data is already per-game
                    pass_att_avg = player_data[pass_att_col].mean() if games_played > 0 else 0
                
                if pass_yds_avg > 0:
                    consistency = min(1.0, (pass_yds_avg / 300.0) * 0.8)
                    
                    passing_stats[player_name] = {
                        'season_pass_yds_avg': round(pass_yds_avg, 2),
                        'recent_pass_yds_avg': round(recent_pass_yds, 2),
                        'pass_attempts': round(pass_att_avg, 1),
                        'consistency_score': round(consistency, 2),
                        'games_played': games_played,
                        'team': str(team)
                    }
        
        # Save to cache files
        print("Saving stats to cache files...")
        
        if receptions_stats:
            with open(RECEPTIONS_CACHE, 'w') as f:
                json.dump(receptions_stats, f, indent=2)
            print(f"  ✓ Saved {len(receptions_stats)} players to receptions cache")
        
        if rushing_stats:
            with open(RUSHING_YARDS_CACHE, 'w') as f:
                json.dump(rushing_stats, f, indent=2)
            print(f"  ✓ Saved {len(rushing_stats)} players to rushing yards cache")
        
        if receiving_stats:
            with open(RECEIVING_YARDS_CACHE, 'w') as f:
                json.dump(receiving_stats, f, indent=2)
            print(f"  ✓ Saved {len(receiving_stats)} players to receiving yards cache")
        
        if passing_stats:
            with open(PASSING_YARDS_CACHE, 'w') as f:
                json.dump(passing_stats, f, indent=2)
            print(f"  ✓ Saved {len(passing_stats)} players to passing yards cache")
        
        total = len(receptions_stats) + len(rushing_stats) + len(receiving_stats) + len(passing_stats)
        
        print()
        print("=" * 70)
        print(f"✅ Successfully fetched stats for {total} total player entries!")
        print("   Run 'nflmodels' to generate picks")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error fetching stats: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution"""
    success = fetch_all_stats()
    
    if not success:
        print("\n⚠️  Automated fetching failed")
        print("   Make sure nflreadpy is installed: pip install nflreadpy")

if __name__ == "__main__":
    main()
