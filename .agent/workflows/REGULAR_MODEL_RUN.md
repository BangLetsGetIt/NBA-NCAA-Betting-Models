# Workflow: Regular Model Execution & Verification

Follow these steps every time a model is modified or a new run is triggered.

## Step 1: Execute Model
// turbo
Run the specific model script:
`python3 nfl/nfl_passing_yards_props_model.py` (or corresponding file)

## Step 2: Global Stats Backfill
// turbo
Always run the backfill utility to ensure ALL pending picks have current stats:
`python3 backfill_all_stats.py`

## Step 3: Grade Existing Picks
// turbo
Ensure previous games are graded so ROI/Record stats are current:
`python3 auto_grader.py`

## Step 4: Regenerate Aggregated HTML
// turbo
Generate the updated Best Plays dashboard:
`python3 best_plays_bot.py`

## Step 5: Final Quality Audit
Check for these "Red Flags" in `best_plays.html`:
- [ ] Any "N/A" or "0.0" values for player props?
- [ ] Any duplicate players?
- [ ] Is the "Model Record" accurate and not hardcoded?
- [ ] Are the team logos appearing?

## Step 6: Git Push
// turbo
`git add . && git commit -m "Standard model run update" && git push origin main`
