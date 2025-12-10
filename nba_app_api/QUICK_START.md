# 🚀 Quick Start - Your NBA App API

## ✅ What's Done (Phase 1 Complete!)

Your FastAPI backend is ready! It reads from your existing NBA model without touching it.

### Files Created:
```
nba_app_api/
├── api.py              ← The FastAPI server
├── requirements.txt    ← Dependencies
├── start.sh           ← Quick start script
├── README.md          ← Full documentation
└── QUICK_START.md     ← This file
```

## 🎯 Your Current Model (UNCHANGED)

Your NBA model continues to work exactly as before:
- Run it: `python3 nba/nba_model_IMPROVED.py`
- Outputs: `nba_model_output.html`, `nba_picks_tracking.json`
- **Nothing changed** - this API just reads those files

## 🏃 Run the API Locally

### Option 1: Use the start script
```bash
cd /Users/rico/sports-models/nba_app_api
./start.sh
```

### Option 2: Manual start
```bash
cd /Users/rico/sports-models/nba_app_api
python3 api.py
```

The API will run at `http://localhost:8000`

## 🧪 Test It

### In Your Browser:
1. **Interactive Docs**: http://localhost:8000/docs
   - Try out all endpoints
   - See example responses
   - Test directly in browser

2. **Get Pending Picks**: http://localhost:8000/picks/pending
3. **Get Stats**: http://localhost:8000/stats

### Using curl:
```bash
# Get today's picks
curl http://localhost:8000/picks/pending

# Get just stats
curl http://localhost:8000/stats

# Get all picks
curl http://localhost:8000/picks
```

## 📱 Next Steps for iOS App

Your API returns JSON like this:

```json
{
  "metadata": {
    "win_rate": 60.5,
    "total_picks": 160,
    "wins": 95,
    "losses": 62,
    "total_profit": 25.96,
    "roi": 15.0
  },
  "games": [
    {
      "home_team": "Los Angeles Lakers",
      "away_team": "Boston Celtics",
      "pick_description": "Los Angeles Lakers -4.5",
      "confidence": "High",
      "game_date": "2025-12-09T19:30:00Z",
      "edge": 8.2
    }
  ]
}
```

Perfect for Swift's `Codable`!

## 🌐 Deploy to Render (Free)

### 1. Create a GitHub repo:
```bash
cd /Users/rico/sports-models/nba_app_api
git init
git add .
git commit -m "NBA Analytics API - Phase 1"
gh repo create nba-analytics-api --public --source=. --push
```

### 2. Deploy on Render:
1. Go to [render.com](https://render.com)
2. New + → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. Deploy!

You'll get a URL like: `https://nba-analytics-api.onrender.com`

## 🔄 How to Update

### Update Picks (Run Your Model):
```bash
cd /Users/rico/sports-models
python3 nba/nba_model_IMPROVED.py
```

The API automatically serves the new data!

### Update API Code:
```bash
cd /Users/rico/sports-models/nba_app_api
# Make changes to api.py
# Restart the server (Ctrl+C then ./start.sh)
```

## ⚠️ Important Notes

1. **Run your model first** - The API needs `nba_picks_tracking.json` to exist
2. **API only reads** - Never modifies your model files
3. **Free tier limits** - Render free tier sleeps after 15 min of inactivity
4. **CORS enabled** - Your iOS app can call this API from anywhere

## 🎨 Ready for Phase 2?

Say the word and I'll create:
1. SwiftUI iOS app code
2. Glassmorphism card design
3. RevenueCat integration
4. Performance charts

The API is done - now let's build the app! 🏀
