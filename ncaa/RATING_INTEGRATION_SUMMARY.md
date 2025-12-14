# A.I. Rating Integration Summary - Quick Reference

## 🎯 Core Concept

**Edge = "How much better is my model than the market?"**
**Rating = "How confident should I be in this edge?"**

They work together, not separately.

---

## 📊 Practical Integration Points in Your Code

### 1. **In `process_games()` function** (around line 994)

**Current:**
```python
game_data = {
    "spread_edge": spread_edge,
    "total_edge": total_edge,
    # ... other fields
}
```

**Add:**
```python
# Calculate A.I. Rating (supplements edge)
ai_rating = calculate_ai_rating(game_data, team_performance, historical_data)

game_data = {
    "spread_edge": spread_edge,      # KEEP - still primary signal
    "total_edge": total_edge,        # KEEP - still primary signal
    "ai_rating": ai_rating,          # ADD - supplemental intelligence
    # ... other fields
}
```

---

### 2. **In Sorting Logic** (around line 2275)

**Current:**
```python
def get_max_edge(game):
    spread_edge = abs(game.get('spread_edge', 0))
    total_edge = abs(game.get('total_edge', 0))
    return max(spread_edge, total_edge)

sorted_results = sorted(results, key=get_max_edge, reverse=True)
```

**Option A - Rating First (Recommended):**
```python
def get_sort_score(game):
    # Sort by rating, but use edge as tiebreaker
    rating = game.get('ai_rating', 0)
    max_edge = max(abs(game.get('spread_edge', 0)), abs(game.get('total_edge', 0)))
    return (rating, max_edge)  # Tuple sorts by rating first, then edge

sorted_results = sorted(results, key=get_sort_score, reverse=True)
```

**Option B - Weighted Combination:**
```python
def get_sort_score(game):
    rating = game.get('ai_rating', 2.3)  # Default to min
    max_edge = max(abs(game.get('spread_edge', 0)), abs(game.get('total_edge', 0)))
    
    # Normalize rating to 0-1 (2.3→0, 4.9→1)
    rating_normalized = (rating - 2.3) / 2.6
    
    # Normalize edge to 0-1 (0→0, 15→1)
    edge_normalized = min(1.0, max_edge / 15.0)
    
    # Weighted: 70% rating, 30% edge
    return rating_normalized * 0.7 + edge_normalized * 0.3

sorted_results = sorted(results, key=get_sort_score, reverse=True)
```

---

### 3. **In Display/Output** (HTML and Terminal)

**Add Rating Column:**
```python
# In display_terminal() and save_html()
# Show rating prominently, but keep edge visible

print(f"A.I. Rating: {game['ai_rating']:.1f} ⭐" * (int(game['ai_rating']) - 2))
print(f"Edge: {game['spread_edge']:+.1f} pts")
```

---

### 4. **In Bet Sizing** (if you implement unit sizing)

**Current:** Fixed unit size or edge-based

**Enhanced:** Rating-based baseline with edge multiplier
```python
def get_recommended_units(game_data, base_unit=1.0):
    rating = game_data['ai_rating']
    max_edge = max(abs(game_data['spread_edge']), abs(game_data['total_edge']))
    
    # Rating-based baseline
    if rating >= 4.5:
        units = 2.0 * base_unit
    elif rating >= 4.0:
        units = 1.5 * base_unit
    elif rating >= 3.5:
        units = 1.0 * base_unit
    elif rating >= 3.0:
        units = 0.75 * base_unit
    else:
        units = 0.5 * base_unit
    
    # Edge multiplier (very large edges boost size)
    if max_edge >= 10:
        units *= 1.25
    elif max_edge >= 8:
        units *= 1.15
    
    return units
```

---

## 🔄 Decision Flow Diagram

```
┌─────────────────────────────────────┐
│   Game with Stats & Odds Available  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Calculate Predictions (Existing)  │
│   • predict_game()                  │
│   • Model spread & total            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Calculate Edges (Existing)        │
│   • spread_edge                     │
│   • total_edge                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Calculate A.I. Rating (NEW)       │
│   • Uses edges + other factors      │
│   • Returns 2.3-4.9 rating          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Dual Filtering                    │
│   IF edge >= threshold OR           │
│      rating >= 3.0:                 │
│      → Display Game                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Sort by Rating (Primary)          │
│   Edge as tiebreaker                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Display Both                      │
│   • Rating prominently              │
│   • Edge details                    │
│   • Both visible for transparency   │
└─────────────────────────────────────┘
```

---

## 💡 Real-World Example

### Scenario: Two Games with Similar Edges

**Game 1:**
- Spread Edge: 6.5 pts
- A.I. Rating: 3.1
- Factors: Inconsistent team data, model uncertainty
- **Verdict:** Moderate edge, lower confidence

**Game 2:**
- Spread Edge: 5.8 pts  
- A.I. Rating: 4.3
- Factors: Reliable data, strong historical performance on similar games
- **Verdict:** Slightly smaller edge, much higher confidence

**With Edge-Only Sorting:** Game 1 appears first
**With Rating Sorting:** Game 2 appears first (better bet)

**You'd rather bet Game 2** because the higher rating indicates it's more trustworthy, even with slightly lower edge.

---

## ✅ What Rating Adds to Your Workflow

| Aspect | Without Rating | With Rating |
|--------|---------------|-------------|
| **Sorting** | By edge magnitude | By quality/trustworthiness |
| **Decision Making** | "Big edge = good bet" | "Big edge + high rating = great bet" |
| **Risk Assessment** | Same risk for all edges | Know which edges are risky |
| **Bet Sizing** | Fixed or edge-based | Rating-informed sizing |
| **Filtering** | Edge threshold only | Edge OR quality threshold |
| **Transparency** | See edge only | See both edge + confidence |

---

## 🎯 Implementation Checklist

- [ ] Add `calculate_ai_rating()` function
- [ ] Integrate rating calculation in `process_games()`
- [ ] Add rating to `game_data` dictionary
- [ ] Update sorting to use rating (or weighted combo)
- [ ] Add rating display in terminal output
- [ ] Add rating column in HTML output
- [ ] Add rating to CSV output
- [ ] Test with historical data
- [ ] Optional: Add rating-based bet sizing
- [ ] Optional: Add dual-filtering logic

---

## 📝 Key Principle

**Keep your edge calculations exactly as they are.** 

Rating doesn't change how you calculate edges—it adds a **quality assessment layer** on top of your existing edge-based system.

This gives you:
1. **Edge** → Quantitative signal strength
2. **Rating** → Qualitative confidence assessment
3. **Together** → Better decision making

---

See `HOW_RATING_SUPPLEMENTS_EDGE.md` for detailed formula and implementation code.
