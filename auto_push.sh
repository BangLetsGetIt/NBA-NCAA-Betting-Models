#!/bin/bash

# Auto-commit and push script for sports models
# This runs after each model completes to update GitHub Pages

cd "/Users/rico/sports-models"

# Add all HTML, CSV, and JSON output files (including root dashboards)
git add *.html *.json nba/*.html nba/*.csv ncaa/*.html ncaa/*.csv nfl/*.html nfl/*.json soccer/*.html soccer/*.json nba/*.json ncaa/*.json 2>/dev/null

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Create commit with timestamp
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
git commit -m "Update model outputs - $TIMESTAMP"

# Push to GitHub
# This will only work after you've set up the remote repository
git push origin main 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed to GitHub!"
else
    echo "⚠️  Push failed - you may need to set up the GitHub remote first"
fi
