# Best Plays Bot - How It Works

This doc explains the `best_plays_bot.py` system for future agents.

## Overview
The Best Plays Bot aggregates picks from all sports models, tracks their performance, and generates `best_plays.html`.

## Key Files
- `best_plays_bot.py` - Main aggregator script
- `best_plays_tracking.json` - Historical tracking of all valued plays (confidence ≥ 50)
- `best_plays.html` - Output dashboard

## Confidence Tiers
| Tier | Score | Display |
|------|-------|---------|
| 🔥 Fire | 80+ | Top-tier plays |
| 💎 Solid | 70-79 | High-confidence |
| ⚡ Value | 50-69 | Standard plays |

## How Records Update

1. **Source Files**: Each model has its own tracking file (e.g., `nba/nba_points_props_tracking.json`)
2. **Grading**: `auto_grader.py` grades plays in source files (status → win/loss/void)
3. **Sync**: `best_plays_bot.py` reads source files and updates `best_plays_tracking.json` statuses
4. **Display**: HTML shows aggregated records by tier

## Critical Functions

### `deduplicate_tracking(plays)`
Removes duplicate entries based on key: `(player, bet_type, game_date, line)`. 
Prioritizes graded status (win/loss) over pending.

### `update_fire_tracking(current_plays)`
1. Adds new high-confidence plays
2. Checks source files for status updates
3. Calculates tier records

### `push_to_git()`
Automatically commits and pushes `best_plays.html` and `best_plays_tracking.json` to GitHub.

## Workflow
To update records properly, run:
```bash
python3 auto_grader.py       # Grade finished games
python3 best_plays_bot.py    # Regenerate HTML + auto-push to GitHub
```

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Records not updating on site | Changes not pushed | Already fixed - auto-push added |
| Inflated record counts | Duplicates in tracking | Already fixed - dedup on load |
| Pending plays stay pending | Source not graded | Run `auto_grader.py` first |
