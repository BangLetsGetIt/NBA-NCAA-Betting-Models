# NCAAB Model Comparison: Reference vs Current Model

## Analysis Date
December 13, 2025

## Overview
This document compares the reference CBB model output (from @ThePropDealer) with the current ncaab model implementation.

---

## 1. OUTPUT STRUCTURE COMPARISON

### Reference Model Output
**Columns:**
- Away Team
- Away Team Projected Score (can be missing)
- @ (separator)
- Home Team
- Home Team Projected Score (can be missing)
- Time (ET)
- **A.I. Rating** (2.3 - 4.9 range) ⭐ KEY FEATURE

**Sorting:** Games sorted by A.I. Rating (descending)

### Current Model Output
**Columns:**
- GameTime
- Matchup (Away @ Home)
- Market Spread / Model Spread / Spread Edge
- Market Total / Model Total / Total Edge
- ATS Pick (with ✅ BET or ❌ NO BET)
- Total Pick (with ✅ BET or ❌ NO BET)
- Predicted Score (always shown if stats available)
- Team Performance Indicator

**Sorting:** Games sorted by maximum edge (spread or total)

---

## 2. KEY DIFFERENCES

### 2.1 A.I. Rating System ⭐ MAJOR DIFFERENCE

**Reference Model:**
- Has an "A.I. Rating" column (2.3 to 4.9 range)
- Rating appears to be a composite confidence/value score
- Games are **always shown** if they have a rating, even without projected scores
- High ratings (4.9) can appear without explicit score projections
- Rating seems to indicate overall betting opportunity quality

**Current Model:**
- **NO A.I. Rating system** - uses edge-based thresholds instead
- Uses confidence levels: LOW, MEDIUM, HIGH, VERY HIGH (derived from edge)
- Games only shown if they meet threshold criteria OR if stats/odds are available
- Confidence is calculated from edge magnitude:
  - Spread: >=12 = VERY HIGH, >=8 = HIGH, >=6 = MEDIUM, else = LOW
  - Total: >=14 = VERY HIGH, >=10 = HIGH, >=7 = MEDIUM, else = LOW

**Inference:** Reference model's A.I. Rating likely combines:
- Edge magnitude (similar to current model)
- Model confidence in prediction quality
- Market efficiency assessment
- Possibly historical performance factors
- Maybe team strength/quality indicators

---

### 2.2 Game Display Logic

**Reference Model:**
- Shows games with high A.I. Ratings even when projected scores are missing
- Suggests the rating is a standalone indicator of betting value
- Missing scores might indicate:
  - Moneyline value instead of spread/total
  - Insufficient data for specific score prediction but enough for rating
  - Rating based on other factors (matchup quality, situational value)

**Current Model:**
- Requires both team stats AND odds data to display games
- Always provides predicted scores (if stats available)
- Skips games without complete data (stats OR odds missing)
- Always shows both spread and total analysis (even if "NO BET")

**Code Location:** `process_games()` function around lines 858-1030

---

### 2.3 Scoring and Projection Logic

**Reference Model:**
- Some games have missing projected scores (especially high-rated ones)
- Suggests selective scoring - only scores when specific conditions met
- High rating without scores might indicate:
  - Quality matchup worth highlighting
  - Value in moneyline rather than spread/total
  - Model confidence in outcome direction but not exact margin

**Current Model:**
- Always calculates and displays projected scores when stats available
- Score calculation in `predict_game()` function (lines 1032-1092)
- Uses:
  - Offensive/Defensive efficiency ratings (60/40 weighting)
  - Pace adjustments
  - Home court advantage (3.2 points)
  - Regression to mean for extreme predictions

---

### 2.4 Betting Threshold Logic

**Reference Model:**
- A.I. Rating appears to be the primary filter (range 2.3-4.9)
- No explicit edge thresholds visible
- High rating = actionable bet (even without scores)

**Current Model:**
- Uses explicit edge thresholds:
  - `SPREAD_THRESHOLD = 2.0` (display threshold)
  - `TOTAL_THRESHOLD = 3.0` (display threshold)
  - `CONFIDENT_SPREAD_EDGE = 3.0` (logging threshold)
  - `CONFIDENT_TOTAL_EDGE = 4.0` (logging threshold)
- Games can be shown even with "NO BET" if they have stats/odds
- Separate thresholds for display vs. confident picks

**Code Location:** Lines 60-67 in config section

---

### 2.5 Sorting and Prioritization

**Reference Model:**
- Sorted by **A.I. Rating** (descending)
- Highest rated games at top
- Rating appears to be composite metric

**Current Model:**
- Sorted by **maximum edge** (spread or total, whichever is higher)
- Function: `get_max_edge()` at lines 2275-2279
- Highest edge games first

**Inference:** Reference model's rating likely considers more than just edge:
- Historical model performance on similar games
- Matchup quality indicators
- Market efficiency factors
- Possibly Kelly Criterion or EV calculations
- Confidence in data quality

---

### 2.6 Data Requirements

**Reference Model:**
- Appears to show games with ratings even without scores
- Suggests more flexible data requirements
- Might use alternative data sources when primary unavailable

**Current Model:**
- Strict requirements:
  - Must have team stats (from Sports-Reference)
  - Must have odds (spreads AND totals)
  - Skips games if either missing
- Uses `fetch_team_stats()` for stats
- Uses `fetch_odds()` from The Odds API

**Code Location:** `process_games()` lines 871-900

---

## 3. POTENTIAL BETTING LOGIC INFERENCE

### Reference Model Logic (Inferred)
1. **Rating Calculation** (hypothetical):
   - Base edge calculation (similar to current model)
   - Confidence adjustment (based on data quality/consistency)
   - Historical performance factor (how model performs on similar matchups)
   - Market efficiency score (how mispriced the line appears)
   - Combined into 2.3-4.9 rating scale

