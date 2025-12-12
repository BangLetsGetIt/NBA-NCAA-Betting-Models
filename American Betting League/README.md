# Dashboard Updater - Usage Guide

## Overview
This script automatically updates your American Betting League dashboard with the biggest gainers from the last two days of data.

## Quick Start

### Auto-Detection Mode (Easiest)
Simply run the script and it will automatically find your dashboard and the two most recent CSV files:

```bash
python3 update_dashboard.py
```

The script will:
- Look for `dashboard.html` in the uploads folder
- Find the two most recent CSV files in the uploads folder
- Calculate the biggest gainers
- Save the updated dashboard to `/mnt/user-data/outputs/dashboard.html`

### Manual Mode
If you want to specify exact files:

```bash
python3 update_dashboard.py <dashboard.html> <older.csv> <newer.csv> [output.html]
```

Example:
```bash
python3 update_dashboard.py dashboard.html 2025-10-28.csv 2025-10-29.csv updated_dashboard.html
```

## Workflow

1. **Upload your files** to the uploads folder:
   - Your current `dashboard.html`
   - Two CSV files (yesterday's and today's data)

2. **Run the script**:
   ```bash
   python3 update_dashboard.py
   ```

3. **Download the updated dashboard** from the outputs folder

## What the Script Does

1. Reads both CSV files
2. Calculates the unit change for each bettor
3. Identifies the top 5 biggest gainers (positive changes only)
4. Updates the "Biggest Risers" section in your dashboard
5. Saves the updated HTML

## Output

The script will show you:
- Which files it's processing
- The top 5 biggest gainers with their unit changes
- Confirmation when the dashboard is updated

Example output:
```
Top 5 Biggest Gainers:
============================================================
1. King Beaver: +18.45 units (-36.14 → -17.69)
2. ANDACTIONBTB: +13.57 units (-19.66 → -6.09)
3. Sean x Juice Room: +5.45 units (-28.92 → -23.47)
4. Stottys Locks: +4.50 units (19.22 → 23.72)
5. Blake Nitty: +4.42 units (-44.61 → -40.19)

✅ Dashboard updated successfully
```

## CSV File Format

The script expects CSV files with these columns:
- `BETTOR`: Bettor name
- `UNIT`: Current unit total

## Troubleshooting

**Error: Could not find two CSV files**
- Make sure you have at least two CSV files in the uploads folder

**Error: dashboard.html not found**
- Upload your dashboard.html file to the uploads folder

**No positive unit changes detected**
- This means no bettors gained units between the two days
- The dashboard will show "No positive unit changes detected"

## Tips

- Name your CSV files with dates (e.g., `2025-10-29.csv`) for easy tracking
- The script only shows **positive** unit gains (biggest risers)
- You can modify the script to show top 10 instead of top 5 by changing the `top_n` parameter
