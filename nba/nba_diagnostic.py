"""
NBA Tracking Diagnostic Tool
This script tests both the NBA API and web scraping methods to fetch game results
"""

from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def test_nba_api():
    """Test if NBA API is accessible"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}TEST 1: NBA API Access{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    try:
        from nba_api.stats.endpoints import scoreboardv2
        test_date = '10/30/2025'
        
        print(f"Attempting to fetch data from stats.nba.com for {test_date}...")
        scoreboard = scoreboardv2.ScoreboardV2(game_date=test_date)
        games_df = scoreboard.get_data_frames()[0]
        
        print(f"{Colors.GREEN}✅ SUCCESS: NBA API is accessible{Colors.END}")
        print(f"Found {len(games_df)} games")
        return True
        
    except Exception as e:
        if '403' in str(e) or 'ProxyError' in str(e) or 'Forbidden' in str(e):
            print(f"{Colors.RED}❌ BLOCKED: stats.nba.com is not accessible{Colors.END}")
            print(f"{Colors.YELLOW}   Error: {str(e)[:100]}...{Colors.END}")
            print(f"\n{Colors.YELLOW}   Root Cause: Network settings block stats.nba.com{Colors.END}")
            print(f"{Colors.YELLOW}   Solution: Add 'stats.nba.com' to allowed domains{Colors.END}")
        else:
            print(f"{Colors.RED}❌ ERROR: {str(e)[:100]}{Colors.END}")
        return False

def test_espn_scraping():
    """Test ESPN web scraping as alternative"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}TEST 2: ESPN Web Scraping (Alternative Method){Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    try:
        # Try yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        url = f"https://www.espn.com/nba/scoreboard/_/date/{yesterday}"
        
        print(f"Attempting to fetch data from ESPN...")
        print(f"URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"{Colors.GREEN}✅ SUCCESS: ESPN is accessible{Colors.END}")
            print(f"Response status: {response.status_code}")
            print(f"Content length: {len(response.content)} bytes")
            
            # Try to parse some content
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title')
            if title:
                print(f"Page title: {title.get_text()[:50]}...")
            
            return True
        else:
            print(f"{Colors.RED}❌ HTTP Error: {response.status_code}{Colors.END}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ ERROR: {str(e)}{Colors.END}")
        return False

def fetch_october_30_games():
    """Try to fetch actual games from October 30, 2025"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}TEST 3: Fetching October 30, 2025 Games{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    try:
        url = "https://www.espn.com/nba/scoreboard/_/date/20251030"
        print(f"Fetching from: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for game information in various ways
            # ESPN's site structure
            print(f"{Colors.GREEN}✅ Page loaded successfully{Colors.END}\n")
            
            # Try to find any mention of teams
            page_text = soup.get_text()
            
            # Common NBA teams to look for
            nba_teams = ['Lakers', 'Warriors', 'Celtics', 'Heat', 'Mavericks', 
                        'Bucks', 'Clippers', 'Nuggets', 'Suns', 'Grizzlies',
                        'Magic', 'Hornets', 'Thunder', 'Spurs', 'Pacers']
            
            found_teams = []
            for team in nba_teams:
                if team in page_text:
                    found_teams.append(team)
            
            if found_teams:
                print(f"Found mentions of: {', '.join(found_teams[:5])}...")
                print(f"{Colors.GREEN}✅ Games exist for this date{Colors.END}")
            else:
                print(f"{Colors.YELLOW}⚠️  No obvious game data found{Colors.END}")
                
            return True
        else:
            print(f"{Colors.RED}❌ HTTP Error: {response.status_code}{Colors.END}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ ERROR: {str(e)}{Colors.END}")
        return False

def main():
    """Run all diagnostic tests"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}🏀 NBA TRACKING DIAGNOSTIC TOOL 🏀{Colors.END}")
    print(f"{Colors.BOLD}Testing why game results aren't being pulled...{Colors.END}\n")
    
    # Test 1: NBA API
    nba_api_works = test_nba_api()
    
    # Test 2: ESPN Scraping
    espn_works = test_espn_scraping()
    
    # Test 3: Specific date
    games_exist = fetch_october_30_games()
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}DIAGNOSTIC SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    if nba_api_works:
        print(f"{Colors.GREEN}✅ NBA API Method: WORKING{Colors.END}")
        print(f"   Your current script should work as-is\n")
    else:
        print(f"{Colors.RED}❌ NBA API Method: BLOCKED{Colors.END}")
        print(f"   stats.nba.com is not in your allowed domains\n")
    
    if espn_works:
        print(f"{Colors.GREEN}✅ ESPN Scraping Method: AVAILABLE{Colors.END}")
        print(f"   Alternative method can be used\n")
    else:
        print(f"{Colors.RED}❌ ESPN Scraping Method: UNAVAILABLE{Colors.END}\n")
    
    print(f"{Colors.BOLD}RECOMMENDED SOLUTION:{Colors.END}")
    print(f"{Colors.YELLOW}1. Add 'stats.nba.com' to your network allowed domains (preferred){Colors.END}")
    print(f"{Colors.YELLOW}2. Or use the updated script with web scraping fallback{Colors.END}")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")

if __name__ == "__main__":
    main()
