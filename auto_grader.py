#!/usr/bin/env python3
"""
CourtSide Analytics Auto-Grader
-------------------------------
Runs continuously (or via cron) to:
1. Grade pending picks for all models (NBA, NFL, etc.)
2. Regenerate HTML outputs with latest results
3. Push updates to GitHub (via auto_push.sh)

Usage:
    python3 auto_grader.py          # Run once
    python3 auto_grader.py --loop   # Run in continuous loop
"""

import os
import sys
import time
import json
import importlib
import importlib.util
import argparse
import subprocess
from datetime import datetime, timedelta
import pytz

# Add subdirectories to path to allow importing models
sys.path.append(os.path.join(os.path.dirname(__file__), 'nba'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'nfl'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'soccer'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'wnba'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'ncaa'))

# ANSI Colors
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(msg, type="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color = Colors.CYAN
    if type == "success": color = Colors.GREEN
    if type == "warning": color = Colors.YELLOW
    if type == "error": color = Colors.RED
    print(f"{Colors.BOLD}[{timestamp}]{Colors.END} {color}{msg}{Colors.END}")

def backup_file(filepath):
    """Create a simple .backup copy of a file"""
    import shutil
    if os.path.exists(filepath):
        try:
            shutil.copy2(filepath, f"{filepath}.backup_grader")
        except Exception:
            pass

def retrieve_active_plays(tracking_data, stat_type="PTS"):
    """
    Reconstruct 'plays' list from tracking data for today's/pending games.
    so the HTML dashboard doesn't go empty on regrade.
    """
    active_plays = []
    if not tracking_data or 'picks' not in tracking_data:
        return active_plays
        
    # Get today's date in ET
    et_tz = pytz.timezone('US/Eastern')
    now = datetime.now(et_tz)
    today_date = now.date()
    yesterday_date = today_date - timedelta(days=1)
    
    for p in tracking_data['picks']:
        try:
            g_time = p.get('game_time') or p.get('game_date')
            if not g_time: continue
            
            # parse
            if 'Z' in g_time:
                dt = datetime.fromisoformat(g_time.replace('Z', '+00:00'))
                dt_et = dt.astimezone(et_tz)
            else:
                dt_et = datetime.fromisoformat(g_time)
            
            p_date = dt_et.date()
            
            # CRITERIA TO DISPLAY:
            # 1. FUTURE games (p_dt > now) -> Show pending plays
            # 2. TODAY's games -> Show only *pending* plays that haven't started (grace period 15m)
            # 3. Old pending games -> HIDE
            
            p_dt_aware = dt_et.astimezone(pytz.utc)
            now_utc = datetime.now(pytz.utc)
            
            should_show = False
            status = (p.get('status') or 'pending').lower()

            if status == 'pending':
                # Show if game is in future OR started within last 15 minutes (grace period)
                if p_dt_aware > (now_utc - timedelta(minutes=15)):
                    should_show = True
            
            if should_show:
                # Reconstruct play object
                # Needed fields: prop, game_time, team, opponent, player, ai_score, odds
                
                # Construct prop string: e.g. "OVER 28.5 PTS"
                line = p.get('prop_line', 0)
                b_type = p.get('bet_type', 'OVER').upper()
                prop_str = f"{b_type} {line} {stat_type}"
                
                play = {
                    'player': p.get('player'),
                    'prop': prop_str,
                    'game_time': p.get('game_time') or p.get('game_date'),
                    'team': p.get('team'),
                    'opponent': p.get('opponent'),
                    'ai_score': p.get('ai_score', 9.5), 
                    'odds': p.get('odds'),
                    'home_team': p.get('team') 
                }
                active_plays.append(play)
        except Exception:
            continue
            
    return active_plays

def retrieve_active_plays_nfl(tracking_data, stats_cache=None):
    """
    Reconstruct active NFL plays for HTML display from tracking data.
    Populates missing fields like projection using edge logic.
    """
    active_picks = []
    
    # 1. Get Pending Picks
    current_time = datetime.now(pytz.UTC)
    us_et = pytz.timezone('US/Eastern')
    today = datetime.now(us_et).date()
    yesterday = today - timedelta(days=1)
    
    picks = tracking_data.get('picks', [])
    
    for p in picks:
        # Check if pending or recent
        status = p.get('status', 'pending').lower()
        game_time_str = p.get('game_time')
        is_relevant = False
        
        if game_time_str:
            try:
                # Parse date
                g_dt_utc = datetime.fromisoformat(game_time_str.replace('Z', '+00:00'))
                now_utc = datetime.now(pytz.UTC)
                
                # Show only if pending AND (future OR started in last 15 mins)
                if status == 'pending':
                    if g_dt_utc > (now_utc - timedelta(minutes=15)):
                        is_relevant = True
            except:
                pass
                
        if is_relevant:
            # Reconstruct Object
            b_type = p.get('bet_type', 'UNK').upper()
            line = p.get('prop_line', 0)
            edge = p.get('edge', 0.0)
            
            # Recalculate Projection
            proj = 'N/A'
            if edge != 0:
                if b_type == 'OVER':
                    proj = round(line + edge, 1)
                elif b_type == 'UNDER':
                    proj = round(line - edge, 1)
            
            # Try to lookup stats if missing
            season_avg = p.get('season_avg', 'N/A')
            recent_avg = p.get('recent_avg', 'N/A')
            
            if stats_cache and (season_avg == 'N/A' or recent_avg == 'N/A'):
                try:
                    p_name = p.get('player')
                    if p_name and p_name in stats_cache:
                        p_stats = stats_cache[p_name]
                        # Handling various key names (season_avg, avg_yards, etc)
                        if season_avg == 'N/A':
                             season_avg = p_stats.get('season_avg', p_stats.get('avg_yards', 'N/A'))
                        if recent_avg == 'N/A':
                             recent_avg = p_stats.get('recent_avg', p_stats.get('last5_avg', 'N/A'))
                except:
                    pass

            play = {
                'player': p.get('player'),
                'team': p.get('team'),
                'matchup': p.get('matchup', 'UNK'),
                'commence_time': p.get('game_time'),
                'game_time': p.get('game_time'),
                'type': b_type,
                'line': line,
                'odds': p.get('odds', -110),
                'model_proj': proj,
                'edge': edge,
                'ai_score': p.get('ai_score', 0),
                'season_avg': season_avg, 
                'recent_avg': recent_avg
            }
            active_picks.append(play)
            
    return active_picks

def run_nba_grading(force=False):
    """
    Grades NBA props by importing model modules dynamically.
    """
    log("Starting NBA Grading...", "info")
    
    # List of NBA prop models to grade
    # (Module Name, Script Filename)
    nba_models = [
        ('nba_points_props_model', 'nba_points_props_model.py'),
        ('nba_assists_props_model', 'nba_assists_props_model.py'),
        ('nba_rebounds_props_model', 'nba_rebounds_props_model.py'),
        ('nba_3pt_props_model', 'nba_3pt_props_model.py'),
        ('nba_model_IMPROVED', 'nba_model_IMPROVED.py'), # Main Model
    ]
    
    any_updates = False
    
    for mod_name, filename in nba_models:
        try:
            log(f"Checking {mod_name}...", "info")
            
            # Dynamic import
            try:
                mod = __import__(mod_name)
            except ImportError:
                spec = importlib.util.spec_from_file_location(mod_name, os.path.join("nba", filename))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
            
            # FORCE RELOAD to ensure fresh code/logic (crucial for long-running process)
            importlib.reload(mod)

            # 1. Run Grading
            updated = False
            if hasattr(mod, 'grade_pending_picks'):
                if hasattr(mod, 'TRACKING_FILE'):
                    backup_file(mod.TRACKING_FILE)
                
                # We can capture if it actually updated anything if grade_pending_picks returned a count,
                # but currently it might just print. 
                # Let's assume we want to rebuild if forced OR if we suspect changes.
                try:
                    # Some models return count, some don't.
                    # We'll just run it.
                    res = mod.grade_pending_picks()
                    if isinstance(res, int) and res > 0: updated = True
                except:
                    pass
            
            # 2. Regenerate HTML ALWAYS to refresh date-dependent stats (TODAY/YESTERDAY)
            if True:  # Always regenerate to ensure TODAY stats are fresh
                if mod_name == 'nba_model_IMPROVED':
                     # Main Model use update_pick_results()
                     if hasattr(mod, 'update_pick_results'):
                         try:
                             # It returns count of updated picks
                             res = mod.update_pick_results()
                             if isinstance(res, int) and res > 0:
                                 log(f"Updated {res} picks for {mod_name}", "success")
                                 any_updates = True
                             
                             # ALWAYS regenerate tracking HTML if available
                             if hasattr(mod, 'generate_tracking_html'):
                                 mod.generate_tracking_html()
                                 log(f"Regenerated tracking HTML for {mod_name}", "success")
                                 any_updates = True
                         except Exception as e:
                             log(f"Error updating main NBA model: {e}", "error")
                elif hasattr(mod, 'generate_html_output') and hasattr(mod, 'load_tracking_data') and hasattr(mod, 'calculate_tracking_stats'):
                    # Load fresh data
                    t_data = mod.load_tracking_data()
                    stats = mod.calculate_tracking_stats(t_data)
                    
                    # Generate HTML with EMPTY plays
                    try:
                        # Determine stat type for display reconstruction
                        stat_label = "PTS"
                        if 'assists' in mod_name: stat_label = "AST"
                        elif 'rebounds' in mod_name: stat_label = "REB"
                        elif '3pt' in mod_name: stat_label = "3PM"
                        
                        # Reconstruct active plays
                        active_plays = retrieve_active_plays(t_data, stat_label)
                        
                        # Prop models usually generate_html_output(over_plays, under_plays, ...)
                        # We will assume all are OVER plays for now if bet_type isn't checked strictly, 
                        # but retrieve_active_plays handles prop string.
                        # We need to split into over/under lists?
                        # auto_grader usually just passes them.
                        # user's models usually put everything in over_plays list for display if they are "top plays".
                        # But wait, generate_html_output takes (over_plays, under_plays, ...)
                        
                        over_plays = [p for p in active_plays if 'OVER' in p['prop']]
                        under_plays = [p for p in active_plays if 'UNDER' in p['prop']]
                        
                        html = mod.generate_html_output(over_plays, under_plays, stats, t_data, {}, {})
                        mod.save_html(html)
                        log(f"Regenerated HTML for {mod_name} with {len(active_plays)} active plays", "success")
                        any_updates = True
                    except Exception as e:
                        # Some might have diff signature
                        try:
                             # Some models might not take defense/player stats args
                             html = mod.generate_html_output([], [], stats, t_data) 
                             mod.save_html(html)
                             any_updates = True
                        except:
                            log(f"HTML generation failed for {mod_name}: {e}", "warning")
            
        except Exception as e:
            log(f"Error processing {mod_name}: {e}", "error")

    return any_updates

def run_nfl_grading(force=False):
    """
    Grades NFL props.
    """
    log("Starting NFL Grading...", "info")
    
    nfl_models = [
        ('nfl_passing_yards_props_model', 'nfl_passing_yards_props_model.py'),
        ('nfl_rushing_yards_props_model', 'nfl_rushing_yards_props_model.py'),
        ('nfl_receiving_yards_props_model', 'nfl_receiving_yards_props_model.py'),
        ('nfl_receptions_props_model', 'nfl_receptions_props_model.py'),
        ('atd_model', 'atd_model.py'),
        ('nfl_model_IMPROVED', 'nfl_model_IMPROVED.py'),
    ]
    
    any_updates = False
    
    for mod_name, filename in nfl_models:
        try:
            log(f"Checking {mod_name}...", "info")
            
            try:
                mod = __import__(mod_name)
            except ImportError:
                spec = importlib.util.spec_from_file_location(mod_name, os.path.join("nfl", filename))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
            
            # FORCE RELOAD
            importlib.reload(mod)
            
            updated = False
            # 1. Grading
            if mod_name == 'nfl_model_IMPROVED':
                if hasattr(mod, 'grade_pending_picks'):
                    try:
                        res = mod.grade_pending_picks()
                        if isinstance(res, int) and res > 0:
                            log(f"Graded {res} picks for {mod_name}", "success")
                            updated = True
                        elif force:
                            updated = True # Force HTML regen
                    except Exception as e:
                        log(f"Error grading NFL main model: {e}", "error")
            elif hasattr(mod, 'grade_props_tracking_file') and hasattr(mod, 'TRACKING_FILE'):
                stat_kind = None
                if 'passing' in filename: stat_kind = 'passing_yards'
                elif 'rushing' in filename: stat_kind = 'rushing_yards'
                elif 'receiving' in filename: stat_kind = 'receiving_yards'
                elif 'receptions' in filename: stat_kind = 'receptions'
                elif 'atd' in filename: stat_kind = 'anytime_td'
                
                if stat_kind:
                    backup_file(mod.TRACKING_FILE)
                    from nfl.props_grader import grade_props_tracking_file
                    updated_count = grade_props_tracking_file(mod.TRACKING_FILE, stat_kind=stat_kind)
                    if updated_count > 0:
                        log(f"Graded {updated_count} picks for {mod_name}", "success")
                        updated = True
            
            # 2. Regenerate HTML
            if True: # Always regen to restore pending plays
                 if mod_name == 'nfl_model_IMPROVED':
                     try:
                         # For NFL main model, we just run main() to refresh odds and HTML
                         # but we might want to avoid re-analysis if just grading.
                         # However, nfl_model_IMPROVED analysis is fast.
                         if hasattr(mod, 'main'):
                             mod.main()
                             log(f"Regenerated HTML for {mod_name}", "success")
                             any_updates = True
                     except Exception as e:
                         log(f"HTML gen failed for {mod_name}: {e}", "warning")
                 elif hasattr(mod, 'generate_html_output') and hasattr(mod, 'load_tracking_data') and hasattr(mod, 'calculate_tracking_stats'):
                    try:
                        t_data = mod.load_tracking_data()
                        # Load Stats Cache if available
                        stats_cache = {}
                        if hasattr(mod, 'PLAYER_STATS_CACHE') and os.path.exists(mod.PLAYER_STATS_CACHE):
                            try:
                                with open(mod.PLAYER_STATS_CACHE, 'r') as f:
                                    stats_cache = json.load(f)
                            except:
                                pass
                        
                        # Restore Active Plays from tracking
                        active_plays = retrieve_active_plays_nfl(t_data, stats_cache)
                        
                        ts = mod.calculate_tracking_stats(t_data)
                        mod.generate_html_output(active_plays, ts, t_data)
                        log(f"Regenerated HTML for {mod_name}", "success")
                        any_updates = True
                    except Exception as e:
                        log(f"HTML gen failed for {mod_name}: {e}", "warning")

        except Exception as e:
            log(f"Error processing {mod_name}: {e}", "error")

    return any_updates

def trigger_git_push():
    """
    Runs auto_push.sh if available
    """
    log("Triggering git push...", "info")
    if os.path.exists("auto_push.sh"):
        try:
            subprocess.run(["bash", "auto_push.sh"], check=False)
        except Exception as e:
            log(f"Git push failed: {e}", "error")
    else:
        log("auto_push.sh not found", "warning")

def run_wnba_grading(force=False):
    """
    Grades WNBA models (Main + Props).
    """
    log("Starting WNBA Grading...", "info")
    
    # WNBA Models
    # 1. Main Model (wnba_model.py)
    # 2. Props Model (wnba_props_model.py)
    
    any_updates = False
    
    # --- 1. Main Model ---
    try:
        mod_name = 'wnba_model'
        filename = 'wnba_model.py'
        log(f"Checking {mod_name}...", "info")
        
        try:
            mod = __import__(mod_name)
        except ImportError:
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join("wnba", filename))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            
        # FORCE RELOAD
        importlib.reload(mod)
            
        # Verify functions exist
        if hasattr(mod, 'generate_html') and hasattr(mod, 'get_stats'):
            # WNBA model has hardcoded games in main(). 
            # Ideally we'd separate prediction logic, but for now let's just re-run main() logic partially?
            # Or just call the functions if we can replicate data.
            # actually wnba_model.py main() does: predict -> track -> get_stats -> generate_html
            # Let's just run the module's main() if we want to regenerate everything?
            # Or better, let's just re-generate HTML with existing tracking data and empty results if strictly grading.
            # But the HTML requires 'results' (predictions). 
            # For simplicity, if force=True, we might just have to run the script or mock the results.
            
            # Since WNBA is offline/mock data mostly in this codebase (based on file content),
            # let's just trigger its main execution method if accessible, or manually replicate:
            
            if force:
                # We can't easy invoke main() without running the whole script which tracks mock picks.
                # Let's just generate HTML with *empty* results list but valid stats, to check headers/tracking.
                stats = mod.get_stats()
                # generate_html(results, stats_tuple)
                mod.generate_html([], stats)
                log(f"Regenerated HTML for {mod_name}", "success")
                any_updates = True
                
    except Exception as e:
        log(f"Error processing WNBA Main: {e}", "error")

    # --- 2. Props Model ---
    try:
        mod_name = 'wnba_props_model'
        filename = 'wnba_props_model.py'
        log(f"Checking {mod_name}...", "info")
        
        try:
            mod = __import__(mod_name)
        except ImportError:
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join("wnba", filename))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            
        # FORCE RELOAD
        importlib.reload(mod)
            
        if hasattr(mod, 'generate_html') and hasattr(mod, 'get_stats'):
            if force:
                 # get_stats returns 5 values now
                 s1, s10, s20, today, yesterday = mod.get_stats()
                 mod.generate_html([], s1, s10, today, yesterday)
                 log(f"Regenerated HTML for {mod_name}", "success")
                 any_updates = True

    except Exception as e:
        log(f"Error processing WNBA Props: {e}", "error")
        
    return any_updates

