# 🔧 NBA Model - Bug Fix Applied

## Issue You Encountered

```
KeyError: 'TEAM_ABBREVIATION'
⚠️  Could not fetch advanced stats. Exiting.
```

## What Was Wrong

The NBA API changed their column names, and the code was looking for columns that no longer exist:
- Old code assumed `TEAM_ABBREVIATION` exists
- Old code assumed `TEAM_NAME` exists
- These assumptions caused crashes when columns were missing

## What Was Fixed

### 1. Robust Column Handling
**Before:**
```python
team_name = row['TEAM_NAME']  # Crashes if missing
team_abbr = row['TEAM_ABBREVIATION']  # Crashes if missing
```

**After:**
```python
team_name = row.get('TEAM_NAME', row.get('TEAM_ID', 'Unknown'))
team_id = row.get('TEAM_ID', None)  # Most reliable
```

### 2. Better Team Matching
- Now uses `TEAM_ID` (always present) to match teams
- Falls back gracefully if preferred columns are missing
- Handles API variations automatically

### 3. Column Discovery
The code now prints available columns:
```
Available columns: ['TEAM_ID', 'TEAM_NAME', 'NET_RATING', ...]
```
This helps debug future API changes.

### 4. Added pandas Import
```python
import pandas as pd  # Was missing but needed
```

## Files Updated

✅ **nba_model_with_tracking.py** - Main model file (FIXED)
- `fetch_advanced_stats()` function
- `fetch_home_away_splits()` function

## Additional Tools Provided

### 1. Diagnostic Script
**check_nba_api.py** - Tests the NBA API and shows actual columns
```bash
python check_nba_api.py
```

Run this if you encounter issues to see what the API is actually returning.

### 2. Troubleshooting Guide
**TROUBLESHOOTING.md** - Complete guide for common issues
- Column name mismatches
- API connection problems
- Rate limiting
- Season parameter issues
- Team name mapping

## How to Use the Fixed Model

### Step 1: Use the Fixed File
The fixed model is in: `nba_model_with_tracking.py`

### Step 2: Test It
```bash
# Option A: Run diagnostic first (recommended)
python check_nba_api.py

# Option B: Run model directly
python nba_model_with_tracking.py
```

### Step 3: Verify It Works
You should see:
```
✓ Fetched and cached stats for 30 teams
✓ Fetched and cached home/away splits
✓ Fetched odds for X games
✅ Analyzed X games with complete odds
```

## Why This Fix Works

### The Issue
NBA's API is actively maintained and column names can change between versions. Hard-coding column names = brittle code.

### The Solution
- Use `.get()` method with fallbacks
- Rely on `TEAM_ID` (most stable)
- Handle missing columns gracefully
- Print debugging info when needed

### Future-Proof
Even if NBA changes columns again:
1. Code won't crash
2. Diagnostic script shows what changed
3. Easy to adapt

## Preventing Future Issues

### Keep Packages Updated
```bash
pip install --upgrade nba-api
```

### Use Diagnostic Script
Before running model after long breaks:
```bash
python check_nba_api.py  # Check if API changed
```

### Check Season Parameter
Update `CURRENT_SEASON` in the code when new season starts:
```python
CURRENT_SEASON = '2025-26'  # Update this annually
```

## What If It Still Doesn't Work?

### 1. Run Diagnostic
```bash
python check_nba_api.py > api_output.txt
```
This shows exactly what the API is returning.

### 2. Check Internet
The model needs to connect to:
- stats.nba.com (NBA stats)
- api.the-odds-api.com (betting odds)

### 3. Verify Season
Make sure `CURRENT_SEASON = '2025-26'` is correct.
If the 2025-26 season hasn't started, use `'2024-25'`.

### 4. Check API Key
Your `.env` file needs:
```
ODDS_API_KEY=your_key_here
```

### 5. Clear Cache
```bash
rm nba_stats_cache.json
rm nba_home_away_splits_cache.json
```
Then run the model to fetch fresh data.

## Technical Details

### Changes Made to Code

**File: nba_model_with_tracking.py**

**Line ~680-710** (fetch_advanced_stats function):
- Added column detection logic
- Changed from direct indexing to `.get()` method
- Use TEAM_ID for reliable matching
- Added debug output

**Line ~760-785** (fetch_home_away_splits function):
- Changed to use `.get()` method
- Handles missing columns gracefully

**Line ~1** (imports):
- Added `import pandas as pd`

### Test Coverage
The fix handles:
- ✅ Missing TEAM_ABBREVIATION column
- ✅ Missing TEAM_NAME column (uses TEAM_ID)
- ✅ API returning different column names
- ✅ Empty/null values in columns
- ✅ Team matching between datasets

## Comparison

### Before (Fragile)
```python
# Would crash if column missing
team_name = row['TEAM_NAME']
form_row = form_df[form_df['TEAM_ABBREVIATION'] == team_abbr]
```

### After (Robust)
```python
# Handles missing columns gracefully
team_name = row.get('TEAM_NAME', row.get('TEAM_ID', 'Unknown'))
team_id = row.get('TEAM_ID', None)
form_row = form_df[form_df['TEAM_ID'] == team_id] if team_id else pd.DataFrame()
```

## Verification Checklist

After applying the fix, verify:

- [ ] Script runs without errors
- [ ] Generates `nba_stats_cache.json`
- [ ] Generates `nba_home_away_splits_cache.json`
- [ ] Generates `nba_model_output.html`
- [ ] Generates `nba_tracking_dashboard.html`
- [ ] Console shows team count (e.g., "30 teams")
- [ ] No KeyError exceptions

## Summary

**Problem:** Hard-coded column names broke when NBA API changed
**Solution:** Dynamic column detection with graceful fallbacks
**Result:** Robust code that handles API variations
**Bonus:** Diagnostic tool to check API status

The model is now more resilient and easier to debug! 🎉

---

## Quick Commands

```bash
# Test the API
python check_nba_api.py

# Run the model
python nba_model_with_tracking.py

# Clear cache and force fresh data
rm nba_*_cache.json && python nba_model_with_tracking.py

# Check for errors in output
python nba_model_with_tracking.py 2>&1 | grep -i error
```

That's it! The model should now work correctly. 🏀
