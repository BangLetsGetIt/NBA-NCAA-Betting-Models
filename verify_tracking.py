#!/usr/bin/env python3
"""
Model Tracking Health Check
---------------------------
Verifies all sports models are tracking correctly.
Run this to get a complete status report.
"""

import json
import os
from datetime import datetime, timedelta
from collections import Counter
import pytz

# Get Eastern timezone
ET = pytz.timezone('US/Eastern')
NOW = datetime.now(ET)
TODAY = NOW.strftime('%Y-%m-%d')
YESTERDAY = (NOW - timedelta(days=1)).strftime('%Y-%m-%d')

# All tracking files to check
TRACKING_FILES = [
    # NBA Props
    ('NBA Points Props', 'nba/nba_points_props_tracking.json'),
    ('NBA Assists Props', 'nba/nba_assists_props_tracking.json'),
    ('NBA Rebounds Props', 'nba/nba_rebounds_props_tracking.json'),
    ('NBA 3PT Props', 'nba/nba_3pt_props_tracking.json'),
    # NFL Props
    ('NFL Passing Yards', 'nfl/nfl_passing_yards_props_tracking.json'),
    ('NFL Rushing Yards', 'nfl/nfl_rushing_yards_props_tracking.json'),
    ('NFL Receiving Yards', 'nfl/nfl_receiving_yards_props_tracking.json'),
    ('NFL Receptions', 'nfl/nfl_receptions_props_tracking.json'),
    # Main Models
    ('NBA Main', 'nba/nba_picks_tracking.json'),
    ('NFL Main', 'nfl/nfl_picks_tracking.json'),
    ('NCAAB Main', 'ncaa/ncaab_picks_tracking.json'),
    ('Soccer', 'soccer/soccer_picks_tracking.json'),
]

def parse_game_date(game_time):
    """Parse game_time string to date string YYYY-MM-DD in ET"""
    if not game_time:
        return None
    try:
        if 'Z' in game_time:
            dt = datetime.fromisoformat(game_time.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(game_time)
        return dt.astimezone(ET).strftime('%Y-%m-%d')
    except:
        return None

def check_tracking_file(name, filepath):
    """Check a single tracking file for issues"""
    result = {
        'name': name,
        'exists': False,
        'total': 0,
        'pending': 0,
        'wins': 0,
        'losses': 0,
        'today': {'wins': 0, 'losses': 0},
        'yesterday': {'wins': 0, 'losses': 0},
        'has_game_time': True,
        'duplicate_players': 0,
        'issues': []
    }
    
    if not os.path.exists(filepath):
        result['issues'].append('❌ File not found')
        return result
    
    result['exists'] = True
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except Exception as e:
        result['issues'].append(f'❌ JSON parse error: {e}')
        return result
    
    # Handle both dict and array formats
    if isinstance(data, dict):
        picks = data.get('picks', [])
    else:
        picks = data
    
    result['total'] = len(picks)
    
    # Count by status
    pending_players = []
    for p in picks:
        status = p.get('status', 'pending').lower()
        
        if status == 'pending':
            result['pending'] += 1
            pending_players.append(p.get('player', 'unknown'))
        elif status in ['win', 'won']:
            result['wins'] += 1
        elif status in ['loss', 'lost']:
            result['losses'] += 1
        
        # Check game_time
        game_time = p.get('game_time') or p.get('game_date')
        if not game_time:
            result['has_game_time'] = False
        else:
            game_date = parse_game_date(game_time)
            if game_date == TODAY:
                if status in ['win', 'won']:
                    result['today']['wins'] += 1
                elif status in ['loss', 'lost']:
                    result['today']['losses'] += 1
            elif game_date == YESTERDAY:
                if status in ['win', 'won']:
                    result['yesterday']['wins'] += 1
                elif status in ['loss', 'lost']:
                    result['yesterday']['losses'] += 1
    
    # Check for duplicate players in pending
    player_counts = Counter(pending_players)
    dupes = [(p, c) for p, c in player_counts.items() if c > 1]
    result['duplicate_players'] = len(dupes)
    
    # Identify issues
    if not result['has_game_time']:
        result['issues'].append('⚠️ Some picks missing game_time')
    if result['duplicate_players'] > 0:
        result['issues'].append(f'⚠️ {result["duplicate_players"]} duplicate players in pending')
    
    return result

def main():
    print("=" * 70)
    print("🏀 COURTSIDE ANALYTICS - TRACKING HEALTH CHECK")
    print(f"📅 Today: {TODAY} | Yesterday: {YESTERDAY}")
    print("=" * 70)
    print()
    
    all_results = []
    
    for name, filepath in TRACKING_FILES:
        result = check_tracking_file(name, filepath)
        all_results.append(result)
    
    # Print results by category
    categories = {
        'NBA Props': [r for r in all_results if 'NBA' in r['name'] and 'Props' in r['name']],
        'NFL Props': [r for r in all_results if 'NFL' in r['name'] and 'Main' not in r['name']],
        'Main Models': [r for r in all_results if 'Main' in r['name'] or 'Soccer' in r['name'] or 'NCAAB' in r['name']],
    }
    
    total_issues = 0
    
    for cat_name, results in categories.items():
        print(f"📊 {cat_name}")
        print("-" * 50)
        
        for r in results:
            if not r['exists']:
                print(f"  {r['name']}: ❌ NOT FOUND")
                total_issues += 1
                continue
            
            record = f"{r['wins']}-{r['losses']}"
            today_str = f"{r['today']['wins']}-{r['today']['losses']}"
            yesterday_str = f"{r['yesterday']['wins']}-{r['yesterday']['losses']}"
            
            status = "✅" if len(r['issues']) == 0 else "⚠️"
            
            print(f"  {status} {r['name']}")
            print(f"      Total: {r['total']} | Record: {record} | Pending: {r['pending']}")
            print(f"      Today: {today_str} | Yesterday: {yesterday_str}")
            
            if r['issues']:
                for issue in r['issues']:
                    print(f"      {issue}")
                    total_issues += 1
        
        print()
    
    # Summary
    print("=" * 70)
    if total_issues == 0:
        print("✅ ALL MODELS TRACKING CORRECTLY")
    else:
        print(f"⚠️ FOUND {total_issues} ISSUE(S) - See details above")
    print("=" * 70)

if __name__ == "__main__":
    main()
