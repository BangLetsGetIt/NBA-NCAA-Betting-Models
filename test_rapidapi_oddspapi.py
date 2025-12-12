#!/usr/bin/env python3
"""
Test script for RapidAPI OddsPapi integration
"""

import requests
import json
import os
import time

API_KEY = os.environ.get('RAPIDAPI_ODDSPAPI_KEY', 'fbb0933d50mshc354fe927e6bcffp101ecejsndc89e340ec39')

rapid_headers = {
    'X-RapidAPI-Key': API_KEY,
    'X-RapidAPI-Host': 'oddspapi.p.rapidapi.com'
}

BASE_URL = 'https://oddspapi.p.rapidapi.com/v1'

def test_endpoint(endpoint, params=None):
    """Test an endpoint"""
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, headers=rapid_headers, params=params, timeout=10)
        print(f"\n{'='*60}")
        print(f"Testing: {endpoint}")
        if params:
            print(f"Params: {params}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS!")
            print(f"Type: {type(data)}")
            if isinstance(data, list):
                print(f"Length: {len(data)}")
                if data:
                    print(f"\nFirst item structure:")
                    print(json.dumps(data[0], indent=2)[:600])
            elif isinstance(data, dict):
                print(f"Keys: {list(data.keys())}")
                print(f"\nSample data:")
                print(json.dumps(data, indent=2)[:600])
            return data
        else:
            print(f"Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def main():
    print("="*60)
    print("RapidAPI OddsPapi Test")
    print("="*60)
    print(f"\nAPI Key: {API_KEY[:20]}...{API_KEY[-10:]}")
    print(f"Base URL: {BASE_URL}\n")
    
    # Test endpoints
    print("Testing endpoints (with delays to avoid rate limits)...\n")
    
    # 1. Events
    time.sleep(1)
    events = test_endpoint('events', {'sportId': 11})
    
    # 2. Odds
    time.sleep(1)
    odds = test_endpoint('odds', {'sportId': 11})
    
    # 3. Test soccer
    time.sleep(1)
    soccer_events = test_endpoint('events', {'sportId': 10})
    
    # 4. Test if we can filter by market type
    time.sleep(1)
    player_props = test_endpoint('odds', {'sportId': 11, 'market': 'player-props'})
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)

if __name__ == '__main__':
    main()

