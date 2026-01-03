
import sys
import os

# Add local directory to path to find modules
sys.path.append(os.getcwd())

from nfl.props_grader import grade_props_tracking_file

print("Running debug grader...")
print("CWD:", os.getcwd())
tracking_file = "nfl/nfl_receiving_yards_props_tracking.json"

if os.path.exists(tracking_file):
    print(f"Found {tracking_file}")
    updated = grade_props_tracking_file(tracking_file, stat_kind="receiving_yards", verbose=True)
    print(f"Updated: {updated}")
else:
    print(f"File not found: {tracking_file}")
