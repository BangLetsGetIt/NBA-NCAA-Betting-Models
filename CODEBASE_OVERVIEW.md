# CourtSide Analytics - Sports Betting Models Codebase

> **Last Updated**: 2025-12-20  
> **Status**: ✅ All Models Operational  
> **GitHub Pages**: https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/

---

## Quick Reference for New Agents

### Repository Purpose
This codebase contains AI-powered sports betting models that:
1. Fetch live odds from The Odds API
2. Analyze matchups using proprietary algorithms
3. Generate +EV (positive expected value) betting picks
4. Track picks with full results history
5. Display picks via GitHub Pages HTML output

### Run Commands (Aliases Available)
```bash
nbamodels    # Runs all NBA models (main + 4 props)
nflmodels    # Runs all NFL models (main + 4 props)
cbbmodels    # Runs NCAAB/CBB models
wnbamodels   # Runs WNBA models
```

### Key Files at a Glance
| Purpose | File |
|---------|------|
| Central automation | `auto_grader.py` |
| NBA runner script | `run_nba_models.sh` |
| NFL runner script | `run_nfl_models.sh` |
| NCAAB runner script | `run_cbb_models.sh` |
| Props grading | `nfl/props_grader.py` |
| Styling guide | `PROPS_HTML_STYLING_GUIDE.md` |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
│  - The Odds API (live odds, game times, scores)                 │
│  - Player stats caches (JSON files for each sport)              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MODEL LAYER                                  │
│  nba_*.py  │  nfl_*.py  │  ncaab_*.py  │  wnba_*.py  │ soccer_*.py │
│  - analyze_props() / process_games()                            │
│  - Edge calculation, AI scoring                                 │
│  - Recommendation generation                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRACKING LAYER                                │
│  *_tracking.json files for each model                           │
│  - Stores all picks (pending, win, loss, push)                  │
│  - profit_loss, actual values, CLV data                         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                                  │
│  - generate_html_output() → *.html files                        │
│  - CSS styling: Dark theme, green/red accents                   │
│  - GitHub Pages hosting                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Model Inventory (All Operational ✅)

### NBA Models (`nba/`)
| Model | File | Output HTML | Tracking File |
|-------|------|-------------|---------------|
| Main Spread/Total | `nba_model_IMPROVED.py` | `nba_model_output.html` | `nba_picks_tracking.json` |
| Points Props | `nba_points_props_model.py` | `nba_points_props.html` | `nba_points_props_tracking.json` |
| Rebounds Props | `nba_rebounds_props_model.py` | `nba_rebounds_props.html` | `nba_rebounds_props_tracking.json` |
| Assists Props | `nba_assists_props_model.py` | `nba_assists_props.html` | `nba_assists_props_tracking.json` |
| 3PT Props | `nba_3pt_props_model.py` | `nba_3pt_props.html` | `nba_3pt_props_tracking.json` |

### NFL Models (`nfl/`)
| Model | File | Output HTML | Tracking File |
|-------|------|-------------|---------------|
| Main Spread/Total | `nfl_model_IMPROVED.py` | `nfl_model_output.html` | `nfl_picks_tracking.json` |
| Passing Yards | `nfl_passing_yards_props_model.py` | `nfl_passing_yards_props.html` | `nfl_passing_yards_props_tracking.json` |
| Rushing Yards | `nfl_rushing_yards_props_model.py` | `nfl_rushing_yards_props.html` | `nfl_rushing_yards_props_tracking.json` |
| Receiving Yards | `nfl_receiving_yards_props_model.py` | `nfl_receiving_yards_props.html` | `nfl_receiving_yards_props_tracking.json` |
| Receptions | `nfl_receptions_props_model.py` | `nfl_receptions_props.html` | `nfl_receptions_props_tracking.json` |
| Anytime TD | `atd_model.py` | `nfl_atd_props.html` | `nfl_atd_props_tracking.json` |

### NCAAB/CBB Models (`ncaa/`)
| Model | File | Output HTML | Tracking File |
|-------|------|-------------|---------------|
| Main Spread/Total | `ncaab_model_2ndFINAL.py` | `ncaab_model_output.html` | `ncaab_picks_tracking.json` |
| Points Props | `cbb_points_props_model.py` | `ncaab_points_props.html` | `cbb_points_props_tracking.json` |
| Rebounds Props | `cbb_rebounds_props_model.py` | `ncaab_rebounds_props.html` | `cbb_rebounds_props_tracking.json` |
| Assists Props | `cbb_assists_props_model.py` | `ncaab_assists_props.html` | `cbb_assists_props_tracking.json` |

