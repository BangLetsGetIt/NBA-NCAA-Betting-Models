#!/bin/bash
# Update API data from your NBA model and deploy to Render

cd "$(dirname "$0")"

echo "📊 Copying latest NBA picks data..."
cp ../nba/nba_picks_tracking.json .

# Check if there are changes
if git diff --quiet nba_picks_tracking.json 2>/dev/null; then
    echo "✅ No changes to picks data"
    exit 0
fi

echo "📝 Committing changes..."
git add nba_picks_tracking.json
git commit -m "Update NBA picks - $(date '+%Y-%m-%d %H:%M')"

echo "🚀 Pushing to GitHub (will trigger Render deployment)..."
git push origin main

echo ""
echo "✅ API data updated and deployed!"
echo "🌐 Check deployment status: https://dashboard.render.com"
echo "📡 Your API: https://courtside-analytics-api.onrender.com"
