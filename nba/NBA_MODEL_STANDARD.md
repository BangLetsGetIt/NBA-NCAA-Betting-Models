# NBA Model Standard Documentation

## Overview

This document serves as the standard template for game-level models (spreads/totals) in the sports-models codebase. The NBA main model (`nba_model_IMPROVED.py`) is the reference implementation.

**Model Type**: Game-level predictions (spreads and totals)  
**File**: `nba/nba_model_IMPROVED.py`  
**Output Files**: `nba_model_output.csv`, `nba_model_output.html`  
**Tracking File**: `nba_picks_tracking.json`

## Architecture

### File Structure

```
nba_model_IMPROVED.py
├── Configuration Section
│   ├── API Configuration
│   ├── File Paths
│   ├── Model Parameters
│   └── Thresholds
├── Helper Functions
│   ├── Team Name Normalization
│   └── Color Codes
├── Tracking Functions
│   ├── load_picks_tracking()
│   ├── save_picks_tracking()
│   ├── log_confident_pick()
│   └── calculate_clv_status()
├── Data Fetching
│   ├── fetch_team_stats()
│   ├── fetch_home_away_splits()
│   └── fetch_odds()
├── Model Calculations
│   ├── calculate_model_spread()
│   ├── calculate_model_total()
│   └── calculate_ai_rating()
├── Game Processing
│   └── process_games()
└── Output Generation
    ├── display_terminal()
    ├── save_csv()
    └── save_html()
```

### Data Flow

```
1. Fetch Odds (The Odds API)
   ↓
2. Fetch Team Stats (NBA API)
   ↓
3. Process Each Game
   ├── Calculate Model Predictions
   ├── Calculate Edges
   ├── Determine Picks
   ├── Update CLV for Existing Picks
   └── Log New Confident Picks
   ↓
4. Generate Output
   ├── Terminal Display
   ├── CSV Export
   └── HTML Dashboard
```

## Key Components

### 1. Configuration

**Required Configuration Variables:**

```python
# API Configuration
API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
PARAMS = {
    "apiKey": API_KEY,
    "regions": "us",
    "markets": "h2h,spreads,totals",
    "oddsFormat": "american",
    "dateFormat": "iso"
}

# File Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, "nba_model_output.csv")
HTML_FILE = os.path.join(SCRIPT_DIR, "nba_model_output.html")
PICKS_TRACKING_FILE = os.path.join(SCRIPT_DIR, "nba_picks_tracking.json")

# Model Parameters
HOME_COURT_ADVANTAGE = 3.0
SPREAD_THRESHOLD = 3.0      # Minimum edge to show
TOTAL_THRESHOLD = 4.0       # Minimum edge to show

# Tracking Thresholds (stricter than display thresholds)
CONFIDENT_SPREAD_EDGE = 8.0  # Minimum edge to track
CONFIDENT_TOTAL_EDGE = 12.0  # Minimum edge to track
```

### 2. Tracking System

**Pick Tracking Structure:**

Each pick in `nba_picks_tracking.json` has the following structure:

```json
{
  "pick_id": "home_team_away_team_commence_time_pick_type",
  "date_logged": "2024-12-16T10:20:00",
  "game_date": "2024-12-16T20:40:00Z",
  "home_team": "New York Knicks",
  "away_team": "San Antonio Spurs",
  "matchup": "San Antonio Spurs @ New York Knicks",
  "pick_type": "Spread",
  "model_line": 13.6,
  "market_line": -2.5,
  "opening_line": -2.5,
  "closing_line": -3.5,
  "edge": 11.1,
  "pick": "✅ BET: New York Knicks -2.5",
  "units": 1,
  "status": "Pending",
  "result": null,
  "profit_loss": 0,
  "actual_home_score": null,
  "actual_away_score": null,
  "clv_status": "positive"
}
```

**Required Tracking Functions:**

1. **`load_picks_tracking()`** - Load tracking data from JSON file
2. **`save_picks_tracking()`** - Save tracking data with backup
3. **`log_confident_pick()`** - Log new picks that meet confidence thresholds
4. **`calculate_clv_status()`** - Calculate if pick beat closing line

### 3. CLV (Closing Line Value) Implementation

