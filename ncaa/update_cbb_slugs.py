import requests
import json
import os
from bs4 import BeautifulSoup

OUTPUT_FILE = "cbb_team_slugs.json"

def update_slugs():
    print("Fetching active CBB schools list from Sports-Reference...")
    url = "https://www.sports-reference.com/cbb/schools/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"Error: {resp.status_code}")
            return
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        table = soup.find('table', {'id': 'NCAAM_schools'})
        
        if not table:
            print("Could not find schools table")
            return
            
        slugs_map = {}
        
        # Iterate rows
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            if 'class' in row.attrs and 'thead' in row.attrs['class']:
                continue
            # DEBUG
            if len(slugs_map) == 0:
                 print(f"Sample row: {row}")
                
            school_cell = row.find('td', {'data-stat': 'school_name'})
            if not school_cell:
                continue
                
            # Check if active
            to_cell = row.find('td', {'data-stat': 'year_max'})
            if to_cell:
                year_max = to_cell.text.strip()
                if year_max not in ["2025", "2026"]: # Only active teams
                    continue
            
            link = school_cell.find('a')
            if link:
                full_name = link.text.strip()
                href = link['href'] # /cbb/schools/duke/men/
                try:
                    slug = href.split('/schools/')[1].split('/')[0]
                except:
                    slug = href.split('/')[-2] if href.endswith('/') else href.split('/')[-1]
                
                slugs_map[full_name] = slug
                
        print(f"Found {len(slugs_map)} active schools.")
        
        # Save
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(slugs_map, f, indent=2)
        print(f"Saved to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_slugs()
