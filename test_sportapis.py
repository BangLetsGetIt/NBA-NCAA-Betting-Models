#!/usr/bin/env python3
"""
Test script for SportAPIs integration
Tests endpoints for NBA and soccer odds/props
"""

import requests
import json
import os
from datetime import datetime

# You'll need to get an API key from https://sportapis.com
SPORTAPIS_API_KEY = os.environ.get('SPORTAPIS_API_KEY', '')

# Common SportAPIs base URLs (need to verify actual URL)
BASE_URLS = [
    'https://api.sportapis.com',
    'https://sportapis.com/api',
    'https://api.sportapis.com/v1',
    'https://sportapis.com/v1',
]

def test_endpoint(base_url, endpoint, params=None):
    """Test an API endpoint"""
    url = f"{base_url}/{endpoint}"
    headers = {}
    if SPORTAPIS_API_KEY:
        headers['Authorization'] = f'Bearer {SPORTAPIS_API_KEY}'
        headers['X-API-Key'] = SPORTAPIS_API_KEY
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"Response type: {type(data)}")
            if isinstance(data, dict):
                print(f"Keys: {list(data.keys())[:10]}")
            elif isinstance(data, list):
                print(f"List length: {len(data)}")
                if data:
                    print(f"First item keys: {list(data[0].keys())[:10] if isinstance(data[0], dict) else 'Not a dict'}")
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def main():
    print("="*60)
    print("SportAPIs API Test")
    print("="*60)
    
    if not SPORTAPIS_API_KEY:
        print("\n⚠️  No API key found. Set SPORTAPIS_API_KEY environment variable.")
        print("   Get your API key from: https://sportapis.com")
        print("\nTesting endpoints without auth to see structure...\n")
    else:
        print(f"\n✅ API Key found: {SPORTAPIS_API_KEY[:10]}...{SPORTAPIS_API_KEY[-4:]}\n")
    
    # Test different base URLs and endpoints
    endpoints_to_test = [
        'sports',
        'sports/basketball_nba',
        'sports/basketball_nba/events',
        'sports/basketball_nba/odds',
        'sports/soccer',
        'sports/soccer/events',
        'odds',
        'events',
    ]
    
    for base_url in BASE_URLS:
        print(f"\n{'#'*60}")
        print(f"Testing base URL: {base_url}")
        print(f"{'#'*60}")
        
        # Test a few key endpoints
        for endpoint in ['sports', 'sports/basketball_nba/events']:
            test_endpoint(base_url, endpoint)
        
        # If we get a successful response, break
        result = test_endpoint(base_url, 'sports')
        if result:
            print(f"\n✅ Found working base URL: {base_url}")
            break
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    print("\nNext steps:")
    print("1. Get API key from https://sportapis.com")
    print("2. Set environment variable: export SPORTAPIS_API_KEY='your_key'")
    print("3. Run this script again to test with authentication")
    print("4. Check documentation for player props endpoints")

if __name__ == '__main__':
    main()

