#!/bin/bash

# Auto-commit and push script for sports models
# This runs after each model completes to update GitHub Pages
# 
# IMPORTANT: This script includes safety measures for iCloud Drive sync issues
# If your repo is in iCloud, files can desync. This script handles that gracefully.

cd "/Users/rico/Dev/sports-models"

# SAFETY: Wait for any iCloud sync to complete (files with .icloud extension)
sync_wait=0
while [ -n "$(find . -name '*.icloud' -maxdepth 3 2>/dev/null | head -1)" ] && [ $sync_wait -lt 30 ]; do
    echo "⏳ Waiting for iCloud sync..."
    sleep 1
    ((sync_wait++))
done

# SAFETY: Pull latest changes before committing to avoid overwriting remote data
echo "📥 Pulling latest changes from remote..."
git stash -q 2>/dev/null  # Stash any uncommitted changes temporarily
git pull --rebase origin main 2>/dev/null || git pull origin main 2>/dev/null
git stash pop -q 2>/dev/null  # Restore stashed changes

# Add all HTML, CSV, and JSON output files (including root dashboards)
git add *.html *.json nba/*.html nba/*.csv ncaa/*.html ncaa/*.csv nfl/*.html nfl/*.json soccer/*.html soccer/*.json nba/*.json ncaa/*.json ufc/*.html ufc/data/*.json 2>/dev/null

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "No changes to commit"
    exit 0
fi

# Create commit with timestamp
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
git commit -m "Update model outputs - $TIMESTAMP"

# Push to GitHub with retry logic
echo "📤 Pushing to GitHub..."
for i in 1 2 3; do
    git push origin main 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Successfully pushed to GitHub!"
        exit 0
    fi
    echo "⚠️  Push attempt $i failed, retrying..."
    git pull --rebase origin main 2>/dev/null
    sleep 2
done

echo "❌ Push failed after 3 attempts - check for conflicts"
exit 1
