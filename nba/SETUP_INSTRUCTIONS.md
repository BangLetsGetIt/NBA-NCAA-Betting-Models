# NBA Model - Setup & Usage Instructions

## 🎯 IMPROVEMENTS MADE

### Critical Fixes:
1. ✅ **Fixed 0.0 Prediction Bug** - Added comprehensive error handling and validation
2. ✅ **Improved Statistical Formula** - Better calculation including defensive ratings
3. ✅ **Added Rest Day Tracking** - Detects back-to-back games and adjusts predictions
4. ✅ **Increased Edge Thresholds** - Now requires 5+ points for spreads, 7+ for totals
5. ✅ **Better Home Court Advantage** - Increased from 2.5 to 3.5 points
6. ✅ **Data Validation** - Rejects extreme/suspicious lines (>25 spread, <180 or >260 totals)
7. ✅ **Enhanced Error Handling** - Won't crash on missing team data
8. ✅ **Automated Tracking** - Automatically updates results when games complete

### New Features:
- 🏃 **Back-to-Back Detection** - Penalizes teams playing on consecutive days (-2.5 points)
- 😴 **Rest Advantage** - Bonuses when opponent is on B2B (+1.5 points)
- 📊 **Improved Total Formula** - Now factors in both offense AND defense properly
- 🎯 **Stricter Pick Criteria** - Only logs bets with significant edges
- 📈 **Better Tracking Dashboard** - Cleaner visualization of performance

---

## 📋 SETUP INSTRUCTIONS

### Step 1: Get Your API Key

1. Go to https://the-odds-api.com/
2. Sign up for a free account
3. Get your API key from the dashboard
4. Free tier gives you 500 requests/month (plenty for daily use)

### Step 2: Create .env File

Create a file called `.env` in `/Users/rico/Downloads/` with this content:

```
ODDS_API_KEY=your_api_key_here
```

Replace `your_api_key_here` with your actual API key.

### Step 3: Install Required Packages

Run this command to install all dependencies:

```bash
pip3 install requests python-dotenv jinja2 pytz pandas nba-api
```

---

## 🚀 HOW TO USE

### Manual Run (Daily):

```bash
cd /Users/rico/Downloads
python3 nba_model_IMPROVED.py
```

This will:
1. Check for completed games and update past picks
2. Fetch fresh NBA stats (cached for 6 hours)
3. Get current odds from The Odds API
4. Generate predictions and identify value bets
5. Save results to HTML/CSV files
6. Update tracking dashboard

### Output Files:

- `nba_model_output.html` - Formatted predictions for today's games
- `nba_model_output.csv` - Raw data in spreadsheet format
- `nba_tracking_dashboard.html` - Your betting performance tracker
- `nba_picks_tracking.json` - Historical picks database

---

## 📊 UNDERSTANDING THE MODEL

### Edge Calculations:

**Spread Edge:**
- Model projects outcome (e.g., Lakers -5.2)
- Market has Lakers -3.5
- Edge = -5.2 + (-3.5) = -8.7 points
- If edge > 5 points → LOG THE BET

**Total Edge:**
- Model projects 218.5 total points
- Market has 225.5
- Edge = 218.5 - 225.5 = -7.0
- If edge > 7 points → LOG THE BET (UNDER)

### What Gets Logged vs. What Gets Shown:

**Shown in Output (Display Threshold):**
- Spread edge: 3+ points
- Total edge: 4+ points

**Logged for Tracking (Confident Bets):**
- Spread edge: 5+ points ← These are your ACTUAL bets
- Total edge: 7+ points ← These are your ACTUAL bets

This 2-tier system lets you see all interesting opportunities but only tracks the highest-confidence plays.

---

## 🤖 AUTOMATION SETUP

### Option 1: Run Daily with Cron (Mac/Linux)

Edit your crontab:
```bash
crontab -e
```

Add this line to run at 10 AM daily:
```
0 10 * * * cd /Users/rico/Downloads && /usr/local/bin/python3 nba_model_IMPROVED.py >> nba_model.log 2>&1
```

### Option 2: Run with Automator (Mac)

1. Open Automator
2. Create new "Calendar Alarm"
3. Add "Run Shell Script" action
4. Paste:
   ```bash
   cd /Users/rico/Downloads
   /usr/local/bin/python3 nba_model_IMPROVED.py
   ```
5. Set to run daily at 10 AM

---

## 💰 BETTING STRATEGY

### Bankroll Management (CRITICAL):

**Never bet more than 1-2% of your bankroll per bet.**

Example with $1000 bankroll:
- Unit size: $10-20 per bet
- Even at 55% win rate, variance can cause 10-game losing streaks
- Proper bankroll management prevents going broke during cold runs

### When to Bet:

