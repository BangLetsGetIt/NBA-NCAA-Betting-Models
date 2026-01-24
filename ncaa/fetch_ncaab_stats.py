"""
Fetch real NCAA basketball team statistics from Sports-Reference
Combines 'Ratings' (for Efficiency) and 'Advanced' (for Pace) tables.
"""
import requests
import pandas as pd
from io import StringIO
import json
import time
import os

def fetch_pace_data(year=2025):
    """
    Fetch Pace data from Advanced Stats page.
    Returns: dict {normalized_school_name: pace_float}
    """
    print("Fetching Pace data from Advanced Stats...")
    url = f'https://www.sports-reference.com/cbb/seasons/men/{year}-advanced-school-stats.html'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    pace_map = {}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Failed to fetch Advanced Stats: {response.status_code}")
            return {}
            
        df_list = pd.read_html(StringIO(response.text))
        if not df_list: return {}
        df = df_list[0]
        
        # Clean columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() for col in df.columns.values]
        df.columns = [col.strip() for col in df.columns]
        
        # Find School and Pace columns
        school_col = next((c for c in df.columns if 'School' in c), None)
        pace_col = next((c for c in df.columns if 'Pace' in c or 'Poss' in c), None)
        
        if not school_col or not pace_col:
            print("Could not identify School or Pace columns in Advanced Stats")
            print(f"Columns: {df.columns}")
            return {}
            
        for _, row in df.iterrows():
            school = str(row[school_col]).strip()
            if school == 'nan' or school == 'School': continue
            
            try:
                pace = float(row[pace_col])
                if 50 < pace < 90:
                    pace_map[school] = pace
            except:
                continue
                
        print(f"✓ Parsed Pace for {len(pace_map)} teams")
        return pace_map
        
    except Exception as e:
        print(f"Error fetching Pace: {e}")
        return {}

def fetch_sports_reference_stats(year=2025):
    """
    Fetch team stats from Sports-Reference (Ratings + Pace)
    Returns dict with team ratings (ORtg, DRtg, pace)
    """
    # 1. Get Pace Map first
    pace_map = fetch_pace_data(year)
    
    # 2. Get Efficiency Ratings
    print(f"Fetching NCAA basketball ratings for {year} season...")

    url = f'https://www.sports-reference.com/cbb/seasons/men/{year}-ratings.html'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # Parse tables
        df_list = pd.read_html(StringIO(response.text))
        if not df_list:
            print("No tables found!")
            return {}

        df = df_list[0]

        # Flatten multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() for col in df.columns.values]

        # Clean up column names
        df.columns = [col.replace('Unnamed:', '').replace('_level_0', '').replace('_level_1', '').strip('_') for col in df.columns]

        print(f"Columns found: {list(df.columns)}")
        
        # Build stats dictionary
        stats_dict = {}

        for _, row in df.iterrows():
            try:
                # Try multiple column name variations
                school = None
                for col in df.columns:
                    if 'School' in col:
                        school = str(row[col]).strip()
                        break

                if not school or school == 'nan' or school == 'School':
                    continue

                # Get offensive and defensive ratings (Adjusted is better)
                ortg = None
                drtg = None

                for col in df.columns:
                    if 'Adjusted_ORtg' in col: 
                         try: ortg = float(row[col])
                         except: pass
                    elif 'ORtg' in col and ortg is None: # Fallback
                         try: ortg = float(row[col]) 
                         except: pass
                         
                    if 'Adjusted_DRtg' in col:
                         try: drtg = float(row[col])
                         except: pass
                    elif 'DRtg' in col and drtg is None:
                         try: drtg = float(row[col])
                         except: pass

                if ortg is None or drtg is None:
                    continue

                # MERGE PACE
                # Try exact match
                pace = pace_map.get(school)
                
                # If no match, try simple fuzzy (remove 'NCAA' suffix etc if needed)
                if pace is None:
                     # Fallback default
                     pace = 68.5

                stats_dict[school] = {
                    "offensive_rating": ortg,
                    "defensive_rating": drtg,
                    "pace": pace,
                    "net_rating": ortg - drtg
                }

            except Exception as e:
                print(f"Error processing row for {school}: {e}")
                continue

        print(f"\n✓ Successfully fetched stats for {len(stats_dict)} teams")
        return stats_dict

    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {}

if __name__ == "__main__":
    stats = fetch_sports_reference_stats(2025)

    if stats:
        # Save to JSON
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, "ncaab_stats_cache.json")
        
        with open(output_file, 'w') as f:
            json.dump({
                "cached_at": pd.Timestamp.now().isoformat(),
                "teams": stats
            }, f, indent=2)

        print(f"\n✓ Stats saved to {output_file}")
        
        # Verify Pace Variance
        paces = [d['pace'] for d in stats.values()]
        print(f"Avg Pace: {sum(paces)/len(paces):.1f}")
        print(f"Unique Pace Values: {len(set(paces))}")
