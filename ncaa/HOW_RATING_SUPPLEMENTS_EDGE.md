# How A.I. Rating System Supplements Edge-Based Approach

## Overview

The A.I. Rating system adds **contextual intelligence** to your raw edge calculations. Think of it as:
- **Edge** = "How big is the discrepancy?" (quantitative)
- **A.I. Rating** = "How trustworthy/actionable is this edge?" (qualitative + quantitative)

---

## 🎯 Five Ways Rating Supplements Edge

### 1. **Intelligent Prioritization**

**Current:** You sort by max edge
**With Rating:** Sort by rating, but keep edge visible

**Benefit:** Rating considers factors beyond raw edge:
- Historical model performance on similar games
- Data quality/consistency
- Market context (is this edge "real" or statistical noise?)
- Confidence in the underlying prediction

**Example:**
```
Game A: Edge = 8.0, Rating = 3.2  ← Lower rating (maybe inconsistent data)
Game B: Edge = 6.0, Rating = 4.1  ← Higher rating (more trustworthy)
```

With pure edge sorting, Game A appears first. With rating, Game B (more trustworthy) appears first.

---

### 2. **Better Risk Assessment**

**Current:** All edges are treated equally
**With Rating:** Distinguish high-confidence edges from risky edges

**Use Cases:**
- **High Edge + Low Rating** = Risky play (maybe pass or bet smaller)
- **High Edge + High Rating** = Premium play (consider larger bet)
- **Moderate Edge + High Rating** = Quality play (often better than high edge + low rating)

**Example Scenario:**
```
Game 1: Spread Edge = 10.0 pts, Rating = 2.8
  → Large edge, but low rating suggests:
     - Inconsistent team data
     - Model uncertainty
     - Market might be right for hidden reasons
  → Action: Smaller bet or pass

Game 2: Spread Edge = 5.5 pts, Rating = 4.2
  → Moderate edge, but high rating suggests:
     - Reliable data
     - Strong model confidence
     - Market likely mispriced
  → Action: Standard or larger bet
```

---

### 3. **Bet Sizing Intelligence**

**Current:** Same unit size for all bets above threshold
**With Rating:** Adjust bet size based on rating

**Proposed Bet Sizing:**
```python
if rating >= 4.5:
    bet_size = 2.0 units  # Premium plays
elif rating >= 4.0:
    bet_size = 1.5 units  # Strong plays
elif rating >= 3.5:
    bet_size = 1.0 units  # Standard plays
elif rating >= 3.0:
    bet_size = 0.75 units # Smaller plays
else:
    bet_size = 0.5 units  # Marginal plays
```

**Edge still matters:** Higher edge still increases bet size, but rating provides the baseline confidence.

---

### 4. **Quality Filtering (Beyond Edge Thresholds)**

**Current:** Display games if edge > threshold (2.0 spread, 3.0 total)
**With Rating:** Additional quality filter

**Dual-Filter Approach:**
```python
# Game qualifies if EITHER:
# 1. Meets edge threshold (your current logic)
# OR
# 2. High rating (even with lower edge - indicates quality matchup)

if (spread_edge >= SPREAD_THRESHOLD) OR (ai_rating >= 3.5):
    display_game()
```

**Why This Helps:**
- Catches quality plays that might have slightly lower edge
- Filters out questionable high-edge plays (low rating)
- Balances edge hunting with quality assessment

---

### 5. **Historical Performance Integration**

**Current:** Edge is calculated fresh each time
**With Rating:** Incorporates how your model has performed on similar games

**What Rating Can Track:**
- Model win rate on games with similar edge magnitude
- Performance on games with similar team strength differentials
- Success rate on games with similar market inefficiencies

**Example:**
```
Game: Edge = 6.0 pts
Historical Performance:
  - Games with 5-7 pt edge: 62% win rate (last 50 games)
  - Similar team matchup types: 58% win rate
  - This conference matchup: 65% win rate
  
→ Rating incorporates these factors
→ Higher historical performance = Higher rating
```

---

## 🔧 Practical Integration Strategy

### Hybrid Approach (Recommended)

**Keep Edge as Primary Signal, Use Rating for:**

