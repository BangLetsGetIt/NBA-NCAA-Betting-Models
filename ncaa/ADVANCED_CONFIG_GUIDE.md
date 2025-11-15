# 🔧 Advanced Configuration & Optimization Guide

## College Basketball Model Tuning

This guide is for advanced users who want to optimize the model for maximum performance.

---

## 🎯 Model Optimization Parameters

### Current Default Settings

```python
# Home Court Advantage
HOME_COURT_ADVANTAGE = 3.5  # Points added to home team

# Display Thresholds (what shows in output)
SPREAD_THRESHOLD = 2.5      # Minimum edge to display spread
TOTAL_THRESHOLD = 4.0       # Minimum edge to display total

# Tracking Thresholds (what gets logged)
CONFIDENT_SPREAD_EDGE = 4.0 # Edge required to track spread bets
CONFIDENT_TOTAL_EDGE = 5.0  # Edge required to track total bets

# Form Analysis
LAST_N_GAMES = 8            # Recent games for momentum
SEASON_WEIGHT = 0.65        # Weight on full season stats
FORM_WEIGHT = 0.35          # Weight on recent form

# Home/Away Splits
SPLITS_WEIGHT = 0.55        # Weight on location-specific stats
COMPOSITE_WEIGHT = 0.45     # Weight on overall stats
```

---

## 📊 Tuning Home Court Advantage

### Default: 3.5 points

**Increase to 4.0-4.5 if:**
- Focusing on mid-major conferences (stronger home effect)
- Betting early season games (home court larger impact)
- Targeting teams with elite home records
- Small venues with rabid fanbases (Davidson, Gonzaga, etc.)

**Decrease to 3.0-3.2 if:**
- Focusing on power conferences (more balanced)
- Betting late season/tournament games
- Neutral site games (adjust to 0)
- Teams playing in temporary venues

**Code Location:** Line 51
```python
HOME_COURT_ADVANTAGE = 3.5  # Modify this value
```

---

## 🎲 Optimizing Bet Thresholds

### Spread Thresholds

**Display Threshold (currently 2.5)**

More aggressive (1.5-2.0):
- More picks shown
- More opportunities
- Lower quality on average
- Good for experienced bettors who can filter

More conservative (3.0-3.5):
- Fewer but sharper picks
- Higher expected win rate
- Miss some marginal value
- Better for beginners

**Tracking Threshold (currently 4.0)**

More aggressive (3.0-3.5):
- Track more bets
- More variance in results
- Potentially lower win rate
- Higher volume = more data

More conservative (4.5-5.0):
- Only elite picks tracked
- Higher expected win rate
- Fewer bets = slower bankroll growth
- Very selective approach

### Total Thresholds

**Display Threshold (currently 4.0)**

More aggressive (3.0-3.5):
- Totals are harder to predict
- Only recommended if you have edge in total betting
- More opportunities but lower accuracy

More conservative (4.5-5.5):
- Recommended for most users
- College totals have high variance
- Focus on clearest edges only

**Tracking Threshold (currently 5.0)**

This is already conservative. Only adjust if:
- You have historical success with totals: Lower to 4.0
- Totals haven't been profitable: Raise to 6.0

---

## 📈 Form vs Season Balance

### Current: 65% Season / 35% Form

**Increase Form Weight (40-45%) if:**
- Early in season (less season data)
- Focusing on teams with roster turnover
- Betting conference tournaments
- Teams showing clear momentum shifts

**Increase Season Weight (70-75%) if:**
- Late in regular season (more data)
- Betting on established programs
- Teams with consistent performance
- Playoff scenarios

**Code Location:** Lines 65-66
```python
SEASON_WEIGHT = 0.65    # Full season data weight
FORM_WEIGHT = 0.35      # Recent games weight
```

**Important:** These must sum to 1.0!

---

## 🏠 Home/Away Split Optimization

### Current: 55% Splits / 45% Composite

**Increase Split Weight (60-65%) if:**
- Clear home/away performance differences
- Road-heavy or home-heavy schedules
- Small conference games (home court matters more)
- Teams with extreme home/away splits

**Decrease Split Weight (45-50%) if:**
- Neutral site games (set to 0)
- Teams with balanced home/away records
- Late season (teams more consistent)
- Professional-style arenas (less home edge)

**Code Location:** Lines 69-70
```python
SPLITS_WEIGHT = 0.55        # Location-specific weight
COMPOSITE_WEIGHT = 0.45     # Overall stats weight
```

