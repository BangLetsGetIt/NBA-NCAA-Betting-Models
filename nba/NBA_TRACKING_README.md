# NBA Betting Model with Automated Tracking

Your NBA model now has automated pick tracking just like your NFL model! 🏀

## 🎯 What's New

### Automated Pick Tracking
- **Automatic logging**: Picks that meet the confidence threshold are automatically logged
- **Result updates**: Script checks NBA scores and automatically updates pick results
- **Performance tracking**: Win rate, ROI, profit/loss all calculated automatically
- **Beautiful dashboards**: HTML tracking dashboard matching your NFL style

## 📁 Files Created

1. **nba_model_with_tracking.py** - Main model with tracking (replaces your perfect_nba_model)
2. **nba_picks_tracking.json** - Stores all logged picks and results
3. **nba_tracking_dashboard.html** - Performance dashboard (like nfl_tracking.html)
4. **nba_model_output.html** - Game predictions (like nfl_picks.html)
5. **nba_model_output.csv** - CSV export of predictions

## ⚙️ Configuration

Edit these variables in the script to customize:

```python
# Confidence thresholds for TRACKING (logging picks)
CONFIDENT_SPREAD_EDGE = 3.0  # Need 3+ point edge to track spread
CONFIDENT_TOTAL_EDGE = 4.0   # Need 4+ point edge to track total

# Display thresholds (showing picks)
SPREAD_THRESHOLD = 2.0  # Show spread picks with 2+ edge
TOTAL_THRESHOLD = 3.0   # Show total picks with 3+ edge

# Betting unit size for profit tracking
UNIT_SIZE = 100  # $100 per unit
```

## 🚀 How to Use

### 1. Run the Model
```bash
python nba_model_with_tracking.py
```

This will:
- Fetch current NBA odds
- Generate predictions for all games
- **Automatically log confident picks** (edge >= threshold)
- Update results for completed games
- Generate both HTML files

### 2. View Your Picks
Open **nba_model_output.html** to see:
- All game predictions
- Spread and total picks
- Model vs Vegas lines
- Predicted scores

### 3. Track Performance
Open **nba_tracking_dashboard.html** to see:
- Overall record and win rate
- Total profit/loss
- ROI percentage
- Upcoming bets
- Completed bets with results

### 4. Update Results (Optional)
The model automatically checks for completed games, but you can manually update:

```python
from nba_model_with_tracking import update_pick_results, generate_tracking_html

# Update results
update_pick_results()

# Regenerate dashboard
generate_tracking_html()
```

## 📊 How Pick Tracking Works

### Automatic Logging
When you run the model:
1. It analyzes all games and calculates edges
2. If **spread edge >= 3.0** → Automatically logs the pick
3. If **total edge >= 4.0** → Automatically logs the pick
4. Pick is saved to `nba_picks_tracking.json`

### Automatic Result Updates
The model checks NBA scores going back 5 days:
1. Finds completed games
2. Matches them to pending picks
3. Determines win/loss/push
4. Updates profit/loss (assumes -110 odds)
5. Updates dashboard

### Pick Result Logic
**Spread Picks:**
- Win: Your team covers the spread
- Loss: Your team doesn't cover
- Push: Lands exactly on the spread

**Total Picks:**
- Win: Game total matches your OVER/UNDER
- Loss: Game total goes opposite way
- Push: Lands exactly on the total

## 🎨 Dashboard Features

Your tracking dashboard shows:

### Summary Stats
- **Total Bets**: Number of completed bets (excludes pushes)
- **Win Rate**: Wins / (Wins + Losses) %
- **Total Profit**: Net profit in units
- **ROI**: Return on investment %

### Upcoming Bets Table
- Game date and time
- Matchup
- Pick type (Spread/Total)
- Your pick
- Line and edge
- Pending status

### Completed Bets Table
- All past bets
- Final scores
- Win/Loss/Push result
- Profit/loss per bet

## 🔧 Customization

