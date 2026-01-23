
import json
import os

files = [f for f in os.listdir('nba') if 'tracking.json' in f]
hawks_picks = []

for f in files:
    try:
        data = json.load(open(os.path.join('nba', f)))
        picks = data.get('picks', [])
        for p in picks:
            team = p.get('home_team') or p.get('team') or p.get('away_team')
            if team == 'Atlanta Hawks':
                hawks_picks.append(p)
    except:
        pass

print(f"Total Hawks Picks: {len(hawks_picks)}")
types = {}
for p in hawks_picks:
    pt = p.get('pick_type', 'Unknown')
    if p.get('player'):
        pt = f"Player Prop ({pt})"
    types[pt] = types.get(pt, 0) + 1

print(json.dumps(types, indent=2))
