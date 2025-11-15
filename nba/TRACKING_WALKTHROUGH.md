# 📊 NBA Tracking System - Example Walkthrough

## Real-World Example: 3-Day Scenario

Let's walk through exactly how the automated tracking works over 3 days.

---

## 🗓️ Day 1: Tuesday, 6:00 PM (Before Games)

### You Run the Model
```bash
$ python nba_model_with_tracking.py
```

### What Happens Behind the Scenes

**Step 1: Fetch Today's Games**
```
Lakers vs Celtics     (7:00 PM)
Warriors vs Nuggets   (9:00 PM)
```

**Step 2: Model Analysis**

Game 1: Lakers vs Celtics
- Market Line: Lakers -6.0
- Model Line: Lakers -2.8
- **Edge: +3.2 points** ✅

Game 2: Warriors vs Nuggets  
- Market Total: 220.5
- Model Total: 216.0
- **Edge: -4.5 points** ✅

**Step 3: Automatic Decision**
```python
# Game 1: Spread edge (3.2) >= CONFIDENT_SPREAD_EDGE (3.0)
📝 LOGGED: ✅ BET Lakers -6.0 (Edge: +3.2)

# Game 2: Total edge (4.5) >= CONFIDENT_TOTAL_EDGE (4.0)  
📝 LOGGED: ✅ BET UNDER 220.5 (Edge: -4.5)
```

### Files Generated

**nba_model_output.html** shows:
```
🏀 NBA MODEL PICKS
━━━━━━━━━━━━━━━━━━━━━━
Lakers vs Celtics
📊 SPREAD BET
Vegas Line: -6.0
Model Prediction: -2.8
✅ BET: Lakers -6.0

🎯 OVER/UNDER BET  
Vegas Total: 220.5
Model Projects: 216.0 pts
✅ BET: UNDER 220.5
```

**nba_tracking_dashboard.html** shows:
```
🏀 NBA BET TRACKING
━━━━━━━━━━━━━━━━━━━━━━
📊 STATS
Total Bets: 0
Win Rate: 0.0%
Total Profit: +0.00u
ROI: +0.0%

🎯 UPCOMING BETS
Date          Game            Type    Pick              Result
10/29 7:00PM  LAL vs BOS     Spread  Lakers -6.0       Pending
10/29 9:00PM  GSW vs DEN     Total   UNDER 220.5       Pending
```

**nba_picks_tracking.json** contains:
```json
{
  "picks": [
    {
      "pick_id": "Lakers_Celtics_2025-10-29T23:00:00Z_spread",
      "game_date": "2025-10-29T23:00:00Z",
      "home_team": "Lakers",
      "away_team": "Celtics",
      "pick_type": "Spread",
      "pick": "✅ BET: Lakers -6.0",
      "edge": 3.2,
      "status": "Pending",
      "profit_loss": 0
    },
    {
      "pick_id": "Nuggets_Warriors_2025-10-30T01:00:00Z_total",
      "game_date": "2025-10-30T01:00:00Z",
      "pick_type": "Total",
      "pick": "✅ BET: UNDER 220.5",
      "edge": -4.5,
      "status": "Pending",
      "profit_loss": 0
    }
  ],
  "summary": {
    "total_picks": 2,
    "pending": 2,
    "wins": 0,
    "losses": 0
  }
}
```

---

## 🗓️ Day 2: Wednesday, 10:00 AM (After Games Finish)

**Last night's results:**
- Lakers 108, Celtics 112 (Lakers lost by 4)
- Warriors 215, Nuggets 210 (Total: 425)

### You Run the Model Again
```bash
$ python nba_model_with_tracking.py
```

### What Happens

**Step 1: Check for Completed Games** (Automatic!)
```
🔄 Checking for completed games...

✅ Updated: Lakers vs Celtics - Spread - LOSS
   Lakers -6.0 line... Lakers lost by 4... didn't cover
   
❌ Updated: Warriors vs Nuggets - Total - LOSS  
   UNDER 220.5 line... game total 425... went over
```

**Step 2: Update Tracking Data**
```python
# Pick 1: Lakers -6.0
# Market line: -6.0, Actual margin: -4
# Lakers needed to win by 6+, only lost by 4 → LOSS

# Pick 2: UNDER 220.5
# Market total: 220.5, Actual total: 425
# Bet UNDER, went way OVER → LOSS
```