**Important:** These must sum to 1.0!

---

## 🔄 Recent Games Window

### Current: Last 8 Games

**Increase to 10-12 games if:**
- Mid to late season (more data available)
- Want smoother momentum indicators
- Teams with inconsistent performance
- Prefer less reactive model

**Decrease to 5-7 games if:**
- Early season or tournaments
- Want more reactive model
- Teams with clear trends
- Injury/lineup changes important

**Code Location:** Line 64
```python
LAST_N_GAMES = 8       # Number of recent games analyzed
```

---

## 💰 Unit Size Configuration

### Default: $100 per unit

**Adjust based on bankroll:**

| Bankroll | Conservative | Standard | Aggressive |
|----------|--------------|----------|------------|
| $1,000 | $10 (1%) | $20 (2%) | $30 (3%) |
| $5,000 | $50 (1%) | $100 (2%) | $150 (3%) |
| $10,000 | $100 (1%) | $200 (2%) | $300 (3%) |
| $25,000 | $250 (1%) | $500 (2%) | $750 (3%) |

**Code Location:** Line 58
```python
UNIT_SIZE = 100  # Your bet size in dollars
```

---

## 🎯 Advanced: Conference-Specific Tuning

### Creating Conference Profiles

You can optimize parameters for specific conferences:

**Example: Mid-Major Conference (More home court)**
```python
# Create a custom function
def get_home_advantage(conference):
    if conference in ["WCC", "A-10", "MVC"]:
        return 4.0  # Higher home court
    elif conference in ["Big Ten", "SEC", "ACC"]:
        return 3.2  # Lower home court
    else:
        return 3.5  # Default

HOME_COURT_ADVANTAGE = get_home_advantage(team_conference)
```

---

## 📊 Backtesting Your Settings

### How to Test Configuration Changes

1. **Save Original Settings**
   ```python
   # Keep a copy of default values
   ORIGINAL_HCA = 3.5
   ORIGINAL_SPREAD_THRESHOLD = 2.5
   # etc.
   ```

2. **Modify One Parameter at a Time**
   - Change only ONE setting
   - Run model for 2-3 weeks
   - Track results separately

3. **Compare Performance**
   - Win rate improvement?
   - ROI increase?
   - More/fewer picks?
   - Bankroll growth?

4. **Keep or Revert**
   - If better: Keep new setting
   - If worse: Revert to original
   - If unclear: Need more data

---

## 🧪 Recommended Testing Protocol

### Week 1: Baseline
- Use all default settings
- Track every result
- Note: Win rate, ROI, edge distribution

### Week 2-3: Test Variables
**Test 1:** Home Court Advantage
- Run with HCA = 3.0
- Run with HCA = 4.0
- Compare to baseline

**Test 2:** Thresholds
- Run with SPREAD_THRESHOLD = 2.0
- Run with SPREAD_THRESHOLD = 3.0
- Compare results

**Test 3:** Form Weight
- Run with FORM_WEIGHT = 0.25
- Run with FORM_WEIGHT = 0.45
- Compare outcomes

### Week 4: Combine Best Performers
- Use best settings from each test
- Monitor for 2+ weeks
- Validate improvements hold

---

## 📈 Performance Metrics to Track

### Essential Metrics

**Win Rate**
- Target: 56%+
- Minimum acceptable: 54%
- Elite: 58%+

**ROI (Return on Investment)**
- Target: 10-14%
- Minimum acceptable: 6%
- Elite: 15%+

**Sharpe Ratio**
- Target: 0.5-0.6
- Formula: (Average Return - Risk Free Rate) / Std Deviation
- Measures risk-adjusted returns

**Maximum Drawdown**
- Target: <15%
- Alert level: 20%
- Stop level: 25%

---

## 🎯 Optimal Settings by Betting Style

### Conservative Bettor
```python
HOME_COURT_ADVANTAGE = 3.5
SPREAD_THRESHOLD = 3.0
TOTAL_THRESHOLD = 5.0
CONFIDENT_SPREAD_EDGE = 4.5
CONFIDENT_TOTAL_EDGE = 6.0
LAST_N_GAMES = 10
SEASON_WEIGHT = 0.70
FORM_WEIGHT = 0.30
```
**Expected:** 57-58% win rate, 8-10% ROI, fewer bets