1. **Sorting:** Sort by rating (or weighted combo: rating * 0.7 + normalized_edge * 0.3)
2. **Filtering:** Dual threshold (edge OR rating)
3. **Bet Sizing:** Rating-based unit sizing
4. **Display:** Show both edge and rating prominently
5. **Confidence:** Use rating to adjust confidence levels

---

## 📊 Rating Calculation Formula (Supplemental to Edge)

```python
def calculate_ai_rating(game_data, historical_performance, team_performance):
    """
    Calculate A.I. Rating that supplements (not replaces) edge calculation
    
    Rating considers:
    1. Normalized edge (0-5 scale)
    2. Data quality score
    3. Historical performance on similar games
    4. Model confidence indicators
    5. Team performance indicators
    """
    
    # 1. BASE: Normalized edge score
    max_edge = max(abs(game_data['spread_edge']), abs(game_data['total_edge']))
    normalized_edge = min(5.0, max_edge / 3.0)  # 15 edge = 5.0 rating
    
    # 2. DATA QUALITY FACTOR (0.85-1.0)
    # Penalty if data seems incomplete or inconsistent
    data_quality = 1.0
    if game_data.get('missing_recent_games', False):
        data_quality = 0.90
    if game_data.get('stats_age_days', 0) > 7:
        data_quality = 0.85
    
    # 3. HISTORICAL PERFORMANCE FACTOR (0.9-1.1)
    # How has model performed on similar games?
    similar_edge_range = f"{int(max_edge)-1}-{int(max_edge)+1}"
    hist_win_rate = historical_performance.get_win_rate(similar_edge_range)
    
    # Convert win rate to multiplier
    # 60% win rate = 1.0, 55% = 0.95, 65% = 1.05
    historical_factor = 0.9 + (hist_win_rate - 0.55) * 2.0
    historical_factor = max(0.9, min(1.1, historical_factor))
    
    # 4. MODEL CONFIDENCE FACTOR (0.85-1.15)
    # Based on prediction stability, data consistency
    confidence = 1.0
    if game_data.get('spread_edge', 0) >= 12:
        confidence = 1.10  # Very large edges = higher confidence
    elif game_data.get('spread_edge', 0) >= 8:
        confidence = 1.05
    elif game_data.get('spread_edge', 0) < 4:
        confidence = 0.95  # Smaller edges = slightly lower confidence
    
    # 5. TEAM PERFORMANCE INDICATOR FACTOR (0.9-1.1)
    # Boost rating if betting on historically profitable team
    team_factor = 1.0
    team_indicator = game_data.get('team_indicator')
    if team_indicator:
        if team_indicator['label'] in ['HOT', 'GOOD']:
            team_factor = 1.05  # Small boost for proven teams
        elif team_indicator['label'] in ['COLD']:
            team_factor = 0.95  # Small penalty for cold teams
    
    # 6. CALCULATE COMPOSITE RATING
    base_rating = normalized_edge
    
    # Apply factors (multiplicative)
    composite_rating = (
        base_rating * 
        data_quality * 
        historical_factor * 
        confidence * 
        team_factor
    )
    
    # 7. SCALE TO 2.3-4.9 RANGE (matching reference model)
    # This ensures rating is always in the observed range
    # Maps 0-5 range to 2.3-4.9 range
    ai_rating = 2.3 + (composite_rating / 5.0) * 2.6
    ai_rating = max(2.3, min(4.9, ai_rating))  # Clamp to range
    
    return round(ai_rating, 1)
```

---

## 🎯 Output Integration Example

### Current Output:
```
Matchup: Team A @ Team B
Spread: Market +3.5 | Model +10.1 | Edge: +6.6
Total: Market 145 | Model 160 | Edge: +15
Pick: ✅ BET: Team B +3.5 | ✅ BET: OVER 145
```

### Enhanced Output (With Rating):
```
Matchup: Team A @ Team B
A.I. Rating: 4.2 ⭐⭐⭐⭐ (Strong Play)

Spread: Market +3.5 | Model +10.1 | Edge: +6.6
Total: Market 145 | Model 160 | Edge: +15
Pick: ✅ BET: Team B +3.5 | ✅ BET: OVER 145

Rating Factors:
  • Edge Score: 4.4/5.0 (High edge)
  • Data Quality: 100% (Complete stats)
  • Historical Performance: +5% (65% win rate on similar)
  • Model Confidence: 105% (Large, stable edge)
  • Team Indicator: 105% (Team B is HOT: 8-2, 72%)
```

