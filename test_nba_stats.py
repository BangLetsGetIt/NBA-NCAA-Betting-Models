
import os
import sys
import json
import pytz
from datetime import datetime, timedelta

# Mock the environment
sys.path.append(os.path.join(os.getcwd(), 'nba'))

# Import the module
try:
    import nba_points_props_model as mod
except ImportError:
    print("Could not import nba_points_props_model")
    sys.exit(1)

def test_grading_logic():
    print(f"Testing stats calculation for {mod.__name__}")
    
    # 1. Load Tracking Data
    t_data = mod.load_tracking_data()
    print(f"Loaded {len(t_data.get('picks', []))} picks")
    
    # 2. Check for recent graded picks
    recent_picks = [p for p in t_data.get('picks', []) if p.get('updated_at') and '2025-12-13' in p.get('updated_at')]
    print(f"Found {len(recent_picks)} picks updated on 2025-12-13")
    
    # 3. Calculate Stats
    stats = mod.calculate_tracking_stats(t_data)
    
    print("\n--- Calculated Stats ---")
    print(f"Total: {stats.get('total')}")
    print(f"Wins: {stats.get('wins')}")
    print(f"Losses: {stats.get('losses')}")
    print(f"Profit: {stats.get('total_profit')} units")
    
    print("\n--- Today's Stats ---")
    today = stats.get('today', {})
    print(f"Record: {today.get('record')}")
    print(f"Profit: {today.get('profit')}")
    
    print("\n--- Yesterday's Stats ---")
    yesterday = stats.get('yesterday', {})
    print(f"Record: {yesterday.get('record')}")
    print(f"Profit: {yesterday.get('profit')}")

if __name__ == "__main__":
    test_grading_logic()
