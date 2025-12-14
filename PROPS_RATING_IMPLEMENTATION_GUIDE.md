# Props Models A.I. Rating Implementation Guide

## ✅ Completed Props Models

1. **NBA Points Props** (`nba/nba_points_props_model.py`) - ✅ Complete
2. **NBA 3PT Props** (`nba/nba_3pt_props_model.py`) - 🔄 In Progress (functions added, need display updates)

## 🔄 Remaining Props Models

### NBA Props (2 remaining):
- `nba_assists_props_model.py`
- `nba_rebounds_props_model.py`

### NFL Props (3 remaining):
- `nfl_passing_yards_props_model.py`
- `nfl_rushing_yards_props_model.py`
- `nfl_receptions_props_model.py`

### NFL Special:
- `atd_model.py` (Anytime TD - already probability-based, may need slight adaptation)

## 📋 Implementation Checklist (Per Model)

### Step 1: Add Rating Functions
Copy these three functions after `calculate_tracking_summary()`:

1. `get_historical_performance_by_edge_props()` - Groups historical picks by EV ranges
2. `calculate_probability_edge()` - Calculates probability edge (model prob - market prob)
3. `calculate_ai_rating_props()` - Calculates final A.I. Rating (2.3-4.9 range)

### Step 2: Update analyze_props() Function Signature
```python
def analyze_props(props_list, player_stats, defense_factors, historical_edge_performance=None):
```

### Step 3: Add Rating Calculation in analyze_props()
For each play (both over and under):

```python
# Calculate probability edge
prob_edge = calculate_probability_edge(ai_score, season_avg, recent_avg, prop_line, odds, bet_type)

play_dict = {
    # ... existing fields ...
    'probability_edge': prob_edge,
}

# Calculate A.I. Rating
if historical_edge_performance:
    play_dict['ai_rating'] = calculate_ai_rating_props(play_dict, historical_edge_performance)

plays.append(play_dict)
```

### Step 4: Update Sorting
Replace:
```python
plays.sort(key=lambda x: x['ai_score'], reverse=True)
```

With:
```python
def get_sort_score(play):
    rating = play.get('ai_rating', 2.3)
    ai_score = play.get('ai_score', 0)
    return (rating, ai_score)

plays.sort(key=get_sort_score, reverse=True)
```

### Step 5: Update main() Function
Before calling `analyze_props()`, add:
```python
tracking_data = load_tracking()
historical_edge_performance = get_historical_performance_by_edge_props(tracking_data)

over_plays, under_plays = analyze_props(..., historical_edge_performance)
```

### Step 6: Update Terminal Display
In the print loop for plays, add rating:
```python
ai_rating = play.get('ai_rating', 2.3)
rating_stars = '⭐' * (int(ai_rating) - 2) if ai_rating >= 3.0 else ''
print(f"... | Rating: {ai_rating:.1f} {rating_stars}")
```

### Step 7: Update HTML Display
Add rating display HTML:
```python
# Before generating bet box HTML
ai_rating = play.get('ai_rating', 2.3)
if ai_rating >= 4.5:
    rating_class = 'ai-rating-premium'
    rating_label = 'PREMIUM PLAY'
    rating_stars = '⭐⭐⭐'
elif ai_rating >= 4.0:
    rating_class = 'ai-rating-strong'
    rating_label = 'STRONG PLAY'
    rating_stars = '⭐⭐'
# ... etc

rating_display = f'<div class="ai-rating {rating_class}">🎯 A.I. Rating: {ai_rating:.1f} {rating_stars} ({rating_label})</div>'

# In HTML template, add after bet-title:
{rating_display}
```

### Step 8: Add CSS Styles
Add to HTML template CSS section:
```css
.ai-rating {
    display: inline-block;
    padding: 0.75rem 1.25rem;
    border-radius: 0.75rem;
    font-weight: 700;
    font-size: 1.125rem;
    margin-bottom: 1rem;
    border-left: 4px solid;
}
.ai-rating-premium {
    background: rgba(74, 222, 128, 0.2);
    color: #4ade80;
    border-color: #4ade80;
}
.ai-rating-strong {
    background: rgba(74, 222, 128, 0.15);
    color: #4ade80;
    border-color: #4ade80;
}
.ai-rating-good {
    background: rgba(96, 165, 250, 0.15);
    color: #60a5fa;
    border-color: #60a5fa;
}
.ai-rating-standard {
    background: rgba(251, 191, 36, 0.15);
    color: #fbbf24;
    border-color: #fbbf24;
}
.ai-rating-marginal {
    background: rgba(251, 191, 36, 0.1);
    color: #fbbf24;
    border-color: #fbbf24;
}
```

## 📝 Quick Reference

See `PROPS_RATING_TEMPLATE.py` for complete function implementations.

All props models follow the same pattern - just adapt the function names and variable names to match each model's structure.
