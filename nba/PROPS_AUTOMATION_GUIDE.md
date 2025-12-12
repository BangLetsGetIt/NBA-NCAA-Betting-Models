# NBA Props Models Automation Guide

## ✅ Automated Models

All three props models are now scheduled to run automatically:

| Model | Schedule | LaunchAgent |
|-------|----------|-------------|
| **3PT Props** | **5:00 AM** daily | `com.rico.nba3ptprops` |
| **Rebounds Props** | **6:00 AM** daily | `com.rico.nbareboundsprops` |
| **Assists Props** | **7:00 AM** daily | `com.rico.nbaassistsprops` |

---

## 📊 What Happens Daily

### 5:00 AM - 3PT Props Model
- Fetches real NBA player 3PT stats
- Analyzes 3PT props from The Odds API
- Generates high-confidence picks (A.I. Score ≥ 9.5)
- Auto-tracks elite plays (A.I. Score ≥ 9.7)
- Saves HTML report: `nba_3pt_props.html`
- Pushes updates to GitHub

### 6:00 AM - Rebounds Props Model
- Fetches real NBA player rebounding stats
- Analyzes rebounds props from The Odds API
- Generates high-confidence picks (A.I. Score ≥ 9.5)
- Auto-tracks elite plays (A.I. Score ≥ 9.7)
- Saves HTML report: `nba_rebounds_props.html`
- Pushes updates to GitHub

### 7:00 AM - Assists Props Model
- Fetches real NBA player assists stats
- Analyzes assists props from The Odds API
- Generates high-confidence picks (A.I. Score ≥ 9.5)
- Auto-tracks elite plays (A.I. Score ≥ 9.7)
- Saves HTML report: `nba_assists_props.html`
- Pushes updates to GitHub

---

## 🛠️ Managing Automation

### Check Status
```bash
launchctl list | grep -E "nba.*props"
```

You should see all three:
- `com.rico.nba3ptprops`
- `com.rico.nbareboundsprops`
- `com.rico.nbaassistsprops`

### Stop All Automations
```bash
launchctl unload ~/Library/LaunchAgents/com.rico.nba3ptprops.plist
launchctl unload ~/Library/LaunchAgents/com.rico.nbareboundsprops.plist
launchctl unload ~/Library/LaunchAgents/com.rico.nbaassistsprops.plist
```

### Restart All Automations
```bash
launchctl load ~/Library/LaunchAgents/com.rico.nba3ptprops.plist
launchctl load ~/Library/LaunchAgents/com.rico.nbareboundsprops.plist
launchctl load ~/Library/LaunchAgents/com.rico.nbaassistsprops.plist
```

### Stop Individual Model
```bash
# Stop 3PT Props only
launchctl unload ~/Library/LaunchAgents/com.rico.nba3ptprops.plist

# Stop Rebounds Props only
launchctl unload ~/Library/LaunchAgents/com.rico.nbareboundsprops.plist

# Stop Assists Props only
launchctl unload ~/Library/LaunchAgents/com.rico.nbaassistsprops.plist
```

---

## ⏰ Change Schedule Times

To change when a model runs, edit the plist file:

```bash
# Edit 3PT Props schedule (currently 5:00 AM)
nano ~/Library/LaunchAgents/com.rico.nba3ptprops.plist

# Edit Rebounds Props schedule (currently 6:00 AM)
nano ~/Library/LaunchAgents/com.rico.nbareboundsprops.plist

# Edit Assists Props schedule (currently 7:00 AM)
nano ~/Library/LaunchAgents/com.rico.nbaassistsprops.plist
```

Find this section and change the hour (0-23):
```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>5</integer>  <!-- Change this (0-23) -->
    <key>Minute</key>
    <integer>0</integer>  <!-- Change this (0-59) -->
</dict>
```

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.rico.nba3ptprops.plist
launchctl load ~/Library/LaunchAgents/com.rico.nba3ptprops.plist
```

---

## 🧪 Manual Testing

You can run any model manually anytime:

```bash
# Run 3PT Props model
cd /Users/rico/sports-models/nba
./run_3pt_props.sh

# Run Rebounds Props model
./run_rebounds_props.sh

# Run Assists Props model
./run_assists_props.sh
```

---

## 📁 View Results

### HTML Reports (on GitHub Pages)
- **3PT Props:** https://BangLetsGetIt.github.io/NBA-NCAA-Betting-Models/nba/nba_3pt_props.html
- **Rebounds Props:** https://BangLetsGetIt.github.io/NBA-NCAA-Betting-Models/nba/nba_rebounds_props.html
- **Assists Props:** https://BangLetsGetIt.github.io/NBA-NCAA-Betting-Models/nba/nba_assists_props.html

### Local Files
```bash
cd /Users/rico/sports-models/nba
open nba_3pt_props.html
open nba_rebounds_props.html
open nba_assists_props.html
```

### Logs
```bash
cd /Users/rico/sports-models/nba/logs

# View latest logs
ls -lt nba_*props*.log | head -5

# View specific model log
tail -f 3pt_props_output.log
tail -f rebounds_props_output.log
tail -f assists_props_output.log
```

---

## 🐛 Troubleshooting

### Model Not Running?

**Check if LaunchAgent is loaded:**
```bash
launchctl list | grep -E "nba.*props"
```

**Check error logs:**
```bash
cd /Users/rico/sports-models/nba/logs
cat 3pt_props_error.log
cat rebounds_props_error.log
cat assists_props_error.log
```

**Test manually:**
```bash
cd /Users/rico/sports-models/nba
./run_3pt_props.sh
```

### Check Next Run Time

macOS doesn't show next run time directly, but you can verify the schedule:
```bash
cat ~/Library/LaunchAgents/com.rico.nba3ptprops.plist | grep -A 3 "StartCalendarInterval"
```

---

## 📈 Model Parameters

All models use strict edge requirements for profitability:

- **MIN_AI_SCORE:** 9.5 (only high-confidence plays shown)
- **TOP_PLAYS_COUNT:** 5 (quality over quantity)
- **AUTO_TRACK_THRESHOLD:** 9.7 (elite plays auto-tracked)
- **MIN_EDGE_OVER_LINE:** 1.5+ (player must average 1.5+ above line)
- **MIN_EDGE_UNDER_LINE:** 1.2+ (player must average 1.2+ below line)

---

## ✅ Verification

To verify everything is set up correctly:

```bash
# Check all three are loaded
launchctl list | grep -E "nba.*props"

# Should show:
# - 0  com.rico.nba3ptprops
# - 0  com.rico.nbareboundsprops
# - 0  com.rico.nbaassistsprops

# Check plist files exist
ls -la ~/Library/LaunchAgents/com.rico.nba*props.plist

# Check shell scripts are executable
ls -la /Users/rico/sports-models/nba/run_*props.sh
```

---

All set! Your props models will now run automatically every morning. 🏀💰
