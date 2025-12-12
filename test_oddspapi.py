#!/usr/bin/env python3
"""
Test script for OddsPapi integration
Tests endpoints for NBA and soccer odds/props
"""

import requests
import json
import os
from datetime import datetime

# You'll need to get an API key from https://oddspapi.io
ODDSPAPI_API_KEY = os.environ.get('ODDSPAPI_API_KEY', '')

# OddsPapi base URL (from their website)
BASE_URL = 'https://api.oddspapi.com/v1'  # Common pattern, may need adjustment

def test_endpoint(endpoint, params=None, method='GET'):
    """Test an API endpoint"""
    url = f"{BASE_URL}/{endpoint}"
    headers = {
        'Content-Type': 'application/json',
    }
    
    # OddsPapi typically uses API key in header or query param
    if ODDSPAPI_API_KEY:
        headers['X-API-Key'] = ODDSPAPI_API_KEY
        # Also try as query param
        if params is None:
            params = {}
        params['apiKey'] = ODDSPAPI_API_KEY
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=10)
        else:
            response = requests.post(url, headers=headers, json=params, timeout=10)
        
        print(f"\n{'='*60}")
        print(f"Testing: {url}")
        if params:
            print(f"Params: {dict((k, v) for k, v in params.items() if k != 'apiKey')}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Success!")
                print(f"Response type: {type(data)}")
                if isinstance(data, dict):
                    print(f"Keys: {list(data.keys())[:10]}")
                    # Print sample data
                    for key in list(data.keys())[:3]:
                        print(f"  {key}: {str(data[key])[:100]}")
                elif isinstance(data, list):
                    print(f"List length: {len(data)}")
                    if data:
                        print(f"First item type: {type(data[0])}")
                        if isinstance(data[0], dict):
                            print(f"First item keys: {list(data[0].keys())[:10]}")
                return data
            except:
                print(f"Response (text): {response.text[:200]}")
                return response.text
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error message: {error_data}")
            except:
                print(f"Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def main():
    print("="*60)
    print("OddsPapi API Test")
    print("="*60)
    
    if not ODDSPAPI_API_KEY:
        print("\n⚠️  No API key found. Set ODDSPAPI_API_KEY environment variable.")
        print("   Get your API key from: https://oddspapi.io/en")
        print("\nTesting endpoints without auth to see structure...\n")
    else:
        print(f"\n✅ API Key found: {ODDSPAPI_API_KEY[:10]}...{ODDSPAPI_API_KEY[-4:]}\n")
    
    # Known sport IDs from testing
    BASKETBALL_SPORT_ID = 11
    SOCCER_SPORT_ID = 10
    
    # Common OddsPapi endpoints to test (with known sport IDs)
    endpoints_to_test = [
        ('sports', {}),
        ('events', {'sportId': BASKETBALL_SPORT_ID}),
        ('odds', {'sportId': BASKETBALL_SPORT_ID}),
        ('events', {'sportId': SOCCER_SPORT_ID}),
        ('odds', {'sportId': SOCCER_SPORT_ID}),
    ]
    
    # Also try alternative base URLs
    base_urls = [
        'https://api.oddspapi.com/v1',
        'https://api.oddspapi.com',
        'https://oddspapi.io/api/v1',
        'https://oddspapi.io/api',
    ]
    
    for base_url in base_urls:
        global BASE_URL
        BASE_URL = base_url
        print(f"\n{'#'*60}")
        print(f"Testing base URL: {BASE_URL}")
        print(f"{'#'*60}")
        
        # Test sports endpoint first
        result = test_endpoint('sports', {})
        if result:
            print(f"\n✅ Found working base URL: {BASE_URL}")
            
            # Test events and odds with known sport IDs
            print(f"\n{'='*60}")
            print("Testing events and odds endpoints...")
            print(f"{'='*60}")
            
            # Test basketball
            print("\n--- Basketball (Sport ID: 11) ---")
            test_endpoint('events', {'sportId': 11})
            test_endpoint('odds', {'sportId': 11})
            
            # Test soccer
            print("\n--- Soccer (Sport ID: 10) ---")
            test_endpoint('events', {'sportId': 10})
            test_endpoint('odds', {'sportId': 10})
            
            # Test player props if available
            print("\n--- Testing Player Props ---")
            test_endpoint('player-props', {'sportId': 11})
            test_endpoint('props', {'sportId': 11})
            test_endpoint('odds', {'sportId': 11, 'market': 'player-props'})
            
            break
        
        # If we got a successful response, test more endpoints
        result = test_endpoint('sports', {})
        if result:
            print(f"\n{'='*60}")
            print("Testing additional endpoints...")
            print(f"{'='*60}")
            
            # Test NBA-specific endpoints
            test_endpoint('sports/basketball/events', {})
            test_endpoint('sports/basketball/odds', {})
            
            # Test player props if available
            test_endpoint('sports/basketball/player-props', {})
            test_endpoint('sports/basketball/props', {})
            
            break
    
    print("\n" + "="*60)
    print("Test Complete")
    print("="*60)
    print("\nNext steps:")
    print("1. Get API key from https://oddspapi.io/en")
    print("2. Set environment variable: export ODDSPAPI_API_KEY='your_key'")
    print("3. Run this script again to test with authentication")
    print("4. Check documentation for exact endpoint structure")

if __name__ == '__main__':
    main()

