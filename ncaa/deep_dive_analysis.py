import json
from collections import defaultdict
import os
import sys

def analyze_performance():
    # Load data
    file_path = '/Users/rico/Dev/sports-models/ncaa/ncaab_picks_tracking.json'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)
    
    picks = data.get('picks', []) if isinstance(data, dict) else data
    
    # Sort by date (newest first) for rolling analysis
    def get_date(x):
        return x.get('game_date') or x.get('date_logged') or ''
    
    picks.sort(key=get_date, reverse=True)
    
    # Filter for decided picks only
    decided_picks = [p for p in picks if p.get('status', '').lower() in ['win', 'loss', 'push']]
    
    print(f"Total Decided Picks: {len(decided_picks)}")
    
    # --- 1. ROLLING WINDOWS ---
    windows = [10, 20, 50, 100, 200]
    print("\n" + "="*50)
    print("MATCH HISTORY BREAKDOWN (Most Recent First)")
    print("="*50)
    
    for window in windows:
        if len(decided_picks) < window:
            print(f"Last {window}: Not enough data (Only {len(decided_picks)} picks)")
            continue
            
        sample = decided_picks[:window]
        wins = sum(1 for p in sample if p['status'] == 'win')
        losses = sum(1 for p in sample if p['status'] == 'loss')
        pushes = sum(1 for p in sample if p['status'] == 'push')
        profit = sum(float(p.get('profit', 0) or (90.9 if p['status']=='win' else -100)) for p in sample)
        
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        color = ""
        if win_rate > 55: color = "🔥 "
        elif win_rate < 48: color = "❄️ "
        
        print(f"{color}Last {window}: {wins}-{losses}-{pushes} ({win_rate:.1f}%) | Profit: {profit:+.2f}u")

    # --- 2. CATEGORY BREAKDOWN ---
    print("\n" + "="*50)
    print("DETAILED CATEGORY BREAKDOWN")
    print("="*50)
    
    categories = {
        'Spreads': lambda p: 'spread' in p.get('pick_type', '').lower(),
        'Totals': lambda p: 'total' in p.get('pick_type', '').lower(),
        '  > Overs': lambda p: 'total' in p.get('pick_type', '').lower() and 'OVER' in p.get('pick_text', '').upper(),
        '  > Unders': lambda p: 'total' in p.get('pick_type', '').lower() and 'UNDER' in p.get('pick_text', '').upper(),
    }
    
    print(f"{'Category':<15} | {'Record':<12} | {'Win %':<6} | {'Profit':<10}")
    print("-" * 50)
    
    for cat_name, filter_func in categories.items():
        cat_picks = [p for p in decided_picks if filter_func(p)]
        wins = sum(1 for p in cat_picks if p['status'] == 'win')
        losses = sum(1 for p in cat_picks if p['status'] == 'loss')
        pushes = sum(1 for p in cat_picks if p['status'] == 'push')
        profit = sum(float(p.get('profit', 0) or (90.9 if p['status']=='win' else -100)) for p in cat_picks)
        
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        print(f"{cat_name:<15} | {wins}-{losses}-{pushes:<5} | {win_rate:.1f}%  | {profit:+.0f}u")

    # --- 3. TEAM PERFORMANCE ---
    team_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pushes': 0, 'profit': 0})
    
    for p in decided_picks:
        # Determine which team was bet on
        pick_text = p.get('pick_text', '').upper()
        home = p.get('home_team', '')
        away = p.get('away_team', '')
        
        bet_team = "Unknown"
        # Simplistic matching - usually works for this model
        if home.upper() in pick_text: bet_team = home
        elif away.upper() in pick_text: bet_team = away
        elif 'OVER' in pick_text or 'UNDER' in pick_text: continue # Skip totals for team analysis
        
        if bet_team != "Unknown":
            s = team_stats[bet_team]
            if p['status'] == 'win': s['wins'] += 1
            elif p['status'] == 'loss': s['losses'] += 1
            elif p['status'] == 'push': s['pushes'] += 1
            s['profit'] += float(p.get('profit', 0) or (90.9 if p['status']=='win' else -100))

    # Convert to list
    team_list = []
    for team, stats in team_stats.items():
        total = stats['wins'] + stats['losses'] + stats['pushes']
        if total >= 5: # Minimum 5 bets to qualify
            wr = stats['wins'] / (stats['wins'] + stats['losses']) * 100 if (stats['wins'] + stats['losses']) > 0 else 0
            team_list.append({
                'team': team,
                'record': f"{stats['wins']}-{stats['losses']}-{stats['pushes']}",
                'win_rate': wr,
                'profit': stats['profit']
            })
    
    # Sort Best
    print("\n" + "="*50)
    print("BEST TEAMS TO BET ON (Min 5 bets)")
    print("="*50)
    team_list.sort(key=lambda x: x['profit'], reverse=True)
    for t in team_list[:10]:
         print(f"✅ {t['team']:<25} | {t['record']:<8} ({t['win_rate']:.0f}%) | {t['profit']:+.0f}u")
         
    # Sort Worst
    print("\n" + "="*50)
    print("WORST TEAMS TO BET ON (Min 5 bets)")
    print("="*50)
    team_list.sort(key=lambda x: x['profit'])
    for t in team_list[:10]:
         print(f"❌ {t['team']:<25} | {t['record']:<8} ({t['win_rate']:.0f}%) | {t['profit']:+.0f}u")

if __name__ == "__main__":
    analyze_performance()
