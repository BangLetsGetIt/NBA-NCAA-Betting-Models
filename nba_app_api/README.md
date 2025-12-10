# 🏀 CourtSide Analytics API

**Phase 1: Backend Bridge for Your NBA Model App**

This API reads your existing NBA model's output and serves it as clean JSON for your iOS app. **Zero changes to your working model** - this is completely separate.

## 📁 What This Does

- Reads from your existing `nba_picks_tracking.json` file
- Transforms data into clean, iOS-friendly JSON
- Provides multiple endpoints for different use cases
- Calculates performance stats automatically
- Ready to deploy to Render/Railway

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /Users/rico/sports-models/nba_app_api
pip3 install -r requirements.txt
```

### 2. Run Locally

```bash
python3 api.py
```

The API will start at `http://localhost:8000`

### 3. View Interactive Docs

Open your browser to `http://localhost:8000/docs` to see:
- All available endpoints
- Try them out interactively
- See example responses

## 📡 API Endpoints

### Get All Picks
```
GET /picks
```
Returns all picks (pending + completed) with full performance stats.

**Example Response:**
```json
{
  "metadata": {
    "win_rate": 60.5,
    "total_picks": 160,
    "wins": 95,
    "losses": 62,
    "pushes": 3,
    "total_profit": 25.96,
    "roi": 15.0,
    "spread_record": "49-30-2",
    "total_record": "46-32-1",
    "last_updated": "2025-12-09 07:00 PM ET"
  },
  "games": [
    {
      "home_team": "Los Angeles Lakers",
      "away_team": "Boston Celtics",
      "matchup": "Boston Celtics @ Los Angeles Lakers",
      "game_date": "2025-12-09T19:30:00Z",
      "pick_type": "Spread",
      "pick_description": "Los Angeles Lakers -4.5",
      "market_line": -4.5,
      "model_line": -7.2,
      "edge": 2.7,
      "odds": -110,
      "confidence": "Medium",
      "status": "pending",
      "result": null,
      "profit_loss": null
    }
  ]
}
```

### Get Pending Picks Only
```
GET /picks/pending
```
Perfect for "Today's Picks" screen in your app.

### Get Completed Picks
```
GET /picks/completed
```
Use this for your "History" or "Transparency" tab.

### Get Stats Only
```
GET /stats
```
Lightweight endpoint for dashboard widgets.

## 🎯 App Store Compliance

The API uses **App Store-safe terminology**:
- "Projection" instead of "Bet"
- "Model Accuracy" instead of "Winnings"
- "Analytics" instead of "Gambling"

## 🌐 Deploy to Render (Free Tier)

### 1. Push to GitHub

```bash
cd /Users/rico/sports-models/nba_app_api
git init
git add .
git commit -m "Initial commit - NBA Analytics API"
gh repo create nba-analytics-api --public --source=. --push
```

### 2. Connect to Render

1. Go to [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repo
4. Settings:
   - **Name**: `nba-analytics-api`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. Click "Create Web Service"

### 3. Your API is Live!

You'll get a URL like: `https://nba-analytics-api.onrender.com`

## 📱 Connect to iOS App

In your Swift app, use this URL:

```swift
let apiURL = "https://nba-analytics-api.onrender.com/picks/pending"
```

## 🔄 How It Updates

**Important:** This API reads from your existing model's output files. To get fresh picks:

1. Run your NBA model as normal: `python3 nba/nba_model_IMPROVED.py`
2. Your model updates `nba_picks_tracking.json`
3. The API automatically serves the new data

The API **never modifies** your model files - it only reads them.

## 🧪 Test Your API

### Using curl:
```bash
curl http://localhost:8000/picks/pending
```

### Using browser:
Just open `http://localhost:8000/picks` in your browser!

## 📊 Next Steps

Now that you have the API (Phase 1), you can:

1. **Phase 2**: Build the SwiftUI iOS app
2. **Phase 3**: Add RevenueCat for subscriptions
3. **Phase 4**: Add transparency charts
4. **Phase 5**: Submit to App Store

## 🛠️ Troubleshooting

**Q: API returns 404 "Model data not found"**
A: Run your NBA model first to generate `nba_picks_tracking.json`

**Q: Old data showing in API**
A: Run your NBA model again to refresh the tracking file

**Q: How do I update picks on Render?**
A: Set up a cron job or GitHub Action to run your model daily, then sync the JSON file to Render

## 📖 Documentation

Full API docs available at `/docs` when server is running.

---

**Ready for Phase 2?** Let me know and I'll create the SwiftUI code for the iOS app! 🚀
