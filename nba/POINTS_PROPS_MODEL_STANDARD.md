# Points Props Model Standard Documentation

## Overview

This document serves as the standard template for player props models in the sports-models codebase. The NBA points props model (`nba_points_props_model.py`) is the reference implementation.

**Model Type**: Player props (individual player statistics)  
**File**: `nba/nba_points_props_model.py`  
**Output File**: `nba_points_props.html`  
**Tracking File**: `nba_points_props_tracking.json`

## Architecture

### File Structure

```
nba_points_props_model.py
├── Configuration Section
│   ├── API Configuration
│   ├── File Paths
│   ├── Model Parameters
│   └── Thresholds
├── Tracking Functions
│   ├── load_tracking_data()
│   ├── save_tracking_data()
│   ├── track_new_picks()
│   ├── grade_pending_picks()
│   └── calculate_clv_status_props()
├── Data Fetching
│   ├── get_nba_player_points_stats()
│   ├── get_opponent_defense_factors()
│   └── get_player_props()
├── Analysis Functions
│   ├── calculate_ai_score()
│   ├── calculate_ev()
│   ├── calculate_probability_edge()
│   ├── calculate_ai_rating_props()
│   └── analyze_props()
├── HTML Generation
│   ├── generate_reasoning_tags()
│   ├── generate_html_output()
│   └── calculate_player_stats()
└── Main Execution
    └── main()
```

### Data Flow

```
1. Grade Pending Picks (Update Results)
   ↓
2. Fetch Player Stats (NBA API)
   ↓
3. Fetch Opponent Defense Factors
   ↓
4. Fetch Player Props (The Odds API)
   ↓
5. Analyze Props
   ├── Calculate AI Score
   ├── Calculate EV
   ├── Calculate AI Rating
   └── Filter by Thresholds
   ↓
6. Track New Picks
   ├── Check for Existing Picks
   ├── Update CLV for Existing
   └── Add New Picks
   ↓
7. Generate HTML Output
   ├── Calculate Tracking Stats
   ├── Generate Play Cards
   └── Add CLV Tags
```

## Key Components

### 1. Configuration

**Required Configuration Variables:**

```python
# API Configuration
API_KEY = os.getenv('ODDS_API_KEY')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# File Paths
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "nba_points_props.html")
TRACKING_FILE = os.path.join(SCRIPT_DIR, "nba_points_props_tracking.json")
PLAYER_STATS_CACHE = os.path.join(SCRIPT_DIR, "nba_player_points_stats_cache.json")
TEAM_DEFENSE_CACHE = os.path.join(SCRIPT_DIR, "nba_team_defense_cache.json")

# Model Parameters
MIN_AI_SCORE = 9.5  # Minimum AI score to show
TOP_PLAYS_COUNT = 5  # Number of top plays to display
RECENT_GAMES_WINDOW = 10  # Games for recent form
CURRENT_SEASON = '2025-26'

# Edge Requirements
MIN_EDGE_OVER_LINE = 2.0  # Minimum edge for OVER
MIN_EDGE_UNDER_LINE = 1.5  # Minimum edge for UNDER
MIN_RECENT_FORM_EDGE = 1.2  # Recent form support
```

### 2. Tracking System

**Pick Tracking Structure:**

Each pick in `nba_points_props_tracking.json` has the following structure:

```json
{
  "pick_id": "player_name_prop_line_bet_type_game_time",
  "player": "LeBron James",
  "prop_line": 23.5,
  "bet_type": "over",
  "team": "Los Angeles Lakers",
  "opponent": "Boston Celtics",
  "ai_score": 9.7,
  "odds": -110,
  "opening_odds": -110,
  "latest_odds": -120,
  "game_time": "2024-12-16T20:00:00Z",
  "tracked_at": "2024-12-16T10:00:00-05:00",
  "last_updated": "2024-12-16T15:00:00-05:00",
  "status": "pending",
  "result": null,
  "actual_pts": null,
  "clv_status": "positive"
}
```

**Required Tracking Functions:**

