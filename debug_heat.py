
import json
import os
from collections import defaultdict

files = ['nba/nba_picks_tracking.json', 'ncaa/ncaab_picks_tracking.json']
team_counts = defaultdict(lambda: {'spread': 0, 'total': 0, 'other': 0})

for f in files:
    try:
        data = json.load(open(f))
        picks = data.get('picks', [])
        for p in picks:
            if p.get('status') not in ['win', 'loss', 'push']:
                continue
            
            # Exclude players
            if p.get('player'):
                continue
                
            team = p.get('home_team') or p.get('team') or p.get('away_team')
            if team == 'Miami Heat':
                pt = str(p.get('pick_type', '')).lower()
                if 'spread' in pt:
                    team_counts['Miami Heat']['spread'] += 1
                elif 'total' in pt or 'over' in pt or 'under' in pt:
                    team_counts['Miami Heat']['total'] += 1
                else:
                    team_counts['Miami Heat']['other'] += 1
                    print(f"Other type: {pt}")
    except Exception as e:
        print(f"Error {f}: {e}")

print(json.dumps(team_counts['Miami Heat'], indent=2))
