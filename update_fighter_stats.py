
import json
import os
import sys
from ufc.ufc_stats_scraper import UFCStatsScraper

def main():
    print("Updating fighter stats for active picks...")
    
    data_dir = "ufc/data"
    picks_file = os.path.join(data_dir, "ufc_picks.json")
    db_file = os.path.join(data_dir, "fighters_db.json")
    
    if not os.path.exists(picks_file) or not os.path.exists(db_file):
        print("Missing data files.")
        return

    with open(picks_file, 'r') as f:
        picks = json.load(f)
        
    with open(db_file, 'r') as f:
        fighters_list = json.load(f)
        
    # Index fighters by Full Name (and maybe last name fallback)
    # The picks have "Fighter Name"
    # The DB has "first", "last"
    
    fighters_map = {}
    for f in fighters_list:
        full_name = f"{f.get('first_name', '')} {f.get('last_name', '')}".strip()
        fighters_map[full_name] = f
        
    scraper = UFCStatsScraper()
    updated_count = 0
    
    # Collect all fighters from picks
    target_fighters = set()
    for p in picks:
        target_fighters.add(p.get('fighter'))
        target_fighters.add(p.get('opponent'))
        
    print(f"Checking stats for {len(target_fighters)} fighters...")
    
    for name in target_fighters:
        if not name: continue
        
        f_obj = fighters_map.get(name)
        if not f_obj:
            # Try fuzzy match or case insensitive?
            # For now skip
            print(f"⚠ Fighter not found in DB: {name}")
            continue
            
        # Check if already has stats AND history
        if 'slpm' in f_obj and 'history' in f_obj:
            # print(f"✓ Stats present for {name}")
            continue
            
        # Scrape
        url = f_obj.get('link')
        if not url:
            print(f"⚠ No link for {name}")
            continue
            
        print(f"Scraping stats for {name}...")
        details = scraper.scrape_fighter_details(url)
        
        if details:
            f_obj.update(details)
            updated_count += 1
            
    if updated_count > 0:
        with open(db_file, 'w') as f:
            json.dump(fighters_list, f, indent=4)
        print(f"Updated {updated_count} fighters in DB.")
    else:
        print("All fighters up to date.")

if __name__ == "__main__":
    main()
