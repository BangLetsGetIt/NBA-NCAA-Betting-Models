# Props Model HTML Styling Guide

## Overview

This guide documents the modern dark-themed HTML/CSS styling for all prop betting models. The styling includes team logos, player stats tracking, and a clean card-based layout.

## Design Philosophy

- **Dark Theme**: Professional dark background (#121212) with card-based layout
- **Visual Hierarchy**: Clear sections with appropriate spacing and typography
- **Player Context**: Team logos and historical player performance metrics
- **Responsive**: Mobile-friendly with breakpoints at 600px
- **Data-Driven**: Designed to display model predictions, AI scores, EV, and player tracking

---

## CSS Theme Variables

```css
:root {
    --bg-main: #121212;
    --bg-card: #1e1e1e;
    --bg-card-secondary: #2a2a2a;
    --text-primary: #ffffff;
    --text-secondary: #b3b3b3;
    --accent-green: #4ade80;
    --accent-red: #f87171;
    --accent-blue: #60a5fa;
    --border-color: #333333;
}
```

---

## HTML Structure

### Main Container

```html
<div class="container">
    <header>
        <h1>[Model Name] Props Model</h1>
        <div class="date-sub">[Version Info] • Season [Year]</div>
    </header>
    
    <section>
        <!-- Summary Stats Grid -->
        <div class="summary-grid">...</div>
    </section>
    
    <section>
        <div class="section-title">
            Top Value Plays <span class="highlight">Min AI Score: [X.X]</span>
        </div>
        
        <!-- Prop Cards -->
        <div class="prop-card">...</div>
    </section>
</div>
```

### Prop Card Structure

```html
<div class="prop-card">
    <!-- Card Header with Logo and Player Info -->
    <div class="card-header">
        <div class="header-left">
            <img src="[TEAM_LOGO_URL]" alt="[TEAM] Logo" class="team-logo">
            <div class="player-info">
                <h2>Player Name</h2>
                <div class="matchup-info">HOME vs AWAY</div>
            </div>
        </div>
        <div class="game-meta">
            <div class="game-date-time">Day, Month DD • H:MM PM ET</div>
        </div>
    </div>
    
    <!-- Card Body -->
    <div class="card-body">
        <!-- Bet Selection -->
        <div class="bet-main-row">
            <div class="bet-selection">
                <span class="txt-green">OVER</span> 
                <span class="line">[LINE]</span> 
                <span class="bet-odds">[ODDS]</span>
            </div>
        </div>
        
        <!-- Model Prediction -->
        <div class="model-subtext">
            Model Predicts: <strong>[PREDICTION]</strong> (Edge: [+/-X.X])
        </div>
        
        <!-- Metrics Grid -->
        <div class="metrics-grid">
            <div class="metric-item">
                <span class="metric-lbl">AI SCORE</span>
                <span class="metric-val txt-green">[SCORE]</span>
            </div>
            <div class="metric-item">
                <span class="metric-lbl">EV</span>
                <span class="metric-val txt-green">[+/-X.X%]</span>
            </div>
            <div class="metric-item">
                <span class="metric-lbl">WIN %</span>
                <span class="metric-val">[XX%]</span>
            </div>
        </div>
        
        <!-- Player Stats (Season Record & ROI) -->
        <div class="player-stats">
            <div class="player-stats-item">
                <div class="player-stats-label">This Season</div>
                <div class="player-stats-value">[W-L]</div>
            </div>
            <div class="player-stats-divider"></div>
            <div class="player-stats-item">
                <div class="player-stats-label">Player ROI</div>
                <div class="player-stats-value txt-green">[+/-X.X%]</div>
            </div>
        </div>
        
        <!-- Reasoning Tags -->
        <div class="tags-container">
            <span class="tag tag-red">[Reasoning Tag 1]</span>
            <span class="tag tag-green">[Reasoning Tag 2]</span>
            <span class="tag tag-blue">[Reasoning Tag 3]</span>
        </div>
    </div>
</div>
```

---

## Key CSS Classes

### Layout Classes

- **`.container`**: Max-width 800px, centered container
- **`.prop-card`**: Main card container with rounded corners and shadow
- **`.card-header`**: Header section with darker background
- **`.card-body`**: Main content area with padding

### Header Classes

- **`.header-left`**: Flex container for logo and player info
- **`.team-logo`**: Circular team logo (45px × 45px)
- **`.player-info`**: Player name and matchup container
- **`.game-meta`**: Right-aligned game date/time container
- **`.game-date-time`**: Styled date/time badge

### Betting Classes

- **`.bet-main-row`**: Container for bet selection
- **`.bet-selection`**: Large, bold bet selection text
- **`.bet-odds`**: Odds displayed inline with margin-left
- **`.line`**: The prop line value
- **`.model-subtext`**: Model prediction with edge

### Metrics Classes

- **`.metrics-grid`**: 3-column grid for AI Score, EV, Win %
- **`.metric-item`**: Individual metric container
- **`.metric-lbl`**: Metric label (uppercase, small)
- **`.metric-val`**: Metric value (large, bold)

### Player Stats Classes

- **`.player-stats`**: Container for player season stats
- **`.player-stats-item`**: Individual stat column
- **`.player-stats-label`**: Stat label (uppercase, small)
- **`.player-stats-value`**: Stat value (large, bold)
- **`.player-stats-divider`**: Vertical divider between stats

### Utility Classes

- **`.txt-green`**: Green text color
- **`.txt-red`**: Red text color
- **`.tag-green`**: Green tag background
- **`.tag-red`**: Red tag background
- **`.tag-blue`**: Blue tag background

---

## Team Logo URLs

### ESPN Logo Format

```
https://a.espncdn.com/i/teamlogos/nba/500/[TEAM_ABBREV].png
```

### NBA Team Abbreviations

Common abbreviations (3-letter codes):
- `atl` - Atlanta Hawks
- `bos` - Boston Celtics
- `bkn` - Brooklyn Nets
- `cha` - Charlotte Hornets
- `chi` - Chicago Bulls
- `cle` - Cleveland Cavaliers
- `dal` - Dallas Mavericks
- `den` - Denver Nuggets
- `det` - Detroit Pistons
- `gsw` - Golden State Warriors
- `hou` - Houston Rockets
- `ind` - Indiana Pacers
- `lac` - LA Clippers
- `lal` - Los Angeles Lakers
- `mem` - Memphis Grizzlies
- `mia` - Miami Heat
- `mil` - Milwaukee Bucks
- `min` - Minnesota Timberwolves
- `no` - New Orleans Pelicans
- `ny` - New York Knicks
- `okc` - Oklahoma City Thunder
- `orl` - Orlando Magic
- `phi` - Philadelphia 76ers
- `phx` - Phoenix Suns
- `por` - Portland Trail Blazers
- `sac` - Sacramento Kings
- `sa` - San Antonio Spurs
- `tor` - Toronto Raptors
- `utah` - Utah Jazz
- `was` - Washington Wizards

---

## Data Requirements

### Required Fields per Prop

1. **Player Information**
   - Player name
   - Team abbreviation (for logo URL)
   - Home/Away status
   - Opponent team

2. **Game Information**
   - Game date (formatted as "Day, Month DD")
   - Game time (formatted as "H:MM PM ET")

3. **Betting Information**
   - Bet type (OVER/UNDER)
   - Prop line (e.g., "31.5 PTS")
   - Odds (e.g., "-115", "+105")

4. **Model Predictions**
   - Model prediction value
   - Edge calculation (+/-)
   - AI Score
   - Expected Value (EV) percentage
   - Win probability percentage

5. **Player Stats (Optional - shown when data available)**
   - Season record (W-L format)
   - Player ROI percentage

6. **Reasoning Tags**
   - Array of contextual tags (opponent stats, recent form, pace, etc.)

---

## Implementation Steps

### 1. Copy Base CSS

Copy the complete `<style>` section from the reference HTML file. Ensure all CSS variables and classes are included.

### 2. Update HTML Template

Replace your existing HTML template with the structure outlined above. Key sections to update:

- Header with model name and season
- Summary stats grid (3 columns)
- Prop card loop with all required elements

### 3. Populate Team Logos

For each player prop, generate the team logo URL:
```python
team_abbrev = "okc"  # Get from your data
logo_url = f"https://a.espncdn.com/i/teamlogos/nba/500/{team_abbrev.lower()}.png"
```

### 4. Format Dates and Times

```python
from datetime import datetime
# Format: "Mon, Dec 15 • 7:10 PM ET"
game_date = game_datetime.strftime("%a, %b %d • %-I:%M %p ET")
```

### 5. Add Player Stats Section

Only show player stats when historical data exists:
```python
if player_season_record and player_roi:
    # Include player-stats div
else:
    # Skip player-stats div
```

### 6. Determine Tag Colors

- **Green tags** (`tag-green`): Positive factors (good form, weak opponent defense, etc.)
- **Red tags** (`tag-red`): Negative factors (bad form, strong opponent defense, etc.)
- **Blue tags** (`tag-blue`): Neutral/contextual factors (pace, totals, etc.)

### 7. Handle OVER/UNDER Colors

- **OVER bets**: Use `txt-green` class on the "OVER" text
- **UNDER bets**: Use `txt-red` class on the "UNDER" text

---

## Mobile Responsiveness

The styling includes mobile breakpoints at 600px:

- Summary grid changes from 3 columns to 2 columns
- Card header padding reduces
- Team logo size reduces (45px → 38px)
- Player name font size reduces (18px → 16px)

---

## Example Python Template Integration

```python
def generate_prop_card(player_data):
    """Generate HTML for a single prop card"""
    
    # Team logo URL
    team_abbrev = player_data['team'].lower()
    logo_url = f"https://a.espncdn.com/i/teamlogos/nba/500/{team_abbrev}.png"
    
    # Format game date/time
    game_dt = player_data['game_datetime']
    date_time_str = game_dt.strftime("%a, %b %d • %-I:%M %p ET")
    
    # Determine bet type color
    bet_type_color = "txt-green" if player_data['bet_type'] == "OVER" else "txt-red"
    
    # Player stats (optional)
    player_stats_html = ""
    if player_data.get('season_record') and player_data.get('player_roi'):
        player_stats_html = f"""
        <div class="player-stats">
            <div class="player-stats-item">
                <div class="player-stats-label">This Season</div>
                <div class="player-stats-value">{player_data['season_record']}</div>
            </div>
            <div class="player-stats-divider"></div>
            <div class="player-stats-item">
                <div class="player-stats-label">Player ROI</div>
                <div class="player-stats-value txt-green">{player_data['player_roi']}</div>
            </div>
        </div>
        """
    
    # Generate tags
    tags_html = ""
    for tag in player_data.get('reasoning_tags', []):
        tag_color = tag.get('color', 'blue')  # 'green', 'red', or 'blue'
        tags_html += f'<span class="tag tag-{tag_color}">{tag["text"]}</span>\n'
    
    return f"""
    <div class="prop-card">
        <div class="card-header">
            <div class="header-left">
                <img src="{logo_url}" alt="{player_data['team']} Logo" class="team-logo">
                <div class="player-info">
                    <h2>{player_data['player_name']}</h2>
                    <div class="matchup-info">{player_data['matchup']}</div>
                </div>
            </div>
            <div class="game-meta">
                <div class="game-date-time">{date_time_str}</div>
            </div>
        </div>
        <div class="card-body">
            <div class="bet-main-row">
                <div class="bet-selection">
                    <span class="{bet_type_color}">{player_data['bet_type']}</span> 
                    <span class="line">{player_data['line']}</span> 
                    <span class="bet-odds">{player_data['odds']}</span>
                </div>
            </div>
            <div class="model-subtext">
                Model Predicts: <strong>{player_data['prediction']}</strong> (Edge: {player_data['edge']})
            </div>
            <div class="metrics-grid">
                <div class="metric-item">
                    <span class="metric-lbl">AI SCORE</span>
                    <span class="metric-val txt-green">{player_data['ai_score']}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-lbl">EV</span>
                    <span class="metric-val txt-green">{player_data['ev']}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-lbl">WIN %</span>
                    <span class="metric-val">{player_data['win_prob']}</span>
                </div>
            </div>
            {player_stats_html}
            <div class="tags-container">
                {tags_html}
            </div>
        </div>
    </div>
    """
```

---

## Models to Update

Apply this styling to:

1. **NBA Props**
   - `nba/nba_points_props_model.py` ✅ (Reference implementation)
   - `nba/nba_rebounds_props_model.py`
   - `nba/nba_assists_props_model.py`
   - `nba/nba_3pt_props_model.py`

2. **NFL Props** (if applicable)
   - `nfl/nfl_passing_yards_props_model.py`
   - `nfl/nfl_rushing_yards_props_model.py`
   - `nfl/nfl_receptions_props_model.py`

3. **Other Sport Props** (if applicable)
   - Any other prop models following similar structure

---

## Notes

- **Player Stats Section**: This section should only appear when historical betting data exists for that player. If no data, simply omit the `.player-stats` div entirely.

- **Team Logo Fallback**: If a team abbreviation doesn't match ESPN's format, you may need a mapping table or fallback image.

- **Font Loading**: The Inter font is loaded from Google Fonts. Ensure internet connection or host locally if needed.

- **Date Formatting**: The `%-I` format (no leading zero on hours) works on Unix/Mac. On Windows, use `%#I` or format manually.

- **Conditional Styling**: Use conditional logic in your template to show/hide sections based on data availability.
