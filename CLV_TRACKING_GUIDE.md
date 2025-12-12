# CLV Tracking & Automated Scheduling Guide

## Overview

You now have two powerful features:

1. **Automated Scheduling** - Model runs 3x daily to catch line movements
2. **CLV Tracking** - Tracks Closing Line Value to measure pick quality

---

## 1. Automated Scheduling

### Schedule
The 3PT props model runs automatically at:
- **10:00 AM** - Initial lines posted
- **3:00 PM** - Lines adjusted after public betting
- **6:00 PM** - Sharp money moves lines

### Managing the Scheduler

**Check status:**
```bash
./setup_scheduler.sh status
```

**Start automatic runs:**
```bash
./setup_scheduler.sh start
```

**Stop automatic runs:**
```bash
./setup_scheduler.sh stop
```

**View logs:**
```bash
./setup_scheduler.sh logs
```

**Manual test run:**
```bash
./setup_scheduler.sh test
```

### How It Works

1. Model runs at scheduled times
2. Fetches current odds from API
3. Calculates AI scores for all props
4. Auto-tracks picks with AI score ≥ 8.5
5. **Updates odds** on already-tracked picks (for CLV)
6. Updates unified dashboard
7. Logs output to `/Users/rico/sports-models/nba/logs/launchd_output.log`

---

## 2. CLV (Closing Line Value) Tracking

### What is CLV?

**Closing Line Value** measures if you're betting at better odds than what's available at game time.

**Example:**
- You bet: Anthony Edwards OVER 3.5 @ **-128** (10 AM)
- Game time odds: OVER 3.5 @ **-144** (6 PM)
- **Result**: You got +16 cents of CLV! ✅

### Why CLV Matters

- **CLV > 50%** = You're consistently beating the closing line (sharp bettor)
- **CLV < 50%** = You're betting at worse odds than closing (square bettor)
- Long-term profitability correlates strongly with positive CLV

### How It's Tracked

Each time the model runs:

1. **First run (10 AM)**:
   - Tracks pick: Edwards OVER 3.5 @ -128
   - Sets `opening_odds: -128`
   - Sets `latest_odds: -128`

2. **Second run (3 PM)**:
   - Sees same pick exists
   - Odds changed to -136
   - Updates `latest_odds: -136` (you got better value!)

3. **Third run (6 PM)**:
   - Odds moved again to -144
   - Updates `latest_odds: -144` (even better value!)

### Reading CLV Stats

In the HTML output, you'll see:

**CLV Rate: 65.2%**
- 65.2% of your picks had positive CLV
- You beat the closing line on most bets!

**Positive CLV: 15/23**
- 15 picks had better odds than closing
- 8 picks had worse odds than closing

### What to Aim For

| CLV Rate | Rating | Meaning |
|----------|--------|---------|
| 60%+ | Excellent | You're beating sharp money |
| 50-60% | Good | Slightly ahead of market |
| 45-50% | Average | Breaking even with market |
| <45% | Poor | Need to improve timing |

---

## 3. Optimal Betting Strategy

### When to Bet

Based on your automated schedule:

**Morning Lines (10 AM run)**:
- ✅ Best for: Soft lines, early value
- ⚠️ Risk: Lines will move
- 💡 Strategy: Bet immediately if AI score ≥ 9.0

**Afternoon Lines (3 PM run)**:
- ✅ Best for: Balanced approach
- ⚠️ Risk: Some value already gone
- 💡 Strategy: Bet if AI score ≥ 8.5

**Evening Lines (6 PM run)**:
- ✅ Best for: Sharp picks still available
- ⚠️ Risk: Running out of time
- 💡 Strategy: Last chance for AI score ≥ 8.5

### Multiple Runs = Better Picks

Running 3x daily helps you:
1. **Catch line drops** - OVER 4.5 becomes OVER 3.5
2. **Catch odds improvements** - -140 becomes +120
3. **Catch new props** - Books add players throughout day
4. **Track CLV** - See which timing works best

---

## 4. Understanding the Output

### Terminal Output

After each run, you'll see:

```
📊 = Auto-tracked (A.I. Score >= 8.5)

TOP OVER PLAYS
================================================================================
📊  1. Anthony Edwards         | OVER 3.5 3PT | MIN vs LAC | A.I.: 8.72
📊  2. Donte DiVincenzo        | OVER 3.5 3PT | MIN vs LAC | A.I.: 8.64
    3. Keegan Murray           | OVER 2.5 3PT | SAC vs MIA | A.I.: 8.57
```