### Balanced Bettor (Default)
```python
HOME_COURT_ADVANTAGE = 3.5
SPREAD_THRESHOLD = 2.5
TOTAL_THRESHOLD = 4.0
CONFIDENT_SPREAD_EDGE = 4.0
CONFIDENT_TOTAL_EDGE = 5.0
LAST_N_GAMES = 8
SEASON_WEIGHT = 0.65
FORM_WEIGHT = 0.35
```
**Expected:** 56-57% win rate, 10-12% ROI, moderate volume

### Aggressive Bettor
```python
HOME_COURT_ADVANTAGE = 3.5
SPREAD_THRESHOLD = 2.0
TOTAL_THRESHOLD = 3.5
CONFIDENT_SPREAD_EDGE = 3.5
CONFIDENT_TOTAL_EDGE = 4.5
LAST_N_GAMES = 6
SEASON_WEIGHT = 0.60
FORM_WEIGHT = 0.40
```
**Expected:** 54-56% win rate, 12-15% ROI, high volume

---

## 🔥 Pro Optimization Tips

### 1. Conference Specialization
Focus on 2-3 conferences and tune for them specifically:
- Collect more data on these conferences
- Adjust home court for venue types
- Factor in travel distances
- Understand coaching styles

### 2. Situational Adjustments
Create rules for specific situations:
```python
# Example: Conference tournament adjustment
if is_conference_tournament:
    HOME_COURT_ADVANTAGE = 1.5  # Neutral site
    FORM_WEIGHT = 0.45  # Recent form matters more

# Example: Rivalry game adjustment
if is_rivalry_game:
    add_variance = 2.0  # Less predictable
    CONFIDENCE_MULTIPLIER = 0.8  # Lower confidence
```

### 3. Time-of-Season Adjustments
```python
if games_played < 10:  # Early season
    SEASON_WEIGHT = 0.50
    FORM_WEIGHT = 0.50
elif games_played > 25:  # Late season
    SEASON_WEIGHT = 0.75
    FORM_WEIGHT = 0.25
```

### 4. Rolling Optimization
Every 25-50 bets, review and adjust:
- Which edge ranges are winning?
- Are home favorites better than road?
- Are totals or spreads more profitable?
- Adjust thresholds accordingly

---

## 🚨 Warning Signs to Watch

### Red Flags for Settings

**Win rate < 52% for 50+ bets:**
- Thresholds too aggressive
- Increase CONFIDENT_SPREAD_EDGE by 0.5
- Increase CONFIDENT_TOTAL_EDGE by 0.5

**ROI < 5% despite >54% win rate:**
- Betting too many dogs/underdogs
- Juice is eating profits
- Need sharper edge selection

**High variance (big swings):**
- Too many total bets
- Increase TOTAL_THRESHOLD
- Focus more on spreads

**Too few picks (< 2 per week):**
- Thresholds too conservative
- Decrease SPREAD_THRESHOLD by 0.5
- Missing value opportunities

---

## 📊 A/B Testing Framework

### Run Parallel Configurations

**Setup:**
1. Create two copies of the model
2. Use different settings in each
3. Track separately for 100+ bets
4. Compare results statistically

**Example Test:**
```
Model A (Conservative): 
- CONFIDENT_SPREAD_EDGE = 4.5
- Result: 58% win rate, 9% ROI

Model B (Moderate):
- CONFIDENT_SPREAD_EDGE = 3.5  
- Result: 54% win rate, 11% ROI

Winner: Model B (higher ROI despite lower win rate)
```

---

## 💡 Final Optimization Checklist

✅ **Before Changing Settings:**
- [ ] Have at least 50 bets with current settings
- [ ] Document current performance metrics
- [ ] Change only one variable at a time
- [ ] Set evaluation period (minimum 50 bets)

✅ **During Testing:**
- [ ] Track results in separate spreadsheet
- [ ] Note any external factors (injuries, etc.)
- [ ] Don't change settings mid-test
- [ ] Stay disciplined with bankroll

✅ **After Testing:**
- [ ] Compare to baseline statistically
- [ ] Verify improvement is significant (not luck)
- [ ] Keep or revert based on data
- [ ] Document findings

---

## 🎯 Remember

**The best settings are:**
1. Backed by data (not hunches)
2. Appropriate for your bankroll
3. Matched to your risk tolerance
4. Proven over 100+ bets minimum
5. Adjusted seasonally as needed

**Don't:**
- Change settings after bad days
- Over-optimize on small samples
- Use too many custom adjustments
- Forget the fundamentals
- Chase losses by lowering thresholds

---

**Optimize smart. Test thoroughly. Bet sharp. 🏀**
