#!/usr/bin/env python3
"""
Fix NBA 3PT Props Tracking - Re-verify completed picks
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nba_3pt_props_model import reverify_completed_picks, load_tracking, calculate_tracking_summary, save_tracking

if __name__ == "__main__":
    print("\n" + "="*70)
    print("FIXING NBA 3PT PROPS TRACKING")
    print("="*70 + "\n")
    
    # Re-verify all completed picks
    updated = reverify_completed_picks()
    
    if updated > 0:
        tracking_data = load_tracking()
        summary = tracking_data['summary']
        print(f"\n{'='*70}")
        print(f"UPDATED SUMMARY:")
        print(f"  Wins: {summary['wins']}")
        print(f"  Losses: {summary['losses']}")
        print(f"  Pending: {summary['pending']}")
        if summary['wins'] + summary['losses'] > 0:
            win_rate = (summary['wins'] / (summary['wins'] + summary['losses'])) * 100
            print(f"  Win Rate: {win_rate:.1f}%")
        print(f"{'='*70}\n")

