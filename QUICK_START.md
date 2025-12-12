# Quick Start Guide - Unified Dashboard

## ✅ Setup Complete!

Your unified dashboard is now **automatically updating** whenever you run your models!

## How It Works

When you run any of these models:
- `nba/nba_model_IMPROVED.py`
- `nba/nba_3pt_props_model.py`
- `ncaa/ncaab_model_FINAL.py`

They will **automatically update** the unified dashboard at the end.

You'll see this at the end of each model run:
```
Updating unified dashboard...
✓ Dashboard updated
```

## View Your Dashboard

### Option 1: Open in Browser
```bash
open unified_dashboard_interactive.html
```

### Option 2: Direct Path
Open this file in any browser:
```
/Users/rico/sports-models/unified_dashboard_interactive.html
```

### Option 3: Manual Update
If you want to manually refresh the dashboard:
```bash
python3 unified_dashboard_interactive.py
```

## Dashboard Features

### Filters Available:
- **Sport**: NBA, NCAA, MLB, CFB, or All
- **Status**: All, Pending Only, Completed Only
- **Pick Type**: All, Spreads, Totals, Player Props
- **Min AI Score**: Filter props by minimum score (e.g., 8.5)
- **Min Edge**: Filter spreads/totals by minimum edge (e.g., 5.0)
- **Search**: Find specific players, teams, or matchups

### Sorting:
- Click any column header to sort
- Click again to reverse sort order

### Stats Displayed:
- Active Picks
- Win Rate %
- Total P/L (units)
- All-Time Record
- Picks by Sport

## Current Performance

**Overall**: 741-636 (53.8%) | +1,356 units

**By Sport**:
- NBA: 76-56 (57.6%) | +1,356u 🔥
- NCAA: 665-580 (53.4%) | Break-even

## Tips

### 1. Bookmark the Dashboard
Add `unified_dashboard_interactive.html` to your browser bookmarks for quick access.

### 2. Refresh After Running Models
After your models finish, just refresh the browser page (F5 or Cmd+R) to see the latest picks.

### 3. Filter for Today's Picks
Set filters to:
- Status: Pending Only
- This shows only active bets

### 4. Find High-Value Picks
- For Props: Set "Min AI Score" to 8.5 or higher
- For Spreads/Totals: Set "Min Edge" to 8.0 or higher

### 5. Quick Search
Use the search box to find:
- Specific players: "LeBron"
- Specific teams: "Lakers"
- Matchups: "Lakers vs"

## File Structure

```
sports-models/
├── unified_dashboard_interactive.html  ← Open this in browser
├── unified_dashboard_interactive.py    ← Auto-runs after models
├── unified_dashboard_data.json         ← Data file (auto-generated)
├── nba/
│   ├── nba_model_IMPROVED.py          ← Auto-updates dashboard ✓
│   └── nba_3pt_props_model.py         ← Auto-updates dashboard ✓
└── ncaa/
    └── ncaab_model_FINAL.py            ← Auto-updates dashboard ✓
```

## Troubleshooting

**Dashboard shows old data**:
- Refresh browser (F5 or Cmd+R)
- Or manually run: `python3 unified_dashboard_interactive.py`

**No picks showing**:
- Check your filters - set Status to "All"
- Make sure your models have run recently

**Dashboard won't load**:
- Make sure `unified_dashboard_data.json` exists
- Re-run: `python3 unified_dashboard_interactive.py`

## What's Next?

Your dashboard is now similar to DGFantasy's basic features. Want to add more?

**Phase 2 Options**:
1. Multi-sportsbook comparison (FanDuel, DraftKings, PrizePicks)
2. Parlay optimizer (build optimal slips)
3. Line movement alerts
4. Bankroll management tools
5. Mobile app version

Just let me know what you'd like to build next! 🚀
