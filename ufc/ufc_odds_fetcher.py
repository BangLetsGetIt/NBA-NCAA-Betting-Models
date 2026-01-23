import requests
import os
import json
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

class UFCOddsFetcher:
    API_KEY = os.getenv("ODDS_API_KEY")
    BASE_URL = "https://api.the-odds-api.com/v4/sports"
    SPORT_KEY = "mma_mixed_martial_arts" # Generic MMA key, usually covers UFC
    
    def __init__(self, data_dir="ufc/data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        if not self.API_KEY:
            raise ValueError("ODDS_API_KEY not found in environment variables.")

    def fetch_upcoming_odds(self):
        """Fetches upcoming MMA odds"""
        url = f"{self.BASE_URL}/{self.SPORT_KEY}/odds"
        params = {
            "apiKey": self.API_KEY,
            "regions": "us",
            "markets": "h2h",
            "bookmakers": "hardrockbet,fanDuel,draftKings", # Prioritize Hard Rock
            "oddsFormat": "american"
        }
        
        print(f"Fetching odds from {url}...")
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching odds: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        
        # Filter for UFC events only (API returns all MMA)
        ufc_events = [
            event for event in data 
            if "UFC" in event.get("sport_title", "") or "UFC" in event.get("commence_time", "") # Heuristic check
        ]
        
        # If sport_title assumption is wrong, we might need to inspect 'competition' field if available
        # But 'mma_mixed_martial_arts_ufc' might be a specific key if generic 'mma_mixed_martial_arts' is too broad.
        # Let's save all for now and inspect.
        
        output_file = os.path.join(self.data_dir, "upcoming_odds.json")
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=4)
            
        print(f"Fetched {len(data)} events. Saved to {output_file}")
        return data

if __name__ == "__main__":
    fetcher = UFCOddsFetcher()
    fetcher.fetch_upcoming_odds()
