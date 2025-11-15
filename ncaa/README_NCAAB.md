# 🏀 College Basketball Sharp Betting Model

**Target Win Rate: 56%+ | Advanced Analytics | Real-time Tracking**

A sophisticated college basketball betting model that leverages efficiency ratings, pace adjustments, home court advantage, and conference strength to identify sharp betting opportunities.

---

## 🎯 Key Features

### Core Model Components
- **Offensive/Defensive Efficiency Ratings** - Points per 100 possessions analysis
- **Pace Adjustments** - Accounts for tempo differences between teams
- **Home Court Advantage** - 3.5 point edge (stronger than NBA's 2.5)
- **Conference Strength Weighting** - Adjusts for quality of competition
- **Recent Form Analysis** - Emphasizes last 8 games (35% weight)
- **Home/Away Splits** - 55% weight on location-specific performance

### Sharp Betting Thresholds
- **Spread Picks**: Minimum 4.0 point edge required for tracking
- **Total Picks**: Minimum 5.0 point edge required for tracking
- **Display Thresholds**: Shows picks with 2.5+ (spread) and 4.0+ (total) edges

### Automated Tracking System
- ✅ Automatic score fetching from The Odds API
- 📊 Real-time win/loss/push tracking
- 💰 Profit/Loss calculations with standard -110 juice
- 📈 ROI and win rate analytics
- 🎯 Separate dashboards for upcoming and completed bets

---

## 📋 Requirements

### Python Dependencies
```bash
pip install requests python-dotenv jinja2 pytz pandas numpy --break-system-packages
```

### API Key (Free)
Get your free API key from [The Odds API](https://the-odds-api.com/)
- 500 free requests per month
- No credit card required

---

## ⚙️ Setup Instructions

### 1. Install Dependencies
```bash
pip install requests python-dotenv jinja2 pytz pandas numpy --break-system-packages
```

### 2. Create Environment File
Create a `.env` file in the same directory as the script:
```
ODDS_API_KEY=your_api_key_here
```

### 3. Run the Model
```bash
python ncaab_model_FINAL.py
```

---

## 📊 Output Files

The model generates three main files:

### 1. **ncaab_model_output.html** 
Beautiful web dashboard showing:
- Game matchups with times
- Model predictions vs market lines
- Confidence meters for each pick
- Spread and total recommendations
- Predicted final scores

### 2. **ncaab_tracking_dashboard.html**
Performance tracking dashboard with:
- Win rate and ROI statistics
- Upcoming bets table
- Recent results history
- Profit/loss tracking

### 3. **ncaab_model_output.csv**
Raw data export for:
- Spreadsheet analysis
- Historical tracking
- Custom reporting

---

## 🎲 How the Model Works

### Prediction Algorithm

1. **Base Efficiency Calculation**
   ```
   Points per 100 possessions = (Team Offensive Rating + Opponent Defensive Rating) / 2
   ```

2. **Pace Adjustment**
   ```
   Expected Points = Points per 100 * (Average Pace / 100)
   ```

3. **Home Court Advantage**
   ```
   Home Team: +1.75 points
   Away Team: -1.75 points
   ```

4. **Final Prediction**
   ```
   Spread = Home Points - Away Points
   Total = Home Points + Away Points
   ```

### Edge Calculation

**Spread Edge:**
```
Edge = Model Spread - Market Spread
```
- Positive edge = Home team undervalued
- Negative edge = Away team undervalued

**Total Edge:**
```
Edge = Model Total - Market Total  
```
- Positive edge = Bet OVER
- Negative edge = Bet UNDER

### Pick Selection

The model only logs confident picks:
- **Spread**: Edge ≥ 4.0 points
- **Total**: Edge ≥ 5.0 points

Lower edges (2.5+ and 4.0+) are displayed but not automatically tracked.

---

## 📈 College Basketball Specifics

### Why College is Different from NBA

| Factor | NBA | College Basketball |
|--------|-----|-------------------|
| Home Court Advantage | 2.5 pts | 3.5 pts |
| Recent Form Weight | 30% | 35% |
| Location Splits Weight | 50% | 55% |
| Spread Threshold | 3.0 pts | 4.0 pts |
| Total Threshold | 4.0 pts | 5.0 pts |

### Conference Strength Tiers

**Tier 1 (1.0x)**: Big Ten, SEC, Big 12, ACC, Big East
**Tier 2 (0.80-0.95x)**: Pac-12, Mountain West, WCC, American, A-10
**Tier 3 (0.60-0.75x)**: MVC, C-USA, Sun Belt, MAC, WAC
**Tier 4 (0.50x)**: Other conferences

---

## 🎯 Usage Tips

### Best Practices

1. **Run Daily** - Execute the script once per day to:
   - Update completed game results
   - Fetch new games
   - Generate fresh predictions

2. **Monitor Timing** - Run in the morning for:
   - Overnight game updates
   - Full day's slate of games
   - Best line value before movement

3. **Line Shopping** - Model shows best available lines:
   - Compare across multiple books
   - Jump on favorable lines early
   - Track line movements

4. **Bankroll Management**
   - Default unit size: $100 (configurable in script)
   - Recommended: 1-2% of bankroll per bet
   - Never chase losses

### Interpreting Confidence

**High Confidence (5+ point edge)**
- Strong statistical advantage
- Model has high conviction
- Consider standard unit size

**Medium Confidence (3-5 point edge)**  
- Solid edge but less certain
- Consider reduced unit size
- Good for parlays

**Low Confidence (<3 points)**
- Minimal edge
- Not tracked automatically
- Pass or very small unit

---

## 🔧 Customization

### Adjustable Parameters (in script)

```python
# Model thresholds
HOME_COURT_ADVANTAGE = 3.5     # Points added to home team
SPREAD_THRESHOLD = 2.5         # Min edge to display
TOTAL_THRESHOLD = 4.0          # Min edge to display

# Tracking thresholds  
CONFIDENT_SPREAD_EDGE = 4.0    # Min edge to log/track
CONFIDENT_TOTAL_EDGE = 5.0     # Min edge to log/track

# Time filters
DAYS_AHEAD_TO_FETCH = 7        # How many days to look ahead

# Form analysis
LAST_N_GAMES = 8               # Recent games for momentum
SEASON_WEIGHT = 0.65           # Weight on full season
FORM_WEIGHT = 0.35             # Weight on recent form
```

---

## 📱 Example Workflow

### Daily Routine

**Morning (9-10 AM ET)**
```bash
python ncaab_model_FINAL.py
```

**Review Output**
1. Open `ncaab_tracking_dashboard.html` - Check results from previous day
2. Open `ncaab_model_output.html` - Review today's picks
3. Compare edges and confidence levels
4. Place bets on highest-confidence plays

**Evening (After games)**
- Results automatically update next run
- Model fetches completed scores
- Tracking dashboard updates with W/L/P

---

## 🎲 Sample Output

### Terminal Display
```
━━━ GAME 1: Duke @ North Carolina ━━━
🕐 03/02 07:00 PM

📊 SPREAD:
  Market: -4.5 | Model: -2.1 | Edge: +2.4
  ✅ BET: Duke -4.5
  HIGH confidence (2.4 edge)

🎯 TOTAL:
  Market: 152.5 | Model: 157.8 | Edge: 5.3
  ✅ BET: OVER 152.5
  HIGH confidence (5.3 edge)

📈 PREDICTED: Duke 79.2, North Carolina 77.1
```

### Tracking Summary
```
📊 TRACKING SUMMARY 📊
Total Tracked Bets: 47
Record: 28-17-2
Win Rate: 62.2%
Profit: +8.73 units
ROI: +19.4%
```

---

## 🚨 Important Notes

### Data Sources
- **Odds Data**: The Odds API (real-time)
- **Team Stats**: Simulated efficiency ratings (can integrate with real stats API)
- **Scores**: The Odds API (for completed games)

### Limitations
- Model uses estimated team statistics by default
- For optimal performance, integrate with KenPom, Bart Torvik, or ESPN API
- College basketball has higher variance than NBA
- Injuries and lineup changes not factored in current version

### Future Enhancements
- Integration with KenPom efficiency data
- Player injury tracking
- Lineup analysis
- Situational factors (back-to-backs, rivalry games)
- Live betting recommendations
- Machine learning optimization

---

## 🛠️ Troubleshooting

### Common Issues

**"ODDS_API_KEY not found"**
- Ensure `.env` file is in the same directory
- Check for typos in the API key
- No spaces around the `=` sign

**"No games found"**
- College basketball season runs November-April
- Try increasing `DAYS_AHEAD_TO_FETCH`
- Check if games are available on The Odds API

**"Could not fetch scores"**
- Normal if no recent completed games
- Scores available after games complete
- API may have rate limits

**Import Errors**
- Run: `pip install [package] --break-system-packages`
- Ensure all dependencies installed
- Check Python version (3.7+ required)

---

## 📞 Support

For issues, questions, or suggestions:
- Check the troubleshooting section
- Review The Odds API documentation
- Verify all dependencies are installed
- Ensure API key is valid and has requests remaining

---

## ⚖️ Disclaimer

**For Entertainment Purposes Only**

This model is provided for educational and entertainment purposes. Sports betting involves risk, and past performance does not guarantee future results. Always:
- Bet responsibly
- Never bet more than you can afford to lose
- Follow local gambling laws and regulations
- Seek help if gambling becomes a problem

**Model Accuracy**
- Target win rate is a goal, not a guarantee
- Variance is inherent in sports betting
- Long-term results may vary significantly
- No model can predict outcomes with certainty

---

## 📊 Model Statistics

**Calibration Goals:**
- Win Rate: 56%+
- ROI: 8-12%
- Sharpe Ratio: 0.5+
- Maximum Drawdown: <15%

**Track these metrics over time to evaluate model performance!**

---

## 🎓 Understanding the Edge

### What is "Edge"?

Edge represents the difference between what the model thinks the line should be versus what the market offers.

**Example - Spread:**
- Market: Duke -5.5
- Model: Duke -8.2
- Edge: +2.7 points

This means the model thinks Duke should be favored by 8.2, but you can get them at -5.5. You're getting 2.7 points of value.

**Example - Total:**
- Market: 145.5
- Model: 151.3
- Edge: +5.8 points

Model projects 151 total points. At 145.5, there's value on the OVER.

### Why Thresholds Matter

Not all edges are created equal:
- **Small edges (1-2 pts)**: Could be noise, line shopping
- **Medium edges (3-4 pts)**: Legitimate value, worth betting
- **Large edges (5+ pts)**: Strong signals, highest confidence

The model's thresholds ensure only statistically significant edges are tracked.

---

## 🔥 Getting Started Quick Guide

**5-Minute Setup:**

1. Get API key: https://the-odds-api.com/
2. Create `.env` file with your key
3. Install dependencies: `pip install requests python-dotenv jinja2 pytz pandas numpy --break-system-packages`
4. Run: `python ncaab_model_FINAL.py`
5. Open `ncaab_model_output.html` in browser

That's it! You're ready to start finding sharp college basketball bets.

---

**Good luck, and bet responsibly! 🏀**
