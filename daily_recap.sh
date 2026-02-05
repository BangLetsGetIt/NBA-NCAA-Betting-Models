#!/bin/bash

# Default to today if no date provided
DATE=${1:-$(date -v-1d +%Y-%m-%d)}
OUTPUT="daily_recap_${DATE}.html"

echo "Generating Daily Recap for $DATE..."
python3 generate_daily_recap.py --date "$DATE" --output "$OUTPUT"

if [ -f "$OUTPUT" ]; then
    echo "Report generated at $OUTPUT"
    # Create persistent link
    cp "$OUTPUT" daily_recap.html
    echo "Updated daily_recap.html"
    
    # Open the report (Mac specific)
    open "$OUTPUT"
else
    echo "Failed to generate report."
fi