**CLV Tracking:**

- **Opening Line**: Market line when pick was first logged
- **Closing Line**: Market line at game time (updated on subsequent runs)
- **CLV Status**: "positive", "negative", or "neutral"

**CLV Calculation Logic:**

For **Spreads**:
- Favorite (negative spread): Better line = smaller absolute value (e.g., -2.5 beats -3.5)
- Underdog (positive spread): Better line = larger value (e.g., +5.5 beats +4.5)

For **Totals**:
- OVER: Better line = lower total (e.g., OVER 234.5 beats OVER 235.5)
- UNDER: Better line = higher total (e.g., UNDER 235.5 beats UNDER 234.5)

**Implementation:**

```python
def calculate_clv_status(opening_line, closing_line, pick_type, pick_text):
    """Calculate if a pick beat the closing line"""
    # Returns "positive", "negative", or "neutral"
    pass
```

**CLV Update in `process_games()`:**

- Check if game has started
- For existing picks, update `closing_line` if changed
- Calculate and store `clv_status`
- Save tracking data if updated

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
        <!-- Title and season record -->
    </header>
    
    {% for r in results %}
    <div class="prop-card">
        <div class="card-header">
            <div class="header-left">
                <div class="team-logos-container">
                    <!-- Away team logo -->
                    <img src="..." class="team-logo away-logo" alt="{{ away_team }}">
                    <!-- Home team logo -->
                    <img src="..." class="team-logo home-logo" alt="{{ home_team }}">
                </div>
                <div class="matchup-info">
                    <!-- Matchup text and home game indicator -->
                </div>
            </div>
            <!-- Game time badge -->
        </div>
        
        <!-- SPREAD BET BLOCK -->
        <div class="bet-row">
            <div class="main-pick green">{{ pick }}</div>
            <div class="model-context">
                Model: {{ model_line }}
                <span class="edge-val">Edge: {{ edge }}</span>
            </div>
        </div>
        
        <!-- TOTAL BET BLOCK -->
        <div class="bet-row">
            <!-- Similar structure -->
        </div>
        
        <!-- METRICS ROW -->
        <div class="metrics-row">
            <!-- AI Score, Win %, Predicted Score -->
        </div>
        
        <!-- TAGS -->
        <div class="tags-row">
            {% if r.team_indicator %}
            <div class="tag tag-blue">{{ indicator }}</div>
            {% endif %}
            
            {% if r.clv_beat_closing %}
            <div class="tag tag-green">✅ CLV: Beat closing line</div>
            {% endif %}
            
            {% if r['ATS Explanation'] %}
            <div class="tag tag-green">{{ explanation }}</div>
            {% endif %}
        </div>
    </div>
    {% endfor %}
    
    <!-- PERFORMANCE STATS -->
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
                        <div class="metric-value">{{ last_10.win_rate }}%</div>
                    </div>
                    <div>
                        <div class="metric-label">Profit</div>
                        <div class="metric-value">{{ last_10.profit }}u</div>
                    </div>
                    <div>
                        <div class="metric-label">ROI</div>
                        <div class="metric-value">{{ last_10.roi }}%</div>
                    </div>
                </div>
            </div>
            
            <!-- LAST 20 Card (same structure) -->
            <!-- LAST 50 Card (same structure) -->
        </div>
    </div>
</body>
</html>
```

**Required CSS Classes:**

- `.prop-card` - Main card container
- `.card-header` - Header with logos and matchup
- `.header-left` - Container for logos and matchup info
- `.team-logos-container` - Container for both team logos (flex layout)
- `.team-logo` - Individual team logo (44px x 44px)
- `.away-logo` - Away team logo (slightly dimmed with opacity 0.85)
- `.home-logo` - Home team logo (full opacity for prominence)
- `.matchup-info` - Matchup text container
- `.bet-row` - Individual bet display
- `.main-pick` - Pick text (with `.green` for confident picks)
- `.model-context` - Model prediction and edge
- `.metrics-row` - Metrics grid
- `.tags-row` - Tags container
- `.tag` - Individual tag (`.tag-green`, `.tag-blue`, `.tag-red`)
- `.tracking-section` - Tracking section container (margin-top: 3rem)
- `.tracking-header` - Section header with border-bottom
- `.metric-label` - Label for individual metrics (Record, Win Rate, etc.)
- `.text-red` - Red color class for negative values

**Dual Logo Display:**

The header displays both away and home team logos side-by-side:

```html
<div class="team-logos-container">
    <img src="..." class="team-logo away-logo" alt="{{ away_team }}">
    <img src="..." class="team-logo home-logo" alt="{{ home_team }}">
