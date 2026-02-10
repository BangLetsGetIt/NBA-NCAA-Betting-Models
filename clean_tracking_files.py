
import json
import glob
import os

files = glob.glob('nba/*tracking.json')

for file in files:
    print(f"Cleaning {file}...")
    with open(file, 'r') as f:
        data = json.load(f)
    
    unique_picks = {}
    original_count = len(data['picks'])
    
    # Sort by updated_at desc to keep latest
    data['picks'].sort(key=lambda x: x.get('last_updated') or x.get('updated_at') or "0", reverse=False)
    
    for pick in data['picks']:
        # Use player + date + bet_type for deduplication (Stronger than pick_id)
        player = pick.get('player')
        bet_type = pick.get('bet_type')
        gt_str = pick.get('game_time', '')
        if not gt_str: continue
        date_str = gt_str.split('T')[0]
        
        # Key
        key = f"{player}_{date_str}_{bet_type}"
        
        # Keep latest
        unique_picks[key] = pick
        
    cleaned_picks = list(unique_picks.values())
    
    # Preserve date sorting?
    cleaned_picks.sort(key=lambda x: x.get('game_time', ''))
    
    data['picks'] = cleaned_picks
    new_count = len(cleaned_picks)
    print(f"  Reduced from {original_count} to {new_count} picks (-{original_count - new_count})")
    
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

print("Done.")