### WNBA Models (`wnba/`)
| Model | File | Output HTML |
|-------|------|-------------|
| Main Model | `wnba_model.py` | `wnba_model_output.html` |
| Props Model | `wnba_props_model.py` | `wnba_props_output.html` |

### Soccer Models (`soccer/`)
| Model | File | Output HTML | Tracking File |
|-------|------|-------------|---------------|
| Main Model | `soccer_model_IMPROVED.py` | `soccer_model_output.html` | `soccer_picks_tracking.json` |

---

## Common Code Patterns

### Standard Model Structure
Every prop model follows this pattern:
```python
# 1. Configuration
API_KEY = os.getenv('ODDS_API_KEY')
TRACKING_FILE = "..._tracking.json"
OUTPUT_HTML = "....html"

# 2. Tracking Functions
def load_tracking_data(): ...
def save_tracking_data(data): ...
def track_new_picks(recommendations, odds_data): ...

# 3. Data Fetching
def load_player_stats(): ...
def get_props_odds(): ...

# 4. Analysis Logic
def analyze_props(props, stats_cache):
    # Calculate edge = projected - line (for OVER)
    # Calculate ai_score based on edge + consistency
    # Return recommendations if thresholds met

# 5. HTML Generation
def generate_html_output(plays, stats, tracking_data): ...

# 6. Main
def main():
    grade_pending_picks()  # First
    props = get_props_odds()
    stats = load_player_stats()
    recommendations = analyze_props(props, stats)
    generate_html_output(...)
    track_new_picks(...)
```

### Tracking JSON Schema
All tracking files use this structure:
```json
{
  "picks": [
    {
      "pick_id": "PlayerName_Line_Type_Date",
      "player": "Player Name",
      "pick_type": "Points|Rebounds|etc",
      "bet_type": "over|under",
      "line": 25.5,
      "prop_line": 25.5,
      "odds": -110,
      "edge": 3.5,
      "ai_score": 8.2,
      "team": "LAL",
      "opponent": "BOS",
      "game_date": "2024-12-19T00:00:00Z",
      "game_time": "2024-12-19T19:00:00Z",
      "status": "pending|win|loss|push",
      "result": null,
      "profit_loss": 0,
      "actual_val": null
    }
  ]
}
```

### Profit/Loss Calculation
```python
# Standard -110 odds:
if status == 'win':
    profit_loss = 91  # Win $91 on $100 bet
elif status == 'loss':
    profit_loss = -100  # Lose $100

# Plus odds (+150):
if odds > 0:
    profit_loss = odds  # Win $150 on $100 bet
```

---

## Environment Setup

### Required Environment Variables
```bash
# .env file
ODDS_API_KEY=your_api_key_here
```

### Dependencies
```bash
pip install requests python-dotenv pytz jinja2 pandas numpy
```

### Shell Aliases (add to ~/.zshrc)
```bash
alias nbamodels="cd /Users/rico/sports-models && ./run_nba_models.sh"
alias nflmodels="cd /Users/rico/sports-models && ./run_nfl_models.sh"
alias cbbmodels="cd /Users/rico/sports-models && ./run_cbb_models.sh"
alias wnbamodels="cd /Users/rico/sports-models && ./run_wnba_models.sh"
```

---

## Recent Fixes Applied (Dec 2024)

### P0 Critical Fixes ✅
1. **Added missing `json` import** to `auto_grader.py`
2. **Fixed sys.path duplicate** - changed 'nfl' to 'soccer' in auto_grader.py
3. **Removed misplaced file** - deleted `soccer/nfl_picks_tracking.json`
4. **Standardized NBA pick_id** - all prop models now include `prop_line` in pick_id
5. **Backfilled NFL edge data** - corrected 16 receiving yards picks with wrong edge values
6. **Added profit_loss field** to 1765 NCAAB picks
7. **Fixed null profit_loss** values in 103 Soccer picks

### P1 Logic Fixes ✅
8. **Added soccer grading** to `auto_grader.py`
9. **Fixed NFL main model** - Jinja2 scoping bug preventing bets from displaying
10. **Added Daily Performance** section to NCAAB model
11. **Regenerated NFL prop HTMLs** - season/recent avg now display correctly

