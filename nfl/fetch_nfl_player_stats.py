#!/usr/bin/env python3
"""
NFL Player Stats Fetcher
Fetches player stats from ESPN API and populates cache files for NFL prop models
"""

import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Cache file paths
RECEPTIONS_CACHE = SCRIPT_DIR / "nfl_player_receptions_stats_cache.json"
RUSHING_YARDS_CACHE = SCRIPT_DIR / "nfl_player_rushing_yards_stats_cache.json"
RECEIVING_YARDS_CACHE = SCRIPT_DIR / "nfl_player_receiving_yards_stats_cache.json"
PASSING_YARDS_CACHE = SCRIPT_DIR / "nfl_player_passing_yards_stats_cache.json"

def fetch_nfl_player_stats_from_espn():
    """
    Fetch NFL player stats from ESPN API
    Returns dict with player stats organized by stat type
    """
    print("Fetching NFL player stats from ESPN API...")
    
    stats_data = {
        'receptions': {},
        'rushing_yards': {},
        'receiving_yards': {},
        'passing_yards': {}
    }
    
    try:
        # ESPN NFL stats endpoint - try to get player stats
        # Note: ESPN API structure may vary, this is a basic implementation
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/statistics"
        
        # Try alternative: Get stats from ESPN's player stats page
        # We'll need to parse the HTML or use their internal API
        
        # For now, let's try to get stats from game logs or player pages
        # ESPN uses a different structure - we may need to scrape or use their internal endpoints
        
        print("⚠️  ESPN API structure requires additional parsing.")
        print("Creating template cache files that can be manually populated...")
        
        return stats_data
        
    except Exception as e:
        print(f"Error fetching from ESPN: {e}")
        return stats_data

def create_template_cache():
    """
    Create template cache files with example structure
    Users can manually populate these or we can fetch from API later
    """
    print("\nCreating template cache files...")
    
    # Template for receptions
    receptions_template = {
        "Example Player Name": {
            "season_rec_avg": 5.5,
            "recent_rec_avg": 6.2,
            "target_share": 0.22,
            "consistency_score": 0.75,
            "games_played": 10,
            "team": "Team Abbreviation"
        }
    }
    
    # Template for rushing yards
    rushing_template = {
        "Example Player Name": {
            "season_rush_yds_avg": 85.5,
            "recent_rush_yds_avg": 92.3,
            "carry_share": 0.25,
            "consistency_score": 0.80,
            "games_played": 10,
            "team": "Team Abbreviation"
        }
    }
    
    # Template for receiving yards
    receiving_template = {
        "Example Player Name": {
            "season_rec_yds_avg": 75.5,
            "recent_rec_yds_avg": 82.1,
            "target_share": 0.22,
            "consistency_score": 0.75,
            "games_played": 10,
            "team": "Team Abbreviation"
        }
    }
    
    # Template for passing yards
    passing_template = {
        "Example Player Name": {
            "season_pass_yds_avg": 245.5,
            "recent_pass_yds_avg": 258.2,
            "pass_attempts": 32.5,
            "consistency_score": 0.85,
            "games_played": 10,
            "team": "Team Abbreviation"
        }
    }
    
    # Write template files if they don't exist
    if not RECEPTIONS_CACHE.exists():
        with open(RECEPTIONS_CACHE, 'w') as f:
            json.dump(receptions_template, f, indent=2)
        print(f"✓ Created template: {RECEPTIONS_CACHE.name}")
    
    if not RUSHING_YARDS_CACHE.exists():
        with open(RUSHING_YARDS_CACHE, 'w') as f:
            json.dump(rushing_template, f, indent=2)
        print(f"✓ Created template: {RUSHING_YARDS_CACHE.name}")
    
    if not RECEIVING_YARDS_CACHE.exists():
        with open(RECEIVING_YARDS_CACHE, 'w') as f:
            json.dump(receiving_template, f, indent=2)
        print(f"✓ Created template: {RECEIVING_YARDS_CACHE.name}")
    
    if not PASSING_YARDS_CACHE.exists():
        with open(PASSING_YARDS_CACHE, 'w') as f:
            json.dump(passing_template, f, indent=2)
        print(f"✓ Created template: {PASSING_YARDS_CACHE.name}")

