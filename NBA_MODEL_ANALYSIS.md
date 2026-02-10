# NBA Model Analysis

## Summary
- The NBA models fetch odds and player/game stats, compute model lines, "edge" vs market lines, and an `ai_score` to rank recommendations. Winning picks are written to the tracking file `nba_picks_tracking.json` and later graded by `auto_grader.py`.

## Canonical Files (entrypoints)
- `nba/nba_model_IMPROVED.py` — primary NBA orchestration and entrypoint (`main()`).
- `nba/nba_points_props_model.py`, `nba/nba_rebounds_props_model.py`, `nba/nba_assists_props_model.py`, `nba/nba_3pt_props_model.py` — per-prop entrypoints (each exposes `main()` or `analyze_props()` flows).
- `nba/nba_model_live.py`, `nba/nba_player_props_v2.py` — live/different variants.

## Key Functions & Flow
1. Fetch odds/stats: helper (pattern) `get_props_odds()` or direct `requests` calls using `ODDS_API_KEY`.
2. Normalize inputs: timezone handling with `pytz`, convert timestamps to UTC-aware datetimes.
3. Compute model metrics: per-player or per-game expected value, model_line, edge = model_line - market_line (or formatted for totals/spreads).
4. Score picks: compute `ai_score` (composite heuristic involving edge, model confidence, and historical metrics).
5. Selection: apply threshold constants (`SPREAD_THRESHOLD`, `TOTAL_THRESHOLD`, `MIN_AI_SCORE`, `CONFIDENT_*_EDGE`) to filter +EV picks.
6. Persist: call `track_new_picks()` / `save_tracking_data()` which appends to `nba_picks_tracking.json`.
7. Grade & display: `auto_grader.py` grades pending picks and `unified_dashboard_interactive.py` aggregates tracking files into the dashboard HTML.

## Thresholds / Key Constants (canonical in `nba/nba_model_IMPROVED.py` and related prop modules)
- `SPREAD_THRESHOLD`: 6.0
- `TOTAL_THRESHOLD`: 10.0
- `CONFIDENT_SPREAD_EDGE`: 6.0
- `CONFIDENT_TOTAL_EDGE`: 10.0
- `TOTAL_CALIBRATION`: 6.0
- `MIN_AI_SCORE` (per-prop examples):
  - points_props: 10.0
  - rebounds_props: 10.0
  - 3pt_props: 7.5

Note: Some backup files and variants exist with different constants; treat the active modules under `nba/` as canonical unless you instruct otherwise.

## Sample Pick Lifecycle
- A model run evaluates candidate props/games and creates a `pick` dict with fields: `pick_id`, `player`, `pick_type`, `bet_type`, `line`, `odds`, `edge`, `ai_score`, `units`, `status` (initially `pending`), `date_logged`.
- `track_new_picks()` appends new picks to `nba_picks_tracking.json` (ensuring `pick_id` deduping by format Player_Line_Type_Date).
- `auto_grader.py` periodically scans tracking files, resolves `pending` picks by comparing actual results, sets `status` (win/loss/push), fills `profit_loss`, and writes back.
- Dashboard generation aggregates `picks` arrays across sports into `unified_dashboard_data.json` and renders `unified_dashboard_interactive.html` with Jinja2 templates.

## Sample Tracking Schema (example fields)
- `pick_id`, `date_logged`, `game_date`, `game_time`, `player`, `home_team`, `away_team`, `pick_type`, `bet_type`, `line`, `odds`, `edge`, `ai_score`, `units`, `status`, `result`, `profit_loss`, `actual_val`

## Runners / Commands
- Per-model: e.g. run points props

```bash
./run_nba_models.sh
python3 -c "from nba.nba_model_IMPROVED import main; main(dry_run=True)"
python3 unified_dashboard_interactive.py
python3 auto_grader.py
```

## External Integrations
- Odds providers via HTTP (`requests`), keyed by `ODDS_API_KEY` env var (python-dotenv supported in docs).
- Jinja2 for HTML rendering.
- pandas/numpy for data transformations and `pytz` for timezone handling.

## Blockers / Runtime Notes
- Valid `ODDS_API_KEY` and network access required to run full model flows.
- Some models rely on local caches or historical stat files (season caches). If missing, runs will be incomplete.
- Multiple backup files exist — verify which files you want canonical before large-scale threshold edits.

## Per-Prop Detailed Analysis

### Points Props (`nba/nba_points_props_model.py`)
- Tracking file: `nba/nba_points_props_tracking.json`
- Canonical constants:
  - `MIN_AI_SCORE = 10.0`
  - `TOP_PLAYS_COUNT = 10`
  - `RECENT_GAMES_WINDOW = 10`
  - `MIN_EDGE_OVER_LINE = 2.0`
  - `MIN_EDGE_UNDER_LINE = 1.5`
  - `MIN_RECENT_FORM_EDGE = 1.2`