**Only bet picks that appear in `nba_picks_tracking.json`**

These are the 5+ spread / 7+ total edge bets - the model's highest confidence plays.

### What Win Rate to Expect:

- **52.4%** = Break-even at -110 odds
- **53-56%** = Realistic target for good models
- **58%+** = Exceptional (professional level)

Don't expect to win 70%+. Even the best bettors in the world hit ~55-58%.

### Track Closing Line Value (CLV):

More important than short-term W/L is whether you're beating the closing line:
- If you bet Lakers -3.5 and line closes at -5.0 → Good bet (even if it loses)
- If you bet Lakers -3.5 and line closes at -2.0 → Bad bet (even if it wins)

**Positive CLV = Long-term profitability**

---

## 🔧 ADJUSTING THE MODEL

### If Too Many Bets:

Increase thresholds in the model file:
```python
CONFIDENT_SPREAD_EDGE = 6.0  # Was 5.0
CONFIDENT_TOTAL_EDGE = 8.0   # Was 7.0
```

### If Too Few Bets:

Decrease thresholds:
```python
CONFIDENT_SPREAD_EDGE = 4.0  # Was 5.0
CONFIDENT_TOTAL_EDGE = 6.0   # Was 7.0
```

### Adjusting Home Court Advantage:

```python
HOME_COURT_ADVANTAGE = 3.5  # Increase if home teams undervalued
```

### Adjusting Back-to-Back Penalty:

```python
BACK_TO_BACK_PENALTY = -3.0  # Increase if B2B teams underperforming
```

---

## 📈 MONITORING PERFORMANCE

### Daily Routine:

1. **Morning (10 AM):**
   - Run the model
   - Review `nba_model_output.html` for today's games
   - Check `nba_tracking_dashboard.html` for pending bets

2. **Before Betting:**
   - Only bet picks logged in tracking file
   - Check for line movement (if line moved in your favor, bet bigger; if against, bet smaller or skip)
   - Check injury reports before betting

3. **After Games (Next Morning):**
   - Run model again to update results
   - Review tracking dashboard for W/L
   - Track your actual profit vs. model profit

### Red Flags to Watch:

- ❌ Win rate < 50% after 50+ bets → Model not working
- ❌ Negative CLV consistently → Bad timing or worse lines
- ❌ Model projecting 0.0 for teams → Data issue, don't bet
- ❌ Extreme lines (>250 totals) → Skip these games

### Green Flags:

- ✅ Win rate 53%+ after 50+ bets
- ✅ Positive CLV on most bets
- ✅ Model identifies B2B situations correctly
- ✅ Predictions seem reasonable (200-240 totals, realistic spreads)

---

## 🐛 TROUBLESHOOTING

### "FATAL: ODDS_API_KEY not found"
- Check `.env` file exists in `/Users/rico/Downloads/`
- Check API key is correct (no quotes needed)

### "Missing stats for team X"
- Stats cache might be corrupted
- Delete `nba_stats_cache.json` and `nba_home_away_splits_cache.json`
- Run model again to fetch fresh data

### "No games found"
- Check API key still has requests remaining (500/month free)
- Might be off-season or no games in next 7 days

### Model predicting 0.0:
- Missing team in stats cache
- Run model with fresh stats (delete cache files)
- Check team name normalization

---

## 📝 IMPORTANT DISCLAIMERS

⚠️ **This model is for EDUCATIONAL purposes**

- No betting model guarantees profits
- Past performance doesn't guarantee future results
- Only bet what you can afford to lose
- Gambling should be recreational, not income
- Check local laws (sports betting illegal in some jurisdictions)

⚠️ **Start Small:**

- Track model performance for 50-100 bets before betting real money
- Start with paper trading (tracking without real bets)
- Verify the model is actually beating the closing line
- Only increase stakes after proven profitability

---

## 🎓 NEXT STEPS TO IMPROVE

After you have 100+ tracked bets, consider:

1. **Line Shopping** - Compare lines across multiple sportsbooks
2. **Player Props** - Extend model to player performance bets
3. **In-Game Betting** - Use live stats to find value during games
4. **ML Models** - Replace simple formulas with regression/neural nets
5. **Advanced Metrics** - Add true shooting %, effective FG%, etc.
6. **Injury Impact** - Integrate real-time injury data with impact weights
7. **Referee Analysis** - Some refs favor over/under differently
8. **Travel Distance** - Account for cross-country road trips

---

## 📞 SUPPORT

If you have issues:

1. Check the troubleshooting section above
2. Review the error messages in terminal
3. Verify all dependencies installed correctly
4. Check The Odds API status/limits

Good luck! Remember: Profit comes from discipline, not predictions. Stick to the system, manage your bankroll, and track everything. 🏀💰
