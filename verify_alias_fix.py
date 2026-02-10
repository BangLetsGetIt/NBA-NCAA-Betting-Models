
from nba_points_props_model import grade_pending_picks
import json

# Create a dummy tracking file with Moe Wagner
with open("nba_points_props_tracking.json", "w") as f:
    json.dump({
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
                "latest_odds": -111,
                "opening_odds": -130
            }
        ]
    }, f)

print("Created dummy tracking file with Moe Wagner (pending).")
print("Running grade_pending_picks...")

# We need to mock fetch_player_assists_from_nba_api or just let it run if it hits real API
# The real API should return stats for Moritz Wagner
# The fix in grade_pending_picks should normalize "Moe Wagner" -> "Moritz Wagner" and find the stats

try:
    graded_count = grade_pending_picks()
    print(f"Graded count: {graded_count}")
    
    with open("nba_points_props_tracking.json", "r") as f:
        data = json.load(f)
        pick = data['picks'][0]
        print(f"Result for {pick['player']}: {pick['status']} (Actual: {pick.get('actual_pts')})")
        if pick['status'] == 'win' or pick['status'] == 'loss':
             print("SUCCESS: Pick was graded!")
        else:
             print("FAILURE: Pick remains pending or void.")
except Exception as e:
    print(f"Error: {e}")
