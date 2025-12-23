
import json
from pathlib import Path
from datetime import datetime

def reset_voided_picks():
    nfl_dir = Path('/Users/rico/sports-models/nfl')
    files = list(nfl_dir.glob('*tracking.json'))
    
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for f in files:
        print(f"Checking {f.name}...")
        with open(f, 'r') as file:
            data = json.load(file)
        
        # Correctly handle both formats: list OR {'picks': [...]}
        if isinstance(data, dict):
            picks = data.get('picks', [])
        else:
            picks = data
            
        updated = 0
        for p in picks:
            # If it's a VOID/PUSH but the game_date is in the future or today
            # (We reset today's games to be safe, since grader will re-check)
            game_date = p.get('game_date', '')[:10]
            if p.get('status') == 'push' and p.get('result') == 'VOID' and game_date >= '2025-12-21':
                p['status'] = 'pending'
                p['result'] = 'PENDING'
                p['profit_loss'] = 0.0
                p['actual_val'] = None
                # Clear all 'actual_...' fields
                keys_to_clear = [k for k in p.keys() if k.startswith('actual_')]
                for k in keys_to_clear:
                    p[k] = None
                updated += 1
        
        if updated > 0:
            print(f"  Reset {updated} picks in {f.name}")
            with open(f, 'w') as file:
                json.dump(data, file, indent=2)

if __name__ == "__main__":
    reset_voided_picks()
