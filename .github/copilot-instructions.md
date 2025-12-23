<!-- Copilot / AI agent instructions for the CourtSide Analytics repo -->
# Copilot Instructions — CourtSide Analytics

Purpose: give an AI coding agent the minimum focused guidance to be productive in this repo.

1. Big picture
- This repo runs sport-specific models that fetch odds, compute edges, track picks in JSON, and render HTML outputs (served via GitHub Pages). See the architecture summary in [CODEBASE_OVERVIEW.md](CODEBASE_OVERVIEW.md).
- Data flow: Odds & stats → model analysis (analyze_props/process_games) → tracking JSON (root or sport folders) → HTML generation → unified dashboard (`unified_dashboard_interactive.html`).

2. Where to run things (common commands)
- Run the NBA suite: `./run_nba_models.sh` or alias `nbamodels` (see [QUICK_START.md](QUICK_START.md)).
- Other runners: `./run_nfl_models.sh`, `./run_cbb_models.sh`, `./run_wnba_models.sh`.
- Manually refresh dashboard: `python3 unified_dashboard_interactive.py` and open [unified_dashboard_interactive.html](unified_dashboard_interactive.html).

3. Key files to inspect when editing behavior
- Model orchestration and auto-grading: [auto_grader.py](auto_grader.py)
- Unified dashboard generator: [unified_dashboard_interactive.py](unified_dashboard_interactive.py)
- Primary NBA model (tunable thresholds): [nba/nba_model_IMPROVED.py](nba/nba_model_IMPROVED.py)
- Props pattern example: `analyze_props()` + `generate_html_output()` in most `*_props_model.py` files under each sport folder (see [CODEBASE_OVERVIEW.md](CODEBASE_OVERVIEW.md) for conventions).
- Tracking verification: [verify_tracking.py](verify_tracking.py) and sport-specific verifiers like [verify_nba_status.py](verify_nba_status.py).

4. Project-specific conventions to follow
- Tracking JSON schema: every tracking file contains a `picks` array with fields like `pick_id`, `player`, `pick_type`, `bet_type`, `line`, `odds`, `edge`, `ai_score`, `status`, `profit_loss`. Treat `pick_id` as the canonical dedup key (format: PlayerName_Line_Type_Date). See [CODEBASE_OVERVIEW.md](CODEBASE_OVERVIEW.md).
- Thresholds are defined as module-level constants in each model (e.g., `SPREAD_THRESHOLD`, `CONFIDENT_TOTAL_EDGE`, `MIN_AI_SCORE`). Change parameters in the model file, not in multiple helpers.
- HTML generation uses Jinja2 templates and local CSS guidelines (see [PROPS_HTML_STYLING_GUIDE.md](PROPS_HTML_STYLING_GUIDE.md)); prefer small, localized changes to templates.
- Time handling uses `pytz` and strict UTC-aware datetimes; do not remove timezone logic when grading picks.

5. Integrations & external dependencies
- Odds provider: environment variable `ODDS_API_KEY` (used across models). Ensure tests and dev runs set this or mock `get_props_odds()`/HTTP calls.
- Typical Python deps: `requests`, `python-dotenv`, `pytz`, `jinja2`, `pandas`, `numpy` — install with `pip install -r requirements.txt` (or the ad-hoc list in [CODEBASE_OVERVIEW.md](CODEBASE_OVERVIEW.md)).

6. Safe change checklist for model changes
- Run `./run_nba_models.sh` (or the corresponding runner) locally and confirm HTML output updates.
- Run `python3 unified_dashboard_interactive.py` to regenerate dashboard data and confirm picks appear.
- Run `python3 verify_tracking.py` after changes that affect grading/tracking to ensure no duplicate or null `profit_loss` values.
- When changing threshold constants, run one model in dry/run mode (add a guard or small data slice) and check historical performance metrics in the tracking JSONs.

7. Small examples to copy/paste
- Regenerate NBA models and dashboard:

```
./run_nba_models.sh
python3 unified_dashboard_interactive.py
open unified_dashboard_interactive.html
```

- Check tracking health:

```
python3 verify_tracking.py
python3 verify_nba_status.py
```

8. What agents should NOT change automatically
- Do not change tracking JSON schema fields or `pick_id` format without coordinated migration (these are used by `auto_grader.py`).
- Avoid bulk formatting-only edits across many model files — keep diffs focused to behavior changes.

9. Where to look for examples of fixes
- Recent, applied fixes and rationale are documented in [CODEBASE_OVERVIEW.md](CODEBASE_OVERVIEW.md) (Dec 2024–2025). Use that file to match past change patterns (threshold tuning, Jinja scoping, time filters).

10. If you need tests or mocks
- There are no formal unit tests; for HTTP interactions, mock `get_props_odds()` and `requests` calls. For grading logic, use small slices of tracking JSON files in `history/` or create a small sample tracking JSON.

— End —

If anything in this guidance is unclear or you want more examples (e.g., a failing-run reproduction, specific model walkthrough), tell me which area to expand.

11. Code-level guidance (for agents who must modify logic)
- Start by reading `auto_grader.py` to understand grading lifecycle: it first calls `grade_pending_picks()` (resolves pending picks), then regenerates dashboard HTML. Any change that affects `status`, `profit_loss`, or `actual_val` must keep this flow intact.
- Search patterns to find model entrypoints quickly:
	- `def main():` in sport model files (grep for `def main()`)
	- `analyze_props(` and `process_games(` for the core analysis logic
	- `track_new_picks(` or `save_tracking_data(` for persistence hooks
- Typical small edit workflow:
	1. Add a feature flag or module-level constant at top of the model (e.g., `DRY_RUN = True`) so you can test without writing tracking changes.
	2. Run a single model file to verify behavior, for example (NBA dry run):

```bash
python3 -c "from nba.nba_model_IMPROVED import main; main(dry_run=True)"
```

	3. Inspect the tracking JSON (e.g., `nba_picks_tracking.json`) and `unified_dashboard_data.json` to confirm expected output.
- Debugging tips:
	- Use `print()` or `logging` at function boundaries: after `get_props_odds()`, after `analyze_props()`, and before `track_new_picks()` so you can trace values (odds, edge, ai_score, pick_id).
	- To find where a `pick_id` is generated, search for `pick_id =` or `format(` within `*_props_model.py` files.
	- If HTML output is empty, check for Jinja scoping issues; many templates rely on `selectattr|first` patterns—see recent fixes in [CODEBASE_OVERVIEW.md](CODEBASE_OVERVIEW.md).
- Mocking external APIs for local tests:
	- Replace `get_props_odds()` with a small fixture that returns a single game/player dict matching the odds API schema.
	- For network isolation, set `ODDS_API_KEY=mock` and patch `requests.get` using `unittest.mock`.
- Quick grep queries useful for agents:
	- Find threshold constants: `grep -R "SPREAD_THRESHOLD\|TOTAL_THRESHOLD\|MIN_AI_SCORE" -n .`
	- Find tracking file names: `grep -R "_tracking.json" -n .`
	- Find HTML generators: `grep -R "generate_html_output" -n .`

12. Recommended developer environment
- Python 3.11+ virtualenv with `pip install -r requirements.txt` (or the ad-hoc list in `CODEBASE_OVERVIEW.md`).
- Use the shell aliases in `QUICK_START.md` for fast runs (or add them to `~/.zshrc`).
- When editing multiple models, run `python3 verify_tracking.py` to catch schema/NULL issues before committing.
