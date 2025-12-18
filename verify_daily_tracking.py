
import os
import sys

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'nfl'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'wnba'))

def verify_nfl(mod_name, filename):
    print(f"Verifying {mod_name}...")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(mod_name, os.path.join("nfl", filename))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        
        # Load data, calc stats, gen html
        if hasattr(mod, 'load_tracking_data') and hasattr(mod, 'calculate_tracking_stats'):
            t_data = mod.load_tracking_data()
            stats = mod.calculate_tracking_stats(t_data)
            mod.generate_html_output([], stats, t_data)
            print("  ✅ HTML Regenerated")
        else:
            print("  ❌ Missing functions")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def verify_wnba_main():
    print("Verifying WNBA Main...")
    try:
        import wnba.wnba_model as mod
        stats = mod.get_stats()
        mod.generate_html([], stats) # Empty results
        print("  ✅ HTML Regenerated")
    except Exception as e:
        print(f"  ❌ Error: {e}")

def verify_wnba_props():
    print("Verifying WNBA Props...")
    try:
        import wnba.wnba_props_model as mod
        s1, s10, s20, today, yesterday = mod.get_stats()
        mod.generate_html([], s1, s10, today, yesterday) # Empty picks
        print("  ✅ HTML Regenerated")
    except Exception as e:
        print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    verify_nfl('nfl_passing_yards_props_model', 'nfl_passing_yards_props_model.py')
    verify_nfl('nfl_rushing_yards_props_model', 'nfl_rushing_yards_props_model.py')
    verify_nfl('nfl_receiving_yards_props_model', 'nfl_receiving_yards_props_model.py')
    verify_nfl('nfl_receptions_props_model', 'nfl_receptions_props_model.py')
    verify_nfl('atd_model', 'atd_model.py')
    
    verify_wnba_main()
    verify_wnba_props()