---

## 📈 Sorting Strategy Options

### Option 1: Pure Rating Sort
```python
sorted_results = sorted(results, key=lambda x: x['ai_rating'], reverse=True)
```
**Pro:** Prioritizes quality/trustworthiness
**Con:** Might de-prioritize very large edges

### Option 2: Weighted Combination (Recommended)
```python
def get_sort_score(game):
    normalized_edge = min(5.0, max(abs(game['spread_edge']), abs(game['total_edge'])) / 3.0)
    rating_score = (game['ai_rating'] - 2.3) / 2.6  # Normalize rating to 0-1
    # 70% weight on rating, 30% on edge
    return rating_score * 0.7 + normalized_edge * 0.3

sorted_results = sorted(results, key=get_sort_score, reverse=True)
```
**Pro:** Balances both edge and quality
**Con:** More complex

### Option 3: Rating Primary, Edge Tiebreaker
```python
sorted_results = sorted(results, 
    key=lambda x: (x['ai_rating'], max(abs(x['spread_edge']), abs(x['total_edge']))), 
    reverse=True
)
```
**Pro:** Simple, rating-first approach
**Con:** Less nuanced

---

## 🎲 Bet Sizing Integration

```python
def calculate_bet_size(game_data, base_unit=1.0):
    """
    Calculate bet size based on both edge and rating
    """
    rating = game_data['ai_rating']
    max_edge = max(abs(game_data['spread_edge']), abs(game_data['total_edge']))
    
    # Base size from rating
    if rating >= 4.5:
        base_size = 2.0
    elif rating >= 4.0:
        base_size = 1.5
    elif rating >= 3.5:
        base_size = 1.0
    elif rating >= 3.0:
        base_size = 0.75
    else:
        base_size = 0.5
    
    # Edge multiplier (very large edges get boost)
    if max_edge >= 10:
        edge_multiplier = 1.25
    elif max_edge >= 8:
        edge_multiplier = 1.15
    elif max_edge >= 6:
        edge_multiplier = 1.05
    else:
        edge_multiplier = 1.0
    
    final_size = base_size * edge_multiplier * base_unit
    return round(final_size, 2)
```

**Example:**
- Rating 4.2, Edge 6.5 → 1.5 units (rating 4.0+ = 1.5, edge 6.5 = 1.05x) = **1.58 units**
- Rating 3.2, Edge 11.0 → 0.75 units (rating 3.0+ = 0.75, edge 11.0 = 1.25x) = **0.94 units**
- Rating 4.6, Edge 8.5 → 2.0 units (rating 4.5+ = 2.0, edge 8.5 = 1.15x) = **2.30 units**

---

## ✅ Key Takeaways

1. **Edge = Signal Strength** (How big is the opportunity?)
2. **Rating = Signal Quality** (How trustworthy is the opportunity?)

3. **Use Edge For:**
   - Initial filtering (meets threshold?)
   - Calculating bet size (larger edge = larger bet)
   - Understanding magnitude of discrepancy

4. **Use Rating For:**
   - Prioritization (which bets to focus on)
   - Risk assessment (trustworthy or risky?)
   - Bet sizing baseline (confidence level)
   - Quality filtering (separate good edges from bad edges)

5. **Best Approach:**
   - Calculate edge first (your current system)
   - Calculate rating second (supplemental layer)
   - Use both in combination for optimal decision-making
   - Display both prominently in output

---

## 🔄 Implementation Priority

**Phase 1: Basic Rating (No changes to edge logic)**
- Add rating calculation function
- Display rating alongside edge in output
- Sort by rating instead of pure edge

**Phase 2: Enhanced Rating (Integrate factors)**
- Add historical performance tracking
- Incorporate data quality assessment
- Add team performance indicators

**Phase 3: Advanced Integration**
- Rating-based bet sizing
- Dual-filtering (edge OR rating)
- Rating breakdown in output

---

**Bottom Line:** Rating doesn't replace edge—it adds context and intelligence to help you make better decisions about which edges to trust and how to size bets.
