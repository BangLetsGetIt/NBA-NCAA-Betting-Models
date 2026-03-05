
import os
import json
import requests
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path, override=True)

# Constants
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cbb_odds_cache.json")
CACHE_DURATION_MINUTES = 45  # Cache for 45 minutes
API_KEY = os.getenv("ODDS_API_KEY")

class CBBOddsClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or API_KEY
        self.base_url = "https://api.the-odds-api.com/v4/sports/basketball_ncaab"

    def get_odds_data(self, markets=None):
        """
        Get odds data for specified markets.
        First checks cache, then fetches from API if stale/missing.

        Args:
            markets (list): List of markets to fetch (e.g. ['player_points', 'player_assists'])
                            If None, defaults to all props markets.

        Returns:
            list: List of odds objects (one per game)
        """
        if markets is None:
            markets = [
                "player_points", "player_assists", "player_rebounds",
                "player_points_rebounds_assists", "player_points_rebounds",
                "player_points_assists", "player_rebounds_assists",
                "player_threes"
            ]

        # Check cache
        cached_data = self._load_cache()
        if cached_data:
            print(f"  ✓ Using cached CBB odds data ({self._get_cache_age(cached_data)} mins old)")
            return cached_data

        # Fetch from API
        print(f"  ⚡ Cache stale or missing. Fetching fresh CBB data from API...")
        return self._fetch_from_api(markets)

    def _load_cache(self):
        """Load data from cache if valid."""
        if not os.path.exists(CACHE_FILE):
            return None

        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)

            timestamp = data.get('timestamp')
            if not timestamp:
                return None

            # Check age
            cache_time = datetime.fromisoformat(timestamp)
            if datetime.now() - cache_time < timedelta(minutes=CACHE_DURATION_MINUTES):
                return data.get('games', [])

            return None
        except Exception as e:
            print(f"  ⚠ Error reading cache: {e}")
            return None

    def _get_cache_age(self, data):
        """Get age of cached data in minutes."""
        try:
            with open(CACHE_FILE, 'r') as f:
                wrapper = json.load(f)
            timestamp = wrapper.get('timestamp')
            cache_time = datetime.fromisoformat(timestamp)
            age = datetime.now() - cache_time
            return int(age.total_seconds() / 60)
        except:
            return 0

    def _fetch_from_api(self, markets):
        """Fetch fresh data from The Odds API."""
        if not self.api_key:
            print("  ✗ Missing API Key")
            return []

        # 1. Fetch Events
        events_url = f"{self.base_url}/events"

        try:
            resp = requests.get(events_url, params={"apiKey": self.api_key}, timeout=10)
            if resp.status_code != 200:
                print(f"  ✗ API Error (Events) {resp.status_code}: {resp.text}")
                return []

            events = resp.json()

            # Check headers for quota
            remaining = resp.headers.get('x-requests-remaining', '?')
            print(f"  ℹ API Requests Remaining: {remaining}")

        except Exception as e:
            print(f"  ✗ Network Error (Events): {e}")
            return []

        # Filter upcoming (next 36 hours)
        upcoming_events = []
        now_utc = datetime.now(timezone.utc)
        for event in events:
            try:
                commence_time = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
                # Include games in next 36 hours
                if now_utc <= commence_time <= now_utc + timedelta(hours=36):
                    upcoming_events.append(event)
            except:
                continue

        print(f"  Found {len(upcoming_events)} upcoming CBB games (next 36h)")

        # 2. Fetch Odds for each game (limit to 15 games)
        games_data = []
        markets_str = ",".join(markets)

        for i, event in enumerate(upcoming_events[:15], 1):
            event_id = event['id']
            # Fetch odds with ALL markets at once
            odds_url = f"{self.base_url}/events/{event_id}/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "us,us2",
                "markets": markets_str,
                "oddsFormat": "american"
            }

            try:
                # Add delay to be nice to API
                time.sleep(0.5)
                resp = requests.get(odds_url, params=params, timeout=15)

                if resp.status_code == 200:
                    game_odds = resp.json()
                    games_data.append(game_odds)
                    print(f"  ✓ Fetched odds for {event['away_team']} @ {event['home_team']}")
                else:
                    print(f"  ⚠ Failed to fetch odds for game {event_id}: {resp.status_code}")

            except Exception as e:
                print(f"  ⚠ Error fetching game {event_id}: {e}")

        # 3. Save to Cache
        if games_data:
            self._save_cache(games_data)

        return games_data

    def _save_cache(self, games_data):
        """Save data to cache file."""
        wrapper = {
            "timestamp": datetime.now().isoformat(),
            "games": games_data
        }
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(wrapper, f, indent=2)
            print(f"  ✓ Saved {len(games_data)} CBB games to cache: {CACHE_FILE}")
        except Exception as e:
            print(f"  ⚠ Failed to save cache: {e}")

# Simple test if run directly
if __name__ == "__main__":
    client = CBBOddsClient()
    data = client.get_odds_data()
    print(f"Retrieved {len(data)} CBB games")
