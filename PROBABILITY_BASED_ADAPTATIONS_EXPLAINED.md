# Probability-Based Adaptations Explained

## 🎯 The Key Difference

### **Team Models (Edge-Based)**
Use **point differences** as edges:
- Model predicts: **Team wins by 10.5 points**
- Market line: **Team -3.5**
- **Edge = 10.5 - 3.5 = 7.0 points**

This is straightforward - you're comparing two point predictions.

---

### **Props Models (Probability-Based)**
Use **probability differences** as edges:
- Model calculates: **Player has 65% chance to score 25+ points**
- Market odds: **-110 (52.4% implied probability)**
- **Edge = 65% - 52.4% = 12.6% probability**

This requires converting odds to probabilities, then comparing probabilities.

---

## 📊 How Props Models Work

### Step 1: Calculate Model Probability

Props models predict the **probability** a player will hit the prop:

```python
# Example: Points prop
prop_line = 25.5  # Over/Under 25.5 points

# Model calculates:
season_avg = 27.3 points
recent_avg = 28.5 points
opponent_defense_rating = 0.95  # Allows 5% more points than average

# Combine factors to get predicted points
predicted_points = (season_avg * 0.6 + recent_avg * 0.4) * opponent_defense_rating
# predicted_points = 27.8

# Convert to probability (using statistical distribution)
model_probability = calculate_probability(predicted_points, prop_line)
# model_probability = 0.65 (65% chance to go OVER 25.5)
```

### Step 2: Get Market Implied Probability

Convert betting odds to implied probability:

```python
# Market odds: -110 (American odds)
# Convert to implied probability
implied_prob = american_to_implied_prob(-110)
# implied_prob = 0.524 (52.4%)

# This means: Book thinks 52.4% chance player goes OVER
```

### Step 3: Calculate Edge

**Edge = Model Probability - Market Probability**

```python
edge = model_probability - implied_prob
edge = 0.65 - 0.524
edge = 0.126  # 12.6% edge

# This means: Model thinks 12.6% higher chance than the market
```

### Step 4: Calculate Expected Value (EV)

**EV = (Edge × Win Amount) - ((1 - Model Prob) × Loss Amount)**

```python
# Bet $110 to win $100 (-110 odds)
if model_probability > implied_prob:
    ev = (model_probability * 100) - ((1 - model_probability) * 110)
    ev = (0.65 * 100) - (0.35 * 110)
    ev = 65 - 38.50
    ev = +26.50  # Positive EV = good bet
```

---

## 🔄 Why Adaptations Are Needed

### Current Rating System (Point-Based)

For team models, we normalize edges like this:

```python
# Point-based normalization
max_edge = 7.0  # points
normalized_edge = max_edge / 3.0  # 15 points = 5.0 rating
# normalized_edge = 2.33
```

**Problem:** This doesn't work for probability edges!

### Needed: Probability-Based Normalization

For props models, we need to normalize probability edges:

```python
# Probability-based normalization
max_edge = 0.126  # 12.6% probability edge
normalized_edge = max_edge / 0.03  # 15% probability = 5.0 rating
# normalized_edge = 4.2
```

---

## 📐 Adaptation Formula

### Current (Point-Based) Normalization:
```python
# For team models (points/goals)
if max_edge >= 15:
    normalized_edge = 5.0
else:
    normalized_edge = max_edge / 3.0  # 15 points = 5.0 rating
```

### Adapted (Probability-Based) Normalization:
```python
# For props models (percentages)
if max_edge >= 0.15:  # 15% probability edge
    normalized_edge = 5.0
else:
    normalized_edge = max_edge / 0.03  # 15% = 5.0 rating
```

**Key Changes:**
- Instead of dividing by 3.0 (for points), divide by 0.03 (for percentages)
- Instead of 15 points max, use 15% (0.15) max
- Everything else stays the same (historical factors, confidence, etc.)

---

## 📊 Example Comparison

