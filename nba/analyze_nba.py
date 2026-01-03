import json
from collections import defaultdict

def analyze_picks():
    with open('nba/nba_picks_tracking.json', 'r') as f:
        data = json.load(f)
    
    picks = data['picks']
    
    stats = {
        'Spread': {'wins': 0, 'losses': 0, 'pushes': 0, 'total': 0, 'profit': 0},
        'Total': {'wins': 0, 'losses': 0, 'pushes': 0, 'total': 0, 'profit': 0},
        'Overall': {'wins': 0, 'losses': 0, 'pushes': 0, 'total': 0, 'profit': 0}
    }
    
    recent_stats = {
        'Spread': {'wins': 0, 'losses': 0},
        'Total': {'wins': 0, 'losses': 0}
    }
    
    # Sort by date
    picks.sort(key=lambda x: x['game_date'], reverse=True)
    
    recent_limit = 50
    count = 0
    
    for pick in picks:
        if pick['status'] == 'Pending':
            continue
            
        p_type = pick['pick_type']
        status = pick['status'].lower()
        profit = pick.get('profit_loss', 0)
        
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

            if count < recent_limit:
                 if status == 'win':
                    recent_stats[p_type]['wins'] += 1
                 elif status == 'loss':
                    recent_stats[p_type]['losses'] += 1
        
        count += 1

    print("=== OVERALL PERFORMANCE ===")
    print(f"Record: {stats['Overall']['wins']}-{stats['Overall']['losses']}-{stats['Overall']['pushes']}")
    if stats['Overall']['total'] > 0:
        win_rate = stats['Overall']['wins'] / (stats['Overall']['wins'] + stats['Overall']['losses']) * 100
        print(f"Win Rate: {win_rate:.1f}%")
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