**Step 3: Generate Today's Picks**
```
Today's games:
Heat vs Bucks     (7:30 PM)
Suns vs Clippers  (10:00 PM)

📝 LOGGED: ✅ BET Heat +4.5 (Edge: +3.5)
(No confident total picks today)
```

### Updated Dashboard

**nba_tracking_dashboard.html** now shows:
```
🏀 NBA BET TRACKING
━━━━━━━━━━━━━━━━━━━━━━
📊 STATS
Total Bets: 2
Win Rate: 0.0%
Total Profit: -2.00u
ROI: -100.0%
━━━━━━━━━━━━━━━━━━━━━━
Wins: 0  Losses: 2  Pushes: 0

🎯 UPCOMING BETS
Date          Game            Type    Pick          Result
10/30 7:30PM  MIA vs MIL     Spread  Heat +4.5     Pending

📊 COMPLETED BETS
Date          Game            Type    Pick           Score     Result  Profit
10/29 7:00PM  LAL vs BOS     Spread  Lakers -6.0    108-112   ❌ Loss  -1.00u
10/29 9:00PM  GSW vs DEN     Total   UNDER 220.5    210-215   ❌ Loss  -1.00u
```

**nba_picks_tracking.json** updated:
```json
{
  "picks": [
    {
      "pick_id": "Lakers_Celtics_2025-10-29T23:00:00Z_spread",
      "status": "Complete",
      "result": "Loss",
      "actual_home_score": 108,
      "actual_away_score": 112,
      "profit_loss": -100
    },
    {
      "pick_id": "Nuggets_Warriors_2025-10-30T01:00:00Z_total",
      "status": "Complete",
      "result": "Loss",
      "actual_total": 425,
      "profit_loss": -100
    },
    {
      "pick_id": "Heat_Bucks_2025-10-30T23:30:00Z_spread",
      "status": "Pending",
      "profit_loss": 0
    }
  ],
  "summary": {
    "total_picks": 3,
    "pending": 1,
    "wins": 0,
    "losses": 2,
    "pushes": 0
  }
}
```

---

## 🗓️ Day 3: Thursday, 10:00 AM

**Last night's result:**
- Heat 105, Bucks 103 (Heat won!)

### You Run the Model
```bash
$ python nba_model_with_tracking.py
```

### What Happens

**Step 1: Check Completed Games**
```
✅ Updated: Heat vs Bucks - Spread - WIN!
   Heat +4.5 line... Heat won outright by 2... covered easily
```

**Step 2: Update Stats**
```python
# Pick 3: Heat +4.5
# Market line: +4.5, Actual margin: +2
# Heat needed to lose by less than 4.5, they WON → WIN!
# Profit: +0.909 units (90.91% of bet at -110 odds)
```

### Updated Dashboard

**nba_tracking_dashboard.html** shows:
```
🏀 NBA BET TRACKING
━━━━━━━━━━━━━━━━━━━━━━
📊 STATS
Total Bets: 3
Win Rate: 33.3%
Total Profit: -1.09u
ROI: -36.4%
━━━━━━━━━━━━━━━━━━━━━━
Wins: 1  Losses: 2  Pushes: 0

📊 COMPLETED BETS
Date          Game            Type    Pick           Score     Result  Profit
10/30 7:30PM  MIA vs MIL     Spread  Heat +4.5      105-103   ✅ Win   +0.91u
10/29 7:00PM  LAL vs BOS     Spread  Lakers -6.0    108-112   ❌ Loss  -1.00u
10/29 9:00PM  GSW vs DEN     Total   UNDER 220.5    210-215   ❌ Loss  -1.00u
```

---

## 🎯 Key Takeaways from Example

### Automatic Logging
- **Day 1**: Model found 2 picks with edge >= threshold → Automatically logged
- **Day 2**: Model found 1 pick with edge >= threshold → Automatically logged

### Automatic Result Updates
- **Day 2**: Checked Day 1 games, updated both picks to LOSS
- **Day 3**: Checked Day 2 game, updated to WIN

### Zero Manual Work
You never had to:
- ❌ Manually enter picks
- ❌ Look up game scores
- ❌ Calculate if you won/lost
- ❌ Update profit/loss
- ❌ Calculate win rate or ROI

Just run the script daily and check the dashboard!

---

## 📈 Understanding Edge & Thresholds

### Example Game: Lakers vs Celtics

**Market Line:** Lakers -6.0 (Lakers favored by 6)
**Model Line:** Lakers -2.8 (Lakers favored by 2.8)
**Edge Calculation:** -2.8 - (-6.0) = **+3.2 points**

