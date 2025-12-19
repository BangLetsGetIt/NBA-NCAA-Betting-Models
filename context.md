# Sports Models Context for AI Agents

> **Last Updated**: 2025-12-19 03:15 AM ET  
> **System Status**: ✅ ALL MODELS OPERATIONAL

---

## 🚀 Quick Start for New Agents

**Read this file first.** For deep dives, see:
- `CODEBASE_OVERVIEW.md` - Full architecture, model inventory, code patterns
- `PROPS_HTML_STYLING_GUIDE.md` - HTML/CSS styling standards
- `AGENT_AUDIT_INSTRUCTIONS.md` - Audit procedures (if doing diagnostics)

---

## What This Codebase Does

AI-powered sports betting models that:
1. **Fetch** live odds from The Odds API
2. **Analyze** games/props using edge + AI scoring algorithms
3. **Generate** +EV picks (positive expected value)
4. **Track** all picks with full results history
5. **Display** picks via GitHub Pages HTML output

---

## Directory Structure

```
sports-models/
├── nba/                    # NBA main model + 4 prop models
├── nfl/                    # NFL main model + 5 prop models
├── ncaa/                   # NCAAB/CBB main model + 3 prop models
├── wnba/                   # WNBA main + props model
├── soccer/                 # Soccer model
├── auto_grader.py          # Central automation/grading script
├── run_nba_models.sh       # alias: nbamodels
├── run_nfl_models.sh       # alias: nflmodels
├── run_cbb_models.sh       # alias: cbbmodels
└── CODEBASE_OVERVIEW.md    # Full documentation
```

---

## Current Model Status (Dec 2025)

| Sport | Main Model | Props Models | Status |
|-------|------------|--------------|--------|
| NBA | ✅ Working | ✅ Points, Rebounds, Assists, 3PT | Fully operational |
| NFL | ✅ Working | ✅ Passing, Rushing, Receiving, Receptions, ATD | Fully operational |
| NCAAB | ✅ Working | ✅ Points, Rebounds, Assists | Fully operational |
| WNBA | ✅ Working | ✅ Props | Seasonal (offseason) |
| Soccer | ✅ Working | N/A | Fully operational |

---

## Common Commands

```bash
# Run all NBA models
nbamodels

# Run all NFL models  
nflmodels

# Run NCAAB/CBB models
cbbmodels

# Run individual model
cd nfl && python3 nfl_receiving_yards_props_model.py

# Push changes to GitHub Pages
git add . && git commit -m "Update" && git push origin main
```

---

## Key Concepts

### Edge Calculation
```
OVER:  edge = projected_value - prop_line
UNDER: edge = prop_line - projected_value
```
Positive edge = +EV opportunity.

### AI Score (0-10)
Composite of edge magnitude + player consistency. Higher = more confident pick.

### Tracking
Each model has a `*_tracking.json` file storing all picks with:
- `status`: pending → win/loss/push
- `profit_loss`: Result in cents (91 = $0.91 profit on $1 bet)
- `actual_val`: Real stat value for grading

---

## Recent Major Fixes (Dec 2024)

1. ✅ NFL main model now displays Model/Edge values (Jinja2 scoping fix)
2. ✅ NFL prop models show Season/Recent avg (regenerated HTML)
3. ✅ NCAAB has Daily Performance section (Today/Yesterday)
4. ✅ Soccer grading integrated into auto_grader.py
5. ✅ All tracking schemas standardized with profit_loss field

---

## When Making Changes

1. **Don't break tracking** - JSON schema must stay compatible
2. **Match styling** - Follow PROPS_HTML_STYLING_GUIDE.md
3. **Test first** - Run model and check HTML before pushing
4. **Commit HTML** - Model runs generate .html files that must be committed
5. **Check GitHub Pages** - Verify live site updated (~30 sec delay)

---

## GitHub Pages URLs

- **Dashboard**: https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/dashboard.html
- **NBA Main**: https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nba/nba_model_output.html
- **NFL Main**: https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/nfl/nfl_model_output.html
- **NCAAB Main**: https://bangletsgetit.github.io/NBA-NCAA-Betting-Models/ncaa/ncaab_model_output.html

---

## Environment

```bash
# Required in .env
ODDS_API_KEY=your_key

# Python dependencies
pip install requests python-dotenv pytz jinja2 pandas numpy
```

---

## Questions?

If anything is unclear, ask the user. They know this codebase well and can provide context on design decisions.