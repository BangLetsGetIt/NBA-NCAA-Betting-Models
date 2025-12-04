# NBA 3-Point Props A.I. Model

## Overview

This model analyzes NBA player 3-point props (3PM - 3-pointers made) and identifies high-value betting opportunities using an A.I. scoring system (0-10 scale).

**Inspired by @ThePropDealer's methodology**

## Features

- **Dual Analysis**: Identifies both OVER and UNDER plays
- **A.I. Scoring**: 0-10 scale ranking (8.0+ are premium plays)
- **Multiple Factors**: Recent form, season averages, matchups, consistency
- **Beautiful HTML Output**: Easy-to-read report for beginner bettors
- **Terminal Output**: Quick results in your command line

## How the A.I. Score Works

The model calculates a 0-10 score for each player prop based on:

### 1. Season Average vs Prop Line (40% weight)
- Compares player's season 3PM average to the betting line
- Higher deviation = higher score

### 2. Recent Form (30% weight)
- Analyzes last 10 games
- Hot streaks boost OVER scores
- Cold streaks boost UNDER scores

### 3. Consistency (20% weight)
- How reliable is the player hitting their numbers?
- Consistent players get higher scores

### 4. Matchup Factor (10% weight)
- Opponent's 3PT defense ranking
- Home/away considerations
- Pace of play factors

## Installation & Setup

### Prerequisites

```bash
# Python 3.8 or higher
python3 --version

# Install required packages
pip3 install requests pytz
```

### API Key Setup

1. Get a free API key from [The Odds API](https://the-odds-api.com/)
2. Set your API key as an environment variable:

```bash
export ODDS_API_KEY='your_api_key_here'
```

Or edit the script directly:
```python
API_KEY = 'your_api_key_here'
```

## Usage

### Run the Model

```bash
cd /Users/rico/sports-models/nba
python3 nba_3pt_props_model.py
```

### Output

The model generates two outputs:

1. **Terminal Display**: Quick view of top 10 plays
2. **HTML Report**: Full report at `nba_3pt_props.html`

### View HTML Report

```bash
# macOS
open nba_3pt_props.html

# Linux
xdg-open nba_3pt_props.html

# Windows
start nba_3pt_props.html
```

## Understanding the Output

### A.I. Score Ranges

| Score | Rating | Description |
|-------|--------|-------------|
| 9.0-10.0 | 🔥 ELITE | Highest confidence plays |
| 8.5-8.9 | ⭐ PREMIUM | Strong plays |
| 8.0-8.4 | ✅ GOOD | Solid plays |
| < 8.0 | ❌ FILTERED | Not shown (below threshold) |

### Example Play

```
Player: Cason Wallace
Prop: OVER 1.5 3PT
Team: OKC
Opponent: GSW
A.I. Score: 9.36
```

**Interpretation**:
- Wallace's recent form and matchup suggest he'll likely make 2+ three-pointers
- Score of 9.36 indicates very high confidence

## Model Parameters

You can adjust these in the script:

```python
MIN_AI_SCORE = 8.0         # Minimum score to display (8.0-10.0)
TOP_PLAYS_COUNT = 15       # How many plays to show
RECENT_GAMES_WINDOW = 10   # Games to analyze for form
```

## For Beginner Bettors

### Step-by-Step Guide

1. **Run the model** before NBA games start
2. **Open the HTML report** for easy viewing
3. **Focus on high scores** (8.5+) for your first bets
4. **Start small** - Don't bet more than you can afford to lose
5. **Track results** - Keep a log of your bets

### Reading the Report

- **Green section** = OVER plays (player will exceed their line)
- **Red section** = UNDER plays (player will fall short)
- **Higher A.I. scores** = More confident predictions
- **Check the matchup** - Some opponents give up more 3PT

### Pro Tips

- ✅ Look for players on hot streaks (recent avg > season avg)
- ✅ Consider the opponent's 3PT defense
- ✅ Check if the player is starting or coming off bench
- ✅ Verify the player is not injured or in foul trouble
- ❌ Don't blindly bet every high-scoring play
- ❌ Don't chase losses by increasing bet size
- ❌ Don't ignore context (blowouts, garbage time, etc.)

## Data Sources

The model can integrate with:

1. **The Odds API** - Player props and lines
2. **NBA Stats API** - Player statistics
3. **Basketball Reference** - Historical data
4. **ESPN API** - Game schedules and matchups

*Note: Current version uses sample data structure. Full integration requires API keys and data parsing.*

## Customization

### Adjust Scoring Weights

Edit the `calculate_ai_score()` function:

```python
# Current weights
season_avg_weight = 0.40  # 40%
recent_form_weight = 0.30  # 30%
consistency_weight = 0.20  # 20%
matchup_weight = 0.10      # 10%
```

### Change Thresholds

```python
MIN_AI_SCORE = 8.5  # Show only elite plays
TOP_PLAYS_COUNT = 10  # Show fewer plays
```

### Modify Styling

The HTML template is embedded in the script. Search for the `<style>` section to customize colors, fonts, and layout.

## Example Output

```
================================================================================
TOP OVER PLAYS
================================================================================
 1. Cason Wallace             | OVER 1.5 3PT    | OKC vs GSW | A.I.: 9.36
 2. Julius Randle             | OVER 1.5 3PT    | MIN vs NOP | A.I.: 9.35
 3. Jaylen Brown              | OVER 1.5 3PT    | BOS vs NYK | A.I.: 9.29
 4. Brandin Podziemski        | OVER 1.5 3PT    | GSW vs OKC | A.I.: 9.26
 5. Mikal Bridges             | OVER 1.5 3PT    | NYK vs BOS | A.I.: 9.20

================================================================================
TOP UNDER PLAYS
================================================================================
 1. Chet Holmgren             | UNDER 1.5 3PT   | OKC vs GSW | A.I.: 9.34
 2. Jaden McDaniels           | UNDER 1.5 3PT   | MIN vs NOP | A.I.: 9.18
 3. Scottie Barnes            | UNDER 1.5 3PT   | TOR vs POR | A.I.: 9.17
```

## Disclaimer

⚠️ **Important**: This model is for **entertainment and educational purposes only**.

- Past performance does not guarantee future results
- No model can predict outcomes with 100% accuracy
- Only bet what you can afford to lose
- Gambling can be addictive - seek help if needed
- Check local laws regarding sports betting

## Support & Updates

- Check the HTML report for generation timestamp
- Model factors in the most recent available data
- For questions or issues, review the code comments

## Credits

- Model methodology inspired by **@ThePropDealer** on Twitter/X
- Built using Python 3 and modern web technologies
- Designed for ease of use by beginner bettors

---

**Good luck and bet responsibly!** 🍀
