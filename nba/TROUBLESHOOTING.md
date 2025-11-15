# NBA Model Troubleshooting Guide

## Issue: KeyError 'TEAM_ABBREVIATION'

**Error Message:**
```
KeyError: 'TEAM_ABBREVIATION'
⚠️  Could not fetch advanced stats. Exiting.
```

**Cause:**
The NBA API changed their column names. The old code was looking for 'TEAM_ABBREVIATION' but the API now uses different column names.

**Fix Applied:**
The updated model now:
1. Checks what columns are actually available
2. Uses `.get()` method instead of direct indexing to handle missing columns
3. Uses `TEAM_ID` (most reliable) to match teams between datasets
4. Provides fallback values if columns are missing

---

## Issue: No Data Returned

**Symptoms:**
- "Could not fetch advanced stats"
- Empty dataframes
- 0 teams fetched

**Possible Causes:**

### 1. Season Parameter Incorrect
Check the season parameter in the code:
```python
CURRENT_SEASON = '2025-26'  # Make sure this matches actual NBA season
```

**Fix:** Update to the current NBA season (e.g., '2024-25' if 2025-26 hasn't started)

### 2. NBA API Rate Limiting
The API has rate limits. The code includes delays:
```python
time.sleep(0.6)  # 600ms between requests
```

**Fix:** If you're running the script multiple times quickly, wait a few minutes between runs.

### 3. NBA API Down/Maintenance
Sometimes the stats.nba.com API is unavailable.

**Fix:** 
- Check https://stats.nba.com in your browser
- Try again later
- Use cached data if available

---

## Diagnostic Script

Run this to check what's actually being returned by the API:

```bash
python check_nba_api.py
```

This will show you:
- All available columns
- Sample data from first team
- Which key columns exist
- Whether the API is working

---

## Common Fixes

### Fix 1: Update nba_api Package
```bash
pip install --upgrade nba_api
```

### Fix 2: Clear Cache Files
```bash
rm nba_stats_cache.json
rm nba_home_away_splits_cache.json
```
Then run the model again to fetch fresh data.

### Fix 3: Check Your Internet Connection
The model needs internet to:
- Fetch NBA stats from stats.nba.com
- Fetch odds from The Odds API
- Update game results

### Fix 4: Verify .env File
Make sure your `.env` file exists with:
```
ODDS_API_KEY=your_key_here
```

---

## Error: "Missing stats for team"

**Error Message:**
```
Missing stats for team: Lakers
```

**Cause:**
Team name mismatch between The Odds API and NBA stats API.

**Fix:**
Add the mapping to `TEAM_NAME_MAP` in the script:
```python
TEAM_NAME_MAP = {
    "LA Clippers": "Los Angeles Clippers",
    "Problem Team Name": "Correct NBA API Name",
}
```

---

## Error: No Games Found from Odds API

**Error Message:**
```
⚠️  No games found from The Odds API.
```

**Possible Causes:**

1. **Invalid API Key**
   - Check your .env file
   - Verify key at https://the-odds-api.com/account/

2. **No Games Today/Tomorrow**
   - The API only returns games in the next 48 hours
   - Check NBA schedule

3. **API Rate Limit Exceeded**
   - Each request uses 1 request from your quota
   - Check remaining requests at the-odds-api.com

4. **API Parameter Issue**
   - Sport: `basketball_nba` (correct)
   - Region: `us` (correct)
   - Markets: `h2h,spreads,totals` (correct)

---

## Error: Results Not Updating

**Symptoms:**
- Games finished but still showing "Pending"
- Dashboard not updating

**Possible Causes:**

1. **Game Not Yet Final**
   - NBA API only returns games marked "Final"
   - May take 10-15 minutes after game ends

2. **Team Name Mismatch**
   - Picks logged with one team name
   - Results returned with different team name

**Fix:**
Run the diagnostic script:
```bash
python check_nba_api.py
```

Check team names match between:
- The Odds API (when logging picks)
- NBA API (when updating results)

Add mappings to `TEAM_NAME_MAP` if needed.

---

## Testing the Fix

### Test 1: Fetch Stats
```bash
python check_nba_api.py
```
Should show all columns and sample data.

### Test 2: Run Model
```bash
python nba_model_with_tracking.py
```
Should complete without errors and generate files.

### Test 3: Check Generated Files
```bash
ls -la nba_*.{json,html,csv}
```
Should see:
- nba_model_output.html
- nba_model_output.csv
- nba_picks_tracking.json
- nba_tracking_dashboard.html
- nba_stats_cache.json (if fetched successfully)
- nba_home_away_splits_cache.json (if fetched successfully)

---

## Still Having Issues?

### 1. Check Python Version
```bash
python --version
```
Recommended: Python 3.8 or higher

### 2. Check Package Versions
```bash
pip list | grep -E "nba-api|pandas|requests|jinja2"
```

Should see:
- nba-api (>=1.1.0)
- pandas (>=1.0.0)
- requests (>=2.25.0)
- jinja2 (>=3.0.0)

### 3. Reinstall Packages
```bash
pip uninstall nba-api pandas requests jinja2 -y
pip install nba-api pandas requests jinja2 python-dotenv pytz
```

### 4. Test with Original Model
If the tracking model doesn't work, test with your original `perfect_nba_model`:
```bash
python perfect_nba_model
```

If that works, the issue is specific to the tracking features.
If that fails too, the issue is with the NBA API fetch.

---

## Understanding the Fix

The updated code now does this:

### Old Code (Breaks):
```python
team_name = row['TEAM_NAME']  # Crashes if column doesn't exist
team_abbr = row['TEAM_ABBREVIATION']  # Crashes if column doesn't exist
```

### New Code (Robust):
```python
team_name = row.get('TEAM_NAME', row.get('TEAM_ID', 'Unknown'))
team_id = row.get('TEAM_ID', None)
# Use TEAM_ID to match teams (most reliable)
```

The new code:
1. Uses `.get()` with fallbacks
2. Relies on TEAM_ID (always present)
3. Handles missing columns gracefully
4. Prints available columns for debugging

---

## Quick Reference: File Locations

```
Working Directory/
├── .env                              # Your API key
├── nba_model_with_tracking.py        # Main script
├── check_nba_api.py                  # Diagnostic script
│
├── nba_model_output.html             # Today's predictions
├── nba_tracking_dashboard.html       # Performance tracking
├── nba_model_output.csv              # CSV export
│
├── nba_picks_tracking.json           # Pick database
├── nba_stats_cache.json              # Cached stats (6hr)
└── nba_home_away_splits_cache.json   # Cached splits (6hr)
```

---

## Getting Help

If you've tried everything above and still have issues:

1. Run the diagnostic script and save output:
   ```bash
   python check_nba_api.py > api_check.txt
   ```

2. Check the error message carefully - it often tells you exactly what's wrong

3. Try the NBA API directly in Python:
   ```python
   from nba_api.stats.endpoints import leaguedashteamstats
   stats = leaguedashteamstats.LeagueDashTeamStats(season='2024-25')
   df = stats.get_data_frames()[0]
   print(df.columns)
   print(df.head())
   ```

4. Verify your internet connection and that stats.nba.com is accessible

---

## Prevention

To avoid future issues:

1. **Always keep packages updated:**
   ```bash
   pip install --upgrade nba-api
   ```

2. **Check season parameter:**
   Update `CURRENT_SEASON` when the new season starts

3. **Monitor API status:**
   If NBA API changes, the diagnostic script will show you

4. **Keep cache fresh:**
   Delete cache files if data seems stale (older than 6 hours)

5. **Test after updates:**
   Run diagnostic script after any package updates

---

## Success Indicators

Your model is working correctly when you see:

```
✓ Using cached composite stats (less than 6 hours old)
✓ Using cached home/away splits (less than 6 hours old)
✓ Fetched odds for X games
✅ Analyzed X games with complete odds
✓ CSV saved: nba_model_output.csv
✓ HTML saved: nba_model_output.html
✓ Tracking data saved to nba_picks_tracking.json
✓ Tracking dashboard saved: nba_tracking_dashboard.html
```

And you can open both HTML files in your browser successfully!