1. **`load_tracking_data()`** - Load tracking data from JSON file
2. **`save_tracking_data()`** - Save tracking data to JSON file
3. **`track_new_picks()`** - Track new picks and update existing ones
4. **`grade_pending_picks()`** - Grade pending picks with actual results
5. **`calculate_clv_status_props()`** - Calculate CLV for props (odds-based)

### 3. CLV (Closing Line Value) Implementation

**CLV Tracking for Props:**

- **Opening Odds**: Odds when pick was first logged
- **Latest Odds**: Current odds (updated on subsequent runs)
- **CLV Status**: "positive", "negative", or "neutral"

**CLV Calculation Logic for Props:**

For **American Odds**:
- **Negative odds** (e.g., -110): Lower number is better (e.g., -110 beats -120)
- **Positive odds** (e.g., +150): Higher number is better (e.g., +150 beats +130)

**Better Odds = Positive CLV**:
- For both OVER and UNDER bets, getting better odds (more favorable) = positive CLV
- Better odds means:
  - For negative odds: Less negative (closer to 0) is better
  - For positive odds: More positive (higher number) is better

**Implementation:**

```python
def calculate_clv_status_props(opening_odds, latest_odds, bet_type):
    """
    Calculate if a props pick beat the closing line (positive CLV).
    
    Args:
        opening_odds: Odds when pick was first logged
        latest_odds: Current odds (closing line)
        bet_type: 'over' or 'under'
    
    Returns:
        "positive" if beat closing line, "negative" if worse, "neutral" if same
    """
    # If odds are the same, no CLV advantage
    if opening_odds == latest_odds:
        return "neutral"
    
    # For negative odds: lower number (less negative) is better
    # For positive odds: higher number is better
    if opening_odds < 0 and latest_odds < 0:
        # Both negative: opening is better if it's less negative
        return "positive" if opening_odds > latest_odds else "negative"
    elif opening_odds > 0 and latest_odds > 0:
        # Both positive: opening is better if it's higher
        return "positive" if opening_odds > latest_odds else "negative"
    elif opening_odds > 0 and latest_odds < 0:
        # Opening positive, closing negative: opening is better
        return "positive"
    else:
        # Opening negative, closing positive: closing is better
        return "negative"
```

**CLV Update in `track_new_picks()`:**

```python
if existing_pick:
    # Update latest odds if different
    if existing_pick.get('latest_odds') != play.get('odds'):
        existing_pick['latest_odds'] = play.get('odds')
        existing_pick['last_updated'] = datetime.now(...).isoformat()
        # Calculate CLV status
        existing_pick['clv_status'] = calculate_clv_status_props(
            existing_pick.get('opening_odds'),
            play.get('odds'),
            existing_pick.get('bet_type')
        )
```

### 4. HTML Output Standards

**Template Structure:**

```html
<!DOCTYPE html>
<html>
<head>
    <!-- Modern dark theme styling -->
    <!-- Inter font family -->
</head>
<body>
    <header>
        <!-- Title and model info -->
    </header>
    
    <!-- Summary Stats -->
    <section>
        <div class="summary-grid">
            <!-- Season ROI, Win Rate, Record -->
        </div>
    </section>
    
    <!-- Top Value Plays Section -->
    <section>
        <div class="section-title">Top Value Plays</div>
        
        <!-- OVER Plays -->
        {% for play in over_plays %}
        <div class="prop-card">
            <div class="card-header">
                <!-- Team logo, player name, matchup, game time -->
            </div>
            <div class="card-body">
                <div class="bet-main-row">
                    <div class="bet-selection">
                        <span class="txt-green">OVER</span>
                        <span class="line">{{ prop_line }}</span>
                        <span class="bet-odds">{{ odds }}</span>
                    </div>
                </div>
                <div class="model-subtext">
                    Model Predicts: <strong>{{ prediction }}</strong> (Edge: {{ edge }})
                </div>
                <div class="metrics-grid">
                    <!-- AI Score, EV, Win % -->
                </div>
                <!-- Player Stats (if available) -->
                <div class="tags-container">
                    <!-- Reasoning tags -->
                    {% if play.clv_beat_closing %}
                    <span class="tag tag-green">✅ CLV: Beat closing line</span>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
        
        <!-- UNDER Plays (similar structure) -->
    </section>
    
    <!-- Performance Stats -->
    <section>
        <!-- Model performance breakdown -->
    </section>
</body>
</html>
```

