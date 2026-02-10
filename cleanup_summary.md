# Cleanup Analysis Report

I have analyzed your codebase to identify unused files and potential areas to clear space.
Full analysis script: `tools/analyze_storage.py` (You can run `python3 tools/analyze_storage.py > report.md` for the raw list).

## 1. High Confidence Cleanup Candidates

### Backup Files
These files appear to be old backups and can likely be deleted:
- `generate_analytics_dashboard_backup.py` (38.6 KB)
- `best_plays_tracking.json.bak` (**10.1 MB**)
- `ncaab_picks_tracking.json.backup` (36.7 KB)
- `nba_picks_tracking.json.backup` (2.6 KB)
- `ncaa/ncaab_picks_tracking.json.backup` (2.6 MB)
- `nba/nba_rebounds_props_model.py.backup` (53.5 KB)
- `nba/nba_picks_tracking.json.backup` (341.7 KB)
- `soccer/soccer_model_IMPROVED.py.bak` (20.0 KB)
- `ufc/ufc_dashboard_template.html.backup` (20.8 KB)

### Log Files
There are **hundreds** of log files, mostly 0KB.
- `autograder.log` (**4.9 MB**)
- `American Betting League/monitor_stderr.log` (**6.7 MB**)
- `ncaab_model_*.log` (Hundreds of files)
- `nba_model_*.log` (Hundreds of files)

**Recommendation**: delete all `*.log` files in `nba/logs/`, `ncaa/logs/`, `nfl/logs/` and the large root logs.

### Cache
- `nfl/.cache/sleeper_players.json` (**14.2 MB**)

## 2. Potential Cleanup Candidates (Scripts)

The following scripts appear to be temporary or debug scripts. Please review if you still need them:
- `check_wagner_name.py`
- `debug_scraper_single.py`
- `check_rebounds_record.py`
- `test_oddspapi.py`
- `debug_scraper.py`
- `debug_grader.py`
- `debug_heat.py`
- `nba/test_*.py` (Various test scripts)

## Action Plan

Do you want me to proceed with:
1.  Deleting all `.log` files?
2.  Deleting the identified `.bak` and `.backup` files?
3.  Deleting the large `sleeper_players.json` cache?
