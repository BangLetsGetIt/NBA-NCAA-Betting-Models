# Last 100/50/20 Picks Performance Breakdown Implementation

## Summary

Successfully added the last 100/50/20 picks performance breakdown feature to the soccer and NFL models, matching the implementation already present in the NBA and NCAA models.

## Soccer Model Implementation (`soccer/soccer_model_IMPROVED.py`)

### Functions Added:

1. **`calculate_tracking_stats()`** - Calculates overall tracking statistics with spread/total breakdown
   - Handles `profit_loss` in cents (converts to units)
   - Calculates win rate, ROI, and breakdown by pick type

2. **`calculate_recent_performance()`** - Calculates rolling window performance stats
   - Supports last 100, 50, and 20 picks
   - Filters completed picks (win/loss/push)
   - Calculates wins, losses, win rate, profit, ROI
   - Breakdown by pick_type (SPREAD vs TOTAL)

3. **`load_picks_tracking()`** - Helper function to load tracking data
   - Wrapper for existing `load_tracking()` function
   - Returns data in standard format compatible with dashboard

4. **`generate_tracking_html()`** - Generates comprehensive HTML tracking dashboard
   - Overall performance metrics section
   - Today's projections table
   - Last 100 picks breakdown with spreads/totals split
   - Last 50 picks breakdown with spreads/totals split
   - Last 20 picks breakdown (labeled as "Hot Streak") with spreads/totals split
   - Fully responsive CSS matching soccer model aesthetic (orange theme)
   - Mobile-optimized layouts

**Output File:** `soccer/soccer_tracking_dashboard.html`

### Soccer-Specific Adaptations:

- Handles uppercase `pick_type`: "SPREAD" or "TOTAL" (vs NBA's "Spread"/"Total")
- Uses `profit_loss` field (stored in cents) like NCAA model
- Uses `game_time` field instead of `game_date`
- Status values are lowercase: "win", "loss", "pending"

## NFL Model Implementation (`nfl/nfl_model_IMPROVED.py`)

### Functions Added:

1. **`normalize_nfl_tracking_data()`** - Converts NFL array format to standard dict format
   - Normalizes field names: `bet_type` → `pick_type`
   - Maps `status: "complete"` + `result: "won"/"lost"` → unified `status: "win"/"loss"`
   - Converts `profit` (float dollars) → `profit_loss` (int cents)
   - Maps `date_placed` → `game_date` for consistency

2. **`load_picks_tracking()`** - Loads and normalizes NFL tracking data
   - Reads array format from JSON
   - Converts to standard `{"picks": [...]}` format
   - Handles missing file gracefully

3. **`calculate_tracking_stats()`** - Calculates detailed tracking statistics
   - Adapted from existing `BettingTracker.get_statistics()` method
   - Includes spread/total breakdown
   - Returns stats in standardized format

4. **`calculate_recent_performance()`** - Calculates rolling window performance
   - Works with normalized NFL data structure
   - Handles NFL-specific field mappings
   - Breakdown by pick_type (Spread vs Total)

5. **`generate_tracking_html()`** - Generates comprehensive HTML tracking dashboard
   - Overall performance metrics section
   - Today's projections table
   - Last 100 picks breakdown with spreads/totals split
   - Last 50 picks breakdown with spreads/totals split
   - Last 20 picks breakdown (labeled as "Hot Streak") with spreads/totals split
   - Fully responsive CSS matching NFL model aesthetic (blue theme)
   - Mobile-optimized layouts

**Output File:** `nfl/nfl_tracking_dashboard.html`

### NFL-Specific Adaptations:

- Normalizes array structure `[{...}]` → dict format `{"picks": [...]}`
- Maps `bet_type: "spread"/"total"` (lowercase) → `pick_type: "Spread"/"Total"`
- Maps `status: "complete"` + `result: "won"/"lost"` → `status: "win"/"loss"`
- Converts `profit` as float (dollars) → `profit_loss` as int (cents)
- Maps `date_placed` → `game_date` for template consistency
- Added `pytz` import for timezone handling

## Common Features Across All Models

### Dashboard Sections:

1. **Overall Performance**
   - Total bets count
   - Overall record (W-L-P)
   - Win rate percentage
   - Total profit in units
   - ROI percentage
   - Spreads vs Totals breakdown

2. **Today's Projections**
   - Table showing all pending picks
   - Game date/time, matchup, pick type, recommendation, line, edge, status

3. **Recent Performance Breakdown**
   - **Last 100 Picks**: Long-term view with full breakdown
   - **Last 50 Picks**: Mid-term performance trends
   - **Last 20 Picks**: Short-term "Hot Streak" indicator
   - Each section includes:
     - Overall record, win rate, profit, ROI
     - Spreads breakdown (record, win %, ROI)
     - Totals breakdown (record, win %, ROI)

### Visual Design:

- Dark theme matching each sport's color scheme
- Responsive design for mobile, tablet, and desktop
- Consistent stat card layouts
- Color-coded performance indicators (green for positive, red for negative)
- Professional typography and spacing

### Technical Implementation:

- Uses Jinja2 templating for HTML generation
- Calculates metrics dynamically from tracking JSON files
- Handles edge cases (no picks, no completed picks, etc.)
- Properly formats dates and currency values
- Maintains compatibility with existing tracking file structures

## Files Modified

1. `soccer/soccer_model_IMPROVED.py`
   - Added tracking dashboard functions
   - Added HTML generation function

2. `nfl/nfl_model_IMPROVED.py`
   - Added data normalization functions
   - Added tracking dashboard functions
   - Added HTML generation function
   - Added `pytz` import

## Output Files Generated

1. `soccer/soccer_tracking_dashboard.html` - Soccer tracking dashboard
2. `nfl/nfl_tracking_dashboard.html` - NFL tracking dashboard

## Usage

To generate the tracking dashboards, call the `generate_tracking_html()` function in each model:

```python
# In soccer model
generate_tracking_html()

# In NFL model  
generate_tracking_html()
```

Or integrate into the main execution flow of each model script.

## Status

✅ All implementation tasks completed
✅ Soccer model fully functional
✅ NFL model fully functional
✅ Both dashboards match NBA/NCAA design patterns
✅ All field mappings and data normalizations implemented correctly
