
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'ufc'))
from ufc_stats_scraper import UFCStatsScraper

print("Debugging UFC Scraper for UFC 324...")
scraper = UFCStatsScraper()
url = "http://www.ufcstats.com/event-details/00e11b5c8b7bfeeb"
print(f"Scraping {url}...")
fights = scraper.scrape_event_details(url)
print(f"Found {len(fights)} fights.")
for f in fights:
    print(f"  {f['fighter_1']} vs {f['fighter_2']} ({f['fighter_1_outcome']}/{f['fighter_2_outcome']})")