def run_ncaab_grading(force=False):
    """
    Grades NCAAB pending picks.
    """
    log("Starting NCAAB Grading...", "info")
    
    mod_name = 'ncaab_model_2ndFINAL'
    filename = 'ncaab_model_2ndFINAL.py'
    
    any_updates = False
    
    try:
        log(f"Checking {mod_name}...", "info")
        
        try:
            mod = __import__(mod_name)
        except ImportError:
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join("ncaa", filename))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            
        # FORCE RELOAD
        importlib.reload(mod)
            
        # Run grading
        if hasattr(mod, 'update_pick_results'):
            try:
                res = mod.update_pick_results()
                if isinstance(res, int) and res > 0:
                    log(f"Updated {res} picks for {mod_name}", "success")
                    any_updates = True
            except Exception as e:
                log(f"Error updating NCAAB model: {e}", "error")
        
        # ALWAYS regenerate HTML to refresh date-dependent stats
        if hasattr(mod, 'generate_tracking_html'):
            try:
                mod.generate_tracking_html()
                log(f"Regenerated HTML for {mod_name}", "success")
                any_updates = True
            except Exception as e:
                log(f"HTML generation failed for {mod_name}: {e}", "warning")
                
    except Exception as e:
        log(f"Error processing {mod_name}: {e}", "error")
        
    return any_updates

