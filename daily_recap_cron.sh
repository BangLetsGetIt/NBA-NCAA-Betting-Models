#!/bin/bash

# Navigate to the project directory
cd /Users/rico/Dev/sports-models

# Load environment variables if necessary (e.g. for Python path)
# source ~/.zshrc or ~/.bash_profile if needed, but often cron has limited env.
# It's safer to use full paths.

# execution date is yesterday (we recap games that already played)
DATE=$(date -v-1d +%Y-%m-%d)

# Run the generation script
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 generate_daily_recap.py --date "$DATE" --output "daily_recap_$DATE.html" > "daily_recap_cron_output.log" 2>&1

# Optional: Link latest to index.html or daily_recap.html
cp "daily_recap_$DATE.html" "daily_recap.html"

# Push to GitHub for deployment
git add daily_recap.html "daily_recap_$DATE.html"
git commit -m "Daily recap - $DATE"
git push origin main

echo "Report generated and pushed for $DATE" >> daily_recap_cron.log
