
import os
import json
import sys

# Ensure we can import the model
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import nba_points_props_model

# Monkeypatch the tracking file path
TEST_TRACKING_FILE = "nba_points_props_tracking_test.json"
nba_points_props_model.TRACKING_FILE = TEST_TRACKING_FILE
nba_points_props_model.MIN_AI_SCORE = -100 # Ensure it tracks even low score for test

# Create dummy tracking data
test_data = {
    "picks": [
        {
            "pick_id": "Moe Wagner_7.5_over_2026-01-27T00:10:00Z",
            "player": "Moe Wagner",
            "prop_line": 7.5,
            "bet_type": "over",
            "team": "Orlando Magic",
            "opponent": "Cleveland Cavaliers",
            "game_time": "2026-01-27T00:10:00Z",
            "status": "pending",
            "ai_score": 10.0,
            "odds": -130,
            "opening_odds": -130,
            "latest_odds": -111
        }
    ]
}

with open(TEST_TRACKING_FILE, "w") as f:
    json.dump(test_data, f)

print(f"Created test tracking file: {TEST_TRACKING_FILE}")
print("Running grade_pending_picks...")

try:
    # Run grading
    graded = nba_points_props_model.grade_pending_picks()
    print(f"Graded count: {graded}")
    
    # Check result
    with open(TEST_TRACKING_FILE, "r") as f:
        data = json.load(f)
        pick = data['picks'][0]
        status = pick.get('status')
        score = pick.get('actual_pts')
        print(f"Pick Status: {status}")
        print(f"Actual Points: {score}")
        
        if score is not None:
             print("SUCCESS: Player stats found!")
        else:
             print("FAILURE: Stats still None.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    if os.path.exists(TEST_TRACKING_FILE):
        os.remove(TEST_TRACKING_FILE)
        print("Cleaned up test file.")
