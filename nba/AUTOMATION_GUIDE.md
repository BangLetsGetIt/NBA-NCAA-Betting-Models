# NBA Model Automation Guide

## ✅ What's Been Set Up:

1. **run_nba_model.sh** - Automation script that runs the model with error handling
2. **LaunchAgent** - macOS service that runs the script daily at 10 AM

---

## 🚀 How to Activate Daily Automation:

### Option 1: Load the LaunchAgent (Recommended)

```bash
# Load the automation service
launchctl load ~/Library/LaunchAgents/com.ricosoloco.nbamodel.plist

# Verify it's loaded
launchctl list | grep nbamodel
```

The model will now run **automatically every day at 10 AM**.

### Option 2: Run Manually Anytime

```bash
cd "/Users/rico/Library/Mobile Documents/com~apple~CloudDocs/Really Rico /Python Coding/NBA Model"
./run_nba_model.sh
```

---

## 📊 What Happens Daily:

1. **10:00 AM** - Model runs automatically
2. Updates past picks with completed game results
3. Fetches fresh NBA stats
4. Gets current odds for upcoming games
5. Generates predictions
6. Logs confident picks (5+ spread, 7+ total edges)
7. Saves results to HTML files
8. Creates log file in `logs/` folder

---

## 📁 Where to Find Results:

**Today's Picks:**
```bash
open "nba_model_output.html"
```

**Performance Tracker:**
```bash
open "nba_tracking_dashboard.html"
```

**Logs (if issues):**
```bash
cd logs
ls -lt | head -5  # Shows latest logs
```

---

## 🛠️ Managing Automation:

### Stop Daily Automation:
```bash
launchctl unload ~/Library/LaunchAgents/com.ricosoloco.nbamodel.plist
```

### Restart Automation:
```bash
launchctl unload ~/Library/LaunchAgents/com.ricosoloco.nbamodel.plist
launchctl load ~/Library/LaunchAgents/com.ricosoloco.nbamodel.plist
```

### Change Run Time:
Edit the plist file:
```bash
nano ~/Library/LaunchAgents/com.ricosoloco.nbamodel.plist
```

Find this section and change the hour:
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>10</integer>  <!-- Change this (0-23) -->
    <key>Minute</key>
    <integer>0</integer>
</dict>
```

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.ricosoloco.nbamodel.plist
launchctl load ~/Library/LaunchAgents/com.ricosoloco.nbamodel.plist
```

---

## ⏰ Recommended Daily Workflow:

### Morning (After 10 AM):
1. Check `nba_model_output.html` for today's games
2. Review `nba_tracking_dashboard.html` for:
   - Pending bets from yesterday
   - Overall performance stats

### Before Betting:
1. **Only bet picks logged in tracking file** (5+/7+ edges)
2. Check for injuries/lineup changes
3. Compare lines across multiple sportsbooks if possible

### Next Day:
- Model automatically updates results when games complete
- Review performance in tracking dashboard

---

## 🎯 What Gets Logged vs. Shown:

**Shown in Output (3+/4+ edges):**
- All interesting opportunities
- For informational purposes

**Logged in Tracking (5+/7+ edges):**
- Only highest confidence plays
- These are your ACTUAL bets
- Shows up in `nba_picks_tracking.json`
- Tracked in dashboard

---

## 🐛 Troubleshooting:

### Model Not Running Automatically?

**Check if LaunchAgent is loaded:**
```bash
launchctl list | grep nbamodel
```

If nothing shows, load it:
```bash
launchctl load ~/Library/LaunchAgents/com.ricosoloco.nbamodel.plist
```

**Check error logs:**
```bash
cd "/Users/rico/Library/Mobile Documents/com~apple~CloudDocs/Really Rico /Python Coding/NBA Model"
cat logs/launchd_error.log
```

### Test Run Manually:

```bash
cd "/Users/rico/Library/Mobile Documents/com~apple~CloudDocs/Really Rico /Python Coding/NBA Model"
./run_nba_model.sh
```

This will show you exactly what's happening.

---

## 📈 Monitoring Performance:

After 50-100 tracked bets, check your tracking dashboard for:

✅ **Win rate 53%+** = Profitable  
✅ **Positive ROI** = Making money  
✅ **Consistent picks** = Model working properly  

⚠️ **Win rate < 52%** = Need to adjust thresholds  
⚠️ **Negative ROI** = Increase edge requirements  

---

## 💡 Pro Tips:

1. **Don't check results obsessively** - Let variance play out over 50+ bets
2. **Stick to unit sizes** - Never bet more than 1-2% of bankroll
3. **Track closing line value** - More important than short-term W/L
4. **Review weekly** - Check what types of picks are performing best
5. **Adjust thresholds** - If too many/few bets, tweak CONFIDENT_SPREAD_EDGE

---

## 🔧 Advanced: Adjust Pick Frequency

Edit `nba_model_IMPROVED.py` around line 50:

```python
# For FEWER bets (more selective):
CONFIDENT_SPREAD_EDGE = 6.0  # Was 5.0
CONFIDENT_TOTAL_EDGE = 8.0   # Was 7.0

# For MORE bets (less selective):
CONFIDENT_SPREAD_EDGE = 4.0  # Was 5.0
CONFIDENT_TOTAL_EDGE = 6.0   # Was 7.0
```

After changing, save and the next run will use new thresholds.

---

Good luck! 🏀💰
