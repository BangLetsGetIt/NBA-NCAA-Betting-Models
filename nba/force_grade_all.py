
import sys
import os

# Add current dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("--- Grading Points Model ---")
    import nba_points_props_model
    nba_points_props_model.grade_pending_picks()
except Exception as e:
    print(f"Error grading points: {e}")

try:
    print("\n--- Grading 3PT Model ---")
    import nba_3pt_props_model
    nba_3pt_props_model.grade_pending_picks()
except Exception as e:
    print(f"Error grading 3pt: {e}")

try:
    print("\n--- Grading Assists Model ---")
    import nba_assists_props_model
    nba_assists_props_model.grade_pending_picks()
except Exception as e:
    print(f"Error grading assists: {e}")

try:
    print("\n--- Grading Rebounds Model ---")
    import nba_rebounds_props_model
    nba_rebounds_props_model.grade_pending_picks()
except Exception as e:
    print(f"Error grading rebounds: {e}")

print("\nDone grading all models.")