**Required CSS Classes:**

- `.prop-card` - Main card container
- `.card-header` - Header with logo and player info
- `.card-body` - Card content
- `.bet-main-row` - Bet selection display
- `.bet-selection` - Pick text with odds
- `.model-subtext` - Model prediction and edge
- `.metrics-grid` - Metrics grid (AI Score, EV, Win %)
- `.tags-container` - Tags container
- `.tag` - Individual tag (`.tag-green`, `.tag-blue`, `.tag-red`)
- `.txt-green`, `.txt-red` - Text color classes

**CLV Tag Display:**

```python
# In generate_html_output(), when generating tags:
for play in over_plays + under_plays:
    tags = generate_reasoning_tags(play, player_data, opponent_defense)
    
    # Check for CLV status
    pick_id = generate_pick_id(play)
    tracked_pick = find_tracked_pick(pick_id, tracking_data)
    
    if tracked_pick and tracked_pick.get('clv_status') == 'positive':
        tags.append({
            "text": "✅ CLV: Beat closing line",
            "color": "green"
        })
    
    # Generate tags HTML
    tags_html = "".join([f'<span class="tag tag-{tag["color"]}">{tag["text"]}</span>' 
                         for tag in tags])
```

**Tracking Table Structure:**

For props models, the tracking section displays "Recent Form" with three side-by-side cards showing LAST 10, LAST 20, and LAST 50 performance. The structure matches the game-level models:

```html
<div class="tracking-section">
    <div class="tracking-header">🔥 Recent Form</div>
    
    <div class="metrics-row" style="margin-bottom: 1.5rem;">
        <!-- LAST 10 Card -->
        <div class="prop-card" style="flex: 1; padding: 1.5rem;">
            <div class="metric-title" style="margin-bottom: 0.5rem; text-align: center;">LAST 10</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                <div>
                    <div class="metric-label">Record</div>
                    <div class="metric-value">{{ last_10.record }}</div>
                </div>
                <div>
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value {{ 'good' if last_10.win_rate >= 55 else ('text-red' if last_10.win_rate < 50) }}">{{ "%.0f"|format(last_10.win_rate) }}%</div>
                </div>
                <div>
                    <div class="metric-label">Profit</div>
                    <div class="metric-value {{ 'good' if last_10.profit > 0 else 'text-red' }}">{{ "%+.1f"|format(last_10.profit) }}u</div>
                </div>
                <div>
                    <div class="metric-label">ROI</div>
                    <div class="metric-value {{ 'good' if last_10.roi > 0 else 'text-red' }}">{{ "%+.1f"|format(last_10.roi) }}%</div>
                </div>
            </div>
        </div>
        
        <!-- LAST 20 Card (same structure) -->
        <!-- LAST 50 Card (same structure) -->
    </div>
</div>
```

**Required CSS for Tracking:**

```css
.tracking-section { margin-top: 3rem; }
.tracking-header { 
    font-size: 1.5rem; 
    font-weight: 700; 
    color: var(--text-primary); 
    margin-bottom: 1.5rem; 
    border-bottom: 2px solid var(--border-color);
    padding-bottom: 0.5rem;
}
.metric-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--text-secondary);
    letter-spacing: 0.05em;
    margin-bottom: 4px;
    font-weight: 600;
}
.text-red { color: var(--accent-red); }
```

**Required Function:**

```python
def calculate_recent_performance(picks_list, count):
    """Calculate performance stats for last N picks"""
    completed = [p for p in picks_list if p.get('status', '').lower() in ['win', 'loss']]
    recent = completed[:count] if len(completed) >= count else completed
    
    wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
    total = wins + losses
    
    # Calculate profit from profit_loss field (in cents) or calculate from odds
    profit_cents = sum(p.get('profit_loss', 0) for p in recent if p.get('profit_loss') is not None)
    profit_units = profit_cents / 100.0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (profit_cents / (total * UNIT_SIZE) * 100) if total > 0 else 0
    
    return {
        'record': f"{wins}-{losses}",
        'win_rate': win_rate,
        'profit': profit_units,
        'roi': roi
    }
```