</div>
```

**Design Notes:**
- Both logos are 44px x 44px
- 8px gap between logos for clean separation
- Away logo has 0.85 opacity to show home team prominence
- Logos align with matchup text
- Responsive: maintains layout on mobile devices

**CLV Tag Display:**

```python
# In save_html(), before template rendering:
for result in results:
    result['clv_beat_closing'] = False
    
    # Check for matching pick with positive CLV
    spread_pick = find_matching_pick(result, 'spread')
    if spread_pick and spread_pick.get('clv_status') == 'positive':
        result['clv_beat_closing'] = True
    
    total_pick = find_matching_pick(result, 'total')
    if total_pick and total_pick.get('clv_status') == 'positive':
        result['clv_beat_closing'] = True
```

**Tracking Table Structure:**

The tracking section displays "Recent Form" with three side-by-side cards showing LAST 10, LAST 20, and LAST 50 performance:

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
    completed = [p for p in picks_list if p.get('status', '').lower() in ['win', 'loss', 'push']]
    recent = completed[:count] if len(completed) >= count else completed
    
    wins = sum(1 for p in recent if p.get('status', '').lower() == 'win')
    losses = sum(1 for p in recent if p.get('status', '').lower() == 'loss')
    pushes = sum(1 for p in recent if p.get('status', '').lower() == 'push')
    total = wins + losses + pushes
    
    profit_cents = sum(p.get('profit_loss', 0) for p in recent if p.get('profit_loss') is not None)
    profit_units = profit_cents / 100.0
    
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (profit_cents / (total * UNIT_SIZE) * 100) if total > 0 else 0
    
    return {
        'record': f"{wins}-{losses}" + (f"-{pushes}" if pushes > 0 else ""),
        'win_rate': win_rate,
        'profit': profit_units,
        'roi': roi
    }
```

**Header Record Display:**

The overall season record appears in the header top-right corner:

```html
<header>
    <div>
        <h1>CourtSide Analytics NBA Picks</h1>
        <div class="date-sub">Generated: {{ timestamp }}</div>
    </div>
    <div style="text-align: right;">
        <div class="metric-title">SEASON RECORD</div>
        <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent-green);">
            {{ season_stats.record }} ({{ "%.1f"|format(season_stats.win_rate) }}%)
        </div>
        <div style="font-size: 0.9rem; color: var(--accent-green);">
            {{ "%+.1f"|format(season_stats.profit) }}u
        </div>
    </div>
</header>
```

### 5. A.I. Rating System

**Rating Calculation:**

- Based on edge magnitude, historical performance, and team indicators
- Range: 2.3 - 4.9
- Higher rating = stronger confidence

**Rating Display:**

- 4.5+ = PREMIUM PLAY
- 4.0-4.4 = STRONG PLAY
- 3.5-3.9 = GOOD PLAY
- 3.0-3.4 = STANDARD PLAY
- <3.0 = MARGINAL PLAY

### 6. Team Performance Indicators

**Indicator Types:**

- Strong performer: High win rate and positive ROI
- Hot streak: Recent strong performance
- Cold streak: Recent poor performance

**Display in HTML:**

```python
team_indicator = get_team_performance_indicator(picked_team, team_performance)
# Returns dict with: emoji, message, color, label
```

## Implementation Checklist

### Required Functions

- [ ] `load_picks_tracking()` - Load tracking data
- [ ] `save_picks_tracking()` - Save tracking data with backup
- [ ] `log_confident_pick()` - Log new picks
- [ ] `calculate_clv_status()` - Calculate CLV
- [ ] `fetch_odds()` - Fetch game odds
- [ ] `process_games()` - Process games and generate picks
- [ ] `save_html()` - Generate HTML output
- [ ] `calculate_ai_rating()` - Calculate confidence rating

