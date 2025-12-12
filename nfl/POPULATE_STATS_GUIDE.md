# How to Add NFL Player Stats to Your Models

Your NFL prop models need player statistics to generate picks. Here are 3 ways to populate the stats:

## Option 1: Manual Entry (Quick Start)

Edit the cache files in the `nfl/` directory:

1. **Receptions Stats**: `nfl_player_receptions_stats_cache.json`
2. **Rushing Yards Stats**: `nfl_player_rushing_yards_stats_cache.json`
3. **Receiving Yards Stats**: `nfl_player_receiving_yards_stats_cache.json`
4. **Passing Yards Stats**: `nfl_player_passing_yards_stats_cache.json`

### Format for Receptions:
```json
{
  "Player Name": {
    "season_rec_avg": 5.5,
    "recent_rec_avg": 6.2,
    "target_share": 0.22,
    "consistency_score": 0.75,
    "games_played": 10,
    "team": "Team Abbreviation"
  }
}
```

### Format for Rushing Yards:
```json
{
  "Player Name": {
    "season_rush_yds_avg": 85.5,
    "recent_rush_yds_avg": 92.3,
    "carry_share": 0.25,
    "consistency_score": 0.80,
    "games_played": 10,
    "team": "Team Abbreviation"
  }
}
```

### Format for Receiving Yards:
```json
{
  "Player Name": {
    "season_rec_yds_avg": 75.5,
    "recent_rec_yds_avg": 82.1,
    "target_share": 0.22,
    "consistency_score": 0.75,
    "games_played": 10,
    "team": "Team Abbreviation"
  }
}
```

### Format for Passing Yards:
```json
{
  "Player Name": {
    "season_pass_yds_avg": 245.5,
    "recent_pass_yds_avg": 258.2,
    "pass_attempts": 32.5,
    "consistency_score": 0.85,
    "games_played": 10,
    "team": "Team Abbreviation"
  }
}
```

### Where to Get Stats:
- **ESPN**: https://www.espn.com/nfl/stats
- **Pro Football Reference**: https://www.pro-football-reference.com/
- **NFL.com**: https://www.nfl.com/stats/

## Option 2: Use ESPN API (Automated)

The models already have ESPN API integration code. You can enhance `fetch_nfl_player_stats.py` to parse ESPN's API responses.

## Option 3: Use nfl-data-py Package

If you can install it successfully:
```bash
pip install nfl-data-py
python3 nfl/fetch_nfl_player_stats.py
```

## Quick Start Example

Add a few key players to get started:

**Receptions Example:**
```json
{
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
  }
}
```

Once you add stats, run your models:
```bash
nflmodels
```

The models will use the cached stats to analyze props and generate picks!