- Key functions:
  - `get_nba_player_points_stats()` — fetches season and recent form from `nba_api`, caches to `nba_player_points_stats_cache.json`.
  - `get_opponent_defense_factors()` — builds team-level defensive metrics used for matchup adjustments.
  - `track_new_picks(over_plays, under_plays)` — creates/updates picks in tracking file; computes `pick_id`, stores `ai_score`, `edge`, `opening_odds`, `latest_odds`.
  - `grade_pending_picks()` — batches pending picks by date, fetches daily stats, resolves DNPs, writes `status`/`profit_loss`.
  - `backfill_profit_loss()` / `calculate_tracking_stats()` — ensure ROI and historical summary correctness.
- Data sources: `nba_api` endpoints (`leaguedashplayerstats`, `playergamelog`), The Odds API via `ODDS_API_KEY`.

### Rebounds Props (`nba/nba_rebounds_props_model.py`)
- Tracking file: `nba/nba_rebounds_props_tracking.json`
- Canonical constants:
  - `MIN_AI_SCORE = 10.0`
  - `TOP_PLAYS_COUNT = 10`
  - `RECENT_GAMES_WINDOW = 10`
  - `MIN_EDGE_OVER_LINE = 1.5`
  - `MIN_EDGE_UNDER_LINE = 1.0`
  - `MIN_RECENT_FORM_EDGE = 1.2`
- Key functions:
  - `fetch_all_player_stats_for_date(game_date_str)` — batch-fetches daily rebounds using `leaguedashplayerstats` and returns mapping player->rebounds for grading.
  - `track_new_picks()` — enforces `MIN_AI_SCORE` gate before adding picks to tracking.
  - `grade_pending_picks()` — uses batch stats + `fetch_completed_teams_for_date()` helper to finalize picks efficiently; handles DNP/void logic.
  - `backfill_profit_loss()` and tracking stats helpers identical to other prop modules.

### Assists Props (`nba/nba_assists_props_model.py`)
- Tracking file: `nba/nba_assists_props_tracking.json`
- Canonical constants:
  - `MIN_AI_SCORE = 10.0`
  - `TOP_PLAYS_COUNT = 5`
  - `RECENT_GAMES_WINDOW = 10`
  - `MIN_EDGE_OVER_LINE = 1.5`
  - `MIN_EDGE_UNDER_LINE = 1.0`
- Key functions:
  - `fetch_player_assists_from_nba_api(player_name, team_name, game_date_str)` — per-player lookup via `playergamelog` (fallback; grading prefers batch methods when available).
  - `track_new_picks()` — filters by `MIN_AI_SCORE` and appends picks.
  - `grade_pending_picks()` — waits a buffer (~4 hours) or checks `fetch_completed_teams_for_date()` before grading; marks DNPs as `void`.

### 3PT Props (`nba/nba_3pt_props_model.py`)
- Tracking file: `nba/nba_3pt_props_tracking.json`
- Canonical constants:
  - `MIN_AI_SCORE = 7.5`
  - `TOP_PLAYS_COUNT = 10`
  - `RECENT_GAMES_WINDOW = 10`
  - `MIN_EDGE_OVER_LINE = 1.0`
  - `MIN_EDGE_UNDER_LINE = 0.8`
- Key functions:
  - `fetch_all_player_stats_for_date(game_date_str)` — batch mapping player -> `FG3M` for grading.
  - `track_new_picks()` / `grade_pending_picks()` — similar behavior to other props modules; handles fuzzy/alias matching for player names.

### Common prop behaviors
- All props modules:
  - Use `ODDS_API_KEY` for market lines; if missing the modules remain importable but cannot fetch odds.
  - Maintain a local cache for expensive `nba_api` calls (6-hour expiration in several modules).
  - Build `pick` dicts with fields: `pick_id`, `player`, `prop_line`, `bet_type`, `team`, `opponent`, `ai_score`, `odds`, `opening_odds`, `latest_odds`, `game_time`, `season_avg`, `recent_avg`, `edge`, `ev`, `tracked_at`, `status`, `result`, and an actual stat field (`actual_pts`, `actual_reb`, `actual_ast`, `actual_3pm`).
  - Use a combination of season averages, recent-form averages, consistency (pts/36, minutes), opponent defense factors, and matchup pace to compute expected model lines and an `ai_score` heuristic.
  - Tracking functions implement deduplication logic (collapse line moves by `player + date + bet_type` key) to avoid double-counting.

## Next Steps (I will continue unless you say otherwise)
- Verify a concrete sample pick in `nba_picks_tracking.json` and add an example JSON snippet here.
- Optionally run a dry-run of `nba/nba_model_IMPROVED.py` if you provide API keys or allow network runs.

If you want me to continue, say which next step to take: "verify sample pick" or "run dry-run".