2. **Display Logic**:
   - If rating >= threshold (maybe 2.5-3.0?), show game
   - If high confidence in specific bet, show scores
   - If value is in moneyline/direction only, show rating without scores

3. **Betting Priority**:
   - Higher rating = better bet
   - 4.5+ rating = premium plays
   - 3.5-4.4 = strong plays
   - 2.5-3.4 = standard plays
   - <2.5 = likely filtered out

### Current Model Logic
1. **Edge Calculation**:
   - Model spread vs market spread → spread edge
   - Model total vs market total → total edge
   - Simple difference calculation

2. **Display Logic**:
   - If spread_edge > SPREAD_THRESHOLD (2.0) → show spread bet
   - If total_edge > TOTAL_THRESHOLD (3.0) → show total bet
   - Always show predicted scores if stats available

3. **Betting Priority**:
   - Sorted by max edge
   - Higher edge = more confidence
   - Explicit confidence levels based on edge magnitude

---

## 4. KEY IMPLEMENTATION DIFFERENCES

### 4.1 Missing Features in Current Model

1. **No A.I. Rating System**
   - Current model lacks composite rating metric
   - Uses edge directly instead of normalized rating

2. **No Flexible Scoring**
   - Always shows scores when stats available
   - Doesn't differentiate between high-confidence scoring vs rating-only displays

3. **Stricter Data Requirements**
   - Skips games without complete data
   - Reference model seems more flexible

4. **No Rating-Based Filtering**
   - Current model uses edge thresholds
   - Reference model uses rating-based prioritization

### 4.2 Advantages of Current Model

1. **Transparency**
   - Shows explicit edges and calculations
   - Clear confidence levels
   - Always provides score predictions when possible

2. **Detailed Analysis**
   - Shows both spread and total analysis
   - Team performance indicators
   - Market vs model comparisons

3. **Explicit Thresholds**
   - Clear betting criteria
   - Easy to adjust and understand

---

## 5. RECOMMENDATIONS FOR ALIGNMENT

### Option 1: Add A.I. Rating System (Preserve Current Features)
- Calculate composite A.I. Rating (2.3-4.9 scale) from:
  - Edge magnitude (normalized)
  - Model confidence
  - Historical performance on similar games
  - Data quality score
- Add A.I. Rating column to output
- Sort by A.I. Rating instead of edge
- Keep current edge/threshold system as secondary

### Option 2: Implement Selective Scoring
- Only show projected scores when:
  - High confidence in specific bet (spread/total)
  - Sufficient data quality
  - Rating indicates detailed prediction value
- Show rating-only for:
  - High-value matchups without clear spread/total edge
  - Moneyline value scenarios
  - Situational plays

### Option 3: Hybrid Approach (RECOMMENDED)
1. **Keep current edge calculations**
2. **Add A.I. Rating as composite metric**:
   ```
   Base Rating = Normalized Edge (0-5 scale)
   Confidence Multiplier = Model confidence (0.8-1.2)
   Historical Factor = Performance on similar games (0.9-1.1)
   Data Quality Factor = Stats/odds completeness (0.8-1.0)
   
   A.I. Rating = Base Rating × Confidence × Historical × Data Quality
   ```
3. **Add rating column and sort by it**
4. **Allow games with high ratings but missing scores**
5. **Maintain current detailed analysis for games with scores**

---

## 6. RATING CALCULATION PROPOSAL

### Hypothetical A.I. Rating Formula

```python
def calculate_ai_rating(game_data, historical_performance, model_confidence):
    # 1. Base edge score (normalized to 0-5 scale)
    max_edge = max(abs(game_data['spread_edge']), abs(game_data['total_edge']))
    base_score = min(5.0, max_edge / 3.0)  # Normalize: 15 edge = 5.0 rating
    
    # 2. Confidence multiplier (based on data quality and model certainty)
    confidence = model_confidence  # 0.8 to 1.2 range
    
    # 3. Historical performance factor
    # How has model performed on similar games?
    historical_factor = historical_performance.get_similar_game_performance()  # 0.9 to 1.1
    
    # 4. Data quality factor
    has_scores = game_data.get('predicted_score') is not None
    data_quality = 1.0 if has_scores else 0.85  # Slight penalty for missing scores
    
    # 5. Calculate final rating
    ai_rating = base_score * confidence * historical_factor * data_quality
    
    # 6. Scale to 2.3-4.9 range (based on reference model)
    # Shift and compress the 0-5 scale to 2.3-4.9
    ai_rating = 2.3 + (ai_rating / 5.0) * 2.6  # Maps 0→2.3, 5→4.9
    
    return round(ai_rating, 1)
```

### Rating Interpretation
- **4.5-4.9**: Premium plays, highest confidence
- **4.0-4.4**: Strong plays, high confidence
- **3.5-3.9**: Good plays, medium-high confidence
- **3.0-3.4**: Standard plays, medium confidence
- **2.5-2.9**: Marginal plays, lower confidence
- **<2.5**: Likely filtered out

---

## 7. NEXT STEPS

Before implementing changes:
1. ✅ Analyze reference model structure (DONE)
2. ✅ Document differences (DONE)
3. ⏳ Review with user
4. ⏳ Decide on implementation approach
5. ⏳ Implement chosen approach
6. ⏳ Test and validate

---

## 8. QUESTIONS FOR USER

1. Do you want to implement the A.I. Rating system?
2. Should we keep current edge-based system as secondary information?
3. Should games with high ratings but missing scores be displayed?
4. What historical performance data is available for rating calculation?
5. Should we maintain current detailed output format or simplify to match reference?
