
import json
from datetime import datetime
import pytz

with open('nba/nba_rebounds_props_tracking.json', 'r') as f:
    data = json.load(f)

wins = 0
losses = 0
voids = 0

print("Rebounds Record for 2026-01-26:")
for pick in data['picks']:
    gt_str = pick.get('game_time', '')
    if not gt_str: continue
    
    # Convert to ET
    dt_utc = datetime.fromisoformat(gt_str.replace('Z', '+00:00'))
    dt_et = dt_utc.astimezone(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d')
    
    if dt_et == '2026-01-26':
        status = pick.get('status')
        player = pick.get('player')
        result = pick.get('result')
        line = pick.get('prop_line')
        actual = pick.get('actual_reb')
        
        print(f"{player}: {status} ({actual} vs {line})")
        
        if status == 'win': wins += 1
        elif status == 'loss': losses += 1
        elif status == 'void': voids += 1

print(f"\nRecord: {wins}-{losses} ({voids} void)")
print(f"Total: {wins+losses}")
