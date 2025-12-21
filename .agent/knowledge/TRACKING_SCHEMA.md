# Tracking & Stats Schema

This document defines the JSON structure for all tracking and cache files.

## 1. Tracking File (`*_tracking.json`)
Every object in the `picks` list must follow this schema:

| Key | Type | Description |
|-----|------|-------------|
| `pick_id` | String | Unique identifier: `Player_BetType_Date` (e.g. `Dak Prescott_over_2024-12-21`) |
| `player` | String | Full player name (must match stats cache) |
| `team` | String | Team abbreviation (upper case, e.g. "DAL") |
| `pick_type`| String | The prop category (e.g. "Passing Yards") |
| `bet_type` | String | "over" or "under" (lower case) |
| `line` | Float | The numerical betting line |
| `prop_line` | Float | **REQUIRED** Same as line (used by `props_grader.py`) |
| `odds` | String/Int| Opening odds |
| `latest_odds`| String/Int| Most recently seen odds |
| `edge` | Float | Model projected edge |
| `ai_score` | Float | Confidence score (0-10) |
| `status` | String | "pending", "win", or "loss" |
| `season_avg`| Float | **REQUIRED** Player's average for the season |
| `recent_avg`| Float | **REQUIRED** Player's L5/L10 average |
| `season_record`| String | Optional: Team record (e.g. "12-4") for main line bets |

## 2. Stats Cache File (`*_stats_cache.json`)
Structure is a dictionary keyed by Player Name.

**Example (NFL Passing):**
```json
{
  "Player Name": {
    "season_pass_yds_avg": 234.0,
    "recent_pass_yds_avg": 227.4,
    "team": "BUF",
    "games_played": 14
  }
}
```

## 3. Best Plays Aggregation (`best_plays_bot.py`)
- **Ranking**: Sorted by `(confidence, has_stats > 0)`.
- **Top 50**: Only the top 50 highly confident plays are displayed.
- **Deduplication**: Keyed by `(Sport, Category, Player)`.