### Required Tracking Fields

- [ ] `pick_id` - Unique identifier
- [ ] `opening_line` - Line when first logged
- [ ] `closing_line` - Latest line (updated on subsequent runs)
- [ ] `clv_status` - CLV calculation result
- [ ] `status` - Pick status (Pending/Win/Loss/Push)
- [ ] `edge` - Model edge over market
- [ ] `model_line` - Model prediction
- [ ] `market_line` - Market line

### HTML Template Sections

- [ ] Header with title and season record
- [ ] Game cards with matchup info
- [ ] Spread bet display
- [ ] Total bet display
- [ ] Metrics row (AI Score, Win %, Prediction)
- [ ] Tags row (team indicators, CLV, explanations)
- [ ] Performance statistics section

### Error Handling Patterns

```python
# Always wrap CLV calculations in try/except
try:
    clv_status = calculate_clv_status(...)
except Exception as e:
    print(f"⚠ Error calculating CLV: {e}")
    clv_status = "neutral"  # Fail gracefully

# Check if game started before updating CLV
if not game_has_started:
    # Update closing line and CLV
    pass

# Graceful degradation in HTML
if clv_beat_closing:
    # Show CLV tag
    pass
# If missing, simply don't show tag
```

## Best Practices

1. **Backward Compatibility**: Always handle missing fields gracefully
2. **Error Handling**: Wrap CLV calculations in try/except blocks
3. **Performance**: Only update CLV for games that haven't started
4. **Consistency**: Use same tag styling across all models
5. **Documentation**: Comment complex calculations (CLV, ratings)
6. **Testing**: Verify CLV works for both spreads and totals
7. **Validation**: Validate market lines before processing

## Code Examples

### Logging a New Pick

```python
def log_confident_pick(game_data, pick_type, edge, model_line, market_line):
    tracking_data = load_picks_tracking()
    pick_id = f"{game_data['home_team']}_{game_data['away_team']}_{game_data['commence_time']}_{pick_type}"
    
    # Check if exists
    existing_pick = next((p for p in tracking_data['picks'] if p['pick_id'] == pick_id), None)
    if existing_pick:
        return
    
    pick_entry = {
        "pick_id": pick_id,
        "opening_line": market_line,
        "closing_line": market_line,
        "clv_status": None,
        # ... other fields
    }
    
    tracking_data['picks'].append(pick_entry)
    save_picks_tracking(tracking_data)
```

### Updating CLV in process_games()

```python
# In process_games(), after calculating results:
if not game_has_started:
    existing_pick = find_existing_pick(pick_id)
    if existing_pick:
        if existing_pick.get('closing_line') != current_line:
            existing_pick['closing_line'] = current_line
            existing_pick['clv_status'] = calculate_clv_status(
                existing_pick.get('opening_line'),
                current_line,
                pick_type,
                pick_text
            )
```

### Displaying CLV Tag in HTML

```python
# In save_html(), before template rendering:
for result in results:
    result['clv_beat_closing'] = False
    pick = find_matching_pick(result, pick_type)
    if pick and pick.get('clv_status') == 'positive':
        result['clv_beat_closing'] = True
```

## Configuration Parameters Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `HOME_COURT_ADVANTAGE` | 3.0 | Points added for home team |
| `SPREAD_THRESHOLD` | 3.0 | Minimum edge to display spread pick |
| `TOTAL_THRESHOLD` | 4.0 | Minimum edge to display total pick |
| `CONFIDENT_SPREAD_EDGE` | 8.0 | Minimum edge to track spread pick |
| `CONFIDENT_TOTAL_EDGE` | 12.0 | Minimum edge to track total pick |
| `DAYS_AHEAD_TO_FETCH` | 2 | Days ahead to fetch games |
| `LAST_N_GAMES` | 10 | Recent games for form calculation |
| `SEASON_WEIGHT` | 0.55 | Weight for season stats |
| `FORM_WEIGHT` | 0.45 | Weight for recent form |

## Summary

This standard ensures:
- Consistent tracking structure across models
- CLV tracking for all picks
- Modern, responsive HTML output
- Graceful error handling
- Backward compatibility
- Clear documentation for future development

Use this document as a reference when creating new game-level models.
