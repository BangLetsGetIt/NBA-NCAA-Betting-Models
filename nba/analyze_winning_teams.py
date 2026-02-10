import json
import os
import re
from collections import defaultdict

TRACKING_FILE = 'nba/nba_picks_tracking.json'

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

def get_canonical_team_name(pick_text, home, away):
    """
    Extract team from '✅ BET: Team Name +/-X.X'
    and match to canonical name (home or away).
    """
    # Remove '✅ BET: ' prefix
    text = pick_text.replace('\u2705 BET: ', '').strip()
    
    # Try to remove spread number at end
    # Match pattern: (Team Name) (+/-Xd.d)
    match = re.search(r'^(.*?) ([+-]?\d+\.?\d*)$', text)
    if match:
        picked_team = match.group(1).strip()
    else:
        # Maybe moneyline (no number) or failed parse
        picked_team = text
    
    # Check if exact match or substring
    if picked_team == home: return home
    if picked_team == away: return away
    
    # Check substring
    if picked_team in home: return home
    if picked_team in away: return away
    
    # If home/away in picked_team (e.g. picked="Team Name", canonical="Team Name Warriors")
    if home in picked_team: return home
    if away in picked_team: return away
    
    return picked_team # Fallback

def analyze_teams():
    data = load_json(TRACKING_FILE)
    picks = data.get('picks', [])
    
    # Team Stats: {team: {'profit': 0, 'wins': 0, 'losses': 0}}
    team_stats = defaultdict(lambda: {'profit': 0, 'wins': 0, 'losses': 0})
    
    total_analyzed = 0
    
    print(f"Scanning NBA picks...")
    
    for pick in picks:
        p_type = pick.get('pick_type', '').lower()
        if p_type not in ['spread', 'moneyline']:
            continue
            
        status = pick.get('status', '').lower()
        if status not in ['win', 'loss']:
            continue
            
        # Determine Team
        home = pick.get('home_team', '')
        away = pick.get('away_team', '')
        text = pick.get('pick_text', '')
        
        team = get_canonical_team_name(text, home, away)
        
        # Calculate Profit
        profit = pick.get('profit_loss')
        # Fallback estimation
        if profit is None:
            odds = -110 # Default spread odds
            if status == 'win':
                profit = 91 # approx for -110
            else:
                profit = -100
                
        team_stats[team]['profit'] += profit
        if status == 'win':
            team_stats[team]['wins'] += 1
        else:
            team_stats[team]['losses'] += 1
            
        total_analyzed += 1
        
    print(f"Analyzed {total_analyzed} spread/ML picks.")
    
    # Sort by Profit (Descending)
    sorted_teams = sorted(team_stats.items(), key=lambda x: x[1]['profit'], reverse=True)
    
    # Output Winners
    print("\n" + "="*80)
    print("🏀 NBA TEAMS TO ALWAYS BET ON (TOP 25) 🏀")
    print("="*80)
    print(f"{'TEAM':<35} | {'NET UNITS':<10} | {'RECORD':<10} | {'WIN %':<8}")
    print("-" * 80)
    
    for team, stats in sorted_teams[:25]:
        net_units = stats['profit'] / 100.0
        wins = stats['wins']
        losses = stats['losses']
        total = wins + losses
        win_pct = (wins / total * 100) if total > 0 else 0
        record = f"{wins}-{losses}"
        
        # if total < 3: continue # Filter low sample size (NBA has fewer teams, so maybe 2 is safer)
        
        print(f"{team:<35} | {net_units:>+9.1f}u | {record:<10} | {win_pct:.0f}%")

    # Output Losers (Bonus)
    print("\n" + "="*80)
    print("🛑 NBA TEAMS TO AVOID (TOP 10 LOSERS) 🛑")
    print("="*80)
    for team, stats in sorted_teams[-10:]:
        net_units = stats['profit'] / 100.0
        wins = stats['wins']
        losses = stats['losses']
        total = wins + losses
        win_pct = (wins / total * 100) if total > 0 else 0
        record = f"{wins}-{losses}"
        
        # if total < 3: continue
        
        print(f"{team:<35} | {net_units:>+9.1f}u | {record:<10} | {win_pct:.0f}%")

if __name__ == "__main__":
    analyze_teams()
