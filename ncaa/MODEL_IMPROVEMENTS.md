# NCAAB Model Improvements - December 10, 2025

## Problem Analysis

After reviewing 1,479 tracked bets, we identified critical issues:

### Historical Performance
- **Spread picks**: 50.6% win rate (361-353) - Below breakeven (need 52.4% at -110)
- **Total picks**: 54.5% win rate (408-340) - Slightly profitable
- **Overall profit**: +8.16 units on 1,481 bets (+0.6% ROI)

### Key Issues Identified

1. **Model Overconfidence**
   - Average spread edge: 14.0 points
   - Average total edge: 17.9 points
   - Picks with 15-24+ point edges were frequently losing
   - This indicates the model was overvaluing its predictions

2. **Poor Prediction Algorithm**
   - Simple average formula: `(team_off + opp_def) / 2`
   - Didn't properly weight offensive vs defensive factors
   - No regression to mean for extreme predictions
   - Fixed home court advantage for all teams

3. **Threshold Misalignment**
   - Display threshold too low (3.5 spread, 4.5 total)
   - Confidence threshold too high (9.0 spread, 13.0 total)
   - Missing value in the 5-8 point edge range
   - Not filtering out likely model errors (20+ edges)

## Changes Made

### 1. Reduced Home Court Advantage
**Before**: 4.0 points
**After**: 3.2 points
**Rationale**: 4.0 was too aggressive, causing model to overvalue home teams

### 2. Increased Display Thresholds (More Selective)
**Before**: 3.5 spread, 4.5 total
**After**: 5.0 spread, 6.0 total
**Rationale**: Filter out marginal edges that don't provide real value

### 3. Optimized Betting Thresholds
**Spread Bets**:
- Minimum edge: 5.5 (down from 9.0)
- Maximum edge: 15.0 (NEW - caps model errors)
- Target range: 5.5-15.0 points

**Total Bets**:
- Minimum edge: 7.0 (down from 13.0)
- Maximum edge: 18.0 (NEW - caps model errors)
- Target range: 7.0-18.0 points

**Rationale**:
- Historical data showed picks with 15-20+ edges were losing
- Missing value in the 5-8 range that was never being logged
- New caps prevent betting on likely model errors

### 4. Improved Prediction Algorithm

**Old Formula**:
```python
home_points_per_100 = (home_off + away_def) / 2
```

**New Formula**:
```python
# 60% offensive strength, 40% opponent defensive weakness
home_points_per_100 = (home_off * 0.60) + ((2 * ncaa_avg - away_def) * 0.40)
```

**Additional Improvements**:
- Pace regression to league average (15%)
- Regression for extreme spreads (>15 points → regress 10%)
- Regression for extreme totals (<130 or >160 → regress 15% to mean)
- Proper weighting prevents overvaluing mismatches

### 5. Better Confidence Labeling

**Spreads**:
- VERY HIGH: 12+ edge
- HIGH: 8-11.9 edge
- MEDIUM: 6-7.9 edge
- LOW: 5-5.9 edge

**Totals**:
- VERY HIGH: 14+ edge
- HIGH: 10-13.9 edge
- MEDIUM: 7-9.9 edge
- LOW: 6-6.9 edge

### 6. Edge Capping with Warnings

Model now:
- Skips picks with edges > max threshold
- Logs warning messages for transparency
- Example: "⚠️ SKIPPED: Edge too large (22.1 > 18.0) - likely model error"

## Expected Impact

### What This Fixes

1. **Eliminates Model Errors**: Capping at 15/18 removes the worst-performing bets
2. **Captures Missed Value**: Lowering minimums from 9/13 to 5.5/7 captures good value
3. **More Accurate Predictions**: Better algorithm with regression to mean
4. **Proper Selectivity**: Higher display thresholds reduce noise

### What to Monitor

1. **Win rate improvement**: Target 54%+ on spreads (up from 50.6%)
2. **Volume changes**: May see fewer bets due to edge capping
3. **ROI improvement**: Should see better than +0.6%
4. **Edge distribution**: Most bets should fall in 5-15 range

## Testing Results

Model successfully ran with new parameters:
- Displays picks with 5+ spread edge, 6+ total edge
- Logs picks in the 5.5-15 spread range, 7-18 total range
- Skips picks with excessive edges (model errors)
- More conservative predictions with regression to mean

## Next Steps

1. **Monitor performance over 100+ bets** with new parameters
2. **Track win rates by edge bucket**:
   - 5.5-8 edge spread picks
   - 8-12 edge spread picks
   - 12-15 edge spread picks
   - Similar for totals
3. **Adjust if needed** based on results
4. **Consider adding**:
   - Conference strength adjustments
   - Recent form weighting
   - Injury/lineup data if available

## Files Modified

- [ncaab_model_FINAL.py](ncaab_model_FINAL.py) - Main model file with all improvements

## Summary

The NCAAB model was being too aggressive with predictions and missing value by:
1. Setting thresholds too high (missing 5-8 edge picks)
2. Not capping edges (betting on likely errors)
3. Using oversimplified prediction algorithm

The new approach is **sharper and more selective**, focusing on moderate edges (5-15 range) where the model has real edge without being overconfident.
