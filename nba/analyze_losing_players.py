import json
import os
from collections import defaultdict

# Configuration
TRACKING_FILES = {
    'Points': 'nba/nba_points_props_tracking.json',
    'Assists': 'nba/nba_assists_props_tracking.json',
    'Rebounds': 'nba/nba_rebounds_props_tracking.json',
    '3-Pointers': 'nba/nba_3pt_props_tracking.json'
}

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"Warning: File not found {filepath}")
        return {'picks': []}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return {'picks': []}

def analyze_losses():
    # Data structure: player -> {'profit_cents': 0, 'wins': 0, 'losses': 0, 'by_model': {model: profit_cents}}
    player_stats = defaultdict(lambda: {'profit_cents': 0, 'wins': 0, 'losses': 0, 'by_model': defaultdict(int)})
    
    total_picks_analyzed = 0

    print(f"Scanning tracking files...")
    
    for model_name, filepath in TRACKING_FILES.items():
        data = load_json(filepath)
        picks = data.get('picks', [])
        print(f"  - {model_name}: Found {len(picks)} picks")
        
        for pick in picks:
            status = pick.get('status', '').lower()
            if status not in ['win', 'loss']:
                continue
                
            player = pick.get('player', 'Unknown').strip()
            profit_loss = pick.get('profit_loss')
            
            # If profit_loss missing, estimate from odds (fallback)
            if profit_loss is None:
                odds = pick.get('odds') or -110
                if status == 'win':
                    if odds > 0: profit_loss = int(odds)
                    else: profit_loss = int((100 / abs(odds)) * 100)
                else:
                    profit_loss = -100
            
            player_stats[player]['profit_cents'] += profit_loss
            player_stats[player]['by_model'][model_name] += profit_loss
            
            if status == 'win':
                player_stats[player]['wins'] += 1
            else:
                player_stats[player]['losses'] += 1
                
            total_picks_analyzed += 1

    print(f"\nAnalyzed {total_picks_analyzed} completed picks across all models.")
    
    # Convert to list and sort by profit (answering: who lost the most money?)
    # Ascending sort because massive negatives = biggest losers
    sorted_players = sorted(player_stats.items(), key=lambda x: x[1]['profit_cents'])
    
    # OUTPUT REPORT
    print("\n" + "="*80)
    print("🚩 DO NOT BET LIST (BIGGEST LOSERS) 🚩")
    print("="*80)
    print(f"{'PLAYER':<25} | {'NET UNITS':<10} | {'RECORD':<10} | {'WORST PROP TYPE':<20}")
    print("-" * 80)
    
    # Show bottom 20 (biggest losers)
    for player, stats in sorted_players[:25]:
        net_units = stats['profit_cents'] / 100.0
        record = f"{stats['wins']}-{stats['losses']}"
        
        # Find worst performing model for this player
        worst_model = min(stats['by_model'].items(), key=lambda x: x[1])[0]
        worst_model_units = stats['by_model'][worst_model] / 100.0
        worst_str = f"{worst_model} ({worst_model_units:+.1f}u)"
        
        color = ""
        # if net_units < -5.0: color = "\033[91m" # Red
        # reset = "\033[0m"
        
        print(f"{player:<25} | {net_units:>+9.1f}u | {record:<10} | {worst_str:<20}")

    print("\n" + "="*80)
    print("📈 HONORABLE MENTIONS (BEST EARNERS) 📈")
    print("="*80)
    # Show top 10 best
    for player, stats in sorted_players[-10:][::-1]:
        net_units = stats['profit_cents'] / 100.0
        record = f"{stats['wins']}-{stats['losses']}"
        best_model = max(stats['by_model'].items(), key=lambda x: x[1])[0]
        best_model_units = stats['by_model'][best_model] / 100.0
        best_str = f"{best_model} ({best_model_units:+.1f}u)"
        
        print(f"{player:<25} | {net_units:>+9.1f}u | {record:<10} | {best_str:<20}")

if __name__ == "__main__":
    analyze_losses()
