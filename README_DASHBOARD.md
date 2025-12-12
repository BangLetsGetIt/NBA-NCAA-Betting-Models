# Unified Sports Dashboard

A unified interface combining all your sports betting models (NBA, NCAA, MLB, CFB) into one interactive platform - similar to DGFantasy.

## Features

### ✅ Current Features (Phase 1 - COMPLETED)

1. **Unified Data Aggregation**
   - Combines picks from all models automatically
   - Normalizes different data formats (spreads, totals, player props)
   - Real-time stats across all sports

2. **Interactive Dashboard**
   - Filter by sport (NBA, NCAA, MLB, CFB)
   - Filter by status (pending, completed, all)
   - Filter by pick type (spreads, totals, player props)
   - Filter by minimum AI score or edge
   - Search functionality for players/teams
   - Sortable columns

3. **Performance Tracking**
   - Overall win rate and P/L
   - Sport-by-sport breakdowns
   - Active picks counter
   - Historical record tracking

4. **Beautiful UI**
   - Modern gradient design
   - Color-coded badges for sports and pick types
   - Responsive mobile layout
   - Hover effects and animations

## Files

- **`unified_dashboard.py`** - Basic dashboard generator (static HTML)
- **`unified_dashboard_interactive.py`** - Advanced interactive dashboard with filters
- **`unified_dashboard_data.json`** - JSON data file for JavaScript
- **`unified_dashboard_interactive.html`** - The interactive web interface

## Usage

### Quick Start

```bash
# Generate the interactive dashboard
python3 unified_dashboard_interactive.py

# Open in browser
open unified_dashboard_interactive.html
```

### Auto-Update (Recommended)

Add this to your existing model scripts to auto-refresh the dashboard:

```python
# At the end of your model's main() function
import subprocess
subprocess.run(['python3', 'unified_dashboard_interactive.py'], cwd='/Users/rico/sports-models')
```

### Filtering Examples

1. **High-confidence NBA picks only**:
   - Sport: NBA
   - Status: Pending Only
   - Min AI Score: 8.5

2. **All player props**:
   - Pick Type: Player Props
   - Status: Pending Only

3. **NCAA games with big edges**:
   - Sport: NCAA
   - Min Edge: 8.0
   - Status: Pending Only

## Roadmap

### Phase 2: Multi-Sportsbook Integration
- [ ] Fetch odds from multiple books (FanDuel, DraftKings, PrizePicks)
- [ ] Line shopping - show best available odds
- [ ] Alert when odds move in your favor
- [ ] Track which book has the best line

### Phase 3: Parlay Optimizer
- [ ] Build optimal parlays from your picks
- [ ] Calculate parlay odds and EV
- [ ] Consider correlation (same-game parlays)
- [ ] Different formats (2-pick, 3-pick, 6-pick)
- [ ] Export to betting slips

### Phase 4: Advanced Analytics
- [ ] Bet sizing recommendations (Kelly Criterion)
- [ ] Bankroll management tracking
- [ ] Historical performance by sport/type
- [ ] Best times to bet (line movement analysis)
- [ ] Closing line value (CLV) tracking

### Phase 5: Monetization (Optional)
- [ ] User authentication system
- [ ] Tiered access (free vs premium)
- [ ] Subscription management
- [ ] Payment processing (Stripe)
- [ ] Email alerts for top picks

### Phase 6: Mobile App
- [ ] React Native app
- [ ] Push notifications
- [ ] Quick bet tracking
- [ ] Live score updates

## Data Sources

Currently aggregating from:
- **NBA**: Spreads/totals + 3PT player props
- **NCAA**: Spreads/totals
- **MLB**: (when season active)
- **CFB**: (when season active)

## Performance Stats

As of last update:
- **Overall Record**: 741-636 (53.8%)
- **Total Profit**: +1,356 units
- **Active Picks**: 19 pending

### By Sport:
- **NBA**: 76-56 (57.6%) | +1,356u
- **NCAA**: 665-580 (53.4%) | +0u

## Technical Details

### Data Flow
```
Individual Models → Tracking JSON Files → Aggregator Script → Unified JSON → Interactive HTML
     (nba_*.py)      (nba_picks_tracking.json)   (unified_dashboard_interactive.py)
```

### File Structure
```
sports-models/
├── nba/
│   ├── nba_picks_tracking.json
│   └── nba_3pt_props_tracking.json
├── ncaa/
│   └── ncaab_picks_tracking.json
├── mlb/ (when active)
├── cfb/ (when active)
├── unified_dashboard_interactive.py
├── unified_dashboard_interactive.html
└── unified_dashboard_data.json
```

## Customization

### Change Minimum Thresholds

Edit `unified_dashboard_interactive.py`:

```python
# Line ~230 - Default filter values
'min_ai_score': 8.0,  # Only show picks with AI score >= 8.0
'min_edge': 5.0,      # Only show picks with edge >= 5.0
```

### Add New Sports

1. Add to `MODEL_FILES` dict in script:
```python
'NHL': {
    'spreads_totals': os.path.join(SCRIPT_DIR, 'nhl', 'nhl_picks_tracking.json')
}
```

2. Update sport badge colors in HTML/CSS

### Customize Colors

Edit the CSS section in `generate_interactive_html()` function:
```css
.sport-badge.nba { background: rgba(237, 100, 166, 0.2); color: #ec4899; }
```

## Troubleshooting

**Dashboard shows 0 picks**:
- Check that tracking JSON files exist and have data
- Verify file paths in `MODEL_FILES` dict
- Run your models first to generate tracking data

**Filters not working**:
- Hard refresh browser (Cmd+Shift+R)
- Check browser console for JavaScript errors
- Ensure `unified_dashboard_data.json` exists

**Old data showing**:
- Re-run `python3 unified_dashboard_interactive.py`
- Set up auto-update in your model scripts

## Next Steps

To make this more like DGFantasy:

1. **Add live odds comparison** - fetch from multiple books
2. **Build parlay optimizer** - combine picks intelligently
3. **Add subscription model** - monetize your picks
4. **Create public landing page** - share with friends/subscribers
5. **Deploy to web** - use Vercel/Netlify for hosting

## Contributing

Want to add features? Fork and submit a PR!

## License

MIT License - use however you want!

---

**Built with ❤️ for better betting decisions**