### Team Model Example:
```
Game: Lakers @ Warriors
Model Spread: +10.5
Market Spread: -3.5
Edge: 14.0 points

Rating Calculation:
- Normalized Edge: 14.0 / 3.0 = 4.67
- Historical Factor: 1.05 (62% win rate on 10+ point edges)
- Confidence: 1.10 (large edge)
- Data Quality: 1.0
- Composite: 4.67 × 1.05 × 1.10 × 1.0 = 5.39
- Final Rating: 2.3 + (5.39/5.0) × 2.6 = 4.9 (PREMIUM)
```

### Props Model Example:
```
Player: LeBron James
Prop: Over 25.5 points
Model Probability: 68% (0.68)
Market Probability: 54% (0.54)
Edge: 14% (0.14)

Rating Calculation:
- Normalized Edge: 0.14 / 0.03 = 4.67
- Historical Factor: 1.05 (62% win rate on 12%+ edges)
- Confidence: 1.10 (large edge)
- Data Quality: 1.0
- Composite: 4.67 × 1.05 × 1.10 × 1.0 = 5.39
- Final Rating: 2.3 + (5.39/5.0) × 2.6 = 4.9 (PREMIUM)
```

**Same formula, different normalization!**

---

## 🎯 What Changes vs What Stays the Same

### ✅ Stays the Same:
- Historical performance lookup (edge ranges)
- Confidence factors (based on edge size)
- Data quality assessment
- Team/player performance indicators
- Rating scaling (2.3-4.9 range)
- Display formatting

### 🔄 Needs Adaptation:
- **Edge normalization** (probability % instead of points)
- **Edge range buckets** (0-5%, 5-10%, 10-15%, etc. instead of 0-5, 5-10, 10-15 points)
- **Historical lookup ranges** (match probability ranges, not point ranges)

---

## 📝 Implementation Example

### Adapted Rating Function for Props:

```python
def calculate_ai_rating_props(analysis, historical_edge_performance):
    """
    Calculate A.I. Rating for props models (probability-based edges)
    """
    # Get max probability edge (as decimal, e.g., 0.126 = 12.6%)
    max_edge = max(abs(analysis.get('edge', 0)), abs(analysis.get('probability_edge', 0)))
    
    # Normalize probability edge to 0-5 scale (15% = 5.0 rating)
    if max_edge >= 0.15:  # 15% probability edge
        normalized_edge = 5.0
    else:
        normalized_edge = max_edge / 0.03  # 15% = 5.0 rating
        normalized_edge = min(5.0, max(0.0, normalized_edge))
    
    # Historical performance (adjusted ranges for probability)
    historical_factor = 1.0
    if historical_edge_performance:
        if max_edge >= 0.12:  # 12%+
            range_key = "12%+"
        elif max_edge >= 0.10:  # 10-11.9%
            range_key = "10-11.9%"
        elif max_edge >= 0.08:  # 8-9.9%
            range_key = "8-9.9%"
        elif max_edge >= 0.05:  # 5-7.9%
            range_key = "5-7.9%"
        else:
            range_key = "0-4.9%"
        
        if range_key in historical_edge_performance:
            hist_win_rate = historical_edge_performance[range_key]
            historical_factor = 0.9 + (hist_win_rate - 0.55) * 2.0
            historical_factor = max(0.9, min(1.1, historical_factor))
    
    # Confidence factor (same logic, different thresholds)
    confidence = 1.0
    if max_edge >= 0.12:  # 12%+ edge
        confidence = 1.10
    elif max_edge >= 0.08:  # 8%+ edge
        confidence = 1.05
    elif max_edge >= 0.05:  # 5%+ edge
        confidence = 1.0
    else:
        confidence = 0.95
    
    # Rest of calculation is identical...
    composite_rating = normalized_edge * data_quality * historical_factor * confidence
    ai_rating = 2.3 + (composite_rating / 5.0) * 2.6
    return round(ai_rating, 1)
```

---

## 🎲 Summary

**Probability-based adaptations** means:
1. **Normalizing probability edges** (percentages) instead of point edges
2. **Adjusting edge ranges** to match probability values (0-15% instead of 0-15 points)
3. **Everything else stays the same** - same rating factors, same display, same logic

The core idea is identical: **rate bets by quality/confidence**, just using probability differences instead of point differences as the base metric.
