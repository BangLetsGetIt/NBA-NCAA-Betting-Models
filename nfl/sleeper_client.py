#!/usr/bin/env python3
import requests
import json
import os
import time
from datetime import datetime, timedelta

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

PLAYER_CACHE_FILE = os.path.join(CACHE_DIR, "sleeper_players.json")
STATS_CACHE_DIR = os.path.join(CACHE_DIR, "stats")
if not os.path.exists(STATS_CACHE_DIR):
    os.makedirs(STATS_CACHE_DIR)

class SleeperClient:
    def __init__(self):
        self.base_url = "https://api.sleeper.app/v1"
        self._players = None

    def _get_all_players(self):
        """Fetch all players and cache them locally for 24 hours."""
        if os.path.exists(PLAYER_CACHE_FILE):
            mtime = os.path.getmtime(PLAYER_CACHE_FILE)
            if datetime.now() - datetime.fromtimestamp(mtime) < timedelta(hours=24):
                with open(PLAYER_CACHE_FILE, 'r') as f:
                    return json.load(f)

        print("Updating Sleeper player cache (this may take a moment)...")
        response = requests.get(f"{self.base_url}/players/nfl")
        if response.status_code == 200:
            players = response.json()
            with open(PLAYER_CACHE_FILE, 'w') as f:
                json.dump(players, f)
            return players
        return {}

    def get_player_id(self, name):
        """Find player ID by name (case-insensitive)."""
        if self._players is None:
            self._players = self._get_all_players()

        normalized_name = name.lower().replace(".", "").replace("'", "").strip()
        
        # Exact match first
        for pid, player in self._players.items():
            full_name = player.get('full_name', '').lower().replace(".", "").replace("'", "").strip()
            if full_name == normalized_name:
                return pid
        
        # Partial match fallback
        for pid, player in self._players.items():
            first = player.get('first_name', '').lower()
            last = player.get('last_name', '').lower()
            if f"{first} {last}".replace(".", "").replace("'", "") == normalized_name:
                return pid
        
        return None

    def get_weekly_stats(self, season_year, week):
        """Fetch stats for a given week."""
        cache_file = os.path.join(STATS_CACHE_DIR, f"nfl_stats_{season_year}_{week}.json")
        
        if os.path.exists(cache_file):
            # Cache hourly during active games
            mtime = os.path.getmtime(cache_file)
            if datetime.now() - datetime.fromtimestamp(mtime) < timedelta(minutes=15):
                with open(cache_file, 'r') as f:
                    return json.load(f)

        url = f"{self.base_url}/stats/nfl/regular/{season_year}/{week}"
        response = requests.get(url)
        if response.status_code == 200:
            stats = response.json()
            with open(cache_file, 'w') as f:
                json.dump(stats, f)
            return stats
        return {}

    def get_player_stat(self, stats, player_id, stat_key):
        """Extract a specific stat for a player."""
        if not stats or not player_id:
            return None
        
        player_stats = stats.get(player_id, {})
        
        # Mapping for common prop keys
        mapping = {
            "passing_yards": "pass_yd",
            "rushing_yards": "rush_yd",
            "receiving_yards": "rec_yd",
            "receptions": "rec",
            "anytime_td": ["rush_td", "rec_td", "pass_td"] # Pass TD usually doesn't count for ATD
        }
        
        sleeper_key = mapping.get(stat_key, stat_key)
        
        if isinstance(sleeper_key, list):
            # Sum up (e.g., for total TDs)
            total = 0
            found = False
            for k in sleeper_key:
                if k in player_stats:
                    total += player_stats[k]
                    found = True
            return float(total) if found else None
            
        return player_stats.get(sleeper_key)

if __name__ == "__main__":
    client = SleeperClient()
    # Test with Joe Burrow (Week 15)
    pid = client.get_player_id("Joe Burrow")
    print(f"Burrow ID: {pid}")
    if pid:
        stats = client.get_weekly_stats(2025, 15)
        yds = client.get_player_stat(stats, pid, "passing_yards")
        print(f"Burrow Pass Yds: {yds}")
