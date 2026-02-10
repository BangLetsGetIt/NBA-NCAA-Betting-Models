import json
from datetime import datetime

target_date = "2026-01-26"
file_path = "nba/nba_points_props_tracking.json"

print(f"Checking {file_path} for date {target_date}...")

with open(file_path, 'r') as f:
    data = json.load(f)
    picks = data['picks']

found_picks = []
seen_ids = set()
duplicates = []

for pick in picks:
    game_time = pick.get('game_time', '')
    if game_time.startswith(target_date):
        found_picks.append(pick)
        pid = pick.get('pick_id')
        if pid in seen_ids:
            duplicates.append(pick)
        seen_ids.add(pid)

print(f"Total Picks Found for {target_date}: {len(found_picks)}")
print(f"Unique IDs: {len(seen_ids)}")
print(f"Duplicates: {len(duplicates)}")

print("\n--- Picks List ---")
for p in found_picks:
    print(f"ID: {p.get('pick_id')} | Player: {p.get('player')} | Status: {p.get('status')} | Result: {p.get('result')}")

print("\n--- Duplicates ---")
for p in duplicates:
    print(f"ID: {p.get('pick_id')} | Player: {p.get('player')}")
