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
import argparse
import subprocess
from datetime import datetime
import pytz

# Add subdirectories to path to allow importing models
sys.path.append(os.path.join(os.path.dirname(__file__), 'nba'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'nfl'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'wnba'))

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
                # If direct import fails, try importlib with path
                import importlib.util
                spec = importlib.util.spec_from_file_location(mod_name, os.path.join("nba", filename))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)

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
            
            # 2. Regenerate HTML
            if updated or force:
                if mod_name == 'nba_model_IMPROVED':
                     # Special case for main model
                     if hasattr(mod, 'save_html') and hasattr(mod, 'calculate_stats'):
                         # Main model usually runs entire main() flow.
                         # We can try to invoke save_html if we can construct args.
                         # actually nba_model_IMPROVED has a very complex save_html signature.
                         # It might be easier to running the main logic if force is True?
                         # For now, let's skip force-gen for main model unless we are sure.
                         # Or just call mod.main() if force?
                         pass
                elif hasattr(mod, 'generate_html_output') and hasattr(mod, 'load_tracking_data') and hasattr(mod, 'calculate_tracking_stats'):
                    # Load fresh data
                    t_data = mod.load_tracking_data()
                    stats = mod.calculate_tracking_stats(t_data)
                    
                    # Generate HTML with EMPTY plays
                    try:
                        # Prop models
                        html = mod.generate_html_output([], [], stats, t_data, {}, {})
                        mod.save_html(html)
                        log(f"Regenerated HTML for {mod_name}", "success")
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
    ]
    
    any_updates = False
    
    for mod_name, filename in nfl_models:
        try:
            log(f"Checking {mod_name}...", "info")
            
            try:
                mod = __import__(mod_name)
            except ImportError:
                import importlib.util
                spec = importlib.util.spec_from_file_location(mod_name, os.path.join("nfl", filename))
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
            
            updated = False
            # 1. Grading
            if hasattr(mod, 'grade_props_tracking_file') and hasattr(mod, 'TRACKING_FILE'):
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
            if updated or force:
                 if hasattr(mod, 'generate_html_output') and hasattr(mod, 'load_tracking_data') and hasattr(mod, 'calculate_tracking_stats'):
                    try:
                        t_data = mod.load_tracking_data()
                        ts = mod.calculate_tracking_stats(t_data)
                        mod.generate_html_output([], ts, t_data)
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
            import importlib.util
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join("wnba", filename))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            
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
            import importlib.util
            spec = importlib.util.spec_from_file_location(mod_name, os.path.join("wnba", filename))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            
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
            
            if updates_nba or updates_nfl or updates_wnba:
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
        
        if updates_nba or updates_nfl or updates_wnba:
            trigger_git_push()
        else:
            log("No updates found.", "info")

if __name__ == "__main__":
    main()