def fetch_from_nflfastr():
    """
    Alternative: Use nflfastR data (if available)
    This would require the nflfastR Python package
    """
    try:
        import nfl_data_py as nfl
        print("Using nfl-data-py package...")
        
        # Get current season
        current_year = datetime.now().year
        season = current_year if datetime.now().month >= 9 else current_year - 1
        
        # Fetch player stats
        player_stats = nfl.import_player_stats([season], stat_type='offense')
        
        # Process stats for each prop type
        receptions_stats = {}
        rushing_stats = {}
        receiving_stats = {}
        passing_stats = {}
        
        # Group by player and calculate averages
        for player_name in player_stats['player_name'].unique():
            player_data = player_stats[player_stats['player_name'] == player_name]
            
            # Receptions
            if 'receptions' in player_data.columns:
                rec_avg = player_data['receptions'].mean()
                recent_rec = player_data.tail(5)['receptions'].mean() if len(player_data) >= 5 else rec_avg
                receptions_stats[player_name] = {
                    'season_rec_avg': round(rec_avg, 2),
                    'recent_rec_avg': round(recent_rec, 2),
                    'target_share': 0.20,  # Would need to calculate from team data
                    'consistency_score': 0.70,
                    'games_played': len(player_data),
                    'team': player_data['team'].iloc[-1] if 'team' in player_data.columns else 'UNK'
                }
            
            # Rushing yards
            if 'rushing_yards' in player_data.columns:
                rush_avg = player_data['rushing_yards'].mean()
                recent_rush = player_data.tail(5)['rushing_yards'].mean() if len(player_data) >= 5 else rush_avg
                rushing_stats[player_name] = {
                    'season_rush_yds_avg': round(rush_avg, 2),
                    'recent_rush_yds_avg': round(recent_rush, 2),
                    'carry_share': 0.20,
                    'consistency_score': 0.70,
                    'games_played': len(player_data),
                    'team': player_data['team'].iloc[-1] if 'team' in player_data.columns else 'UNK'
                }
            
            # Receiving yards
            if 'receiving_yards' in player_data.columns:
                rec_yds_avg = player_data['receiving_yards'].mean()
                recent_rec_yds = player_data.tail(5)['receiving_yards'].mean() if len(player_data) >= 5 else rec_yds_avg
                receiving_stats[player_name] = {
                    'season_rec_yds_avg': round(rec_yds_avg, 2),
                    'recent_rec_yds_avg': round(recent_rec_yds, 2),
                    'target_share': 0.20,
                    'consistency_score': 0.70,
                    'games_played': len(player_data),
                    'team': player_data['team'].iloc[-1] if 'team' in player_data.columns else 'UNK'
                }
            
            # Passing yards
            if 'passing_yards' in player_data.columns:
                pass_yds_avg = player_data['passing_yards'].mean()
                recent_pass_yds = player_data.tail(5)['passing_yards'].mean() if len(player_data) >= 5 else pass_yds_avg
                passing_stats[player_name] = {
                    'season_pass_yds_avg': round(pass_yds_avg, 2),
                    'recent_pass_yds_avg': round(recent_pass_yds, 2),
                    'pass_attempts': 30.0,
                    'consistency_score': 0.70,
                    'games_played': len(player_data),
                    'team': player_data['team'].iloc[-1] if 'team' in player_data.columns else 'UNK'
                }
        
        # Save to cache files
        if receptions_stats:
            with open(RECEPTIONS_CACHE, 'w') as f:
                json.dump(receptions_stats, f, indent=2)
            print(f"✓ Saved {len(receptions_stats)} players to receptions cache")
        
        if rushing_stats:
            with open(RUSHING_YARDS_CACHE, 'w') as f:
                json.dump(rushing_stats, f, indent=2)
            print(f"✓ Saved {len(rushing_stats)} players to rushing yards cache")
        
        if receiving_stats:
            with open(RECEIVING_YARDS_CACHE, 'w') as f:
                json.dump(receiving_stats, f, indent=2)
            print(f"✓ Saved {len(receiving_stats)} players to receiving yards cache")
        
        if passing_stats:
            with open(PASSING_YARDS_CACHE, 'w') as f:
                json.dump(passing_stats, f, indent=2)
            print(f"✓ Saved {len(passing_stats)} players to passing yards cache")
        
        return True
        
    except ImportError:
        print("⚠️  nfl-data-py package not installed.")
        print("   Install with: pip install nfl-data-py")
        return False
    except Exception as e:
        print(f"Error fetching from nfl-data-py: {e}")
        return False

def main():
    """Main execution"""
    print("=" * 70)
    print("NFL Player Stats Fetcher")
    print("=" * 70)
    print()
    
    # Try to fetch from nfl-data-py first (best option)
    if fetch_from_nflfastr():
        print("\n✅ Successfully fetched stats from nfl-data-py!")
        return
    
    # If that fails, create templates
    print("\nCreating template cache files...")
    create_template_cache()
    
    print("\n" + "=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("1. Install nfl-data-py: pip install nfl-data-py")
    print("   Then run this script again to auto-populate stats")
    print()
    print("2. OR manually edit the cache files in the nfl/ directory:")
    print(f"   - {RECEPTIONS_CACHE.name}")
    print(f"   - {RUSHING_YARDS_CACHE.name}")
    print(f"   - {RECEIVING_YARDS_CACHE.name}")
    print(f"   - {PASSING_YARDS_CACHE.name}")
    print()
    print("3. Use ESPN, Pro Football Reference, or other sources to")
    print("   populate player stats in the cache files")
    print("=" * 70)

if __name__ == "__main__":
    main()