### 5. AI Score Calculation

**AI Score Components:**

- Season average vs prop line
- Recent form vs season average
- Consistency score
- Opponent defense factors
- Usage rate and minutes
- Matchup advantages

**Score Range:** 0.0 - 10.0  
**Minimum Threshold:** 9.5 (configurable)

### 6. EV (Expected Value) Calculation

**EV Formula:**

```python
def calculate_ev(ai_score, prop_line, season_avg, recent_avg, odds, bet_type):
    # Calculate win probability from AI score
    win_prob = calculate_win_probability(ai_score, season_avg, prop_line, bet_type)
    
    # Calculate implied probability from odds
    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)
    
    # EV = (win_prob * payout) - (loss_prob * stake)
    if odds > 0:
        payout = odds / 100
    else:
        payout = 100 / abs(odds)
    
    ev = (win_prob * payout) - ((1 - win_prob) * 1.0)
    return ev * 100  # Return as percentage
```

### 7. Reasoning Tags

**Tag Types:**

- **Opponent Defense**: Points allowed, pace
- **Recent Form**: Last 10 games average
- **Edge**: Strong edge, good edge
- **CLV**: Beat closing line (when applicable)

**Tag Colors:**

- `green` - Positive factors (weak defense, hot streak, positive CLV)
- `red` - Negative factors (strong defense, cold streak)
- `blue` - Neutral/informational

## Implementation Checklist

### Required Functions

- [ ] `load_tracking_data()` - Load tracking data
- [ ] `save_tracking_data()` - Save tracking data
- [ ] `track_new_picks()` - Track new picks and update CLV
- [ ] `calculate_clv_status_props()` - Calculate CLV for props
- [ ] `grade_pending_picks()` - Grade picks with results
- [ ] `get_player_props()` - Fetch props from API
- [ ] `get_nba_player_points_stats()` - Fetch player stats
- [ ] `get_opponent_defense_factors()` - Fetch defense stats
- [ ] `analyze_props()` - Analyze and score props
- [ ] `calculate_ai_score()` - Calculate AI score
- [ ] `calculate_ev()` - Calculate expected value
- [ ] `generate_html_output()` - Generate HTML
- [ ] `generate_reasoning_tags()` - Generate tags

### Required Tracking Fields

- [ ] `pick_id` - Unique identifier
- [ ] `opening_odds` - Odds when first logged
- [ ] `latest_odds` - Current odds (updated on subsequent runs)
- [ ] `clv_status` - CLV calculation result
- [ ] `status` - Pick status (pending/win/loss)
- [ ] `bet_type` - over or under
- [ ] `prop_line` - Prop line value
- [ ] `ai_score` - AI score when tracked
- [ ] `game_time` - Game start time
- [ ] `tracked_at` - When pick was first tracked
- [ ] `last_updated` - When odds were last updated

### HTML Template Sections

- [ ] Header with title and model info
- [ ] Summary stats grid (ROI, Win Rate, Record)
- [ ] Top Value Plays section
- [ ] Individual play cards
  - [ ] Card header (logo, player, matchup, time)
  - [ ] Bet selection (OVER/UNDER, line, odds)
  - [ ] Model prediction and edge
  - [ ] Metrics grid (AI Score, EV, Win %)
  - [ ] Player stats (if available)
  - [ ] Tags container (reasoning tags + CLV)
- [ ] Performance breakdown section

### Error Handling Patterns

```python
# Always wrap CLV calculations in try/except
try:
    clv_status = calculate_clv_status_props(...)
except Exception as e:
    print(f"⚠ Error calculating CLV: {e}")
    clv_status = "neutral"  # Fail gracefully

# Handle missing tracking data
if tracking_data and tracking_data.get('picks'):
    # Process picks
    pass
else:
    # No tracking data available
    pass

# Graceful degradation in HTML
if tracked_pick and tracked_pick.get('clv_status') == 'positive':
    # Show CLV tag
    tags.append({"text": "✅ CLV: Beat closing line", "color": "green"})
# If missing, simply don't show tag
```

