#!/usr/bin/env python3
"""
Manual Pick Result Updater
Use this when NBA API is blocked to manually enter game scores and update picks
"""

import json
import os
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def load_tracking():
    """Load tracking data"""
    tracking_file = 'nba_picks_tracking.json'
    
    if not os.path.exists(tracking_file):
        print(f"{Colors.RED}❌ No tracking file found: {tracking_file}{Colors.END}")
        print(f"{Colors.YELLOW}Make sure you're in the same directory as your tracking file{Colors.END}")
        return None
    
    with open(tracking_file, 'r') as f:
        return json.load(f)

def save_tracking(tracking_data):
    """Save tracking data"""
    with open('nba_picks_tracking.json', 'w') as f:
        json.dump(tracking_data, f, indent=2)
    print(f"{Colors.GREEN}✅ Tracking data saved{Colors.END}")

def manual_update_picks():
    """Manually update pick results by entering scores"""
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}🏀 NBA PICK MANUAL UPDATER 🏀{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    # Load tracking data
    tracking_data = load_tracking()
    if not tracking_data:
        return
    
    # Find pending picks
    pending = [p for p in tracking_data['picks'] if p['status'] == 'Pending']
    
    if not pending:
        print(f"{Colors.GREEN}✅ No pending picks to update!{Colors.END}")
        
        # Show summary
        total = tracking_data['summary']['total_picks']
        wins = tracking_data['summary']['wins']
        losses = tracking_data['summary']['losses']
        pushes = tracking_data['summary']['pushes']
        
        if total > 0:
            print(f"\n{Colors.CYAN}Current Record:{Colors.END}")
            print(f"  Total: {total}")
            print(f"  Wins: {wins}")
            print(f"  Losses: {losses}")
            print(f"  Pushes: {pushes}")
            if (wins + losses) > 0:
                win_rate = (wins / (wins + losses)) * 100
                print(f"  Win Rate: {win_rate:.1f}%")
        
        return
    
    print(f"{Colors.CYAN}Found {len(pending)} pending picks{Colors.END}\n")
    
    updated_count = 0
    
    for i, pick in enumerate(pending, 1):
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}PICK #{i} of {len(pending)}{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
        
        print(f"{Colors.CYAN}Game:{Colors.END}     {pick['matchup']}")
        print(f"{Colors.CYAN}Date:{Colors.END}     {pick['game_date'][:10]}")
        print(f"{Colors.CYAN}Type:{Colors.END}     {pick['pick_type']}")
        print(f"{Colors.CYAN}Pick:{Colors.END}     {pick['pick']}")
        print(f"{Colors.CYAN}Line:{Colors.END}     {pick['market_line']}")
        print(f"{Colors.CYAN}Edge:{Colors.END}     {pick['edge']:+.1f} points")
        
        # Ask if game is complete
        print(f"\n{Colors.YELLOW}Is this game completed?{Colors.END}")
        complete = input("Enter 'y' for yes, 'n' for no, 's' to skip all: ").lower().strip()
        
        if complete == 's':
            print(f"{Colors.YELLOW}Skipping remaining picks...{Colors.END}")
            break
        
        if complete != 'y':
            print(f"{Colors.YELLOW}Skipped{Colors.END}")
            continue
        
        # Get scores
        try:
            print(f"\n{Colors.CYAN}Enter final scores:{Colors.END}")
            away_score = int(input(f"  {pick['away_team']}: ").strip())
            home_score = int(input(f"  {pick['home_team']}: ").strip())
        except ValueError:
            print(f"{Colors.RED}❌ Invalid score entered, skipping this pick{Colors.END}")
            continue
        
        # Update pick with scores
        pick['actual_away_score'] = away_score
        pick['actual_home_score'] = home_score
        
        # Calculate result based on pick type
        if pick['pick_type'] == 'Spread':
            actual_spread = home_score - away_score  # Positive if home won by more
            market_line = pick['market_line']
            
            # Determine which team we picked
            if pick['home_team'] in pick['pick'] or 'Home' in pick['pick']:
                # We picked home team
                ats_result = actual_spread + market_line
                if abs(ats_result) < 0.5:
                    result = 'Push'
                    profit = 0
                elif ats_result > 0:
                    result = 'Win'
                    profit = 91  # Standard -110 payout
                else:
                    result = 'Loss'
                    profit = -100
            else:
                # We picked away team
                ats_result = -actual_spread + market_line
                if abs(ats_result) < 0.5:
                    result = 'Push'
                    profit = 0
                elif ats_result > 0:
                    result = 'Win'
                    profit = 91
                else:
                    result = 'Loss'
                    profit = -100
        
        elif pick['pick_type'] == 'Total':
            actual_total = home_score + away_score
            market_total = pick['market_line']
            
            if 'OVER' in pick['pick'].upper():
                if abs(actual_total - market_total) < 0.5:
                    result = 'Push'
                    profit = 0
                elif actual_total > market_total:
                    result = 'Win'
                    profit = 91
                else:
                    result = 'Loss'
                    profit = -100
            else:  # UNDER
                if abs(actual_total - market_total) < 0.5:
                    result = 'Push'
                    profit = 0
                elif actual_total < market_total:
                    result = 'Win'
                    profit = 91
                else:
                    result = 'Loss'
                    profit = -100
        
        # Update the pick
        pick['result'] = result
        pick['status'] = result
        pick['profit_loss'] = profit
        
        # Update summary
        tracking_data['summary']['pending'] -= 1
        if result == 'Win':
            tracking_data['summary']['wins'] += 1
            print(f"\n{Colors.GREEN}✅ WIN - Profit: +${profit/100:.2f} units{Colors.END}")
        elif result == 'Loss':
            tracking_data['summary']['losses'] += 1
            print(f"\n{Colors.RED}❌ LOSS - Loss: -${abs(profit)/100:.2f} units{Colors.END}")
        else:
            tracking_data['summary']['pushes'] += 1
            print(f"\n{Colors.YELLOW}➖ PUSH - No change{Colors.END}")
        
        updated_count += 1
    
    # Save all updates
    if updated_count > 0:
        save_tracking(tracking_data)
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}SUMMARY{Colors.END}")
        print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
        print(f"Updated {updated_count} pick(s)")
        
        # Calculate and show stats
        total = tracking_data['summary']['total_picks']
        wins = tracking_data['summary']['wins']
        losses = tracking_data['summary']['losses']
        pushes = tracking_data['summary']['pushes']
        pending_remaining = tracking_data['summary']['pending']
        
        print(f"\n{Colors.CYAN}Overall Record:{Colors.END}")
        print(f"  Total Picks: {total}")
        print(f"  Wins: {wins}")
        print(f"  Losses: {losses}")
        print(f"  Pushes: {pushes}")
        print(f"  Pending: {pending_remaining}")
        
        if (wins + losses) > 0:
            win_rate = (wins / (wins + losses)) * 100
            print(f"  Win Rate: {win_rate:.1f}%")
        
        # Calculate profit
        total_profit = sum(p['profit_loss'] for p in tracking_data['picks'] 
                          if p['status'] in ['Win', 'Loss', 'Push'])
        total_risked = abs(sum(p['profit_loss'] for p in tracking_data['picks'] 
                               if p['status'] == 'Loss'))
        
        if total_risked > 0:
            roi = (total_profit / total_risked) * 100
            profit_color = Colors.GREEN if total_profit > 0 else Colors.RED
            print(f"{profit_color}  Profit: {total_profit/100:+.2f} units{Colors.END}")
            print(f"{profit_color}  ROI: {roi:+.1f}%{Colors.END}")
        
        print(f"\n{Colors.GREEN}✅ Don't forget to run your main script to regenerate the HTML dashboard!{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}No picks were updated{Colors.END}")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")

if __name__ == "__main__":
    try:
        manual_update_picks()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Cancelled by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