**What This Means:**
- Market thinks Lakers win by 6
- Model thinks Lakers win by ~3
- Market is overvaluing Lakers by 3.2 points
- Betting **Lakers -6.0** has a +3.2 point edge

**Threshold Check:**
```python
if abs(edge) >= CONFIDENT_SPREAD_EDGE:  # 3.2 >= 3.0
    log_confident_pick()  # ✅ LOG IT!
```

### Example Total: Warriors vs Nuggets

**Market Total:** 220.5
**Model Total:** 216.0
**Edge:** 216.0 - 220.5 = **-4.5 points**

**What This Means:**
- Market expects ~221 total points
- Model expects ~216 total points
- Game likely to go UNDER by 4.5 points

**Threshold Check:**
```python
if abs(edge) >= CONFIDENT_TOTAL_EDGE:  # 4.5 >= 4.0
    log_confident_pick()  # ✅ LOG IT!
```

---

## 🔧 Customizing Your Tracking

Want to track MORE picks?
```python
CONFIDENT_SPREAD_EDGE = 2.0  # Lower threshold
CONFIDENT_TOTAL_EDGE = 3.0   # Lower threshold
```

Want to track FEWER picks?
```python
CONFIDENT_SPREAD_EDGE = 5.0  # Higher threshold
CONFIDENT_TOTAL_EDGE = 6.0   # Higher threshold
```

Want to track EVERYTHING?
```python
CONFIDENT_SPREAD_EDGE = 0.1  # Almost everything
CONFIDENT_TOTAL_EDGE = 0.1   # Almost everything
```

---

## 💡 Pro Tips

### Best Practice Workflow
```bash
# Morning (10 AM): Update yesterday's results
python nba_model_with_tracking.py

# Afternoon (4 PM): Check today's picks
open nba_model_output.html

# Evening (7 PM): Place your bets
# Based on what's in tracking dashboard

# Next morning: Repeat!
```

### Monitoring Performance
- Check dashboard weekly
- If win rate < 52.4%, you're losing money at -110 odds
- If ROI is negative, adjust thresholds or strategy
- Track separately: spreads vs totals, home vs away, etc.

### Understanding ROI
- **Break-even at -110 odds:** 52.4% win rate
- **Good ROI:** 5-10% long-term
- **Great ROI:** 10-15% long-term
- **Unrealistic:** 20%+ long-term

### Record Keeping
The JSON file is your official record:
- Backed up automatically each run
- Shows exact time picks were logged
- Includes all edge calculations
- Can export to Excel for analysis

---

## 📊 Dashboard Features Explained

### Summary Stats Card
```
Total Bets: 25     ← Completed bets (excludes pushes)
Win Rate: 56.0%    ← Wins / (Wins + Losses)
Total Profit: +2.27u  ← Net profit in units
ROI: +9.1%         ← (Profit / Risk) * 100
```

### Upcoming Bets Table
- Shows all pending picks
- Sorted by game date
- Shows your edge for reference
- Updates automatically when games complete

### Completed Bets Table
- Shows all past picks
- Color-coded results (green/red/gray)
- Actual scores displayed
- Running profit/loss

---

## 🎓 Advanced: Understanding the Code

If you want to customize further, here's what's happening:

### Pick Logging (Automatic)
```python
# In process_games() function
if abs(spread_edge) >= CONFIDENT_SPREAD_EDGE:
    log_confident_pick(
        game_data=result,
        pick_type='spread',
        edge=spread_edge,
        model_line=model_spread,
        market_line=home_spread
    )
```

### Result Updates (Automatic)
```python
# In update_pick_results() function
for days_ago in range(5):  # Check last 5 days
    # Fetch scoreboard from NBA API
    # Match games to pending picks
    # Calculate win/loss
    # Update JSON file
```

### Profit Calculation
```python
# Standard -110 odds (American odds)
if pick_won:
    profit = UNIT_SIZE * 0.909  # Win $90.91 on $100 bet
else:
    profit = -UNIT_SIZE  # Lose $100
```

---

## 🔚 That's Everything!

Your NBA tracking system is now identical to your NFL system:
- ✅ Automatic pick logging
- ✅ Automatic result updates
- ✅ Performance tracking
- ✅ Professional dashboard
- ✅ Zero manual work

Just run it daily and check your dashboard! 🎯🏀

**Questions? Check the README files or adjust the configuration variables at the top of the script.**