- 📊 = This pick was auto-tracked
- No emoji = Pick qualifies but already tracked or below threshold

### HTML Dashboard

Shows 4 key metrics:

1. **Win Rate**: 35.3% (your success rate)
2. **Record**: 6-11 (wins-losses)
3. **ROI**: -5.54u (profit/loss in units)
4. **CLV Rate**: 0.0% (closing line value - will populate after multiple runs)

---

## 5. Examples

### Scenario 1: Line Movement in Your Favor

**10 AM Run:**
- Model finds: Harden OVER 3.5 @ +130
- AI Score: 8.56 ✓ Auto-tracked

**3 PM Run:**
- Same prop now: Harden OVER 3.5 @ +120
- Model updates: `latest_odds: +120`
- Your bet: Still +130 (you got better odds!)

**Result:** Positive CLV ✅

### Scenario 2: Line Movement Against You

**10 AM Run:**
- Model finds: Garland OVER 2.5 @ +124
- AI Score: 8.57 ✓ Auto-tracked

**3 PM Run:**
- Same prop now: Garland OVER 2.5 @ +135
- Model updates: `latest_odds: +135`
- Your bet: Only +124 (closing was better)

**Result:** Negative CLV ❌

### Scenario 3: New Opportunity

**10 AM Run:**
- DiVincenzo OVER 3.5 @ -150
- AI Score: 7.8 (too low, not tracked)

**3 PM Run:**
- DiVincenzo OVER 3.5 @ +128 (line moved!)
- AI Score: 8.64 ✓ Auto-tracked (new opportunity!)

**Result:** Caught value from line movement ✅

---

## 6. Tips for Success

### Timing Strategy

1. **Check all 3 runs** - Don't just bet morning lines
2. **Act fast on 9.0+ scores** - These rarely last
3. **Be patient with 8.5-8.9** - Often available at multiple times

### CLV Optimization

1. **Track your CLV by time** - Which run time gets best CLV?
2. **Adjust betting windows** - If 3 PM has best CLV, focus there
3. **Don't chase closing** - Sometimes early value is best

### Model Confidence

- **AI 9.0+**: Rare, bet immediately
- **AI 8.5-8.9**: Strong pick, track and bet
- **AI 8.0-8.4**: Good pick, shows in report but not auto-tracked

---

## 7. Monitoring Performance

### Daily Check

```bash
# View today's picks
./setup_scheduler.sh logs | tail -20

# Check dashboard
open /Users/rico/sports-models/unified_dashboard_interactive.html
```

### Weekly Review

Track your CLV rate over time:
- Week 1: 45% CLV (learning)
- Week 2: 52% CLV (improving)
- Week 3: 58% CLV (profitable territory)

---

## 8. Troubleshooting

**Scheduler not running?**
```bash
./setup_scheduler.sh restart
```

**Want to change schedule times?**
Edit: `/Users/rico/Library/LaunchAgents/com.rico.nba3ptprops.plist`

**Want to disable specific run times?**
Comment out unwanted times in the plist file

**Want more/fewer runs per day?**
Add/remove `<dict>` blocks in StartCalendarInterval

---

## 9. Advanced: Custom Schedule

To run at different times, edit the plist:

```xml
<key>StartCalendarInterval</key>
<array>
    <!-- Morning: 9 AM -->
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <!-- Afternoon: 2 PM -->
    <dict>
        <key>Hour</key>
        <integer>14</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <!-- Evening: 5 PM -->
    <dict>
        <key>Hour</key>
        <integer>17</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <!-- Pre-game: 7 PM -->
    <dict>
        <key>Hour</key>
        <integer>19</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
</array>
```

Then restart:
```bash
./setup_scheduler.sh restart
```

---

## Summary

✅ **Automated**: Model runs 3x daily
✅ **CLV Tracking**: Measures pick quality
✅ **Smart Tracking**: Only tracks high-confidence picks once
✅ **Line Monitoring**: Updates odds for CLV calculation
✅ **Unified Dashboard**: All stats in one place

**Next time you check the dashboard, look for:**
1. New picks from latest run
2. Your CLV rate improving over time
3. Which run times produce best picks

Happy betting! 🎯
