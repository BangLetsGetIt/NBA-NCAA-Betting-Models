import json
from collections import defaultdict
import os

def analyze_picks():
    # Use absolute path
    file_path = '/Users/rico/Dev/sports-models/ncaa/ncaab_picks_tracking.json'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Check structure - ncaab might handle picks differently (list vs dict)
    if isinstance(data, list):
        picks = data
    else:
        picks = data.get('picks', [])
    
    stats = {
        'Spread': {'wins': 0, 'losses': 0, 'pushes': 0, 'total': 0, 'profit': 0},
        'Total': {'wins': 0, 'losses': 0, 'pushes': 0, 'total': 0, 'profit': 0},
        'Overall': {'wins': 0, 'losses': 0, 'pushes': 0, 'total': 0, 'profit': 0}
    }
    
    recent_stats = {
        'Spread': {'wins': 0, 'losses': 0},
        'Total': {'wins': 0, 'losses': 0}
    }
    
    # Try to sort by date_logged or game_date
    def get_date(x):
        return x.get('game_date') or x.get('date_logged') or ''
        
    picks.sort(key=get_date, reverse=True)
    
    recent_limit = 50
    decided_count = 0
    
    for pick in picks:
        # Standardize status
        status = pick.get('status', '').lower()
        if status not in ['win', 'loss', 'push']:
            continue
            
        p_type = pick.get('pick_type', '')
        # Normalize pick type
        if 'spread' in p_type.lower():
            p_type = 'Spread'
        elif 'total' in p_type.lower() or 'over' in p_type.lower() or 'under' in p_type.lower():
             p_type = 'Total'
        
        profit = pick.get('profit_loss', 0)
        # Some old tracking might not have profit calculated
        if profit == 0:
            if status == 'win': profit = 91.0 # assume -110
            elif status == 'loss': profit = -100.0
        
        # Update overall
        stats['Overall']['total'] += 1
        stats['Overall']['profit'] += profit
        
        if status == 'win':
            stats['Overall']['wins'] += 1
        elif status == 'loss':
            stats['Overall']['losses'] += 1
        elif status == 'push':
            stats['Overall']['pushes'] += 1
            
        # Update specific
        if p_type in stats:
            stats[p_type]['total'] += 1
            stats[p_type]['profit'] += profit
            
            if status == 'win':
                stats[p_type]['wins'] += 1
            elif status == 'loss':
                stats[p_type]['losses'] += 1
            elif status == 'push':
                stats[p_type]['pushes'] += 1

            if decided_count < recent_limit:
                 if status == 'win':
                    recent_stats[p_type]['wins'] += 1
                 elif status == 'loss':
                    recent_stats[p_type]['losses'] += 1
        
        decided_count += 1

    print("=== OVERALL PERFORMANCE ===")
    print(f"Record: {stats['Overall']['wins']}-{stats['Overall']['losses']}-{stats['Overall']['pushes']}")
    if stats['Overall']['total'] > 0:
        win_rate = stats['Overall']['wins'] / (stats['Overall']['wins'] + stats['Overall']['losses']) * 100
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Total Decided Picks: {stats['Overall']['total']}")
    print(f"Profit: {stats['Overall']['profit']:.1f} units")
    
    print("\n=== SPREAD PERFORMANCE ===")
    print(f"Record: {stats['Spread']['wins']}-{stats['Spread']['losses']}-{stats['Spread']['pushes']}")
    if (stats['Spread']['wins'] + stats['Spread']['losses']) > 0:
        win_rate = stats['Spread']['wins'] / (stats['Spread']['wins'] + stats['Spread']['losses']) * 100
        print(f"Win Rate: {win_rate:.1f}%")
    print(f"Profit: {stats['Spread']['profit']:.1f} units")
    
    print("\n=== TOTAL PERFORMANCE ===")
    print(f"Record: {stats['Total']['wins']}-{stats['Total']['losses']}-{stats['Total']['pushes']}")
    if (stats['Total']['wins'] + stats['Total']['losses']) > 0:
        win_rate = stats['Total']['wins'] / (stats['Total']['wins'] + stats['Total']['losses']) * 100
        print(f"Win Rate: {win_rate:.1f}%")
    print(f"Profit: {stats['Total']['profit']:.1f} units")

    print(f"\n=== RECENT {recent_limit} DECIDED PICKS breakdown ===")
    print(f"Spread: {recent_stats['Spread']['wins']}-{recent_stats['Spread']['losses']}")
    print(f"Total: {recent_stats['Total']['wins']}-{recent_stats['Total']['losses']}")

if __name__ == "__main__":
    analyze_picks()
