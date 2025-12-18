# Prop Model Design - Context & Template

This document serves as the design specification and template for creating prop betting models across different sports and stat categories.

## Overview

The prop model system analyzes player prop bets using real statistical data, AI scoring, and expected value calculations to identify profitable betting opportunities. The model focuses on quality over quantity, showing only high-confidence plays that meet strict edge requirements.

## Core Architecture

### 1. Data Sources

#### Primary APIs
- **NBA Stats API** (`nba_api` package)
  - Player season statistics
  - Recent form (last N games)
  - Team defense statistics
  - Game logs for verification
  
- **The Odds API** (`api.the-odds-api.com`)
  - Player prop odds
  - Game schedules
  - Bookmaker lines (FanDuel primary)

#### Data Caching
- Player stats cache: 6-hour TTL
- Team defense cache: 6-hour TTL
- Reduces API calls and improves performance

### 2. Model Parameters

```python
# Strict thresholds for profitability
MIN_AI_SCORE = 9.5  # Only show high-confidence plays
TOP_PLAYS_COUNT = 5  # Quality over quantity
RECENT_GAMES_WINDOW = 10  # Games for recent form calculation
CURRENT_SEASON = '2025-26'

# Edge requirements (prop-specific)
MIN_EDGE_OVER_LINE = 2.0  # Player must average 2.0+ above prop line for OVER
MIN_EDGE_UNDER_LINE = 1.5  # Player must average 1.5+ below prop line for UNDER
MIN_RECENT_FORM_EDGE = 1.2  # Recent form must strongly support
```

### 3. AI Scoring System

The AI score (0-10 scale) evaluates prop bets based on multiple factors:

#### For OVER Bets:
- **Edge Above Line**: Season average vs prop line
  - ≥2.0 above: +3.5 points
  - ≥1.5 above: +2.5 points
  - ≥1.0 above: +1.5 points
  - ≥0.5 above: +0.5 points
  - <0.5 above: -2.0 points (may disqualify)

- **Recent Form**: Last 10 games average
  - ≥1.2 above line: +2.5 points
  - ≥1.0 above line: +1.5 points
  - Trending up: +1.0 points
  - At/above line: +0.5 points
  - Below line: -1.5 points

- **Scoring Rate**: Points per 36 minutes
  - ≥25.0: +1.5 points
  - ≥20.0: +1.0 points
  - ≥15.0: +0.5 points

- **Consistency Score**: Normalized performance stability
  - Multiplied by 0.8

- **Shooting Efficiency**: Field goal percentage
  - ≥48%: +0.5 points
  - ≥45%: +0.3 points

- **Opponent Defense**: Matchup factors
  - Favorable (def_factor > 1.05): +1.0 points
  - Unfavorable (def_factor < 0.95): -0.5 points

#### For UNDER Bets:
- **Edge Below Line**: Prop line vs season average
  - ≥1.5 below: +3.5 points
  - ≥1.2 below: +2.5 points
  - ≥0.8 below: +1.5 points
  - ≥0.4 below: +0.5 points
  - <0.4 below: -2.0 points (may disqualify)

- **Recent Form**: Last 10 games average
  - ≥1.2 below line: +2.5 points
  - ≥1.0 below line: +1.5 points
  - Trending down: +1.0 points
  - At/below line: +0.5 points
  - Above line: -1.5 points

- **Low Scoring Rate**: Points per 36 minutes
  - <15.0: +1.0 points
  - <18.0: +0.5 points

- **Inconsistency Bonus**: (1.0 - consistency) * 0.5

- **Opponent Defense**: Matchup factors
  - Strong defense (def_factor < 0.95): +1.0 points
  - Weak defense (def_factor > 1.05): -0.5 points

#### Minimum Requirements
- Games played: ≥5 games
- Minutes per game: ≥15 minutes
- Final score capped at 10.0
- Scores <9.5 are filtered out

### 4. Expected Value (EV) Calculation

EV is calculated using probability-based methodology:

```python
# Convert American odds to implied probability
if odds > 0:
    implied_prob = 100 / (odds + 100)
else:
    implied_prob = abs(odds) / (abs(odds) + 100)

# Calculate true probability from AI score and stats
base_prob = 0.50  # Starting point
ai_multiplier = max(0, (ai_score - 9.0) / 1.0)  # Scale from 9.0-10.0 to 0-1.0

# Edge factor: larger edge = higher true probability
edge = season_avg - prop_line  # for OVER
edge = prop_line - season_avg  # for UNDER
edge_factor = min(abs(edge) / 2.0, 1.0)

# Recent form bonus
recent_factor = 0.0
if bet_type == 'over' and recent_avg > season_avg:
    recent_factor = min((recent_avg - season_avg) / 2.0, 0.1)
elif bet_type == 'under' and recent_avg < season_avg:
    recent_factor = min((season_avg - recent_avg) / 2.0, 0.1)

# True probability (capped 40-70%)
true_prob = base_prob + (ai_multiplier * 0.15) + (edge_factor * 0.15) + recent_factor
true_prob = min(max(true_prob, 0.40), 0.70)

# Calculate EV
if odds > 0:
    ev = (true_prob * (odds / 100)) - (1 - true_prob)
else:
    ev = (true_prob * (100 / abs(odds))) - (1 - true_prob)

return ev * 100  # Return as percentage
```

### 5. AI Rating System (2.3-4.9 Scale)

The AI Rating provides a user-friendly quality indicator:

```python
# Probability edge calculation
prob_edge = abs(model_prob - implied_prob)

# Normalize probability edge to 0-5 scale (15% = 5.0 rating)
if prob_edge >= 0.15:
    normalized_edge = 5.0
else:
    normalized_edge = prob_edge / 0.03  # 15% = 5.0 rating
    normalized_edge = min(5.0, max(0.0, normalized_edge))

# Data quality factor
data_quality = 1.0 if ai_score >= 9.0 else 0.85

# Model confidence factor
confidence = 1.0
if ai_score >= 9.8 and ev >= 12:
    confidence = 1.12
elif ai_score >= 9.5 and ev >= 10:
    confidence = 1.08
elif ai_score >= 9.0 and ev >= 8:
    confidence = 1.05

# Composite rating
composite_rating = normalized_edge * data_quality * confidence

# Scale to 2.3-4.9 range
ai_rating = 2.3 + (composite_rating / 5.0) * 2.6
ai_rating = max(2.3, min(4.9, ai_rating))
```

#### Rating Tiers:
- **4.5-4.9**: Premium Play ⭐⭐⭐ (Green)
- **4.0-4.4**: Strong Play ⭐⭐ (Green)
- **3.5-3.9**: Good Play ⭐ (Blue)
- **3.0-3.4**: Standard Play (Yellow)
- **2.3-2.9**: Marginal Play (Yellow)

### 6. HTML Output Structure

#### Header Section
- Branding: "CourtSide Analytics"
- Model name (e.g., "NBA Points Props Model")
- Feature badges:
  - "REAL NBA STATS API"
  - "A.I. SCORE ≥ 9.5"
  - "STRICT EDGE REQUIREMENTS"
- Generation timestamp

#### Play Cards
Each play card displays:
- **Prop Title**: "OVER/UNDER X.X PTS" (color-coded)
- **Player Name**: With team logo
- **Matchup**: "Away @ Home"
- **Game Time**: Formatted date/time
- **Odds**: The opening odds the bet was placed at (e.g., -110, +150) - **CRITICAL**: Prop bets have varying odds, not standardized like -110 for sides/totals
- **AI Rating Badge**: Top-right corner with stars
- **Season Average**: Player's season stat
- **Recent Average**: Last 10 games stat
- **AI Score**: With confidence bar (0-100%)
- **Pick**: "✅ OVER/UNDER X.X PTS" with EV badge

**Note on Odds Display**: The odds shown are the `opening_odds` (the odds when the pick was first tracked). This is critical because:
- Prop bets have varying odds (not standardized like -110)
- Users need to see what odds the bet was actually placed at
- ROI calculations use `opening_odds` to ensure accuracy

#### Color Scheme
- Background: `#000000` (black)
- Cards: `#1a1a1a` (dark gray)
- Bet boxes: `#262626` (lighter gray)
- OVER plays: `#10b981` (green)
- UNDER plays: `#ef4444` (red)
- Text: `#ffffff` (white)
- Secondary text: `#94a3b8` (slate)

### 7. Key Functions

#### Data Fetching
- `get_nba_player_[stat]_stats()`: Fetch player statistics
- `get_opponent_defense_factors()`: Fetch team defense stats
- `get_player_props()`: Fetch prop odds from The Odds API

#### Analysis
- `calculate_ai_score()`: Calculate AI score (0-10)
- `calculate_ev()`: Calculate expected value
- `calculate_probability_edge()`: Calculate probability edge
- `calculate_ai_rating_props()`: Calculate AI rating (2.3-4.9)
- `analyze_props()`: Main analysis function

#### Output
- `generate_html_output()`: Generate HTML report
- `save_html()`: Save HTML to file

### 8. Edge Requirements

#### OVER Bets
- Season average must be ≥ prop_line + 0.5
- Recent average must be ≥ prop_line + 0.3
- Minimum edge: 2.0+ above line

