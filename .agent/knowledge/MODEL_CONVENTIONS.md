# Model Conventions & Standards

This document defines the standard structure and naming conventions for all sports models in the `sports-models` repository. **All agents must strictly adhere to these patterns.**

## 1. Core Variable Naming
| Variable Name | Description | Standardized Name |
|--------------|-------------|-------------------|
| Recommendations | The list of analyzed plays passed to tracking | `recommendations` |
| Pending Plays | List of plays with "pending" status | `pending_picks` |
| Analysis list | Final list of plays after edge/AI scoring | `top_picks` |
| Stats Cache | Loaded JSON data for player stats | `stats_cache` |

## 2. Function Signatures
Every prop model (`nba/*.py`, `nfl/*.py`) should implement these functions with these exact names:

- `load_tracking_data()`: Returns the JSON tracking data dict.
- `save_tracking_data(data)`: Saves the tracking data to disk.
- `track_new_picks(recommendations, odds_data)`: Handles adding new plays and backfilling stats for existing ones.
- `main()`: The primary execution flow.

## 3. The "Robust Backfill" Logic
When implementing `track_new_picks`, agents must include the **Player-Name-Based Backfill** (added Dec 20, 2024). This ensures that even if `pick_id` formats change, older "zombie" picks receive stats updates.

**Pattern:**
```python
def track_new_picks(recommendations, odds_data):
    data = load_tracking_data()
    # 1. Create Lookup
    stats_lookup = {p['player']: {'season_avg': p.get('season_avg'), 'recent_avg': p.get('recent_avg'), 'odds': p.get('odds')} for p in recommendations}
    # 2. Iterate PENDING picks
    for pick in data['picks']:
        if pick.get('status') == 'pending' and pick['player'] in stats_lookup:
            # Update missing stats or refresh odds
            ...
```

## 4. Sport-Specific Settings
- **NBA**: Uses "L10 Avg" for recent form.
- **NFL**: Uses "L5 Avg" for recent form.
- **Model Record**: Displayed as "Model Record" in `best_plays_bot.py` to differentiate from team records.

## 5. UI & Styling
- All models must produce HTML output referencing the latest CSS in `PROPS_HTML_STYLING_GUIDE.md`.
- `best_plays_bot.py` is the aggregator; do not change its sorting (Confidence + HasStats) without verification.