def run_soccer_grading(force=False):
    """
    Grades Soccer pending picks and regenerates HTML with fresh data.
    """
    log("Starting Soccer Grading...", "info")
    
    mod_name = 'soccer_model_IMPROVED'
    filename = 'soccer_model_IMPROVED.py'
    
    any_updates = False
    
    try:
        log(f"Checking {mod_name}...", "info")
        
        try:
            mod = __import__(mod_name)
        except ImportError:
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join("soccer", filename))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)

        # FORCE RELOAD
        importlib.reload(mod)
        
        # Call update_pick_results (Soccer's grading function)
        if hasattr(mod, 'update_pick_results'):
            graded = mod.update_pick_results()
            if graded and graded > 0:
                log(f"Graded {graded} soccer picks", "success")
                any_updates = True
        else:
            log(f"{mod_name} has no update_pick_results function", "warning")
        
        # Always run full model to get fresh games (Dec 20, 2024 fix)
        if hasattr(mod, 'main'):
            log("Running full soccer model for fresh games...", "info")
            mod.main()
            any_updates = True
    
    except Exception as e:
        log(f"Error processing Soccer: {e}", "error")
        import traceback
        traceback.print_exc()
    
    return any_updates

def main():
    parser = argparse.ArgumentParser(description='Auto-Grader for Sports Models')
    parser.add_argument('--loop', action='store_true', help='Run in a loop every 15 minutes')
    parser.add_argument('--interval', type=int, default=900, help='Interval in seconds (default: 900s = 15m)')
    parser.add_argument('--force', action='store_true', help='Force regeneration of all HTML files')
    args = parser.parse_args()
    
    log("Auto-Grader initialized", "info")
    
    if args.loop:
        while True:
            updates_nba = run_nba_grading(force=args.force)
            updates_nfl = run_nfl_grading(force=args.force)
            updates_wnba = run_wnba_grading(force=args.force)
            updates_ncaab = run_ncaab_grading(force=args.force)
            updates_soccer = run_soccer_grading(force=args.force)
            
            if updates_nba or updates_nfl or updates_wnba or updates_ncaab or updates_soccer:
                # Regenerate Best Plays aggregator
                try:
                    import best_plays_bot
                    import importlib
                    importlib.reload(best_plays_bot)
                    best_plays_bot.main()
                    log("Regenerated best_plays.html", "success")
                except Exception as e:
                    log(f"Best plays generation failed: {e}", "warning")
                
                trigger_git_push()
            else:
                log("No updates found.", "info")
                
            log(f"Sleeping for {args.interval} seconds...", "info")
            time.sleep(args.interval)
            # Reset force after first loop if intended? usually yes.
            args.force = False 
    else:
        # Run once
        updates_nba = run_nba_grading(force=args.force)
        updates_nfl = run_nfl_grading(force=args.force)
        updates_wnba = run_wnba_grading(force=args.force)
        updates_ncaab = run_ncaab_grading(force=args.force)
        updates_soccer = run_soccer_grading(force=args.force)
        
        if updates_nba or updates_nfl or updates_wnba or updates_ncaab or updates_soccer:
            # Regenerate Best Plays aggregator
            try:
                import best_plays_bot
                import importlib
                importlib.reload(best_plays_bot)
                best_plays_bot.main()
                log("Regenerated best_plays.html", "success")
            except Exception as e:
                log(f"Best plays generation failed: {e}", "warning")
            
            trigger_git_push()
        else:
            log("No updates found.", "info")

if __name__ == "__main__":
    main()
