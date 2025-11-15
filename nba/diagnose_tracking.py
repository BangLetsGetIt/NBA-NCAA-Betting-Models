import json
import os
from collections import Counter

def diagnose_tracking_file(json_file):
    """Diagnose issues with a bet tracking JSON file"""
    
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        return
    
    print(f"\n{'='*60}")
    print(f"📊 DIAGNOSING: {json_file}")
    print(f"{'='*60}\n")
    
    # Load data
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    if not data:
        print("⚠️  File is empty!")
        return
    
    total_rows = len(data)
    
    # Count by status
    status_counts = Counter([bet.get('Status', 'Unknown') for bet in data])
    
    wins = status_counts.get('Win', 0)
    losses = status_counts.get('Loss', 0)
    pushes = status_counts.get('Push', 0)
    pending = status_counts.get('Pending', 0)
    errors = status_counts.get('Error', 0)
    unknown = sum(status_counts[k] for k in status_counts if k not in ['Win', 'Loss', 'Push', 'Pending', 'Error'])
    
    completed = wins + losses + pushes
    
    # Calculate what stats SHOULD be
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    total_profit = (wins * 0.91) - (losses * 1.0)
    roi = (total_profit / completed * 100) if completed > 0 else 0
    
    # Display findings
    print("📈 RAW DATA COUNTS:")
    print(f"   Total rows in file: {total_rows}")
    print(f"   ├─ Pending: {pending}")
    print(f"   ├─ Completed: {completed}")
    print(f"   │  ├─ Wins: {wins}")
    print(f"   │  ├─ Losses: {losses}")
    print(f"   │  └─ Pushes: {pushes}")
    if errors > 0:
        print(f"   ├─ Errors: {errors}")
    if unknown > 0:
        print(f"   └─ Unknown status: {unknown}")
    
    print(f"\n✅ CORRECT STATS (from completed bets only):")
    print(f"   Total Bets: {completed}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Total Profit: {total_profit:+.2f}u")
    print(f"   ROI: {roi:+.1f}%")
    print(f"   Record: {wins}-{losses}-{pushes}")
    
    print(f"\n❌ WRONG STATS (if counting all rows):")
    wrong_win_rate = (wins / total_rows * 100) if total_rows > 0 else 0
    wrong_roi = (total_profit / total_rows * 100) if total_rows > 0 else 0
    print(f"   Total Bets: {total_rows}  ← WRONG! Includes {pending} pending games")
    print(f"   Win Rate: {wrong_win_rate:.1f}%  ← WRONG!")
    print(f"   ROI: {wrong_roi:+.1f}%  ← WRONG!")
    
    print(f"\n🔍 THE PROBLEM:")
    if pending > 0:
        pct_pending = (pending / total_rows * 100)
        print(f"   {pct_pending:.1f}% of your data is PENDING games that haven't happened yet")
        print(f"   But they're being counted in 'Total Bets' = {total_rows}")
        print(f"   This inflates your totals and skews all your percentages!")
    
    print(f"\n💡 THE FIX:")
    print(f"   Only count completed bets: {completed} (not {total_rows})")
    print(f"   This gives you the REAL stats shown above")
    
    # Check for data quality issues
    print(f"\n🔎 DATA QUALITY CHECK:")
    issues = []
    
    for i, bet in enumerate(data):
        if bet.get('Status') in ['Win', 'Loss'] and not bet.get('Result'):
            issues.append(f"Row {i+1}: {bet['Status']} but missing Result field")
        if bet.get('Status') in ['Win', 'Loss'] and not bet.get('Profit'):
            issues.append(f"Row {i+1}: {bet['Status']} but missing Profit field")
    
    if issues:
        print("   ⚠️  Found issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"      - {issue}")
        if len(issues) > 10:
            print(f"      ... and {len(issues) - 10} more")
    else:
        print("   ✅ No data quality issues found")
    
    print(f"\n{'='*60}\n")

def main():
    """Run diagnostics on all tracking files"""
    files_to_check = [
        'nba_bet_history.json',
        'ncaab_bet_history.json'
    ]
    
    found_any = False
    for file in files_to_check:
        if os.path.exists(file):
            found_any = True
            diagnose_tracking_file(file)
    
    if not found_any:
        print("\n❌ No tracking files found!")
        print("Looking for:")
        for file in files_to_check:
            print(f"  - {file}")
        print("\nPlace your bet history JSON files in the current directory and run again.")

if __name__ == "__main__":
    main()
