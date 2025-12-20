#!/bin/bash
# ABL Dashboard Auto-Update Script
# Runs abl_recap.py, updates dashboard, and pushes to GitHub

cd "/Users/rico/sports-models/American Betting League"

echo "============================================================"
echo "ABL Dashboard Update: $(date)"
echo "============================================================"

# Run the dashboard generator
/usr/bin/python3 abl_recap.py

# Check if dashboard was updated
if [ -f "dashboard.html" ]; then
    cd /Users/rico/sports-models
    
    # Add and commit changes
    git add "American Betting League/dashboard.html" "American Betting League/history/"
    
    # Only commit if there are changes
    if git diff --staged --quiet; then
        echo "No changes to commit"
    else
        git commit -m "ABL: Auto-update dashboard $(date '+%Y-%m-%d %H:%M')"
        git push origin main
        echo "✅ Dashboard pushed to GitHub"
    fi
else
    echo "❌ Dashboard generation failed"
fi

echo "============================================================"