## Best Practices

1. **Backward Compatibility**: Always handle missing fields gracefully
2. **Error Handling**: Wrap CLV calculations in try/except blocks
3. **Performance**: Only update CLV for picks that haven't been graded
4. **Consistency**: Use same tag styling across all props models
5. **Documentation**: Comment complex calculations (AI score, EV, CLV)
6. **Testing**: Verify CLV works for both OVER and UNDER bets
7. **Validation**: Validate odds format before processing
8. **Caching**: Cache player stats and defense factors to reduce API calls

## Code Examples

### Tracking a New Pick with CLV

```python
def track_new_picks(over_plays, under_plays):
    tracking_data = load_tracking_data()
    
    for play in over_plays + under_plays:
        pick_id = generate_pick_id(play)
        existing_pick = find_existing_pick(pick_id, tracking_data)
        
        if existing_pick:
            # Update latest odds and CLV
            if existing_pick.get('latest_odds') != play.get('odds'):
                existing_pick['latest_odds'] = play.get('odds')
                existing_pick['clv_status'] = calculate_clv_status_props(
                    existing_pick.get('opening_odds'),
                    play.get('odds'),
                    existing_pick.get('bet_type')
                )
        else:
            # Add new pick
            new_pick = {
                'pick_id': pick_id,
                'opening_odds': play.get('odds'),
                'latest_odds': play.get('odds'),
                'clv_status': None,  # Will be calculated on next run
                # ... other fields
            }
            tracking_data['picks'].append(new_pick)
    
    save_tracking_data(tracking_data)
```

### Displaying CLV Tag in HTML

```python
# In generate_html_output(), when generating tags:
def generate_tags_with_clv(play, tracking_data, player_data, opponent_defense):
    tags = generate_reasoning_tags(play, player_data, opponent_defense)
    
    # Check for CLV
    pick_id = f"{play['player']}_{prop_line}_{bet_type}_{play.get('game_time', '')}"
    tracked_pick = next((p for p in tracking_data.get('picks', []) 
                         if p.get('pick_id') == pick_id), None)
    
    if tracked_pick and tracked_pick.get('clv_status') == 'positive':
        tags.append({
            "text": "✅ CLV: Beat closing line",
            "color": "green"
        })
    
    return tags
```

### CLV Calculation Function

```python
def calculate_clv_status_props(opening_odds, latest_odds, bet_type):
    """Calculate CLV for props based on odds comparison"""
    try:
        if opening_odds == latest_odds:
            return "neutral"
        
        # Both negative: less negative is better
        if opening_odds < 0 and latest_odds < 0:
            return "positive" if opening_odds > latest_odds else "negative"
        
        # Both positive: higher is better
        elif opening_odds > 0 and latest_odds > 0:
            return "positive" if opening_odds > latest_odds else "negative"
        
        # Opening positive, closing negative: opening is better
        elif opening_odds > 0 and latest_odds < 0:
            return "positive"
        
        # Opening negative, closing positive: closing is better
        else:
            return "negative"
    
    except Exception as e:
        return "neutral"  # Fail gracefully
```

## Configuration Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MIN_AI_SCORE` | 9.5 | Minimum AI score to display |
| `TOP_PLAYS_COUNT` | 5 | Number of top plays per type |
| `RECENT_GAMES_WINDOW` | 10 | Games for recent form |
| `MIN_EDGE_OVER_LINE` | 2.0 | Minimum edge for OVER |
| `MIN_EDGE_UNDER_LINE` | 1.5 | Minimum edge for UNDER |
| `MIN_RECENT_FORM_EDGE` | 1.2 | Recent form support threshold |

## Summary

This standard ensures:
- Consistent tracking structure across props models
- CLV tracking for all picks (odds-based)
- Modern, responsive HTML output
- Graceful error handling
- Backward compatibility
- Clear documentation for future development

Use this document as a reference when creating new player props models.
