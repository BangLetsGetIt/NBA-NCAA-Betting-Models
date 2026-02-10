
import json
import os
from datetime import datetime

picks_file = "ufc/data/ufc_picks.json"

with open(picks_file, 'r') as f:
    picks = json.load(f)

updated = False
for p in picks:
    if p['fighter'] == "Ricky Turcios" and p['status'] == 'pending':
        print("Marking Ricky Turcios as void (not found in results).")
        p['status'] = 'void'
        p['result_timestamp'] = datetime.now().isoformat()
        updated = True

if updated:
    with open(picks_file, 'w') as f:
        json.dump(picks, f, indent=4)
    print("Updated picks file.")
else:
    print("No Ricky Turcios pending pick found.")
