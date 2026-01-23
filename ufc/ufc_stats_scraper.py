import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import json
import re

class UFCStatsScraper:
    BASE_URL = "http://www.ufcstats.com/statistics/fighters"
    EVENTS_URL = "http://www.ufcstats.com/statistics/events/completed"
    
    def __init__(self, data_dir="ufc/data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        })

    def clean_text(self, text):
        if text:
            return text.strip()
        return None

    def scrape_all_fighters(self, limit=None):
        """Scrapes all fighters from A-Z"""
        all_fighters = []
        alphabet = "abcdefghijklmnopqrstuvwxyz"
        
        print("Starting fighter scrape...")
        count = 0
        for char in alphabet:
            if limit and count >= limit:
                break
            print(f"Scraping fighters starting with '{char.upper()}'...")
            url = f"{self.BASE_URL}?char={char}&page=all"
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            rows = soup.find_all('tr', class_='b-statistics__table-row')
            # Skip header row
            for row in rows[1:]:
                cols = row.find_all('td')
                if not cols or len(cols) < 10:
                    continue
                
                try:
                    # Basic info
                    first_name = self.clean_text(cols[0].get_text())
                    last_name = self.clean_text(cols[1].get_text())
                    nickname = self.clean_text(cols[2].get_text())
                    height = self.clean_text(cols[3].get_text())
                    weight = self.clean_text(cols[4].get_text())
                    reach = self.clean_text(cols[5].get_text())
                    stance = self.clean_text(cols[6].get_text())
                    w_l_d = self.clean_text(cols[7].get_text())
                    
                    # Link to details
                    link = cols[0].find('a')['href'] if cols[0].find('a') else None
                    
                    fighter_data = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "nickname": nickname,
                        "height": height,
                        "weight": weight,
                        "reach": reach,
                        "stance": stance,
                        "record": w_l_d,
                        "link": link
                    }
                    
                    # Fetch detailed stats (optional, can do lazy loading later)
                    # self.scrape_fighter_details(link, fighter_data)
                    
                    all_fighters.append(fighter_data)
                except Exception as e:
                    print(f"Skipping row due to error: {e}")
                    # print(f"Row content: {row}")
                    continue
            
            count += 1
            time.sleep(1) # Respectful delay

        # Save to JSON
        output_file = os.path.join(self.data_dir, "fighters_db.json")
        with open(output_file, 'w') as f:
            json.dump(all_fighters, f, indent=4)
        
        print(f"Scraped {len(all_fighters)} fighters. Saved to {output_file}")
        return all_fighters

    def scrape_fighter_details(self, url):
        """Fetches advanced stats (SLpM, StrAcc, TD Avg, etc.) from individual profile"""
        if not url:
            return {}
            
        try:
            response = self.session.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # This part needs to be tailored to the specific detailed page structure
            # For now returning placeholder, will implement if 'all fighters' list isn't enough
            pass 
        except Exception as e:
            print(f"Error scraping details for {url}: {e}")
            return {}

    def scrape_completed_events(self):
        """Scrapes list of all completed events and their results"""
        print("Scraping completed events history...")
        response = self.session.get(self.EVENTS_URL + "?page=all")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        rows = soup.find_all('tr', class_='b-statistics__table-row')
        
        # Skip header info usually found in first 2 rows of this specific table structure
        # The structure is usually <table><tbody><tr>(Header)</tr><tr>(Event)</tr>...
        
        for row in rows[1:]: # Skip header
            cols = row.find_all('td')
            if len(cols) < 2:
                continue
                
            try:
                # Event Name & Link
                event_link_tag = cols[0].find('a')
                if not event_link_tag: continue
                
                event_name = self.clean_text(event_link_tag.get_text())
                event_url = event_link_tag['href']
                
                # Date
                event_date = self.clean_text(cols[0].find('span').get_text())
                
                # Location
                location = self.clean_text(cols[1].get_text())
                
                events.append({
                    "name": event_name,
                    "date": event_date,
                    "location": location,
                    "url": event_url
                })
            except Exception as e:
                print(f"Error parsing event row: {e}")
                continue
                
        # Save to JSON
        output_file = os.path.join(self.data_dir, "events_history.json")
        with open(output_file, 'w') as f:
            json.dump(events, f, indent=4)
            
        print(f"Scraped {len(events)} historical events. Saved to {output_file}")
        
        # Now scrape details for these events (limiting to last 50 for now to save time/bandwidth)
        print("Scraping fight results for the last 50 events...")
        all_fights = []
        for event in events[:50]:
            fights = self.scrape_event_details(event['url'])
            # Add event metadata to each fight
            for f in fights:
                f['event_name'] = event['name']
                f['event_date'] = event['date']
            all_fights.extend(fights)
            time.sleep(1)
            
        fights_file = os.path.join(self.data_dir, "historical_fights.json")
        with open(fights_file, 'w') as f:
            json.dump(all_fights, f, indent=4)
            
        return events

    def scrape_event_details(self, event_url):
        """Scrapes all fights on a specific event card"""
        if not event_url: return []
        
        try:
            response = self.session.get(event_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            rows = soup.find_all('tr', class_='b-fight-details__table-row')
            
            fights = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 5: continue
                
                # Winner extraction
                # Look for the verified flag class 'b-flag__text'
                outcomes = cols[0].find_all('i', class_='b-flag__text')
                
                f1_outcome = "?"
                f2_outcome = "?"
                
                if len(outcomes) >= 2:
                    f1_outcome = self.clean_text(outcomes[0].get_text()).lower()
                    f2_outcome = self.clean_text(outcomes[1].get_text()).lower()
                elif len(outcomes) == 1:
                    # If only one flag found, assume it belongs to the first fighter (top one)
                    # This is a heuristic that usually the winner is prioritized or listed first?
                    # Or check text content.
                    text = self.clean_text(outcomes[0].get_text()).lower()
                    f1_outcome = text
                    f2_outcome = "loss" if text == "win" else "win"
                else:
                    # Debug: Print column content to see why no flags found
                    # print(f"No flags found in row. Col0: {cols[0]}")
                    pass 
                
                # NamesMatch names to ensure alignment if needed, but typically:
                # Flag 1 -> Fighter 1
                # Flag 2 -> Fighter 2
                
                # Names
                names = cols[1].find_all('a')
                if len(names) < 2: continue
                fighter_1_name = self.clean_text(names[0].get_text())
                fighter_1_url = names[0]['href']
                fighter_2_name = self.clean_text(names[1].get_text())
                fighter_2_url = names[1]['href']
                
                # Weight class
                weight_class = self.clean_text(cols[6].get_text())
                
                # Method
                method = self.clean_text(cols[7].get_text())
                
                # Round
                round_num = self.clean_text(cols[8].get_text())
                
                fights.append({
                    "fighter_1": " ".join(fighter_1_name.split()),
                    "fighter_2": " ".join(fighter_2_name.split()),
                    "fighter_1_outcome": f1_outcome,
                    "fighter_2_outcome": f2_outcome,
                    "weight_class": weight_class,
                    "method": method,
                    "round": round_num,
                    "fighter_1_url": fighter_1_url,
                    "fighter_2_url": fighter_2_url
                })
                
            return fights
        except Exception as e:
            print(f"Error scraping event {event_url}: {e}")
            return []

if __name__ == "__main__":
    import sys
    scraper = UFCStatsScraper()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "fighters":
            # Run full fighter scrape
            scraper.scrape_all_fighters()
        elif command == "events":
            # Run event scrape
            scraper.scrape_completed_events()
        elif command == "test":
            scraper.scrape_all_fighters(limit=1)
    else:
        # Default behavior if no args (safe default)
        print("Usage: python ufc_stats_scraper.py [fighters|events|test]")
        # scraper.scrape_all_fighters(limit=1)
