#!/usr/bin/env python3
"""
Quick script to add example player stats to cache files
You can modify this to add real stats from ESPN or other sources
"""

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Example stats - Replace with real data from ESPN/Pro Football Reference
EXAMPLE_RECEPTIONS = {
    "CeeDee Lamb": {
        "season_rec_avg": 7.8,
        "recent_rec_avg": 8.5,
        "target_share": 0.28,
        "consistency_score": 0.85,
        "games_played": 12,
        "team": "DAL"
    },
    "Tyreek Hill": {
        "season_rec_avg": 7.2,
        "recent_rec_avg": 7.8,
        "target_share": 0.26,
        "consistency_score": 0.82,
        "games_played": 12,
        "team": "MIA"
    },
    "Amon-Ra St. Brown": {
        "season_rec_avg": 7.5,
        "recent_rec_avg": 8.2,
        "target_share": 0.27,
        "consistency_score": 0.83,
        "games_played": 12,
        "team": "DET"
    }
}

EXAMPLE_RUSHING_YARDS = {
    "Christian McCaffrey": {
        "season_rush_yds_avg": 95.5,
        "recent_rush_yds_avg": 102.3,
        "carry_share": 0.28,
        "consistency_score": 0.88,
        "games_played": 12,
        "team": "SF"
    },
    "Derrick Henry": {
        "season_rush_yds_avg": 88.2,
        "recent_rush_yds_avg": 92.5,
        "carry_share": 0.25,
        "consistency_score": 0.85,
        "games_played": 12,
        "team": "BAL"
    }
}

EXAMPLE_RECEIVING_YARDS = {
    "CeeDee Lamb": {
        "season_rec_yds_avg": 98.5,
        "recent_rec_yds_avg": 105.2,
        "target_share": 0.28,
        "consistency_score": 0.85,
        "games_played": 12,
        "team": "DAL"
    },
    "Tyreek Hill": {
        "season_rec_yds_avg": 95.2,
        "recent_rec_yds_avg": 102.8,
        "target_share": 0.26,
        "consistency_score": 0.82,
        "games_played": 12,
        "team": "MIA"
    }
}

EXAMPLE_PASSING_YARDS = {
    "Patrick Mahomes": {
        "season_pass_yds_avg": 285.5,
        "recent_pass_yds_avg": 295.2,
        "pass_attempts": 38.5,
        "consistency_score": 0.90,
        "games_played": 12,
        "team": "KC"
    },
    "Josh Allen": {
        "season_pass_yds_avg": 275.8,
        "recent_pass_yds_avg": 282.3,
        "pass_attempts": 36.2,
        "consistency_score": 0.88,
        "games_played": 12,
        "team": "BUF"
    }
}

def add_example_stats():
    """Add example stats to cache files"""
    
    # Receptions
    rec_file = SCRIPT_DIR / "nfl_player_receptions_stats_cache.json"
    with open(rec_file, 'w') as f:
        json.dump(EXAMPLE_RECEPTIONS, f, indent=2)
    print(f"✓ Added {len(EXAMPLE_RECEPTIONS)} players to receptions cache")
    
    # Rushing Yards
    rush_file = SCRIPT_DIR / "nfl_player_rushing_yards_stats_cache.json"
    with open(rush_file, 'w') as f:
        json.dump(EXAMPLE_RUSHING_YARDS, f, indent=2)
    print(f"✓ Added {len(EXAMPLE_RUSHING_YARDS)} players to rushing yards cache")
    
    # Receiving Yards
    rec_yds_file = SCRIPT_DIR / "nfl_player_receiving_yards_stats_cache.json"
    with open(rec_yds_file, 'w') as f:
        json.dump(EXAMPLE_RECEIVING_YARDS, f, indent=2)
    print(f"✓ Added {len(EXAMPLE_RECEIVING_YARDS)} players to receiving yards cache")
    
    # Passing Yards
    pass_yds_file = SCRIPT_DIR / "nfl_player_passing_yards_stats_cache.json"
    with open(pass_yds_file, 'w') as f:
        json.dump(EXAMPLE_PASSING_YARDS, f, indent=2)
    print(f"✓ Added {len(EXAMPLE_PASSING_YARDS)} players to passing yards cache")
    
    print("\n✅ Example stats added! Update with real stats from ESPN/Pro Football Reference")
    print("   Then run: nflmodels")

if __name__ == "__main__":
    add_example_stats()

