import json
from collections import defaultdict
from datetime import datetime

TRACKING_FILE = 'nba/nba_picks_tracking.json'

def analyze():
    with open(TRACKING_FILE, 'r') as f:
        data = json.load(f)
    
    picks = data['picks']
    
    stats = {
        'overall': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
        'spread': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
        'total': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
        'overs': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
        'unders': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
        'favorites': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
        'underdogs': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
        'home': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
        'away': {'w': 0, 'l': 0, 'p': 0, 'profit': 0},
    }
    
    # Analyze by Edge Bucket
    edge_buckets = defaultdict(lambda: {'w': 0, 'l': 0})
    
    # Recent Form (Last 50)
    graded_picks = [p for p in picks if p.get('status', '').lower() in ['win', 'loss', 'push']]
    # Sort by date
    # Some older picks might not have date_logged in standard format, so handle gracefully
    # We'll just assume list order is roughly chronological or reverse chronological depending on how it's appended.
    # Usually appended -> last is newest.
    
    recent_50 = graded_picks[-50:]
    
    for p in graded_picks:
        status = p.get('status', '').lower()
        if status not in ['win', 'loss', 'push']: continue
        
        profit = p.get('profit_loss', 0)
        # Helper for profit
        if profit == 0:
            if status == 'win': profit = 90.9
            elif status == 'loss': profit = -100
            
        pick_type = p.get('pick_type', '').lower()
        pick_text = (p.get('pick') or '').upper()
        
        # Determine category
        cats = ['overall']
        
        if 'spread' in pick_type:
            cats.append('spread')
            if '-' in pick_text: cats.append('favorites')
            if '+' in pick_text: cats.append('underdogs')
        elif 'total' in pick_type:
            cats.append('total')
            if 'OVER' in pick_text: cats.append('overs')
            if 'UNDER' in pick_text: cats.append('unders')
            
        if p.get('home_team') in pick_text: cats.append('home')
        if p.get('away_team') in pick_text: cats.append('away')
            
        # Update Stats
        for c in cats:
            if status == 'win': stats[c]['w'] += 1
            elif status == 'loss': stats[c]['l'] += 1
            elif status == 'push': stats[c]['p'] += 1
            stats[c]['profit'] += profit
            
        # Edge Analysis
        edge = abs(p.get('edge', 0))
        bucket = int(edge // 2) * 2 # 0-2, 2-4, 4-6, etc.
        if status == 'win': edge_buckets[bucket]['w'] += 1
        elif status == 'loss': edge_buckets[bucket]['l'] += 1

    print("=== NBA MODEL PERFORMANCE DIAGNOSTIC ===")
    print(f"Total Graded Bets: {len(graded_picks)}")
    
    print("\n-- By Category --")
    for cat, s in stats.items():
        total = s['w'] + s['l'] + s['p']
        if total == 0: continue
        wr = s['w'] / (s['w'] + s['l']) * 100 if (s['w'] + s['l']) > 0 else 0
        roi = s['profit'] / (total * 110) * 100 # Approx ROI
        print(f"{cat.ljust(12)}: {s['w']}-{s['l']}-{s['p']} ({wr:.1f}%) | Profit: {s['profit']:.1f} | ROI: {roi:.1f}%")
        
    print("\n-- By Edge (Spread/Total Edge) --")
    for b in sorted(edge_buckets.keys()):
        s = edge_buckets[b]
        total = s['w'] + s['l']
        wr = s['w'] / total * 100 if total > 0 else 0
        print(f"Edge {b}-{b+2}: {s['w']}-{s['l']} ({wr:.1f}%)")

    print("\n-- Recent Form (Last 50) --")
    rec_w = sum(1 for p in recent_50 if p['status']=='win')
    rec_l = sum(1 for p in recent_50 if p['status']=='loss')
    rec_wr = rec_w / (rec_w + rec_l) * 100 if (rec_w + rec_l) > 0 else 0
    print(f"Last 50: {rec_w}-{rec_l} ({rec_wr:.1f}%)")

if __name__ == "__main__":
    analyze()