### Change Confidence Thresholds
Want to track more/fewer picks?

```python
# Track more picks (lower bars)
CONFIDENT_SPREAD_EDGE = 2.0  
CONFIDENT_TOTAL_EDGE = 3.0   

# Track fewer picks (higher bars)
CONFIDENT_SPREAD_EDGE = 5.0  
CONFIDENT_TOTAL_EDGE = 6.0   
```

### Change Unit Size
```python
UNIT_SIZE = 50   # Track in $50 units
UNIT_SIZE = 200  # Track in $200 units
```

### Adjust Display Thresholds
These control what shows in the HTML (doesn't affect tracking):

```python
SPREAD_THRESHOLD = 1.5  # Show more picks
TOTAL_THRESHOLD = 2.0   # Show more picks
```

## 📝 Data Structure

The `nba_picks_tracking.json` file stores:

```json
{
  "picks": [
    {
      "pick_id": "unique_identifier",
      "date_logged": "2025-10-29T...",
      "game_date": "2025-10-30T...",
      "home_team": "Lakers",
      "away_team": "Celtics",
      "matchup": "Celtics @ Lakers",
      "pick_type": "Spread",
      "model_line": -3.5,
      "market_line": -6.0,
      "edge": 2.5,
      "pick": "✅ BET: Lakers -6.0",
      "units": 1,
      "status": "Pending",
      "result": null,
      "profit_loss": 0,
      "actual_home_score": null,
      "actual_away_score": null
    }
  ],
  "summary": {
    "total_picks": 25,
    "wins": 15,
    "losses": 8,
    "pushes": 2,
    "pending": 5
  }
}
```

## 🔄 Workflow Example

### Day 1: Monday Night
```bash
# Run model to get picks
python nba_model_with_tracking.py
```
- 5 games today
- Model finds 2 picks with edge >= threshold
- **Automatically logs** both picks
- Generates HTML files

### Day 2: Tuesday Morning  
```bash
# Run model again
python nba_model_with_tracking.py
```
- Checks yesterday's games
- **Automatically updates** Monday's pick results
- Shows today's new games
- Logs any new confident picks

### Anytime: Check Dashboard
- Open `nba_tracking_dashboard.html`
- See your cumulative performance
- View upcoming and completed bets

## ⚡ Best Practices

1. **Run daily**: Run the model once per day (before games start)
2. **Let it auto-track**: Don't worry about manually logging - it's automatic
3. **Check dashboard regularly**: Monitor your performance
4. **Adjust thresholds**: If you're logging too many/few picks, adjust the thresholds

## 🆚 NFL Model Comparison

Your NBA model now works **exactly like** your NFL model:

| Feature | NFL Model | NBA Model |
|---------|-----------|-----------|
| Auto-log picks | ✅ | ✅ |
| Auto-update results | ✅ | ✅ |
| Tracking dashboard | ✅ | ✅ |
| Performance metrics | ✅ | ✅ |
| Black/yellow theme | ✅ | ✅ |
| Pending/Completed tables | ✅ | ✅ |

## 🐛 Troubleshooting

**No picks being tracked?**
- Lower `CONFIDENT_SPREAD_EDGE` and `CONFIDENT_TOTAL_EDGE`
- Check if model is finding enough edge in games

**Results not updating?**
- Make sure games are marked "Final" in NBA API
- Model checks last 5 days automatically
- Can take a few minutes after game ends

**Dashboard not showing?**
- Make sure script ran successfully
- Check for `nba_tracking_dashboard.html` file
- Open file directly in browser

## 📞 Support

The tracking system is fully automated. Just run the model and it handles:
- ✅ Finding confident picks
- ✅ Logging picks automatically
- ✅ Updating results
- ✅ Calculating metrics
- ✅ Generating dashboards

Your job: Run the script daily and check the dashboard! 🎯

---

**Remember:** The model automatically logs picks when edge >= threshold. You don't need to do anything manually - just run it and check your dashboard!