#### UNDER Bets
- Season average must be ≤ prop_line - 0.5
- Recent average must be ≤ prop_line - 0.3
- Minimum edge: 1.5+ below line

### 9. Player Matching

The model uses roster matching to associate players with teams:
- Last name matching
- Full name matching
- Handles name variations (e.g., "Paul George" vs "George")
- Fallback to home team if no match found

### 10. Team Defense Factors

Opponent defense is evaluated using:
- **Opponent Points Allowed**: Higher = easier to score
- **Pace**: Higher = more possessions
- **Defensive Rating**: Lower = better defense

Formula:
```python
defense_factor = (opp_pts / 110.0) * (pace / 100) * (110.0 / def_rating)
```

Higher defense_factor = better matchup for scoring

### 11. Filtering & Sorting

#### Filtering
1. Remove plays with AI score < 9.5
2. Remove plays that don't meet edge requirements
3. Remove duplicate plays (same player + prop)
4. Limit to top 5 OVER and top 5 UNDER plays

#### Sorting
Primary: AI Rating (descending)
Secondary: AI Score (descending)

### 12. Adapting for Other Props

To create a new prop model (e.g., rebounds, assists, 3-pointers):

1. **Update Stat Category**
   - Change `get_nba_player_points_stats()` to fetch relevant stat
   - Update stat field names (e.g., `PTS` → `REB`, `AST`, `FG3M`)

2. **Adjust Edge Requirements**
   - Points: 2.0 OVER / 1.5 UNDER
   - Assists: May need stricter (2.5 OVER / 2.0 UNDER)
   - Rebounds: Similar to points
   - 3-pointers: May need different thresholds

3. **Update AI Score Factors**
   - Replace scoring-specific factors with relevant metrics
   - For assists: focus on usage rate, assist rate, team pace
   - For rebounds: focus on rebounding rate, opponent rebounding allowed
   - For 3-pointers: focus on 3P%, 3PA, opponent 3P defense

4. **Update HTML Labels**
   - Change "PTS" to "REB", "AST", "3PT", etc.
   - Update prop title format

5. **Update File Names**
   - Model file: `nba_[stat]_props_model.py`
   - Output HTML: `nba_[stat]_props.html`
   - Cache files: `nba_player_[stat]_stats_cache.json`

### 13. Design Principles

1. **Quality Over Quantity**: Only show top 5 plays per category
2. **Strict Thresholds**: High AI score requirement (9.5+)
3. **Real Data**: Always use official NBA stats API
4. **Transparency**: Show all key metrics (season avg, recent avg, AI score, EV)
5. **Visual Clarity**: Color-coded, card-based layout
6. **Mobile Responsive**: Responsive design for all screen sizes

### 14. Error Handling

- API failures: Fall back to cached data
- Missing player stats: Skip prop (counted in skipped stats)
- Missing odds: Skip prop
- Invalid data: Graceful degradation

### 15. Performance Considerations

- 6-hour caching for stats
- Rate limiting: 0.6s delay between NBA API calls
- Batch processing of props
- Efficient data structures (dictionaries for lookups)

## Example Output Structure

```
CourtSide Analytics
NBA Points Props Model

[Badges: REAL NBA STATS API | A.I. SCORE ≥ 9.5 | STRICT EDGE REQUIREMENTS]

TOP OVER PLAYS
┌─────────────────────────────────┐
│ [4.9 ⭐⭐⭐]                      │
│ OVER 5.5 PTS                    │
│ Rui Hachimura [LAL logo]        │
│ Lakers @ Suns                   │
│ 12/14 08:11 PM ET              │
│ Season Avg: 13.7               │
│ Recent Avg: 11.0               │
│ A.I. Score: 10.00 [████████]   │
│ ✅ OVER 5.5 PTS [+34.8% EV]    │
└─────────────────────────────────┘

TOP UNDER PLAYS
[Similar structure with red color scheme]
```

## Key Metrics Displayed

1. **AI Score**: 0-10 scale, confidence indicator
2. **AI Rating**: 2.3-4.9 scale, quality indicator with stars
3. **Expected Value**: Percentage-based, shows profitability
4. **Season Average**: Full season performance
5. **Recent Average**: Last 10 games performance
6. **Edge**: Difference between average and prop line

## Notes for Implementation

- Always validate data before processing
- Handle timezone conversions (ET for display)
- Format numbers consistently (2 decimal places for stats)
- Use consistent naming conventions
- Maintain separation of concerns (data, analysis, output)
- Include comprehensive error handling
- Add logging for debugging
- Test with various edge cases
