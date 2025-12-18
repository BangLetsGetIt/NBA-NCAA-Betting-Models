# Fix Soccer Model - Show Games and Add Debugging

## Problem
Soccer model shows "No upcoming games found matching model criteria" because:
1. Line 504 filters out ALL games without bets meeting thresholds
2. 72-hour time window may be too restrictive  
3. No debug output to diagnose filtering

## Solution

### 1. Remove Strict Filtering
**File**: `soccer/soccer_model_IMPROVED.py` (line 504)

**Current**:
```python
analyses = [a for a in analyses if a and a.get('bets')]
```

**Change to**: Show all games, even without strong edges
```python
# Show all games - display "No edge" for markets without value
analyses = [a for a in analyses if a]  # Only filter None values
```

### 2. Expand Time Window
**File**: `soccer/soccer_model_IMPROVED.py` (line 340)

**Current**: 72 hours
**Change to**: 7 days (168 hours)

```python
# Check if game is too far in future (> 7 days)
if (dt - now).total_seconds() > (7 * 24 * 3600):
    return None
```

### 3. Update HTML Template
**File**: `soccer/soccer_model_IMPROVED.py` (template section, lines 769-795)

The template already handles missing bets correctly (shows "--" or market line). No changes needed here - just need to ensure games are passed through.

### 4. Add Debug Logging
**File**: `soccer/soccer_model_IMPROVED.py` (main function and analyze_game)

Add diagnostic output in `main()`:
```python
# After analyzing games:
games_with_bets = sum(1 for a in analyses if a.get('bets'))
total_bets = sum(len(a.get('bets', [])) for a in analyses)
print(f"\n📊 Analysis Summary:")
print(f"   Games fetched: {len(games)}")
print(f"   Games analyzed: {len(analyses)}")
print(f"   Games with bets: {games_with_bets}")
print(f"   Total bets found: {total_bets}")
```

Add logging in `analyze_game()` to track filtering:
- Count games filtered by time
- Count games without markets
- Count games without edges

## Implementation Steps

1. Remove strict filtering (line 504)
2. Expand time window (line 340)  
3. Add debug logging (main function)
4. Test to verify games appear

## Expected Outcome

- Games will appear in HTML output even if edges don't meet thresholds
- More games visible due to expanded time window (7 days vs 72 hours)
- Better debugging information to understand filtering
- Games without strong edges will show market lines with "No edge" indicators
