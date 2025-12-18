
import os
import sys
import traceback

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'nba'))

def verify_nba(mod_name, filename):
    print(f"Verifying {mod_name}...")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(mod_name, os.path.join("nba", filename))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        
        # Load data, calc stats, gen html
        if hasattr(mod, 'load_tracking_data') and hasattr(mod, 'calculate_tracking_stats') and hasattr(mod, 'generate_html_output'):
            t_data = mod.load_tracking_data()
            stats = mod.calculate_tracking_stats(t_data)
            # Pass empty lists for plays to avoid API calls or data logic needs
            # generate_html_output(over_plays, under_plays, stats=None, tracking_data=None, factors=None, player_stats=None)
            mod.generate_html_output([], [], stats, t_data, {}, {})
            print("  ✅ HTML Regenerated without error")
        else:
            print("  ❌ Missing functions")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    verify_nba('nba_points_props_model', 'nba_points_props_model.py')
    verify_nba('nba_assists_props_model', 'nba_assists_props_model.py')
    verify_nba('nba_rebounds_props_model', 'nba_rebounds_props_model.py')
    verify_nba('nba_3pt_props_model', 'nba_3pt_props_model.py')
