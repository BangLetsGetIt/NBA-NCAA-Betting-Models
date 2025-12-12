# ABL Recap Script - Updates Summary

## What Was Fixed

Your `abl_recap.py` script now correctly calculates the **Biggest Risers** based on **unit gains** from the previous day's data stored in your `history` folder.

## Key Changes Made

### 1. **Biggest Risers Logic** (Lines ~190-230)
**OLD BEHAVIOR:**
- Sorted by rank changes first, then unit changes
- Showed anyone with positive rank OR unit changes
- Less clear output

**NEW BEHAVIOR:**
- ✅ **Sorts by unit changes FIRST** (biggest gains at the top)
- ✅ **Only shows POSITIVE unit gains**
- ✅ Adds debug output showing which file it's comparing against
- ✅ Prints top gainers to console for verification

### 2. **HTML Display** (Template section)
**OLD DISPLAY:**
```
🟩 John Doe jumped +5 ranks and gained +10.50 units
```

**NEW DISPLAY:**
```
1. John Doe 🏅
+10.50 units
Rank: +5 positions
[sparkline chart]
```

- Cleaner, more focused on unit gains
- Shows numbered list
- Unit gain is prominent in green
- Rank change shown as secondary info
- Medal emoji (🏅) for huge gains (≥5 units)

## How It Works

1. **Pulls data from Google Sheets** and saves to `history` folder as `YYYY-MM-DD.csv`
2. **Compares today's data** with the most recent previous day's CSV file
3. **Calculates unit changes** for each bettor
4. **Sorts by unit gains** (highest first)
5. **Shows top 5 gainers** in the dashboard

## Expected Console Output

When you run the script, you should see:

```
--- DEBUG: Data *After* Force-Cleaning ---
...

📊 Comparing today's data with: history/2025-10-30.csv

🚀 Top 5 Biggest Unit Gainers:
============================================================
  King Beaver: +18.45 units (-36.14 → -17.69)
  ANDACTIONBTB: +13.57 units (-19.66 → -6.09)
  Sean x Juice Room: +5.45 units (-28.92 → -23.47)
  Stottys Locks: +4.50 units (19.22 → 23.72)
  Blake Nitty: +4.42 units (-44.61 → -40.19)

🎉 Dashboard updated! Open this *exact* file: /path/to/dashboard.html
```

## Requirements

Your `history` folder must contain at least 2 CSV files for the comparison to work. The script will automatically:
- Save today's data as a new CSV
- Compare with the previous day's CSV
- Calculate the differences

## Troubleshooting

**Issue: "No positive unit changes detected"**
- Check that your `history` folder has at least 2 CSV files
- Verify the CSV files have `BETTOR` and `UNIT` columns
- Make sure the bettors' names match exactly between files

**Issue: Script errors when comparing**
- The script now has better error handling and will print warnings
- Check the console output for specific error messages

**Issue: No history folder**
- The script creates it automatically on first run
- First run won't show "Biggest Risers" (needs 2 days of data)

## File Structure

```
your-project/
├── abl_recap.py           ← Your main script (UPDATED)
├── dashboard.html         ← Generated output
├── history/               ← Auto-created
│   ├── 2025-10-28.csv
│   ├── 2025-10-29.csv
│   ├── 2025-10-30.csv
│   └── 2025-10-31.csv
└── images/                ← Screenshots (optional)
    └── screenshot1.png
```

## Next Steps

1. **Download the updated script**: `abl_recap.py`
2. **Replace your old script** with the new version
3. **Run it**: `python3 abl_recap.py`
4. **Check the console** for the debug output
5. **Open dashboard.html** to see the results

The script will now correctly show your biggest unit gainers from the previous day! 🚀
