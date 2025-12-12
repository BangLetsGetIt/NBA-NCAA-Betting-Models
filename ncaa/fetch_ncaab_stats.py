"""
Fetch real NCAA basketball team statistics from Sports-Reference
"""
import requests
import pandas as pd
from io import StringIO
import json
import time

def fetch_sports_reference_stats(year=2025):
    """
    Fetch team stats from Sports-Reference
    Returns dict with team ratings (ORtg, DRtg, tempo/pace equivalent)
    """
    print(f"Fetching NCAA basketball stats for {year} season...")

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
        print(f"\nSample data:")
        print(df.head(3))

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

                # Get offensive and defensive ratings
                ortg = None
                drtg = None

                for col in df.columns:
                    if 'ORtg' in col and ortg is None:
                        ortg = float(row[col])
                    if 'DRtg' in col and drtg is None:
                        drtg = float(row[col])

                if ortg is None or drtg is None:
                    continue

                # Estimate pace (college basketball averages ~70 possessions/game)
                # We'll use a baseline of 70 since Sports-Reference doesn't provide tempo
                pace = 70.0

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
        output_file = "ncaab_stats_cache.json"
        with open(output_file, 'w') as f:
            json.dump({
                "cached_at": pd.Timestamp.now().isoformat(),
                "teams": stats
            }, f, indent=2)

        print(f"\n✓ Stats saved to {output_file}")
        print(f"\nSample teams:")
        for i, (team, data) in enumerate(list(stats.items())[:5]):
            print(f"  {team}: ORtg={data['offensive_rating']:.1f}, DRtg={data['defensive_rating']:.1f}, Net={data['net_rating']:.1f}")
