#!/usr/bin/env python3
"""
RECOVERY SCRIPT - Manually Add Lost Picks from 10/31

Use this if your 10/31 picks with 9-4 record are missing from tracking.
This will add them back as completed picks.
"""

import json
import os
from datetime import datetime

TRACKING_FILE = "nba_picks_tracking.json"

# Load current tracking data
if os.path.exists(TRACKING_FILE):
    with open(TRACKING_FILE, 'r') as f:
        tracking_data = json.load(f)
    print(f"✓ Loaded tracking file: {len(tracking_data['picks'])} picks")
else:
    print("❌ Tracking file not found!")
    exit(1)

print("\n" + "="*80)
print("RECOVERY SCRIPT - Add Your Missing 10/31 Picks")
print("="*80)
print("\nYou said you had 13 picks on 10/31 that went 9-4.")
print("This script will help you add them back.\n")

print("Current tracking file has:")
print(f"  Total: {len(tracking_data['picks'])} picks")
print(f"  Completed: {sum(1 for p in tracking_data['picks'] if p['status'] == 'Completed')}")
print(f"  Pending: {sum(1 for p in tracking_data['picks'] if p['status'] == 'Pending')}")
print()

response = input("Do you want to manually add the missing 10/31 picks? (yes/no): ")

if response.lower() != 'yes':
    print("Exiting without changes.")
    exit(0)

print("\n" + "="*80)
print("MANUAL ENTRY MODE")
print("="*80)
print("\nFor each of your 13 picks from 10/31, enter the details:")
print("(Press Ctrl+C at any time to cancel)\n")

try:
    for i in range(13):
        print(f"\n--- Pick #{i+1}/13 ---")
        
        away_team = input("Away Team: ").strip()
        home_team = input("Home Team: ").strip()
        pick_type = input("Type (Spread/Total): ").strip().capitalize()
        
        pick_text = input("Pick (e.g., 'Team -7.5' or 'OVER 230'): ").strip()
        market_line = input("Market Line (e.g., -7.5 or 230.5): ").strip()
        
        result = input("Result (Win/Loss/Push): ").strip().capitalize()
        
        if result not in ['Win', 'Loss', 'Push']:
            print(f"Invalid result: {result}. Skipping this pick.")
            continue
        
        # Calculate profit/loss
        if result == 'Win':
            profit_loss = 100
        elif result == 'Loss':
            profit_loss = -110
        else:  # Push
            profit_loss = 0
        
        # Create pick entry
        pick_entry = {
            "pick_id": f"{home_team}_{away_team}_10-31-2025_{pick_type.lower()}_{i}",
            "date_logged": "2025-10-31T19:00:00",
            "game_date": "2025-10-31T19:00:00",
            "home_team": home_team,
            "away_team": away_team,
            "matchup": f"{away_team} @ {home_team}",
            "pick_type": pick_type,
            "model_line": 0,  # Unknown
            "market_line": market_line,
            "edge": 0,  # Unknown
            "pick": pick_text,
            "units": 1,
            "status": "Completed",
            "result": result,
            "profit_loss": profit_loss,
            "actual_home_score": None,
            "actual_away_score": None
        }
        
        tracking_data['picks'].append(pick_entry)
        print(f"✓ Added: {pick_text} - {result}")

except KeyboardInterrupt:
    print("\n\nCancelled by user.")
    response = input("Save the picks added so far? (yes/no): ")
    if response.lower() != 'yes':
        print("Exiting without saving.")
        exit(0)

# Recalculate summary
tracking_data['summary'] = {
    'total_picks': len(tracking_data['picks']),
    'wins': sum(1 for p in tracking_data['picks'] if p.get('result') == 'Win'),
    'losses': sum(1 for p in tracking_data['picks'] if p.get('result') == 'Loss'),
    'pushes': sum(1 for p in tracking_data['picks'] if p.get('result') == 'Push'),
    'pending': sum(1 for p in tracking_data['picks'] if p.get('status') == 'Pending')
}

# Create backup
backup_file = f"{TRACKING_FILE}.before_recovery"
with open(backup_file, 'w') as f:
    json.dump(tracking_data, f, indent=2)
print(f"\n✓ Backup created: {backup_file}")

# Save updated tracking data
with open(TRACKING_FILE, 'w') as f:
    json.dump(tracking_data, f, indent=2)

print("\n" + "="*80)
print("✅ RECOVERY COMPLETE!")
print("="*80)
print(f"Total picks now: {tracking_data['summary']['total_picks']}")
print(f"Record: {tracking_data['summary']['wins']}-{tracking_data['summary']['losses']}-{tracking_data['summary']['pushes']}")
total_profit = sum(p.get('profit_loss', 0) for p in tracking_data['picks']) / 100
print(f"Profit: {total_profit:+.2f} units")
print("\nRun the main script now to see your complete tracking history!")