### NBA Model Optimization (Dec 20, 2024) ✅
12. **Fixed 98% UNDER bias** - Model projected totals ~18pts below market
    - Added `TOTAL_CALIBRATION = 12.0` to balance OVER/UNDER betting
13. **Tightened edge thresholds** to filter weak plays:
    - `SPREAD_THRESHOLD`: 3.0 → 5.0
    - `TOTAL_THRESHOLD`: 4.0 → 6.0
    - `CONFIDENT_TOTAL_EDGE`: 12.0 → 15.0
14. **Analysis showed Edge 5-8 range was 10-17 (37%)** losing -8.59u - now filtered out

---

## NBA Model Parameters (nba_model_IMPROVED.py)

> **Important**: These parameters control pick selection and should be tuned based on performance.

```python
# Display Thresholds (minimum edge to show a potential bet)
SPREAD_THRESHOLD = 5.0      # Show spread picks with 5+ edge
TOTAL_THRESHOLD = 6.0       # Show total picks with 6+ edge

# Logging Thresholds (minimum edge to actually track/bet)
CONFIDENT_SPREAD_EDGE = 8.0  # Track spread picks with 8+ edge
CONFIDENT_TOTAL_EDGE = 15.0  # Track total picks with 15+ edge

# Calibration (fixes systematic model bias)
TOTAL_CALIBRATION = 12.0    # Add to model total - fixes UNDER bias
HOME_COURT_ADVANTAGE = 3.0  # Points added for home team
```

### When to Adjust Parameters
- If **win rate drops below 52%**, consider raising thresholds
- If **one bet type underperforms** (spreads vs totals), adjust that type's threshold
- If **OVER/UNDER imbalance** reappears, adjust `TOTAL_CALIBRATION`
- Run analysis: `python3 -c "..."` scripts in model file to check edge range performance

---

## HTML Styling Reference

### Color Scheme
```css
--bg-main: #121212;       /* Main background */
--bg-card: #1c1c1e;       /* Card background */
--bg-metric: #2c2c2e;     /* Metric box background */
--text-primary: #ffffff;   /* White text */
--text-secondary: #8e8e93; /* Gray text */
--accent-green: #34c759;   /* Win/positive */
--accent-red: #ff3b30;     /* Loss/negative */
```

### Standard HTML Sections
1. **Header** - Title, Generated timestamp, Season Record
2. **Daily Performance** - TODAY and YESTERDAY records
3. **Game/Player Cards** - Individual picks with edge, model prediction
4. **Recent Form** - Last 10/20/50 performance
5. **Tracking Table** - Optional detailed pick history

---

## Common Tasks for Agents

### Adding a New Model
1. Copy existing model as template (e.g., `nba_points_props_model.py`)
2. Update API endpoint for new prop type
3. Update stats cache filename
4. Update tracking filename
5. Update HTML output filename
6. Add to runner script (`run_*_models.sh`)

### Debugging Missing Data
1. Check if stats cache exists: `ls -la *_stats_cache.json`
2. Check if API key is set: `echo $ODDS_API_KEY`
3. Run model directly: `python3 model_file.py`
4. Check tracking file for data: `cat *_tracking.json | python3 -m json.tool | head`

### Regenerating HTML
```bash
cd /Users/rico/sports-models/nfl
python3 nfl_receiving_yards_props_model.py
git add *.html
git commit -m "Regenerate HTML"
git push origin main
```

---

## GitHub Pages URLs

| Model | URL |
|-------|-----|
| Dashboard | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/dashboard.html |
| NBA Main | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nba/nba_model_output.html |
| NBA Points | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nba/nba_points_props.html |
| NBA Rebounds | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nba/nba_rebounds_props.html |
| NBA Assists | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nba/nba_assists_props.html |
| NBA 3PT | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nba/nba_3pt_props.html |
| NFL Main | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nfl/nfl_model_output.html |
| NFL Passing | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nfl/nfl_passing_yards_props.html |
| NFL Rushing | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nfl/nfl_rushing_yards_props.html |
| NFL Receiving | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nfl/nfl_receiving_yards_props.html |
| NFL Receptions | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nfl/nfl_receptions_props.html |
| NCAAB Main | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/ncaa/ncaab_model_output.html |
| Soccer | https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/soccer/soccer_model_output.html |

---

## Contact & Support

Repository: https://github.com/BangLetsGetIt/NBA-NCAA-Betting-Models
