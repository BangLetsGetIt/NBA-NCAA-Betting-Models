================================================================================
🚀 YOUR NBA ANALYTICS API - READY TO DEPLOY
================================================================================

EVERYTHING IS READY. Your API has:
✅ Real NBA picks data (103KB of picks)
✅ FastAPI backend code
✅ Docker configuration for Render
✅ .gitignore for clean commits
✅ Auto-update script

FILES IN THIS DIRECTORY:
📄 DEPLOY_NOW.md          ← START HERE! Quick deployment steps
📄 DEPLOYMENT_GUIDE.md    ← Full detailed guide with troubleshooting
📄 api.py                 ← Your FastAPI application
📄 Dockerfile             ← Docker configuration for Render
📄 render.yaml            ← Render service configuration
📄 requirements.txt       ← Python dependencies
📄 nba_picks_tracking.json ← YOUR REAL NBA PICKS DATA
📄 update_api_data.sh     ← Script to update data after model runs

================================================================================
⚡ QUICK START (10 minutes total)
================================================================================

1. CREATE GITHUB REPO (2 min)
   → Go to: https://github.com/new
   → Name: courtside-analytics-api
   → Make it PRIVATE
   → Do NOT check any boxes
   → Click "Create repository"

2. PUSH CODE (1 min)
   → Open Terminal
   → Run:
     cd /Users/rico/sports-models/nba_app_api
     git init
     git add .
     git commit -m "Initial commit: NBA Analytics API"
     git remote add origin https://github.com/YOUR-USERNAME/courtside-analytics-api.git
     git branch -M main
     git push -u origin main

   (Replace YOUR-USERNAME with your actual GitHub username)

3. DEPLOY TO RENDER (5 min)
   → Go to: https://dashboard.render.com
   → Click "New +" → "Web Service"
   → Connect your GitHub repo
   → Settings:
     Name: courtside-analytics-api
     Runtime: Docker
     Instance: Free
   → Click "Create Web Service"
   → Wait for deployment (5-10 min)

4. TEST IT (1 min)
   → Open: https://YOUR-APP-NAME.onrender.com/docs
   → Should see your API documentation
   → Try: /picks/pending endpoint
   → Should see your NBA picks!

================================================================================
🔄 DAILY UPDATES (After your NBA model runs)
================================================================================

Run this script to update your deployed API with latest picks:

  cd /Users/rico/sports-models/nba_app_api
  ./update_api_data.sh

This will:
  1. Copy latest picks from ../nba/nba_picks_tracking.json
  2. Commit to git
  3. Push to GitHub
  4. Auto-deploy to Render (takes 2-3 minutes)

================================================================================
📱 CONNECT YOUR iOS APP
================================================================================

After deployment, update your iOS app's Config.swift:

  static let apiBaseURL = "https://YOUR-APP-NAME.onrender.com"

Then rebuild your app and it will fetch data from your live API!

================================================================================
💰 COST
================================================================================

GitHub (private repo):  FREE
Render (web service):   FREE (750 hrs/month, sleeps after 15 min inactivity)
Total:                  $0/month

Optional upgrade: $7/month for no sleep + better performance

================================================================================
🆘 HELP & TROUBLESHOOTING
================================================================================

Can't push to GitHub?
  → Use Personal Access Token instead of password
  → Generate at: https://github.com/settings/tokens/new
  → Select 'repo' scope

Build failed on Render?
  → Check logs in Render dashboard
  → Look for red error messages
  → Most common: files not committed to git

API works but no data?
  → Check nba_picks_tracking.json exists and has data
  → Run: cat nba_picks_tracking.json | head -20

More help:
  → Read DEPLOY_NOW.md for step-by-step guide
  → Read DEPLOYMENT_GUIDE.md for detailed troubleshooting

================================================================================
🎯 YOU'RE SO CLOSE!
================================================================================

Your model is running daily ✅
Your API code is ready ✅
Your data is included ✅
Your documentation is complete ✅

Just follow DEPLOY_NOW.md and you'll have a live API in 10 minutes!

Let's finish this! 🚀
================================================================================
