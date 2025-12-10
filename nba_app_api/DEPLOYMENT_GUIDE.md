# 🚀 Complete Deployment Guide - Render.com

## What We're Deploying
Your NBA Analytics API with REAL data from your model. This will give you a public URL like `https://courtside-analytics-api.onrender.com` that your iOS app can use.

---

## ✅ Prerequisites (Check These First)

- [x] GitHub account (create at github.com if needed)
- [x] Render.com account (create at render.com - free tier)
- [x] Your API code is ready in `/Users/rico/sports-models/nba_app_api/`
- [x] Real NBA picks data is copied to this directory

---

## 📦 Step 1: Create GitHub Repository

### 1.1 Create the Repo on GitHub
1. Go to https://github.com/new
2. Repository name: `courtside-analytics-api`
3. Description: "NBA Analytics API Backend"
4. **Important**: Make it **PRIVATE** (your picks data is valuable!)
5. Do NOT initialize with README, .gitignore, or license
6. Click "Create repository"

### 1.2 Push Your Code to GitHub

Open Terminal and run these commands EXACTLY as written:

```bash
cd /Users/rico/sports-models/nba_app_api

# Initialize git repo
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: NBA Analytics API with real data"

# Add your GitHub repo (REPLACE 'YOUR-USERNAME' with your actual GitHub username)
git remote add origin https://github.com/YOUR-USERNAME/courtside-analytics-api.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Note**: When you push, GitHub will ask for your username and password. Use a Personal Access Token instead of password:
- Go to https://github.com/settings/tokens
- Generate new token (classic)
- Select `repo` scope
- Copy the token and use it as your password

---

## 🌐 Step 2: Deploy to Render

### 2.1 Connect GitHub to Render
1. Go to https://dashboard.render.com
2. Click "New +" button (top right)
3. Select "Web Service"
4. Click "Connect GitHub" (or use existing connection)
5. Find and select your `courtside-analytics-api` repository

### 2.2 Configure the Web Service

Fill in these settings EXACTLY:

| Field | Value |
|-------|-------|
| **Name** | `courtside-analytics-api` |
| **Region** | Choose closest to you (e.g., Oregon, Ohio) |
| **Branch** | `main` |
| **Root Directory** | Leave blank |
| **Runtime** | `Docker` |
| **Instance Type** | `Free` |

### 2.3 Advanced Settings (Optional)
Click "Advanced" if you want to set:
- **Auto-Deploy**: `Yes` (recommended - auto-deploys on git push)

### 2.4 Deploy!
1. Click "Create Web Service" button at the bottom
2. Wait 5-10 minutes for deployment
3. You'll see logs streaming as it builds

---

## ✅ Step 3: Verify Deployment

### 3.1 Check Build Logs
Watch the logs. You should see:
```
==> Building...
==> Deploying...
==> Your service is live 🎉
```

### 3.2 Test Your API

Once deployed, you'll get a URL like: `https://courtside-analytics-api.onrender.com`

Test these endpoints in your browser:

1. **Health Check**:
   ```
   https://courtside-analytics-api.onrender.com/
   ```
   Should return: `{"name": "CourtSide Analytics API", "status": "operational", ...}`

2. **Pending Picks**:
   ```
   https://courtside-analytics-api.onrender.com/picks/pending
   ```
   Should return JSON with your NBA picks

3. **Interactive Docs**:
   ```
   https://courtside-analytics-api.onrender.com/docs
   ```
   Should show FastAPI Swagger UI

---

## 📱 Step 4: Connect Your iOS App

### 4.1 Update API URL in Your iOS App

Find the file `Config.swift` in your iOS app and update:

```swift
struct Config {
    // PRODUCTION: Use your Render URL
    static let apiBaseURL = "https://courtside-analytics-api.onrender.com"

    // DEVELOPMENT: Use localhost
    // static let apiBaseURL = "http://localhost:8000"
}
```

### 4.2 Test the App
1. Run your iOS app in Xcode
2. It should now fetch data from your deployed API
3. You should see all your NBA picks in the app!

---

## 🔄 Step 5: Update Data (When Your Model Runs)

Your model updates `nba_picks_tracking.json` daily. To update the deployed API:

### Option A: Manual Update (Simple)
```bash
cd /Users/rico/sports-models/nba_app_api

# Copy latest data
cp ../nba/nba_picks_tracking.json .

# Push to GitHub
git add nba_picks_tracking.json
git commit -m "Update NBA picks data"
git push

# Render will auto-deploy in 2-3 minutes
```

### Option B: Automated Script (Recommended)
Create a file `update_api_data.sh`:

```bash
#!/bin/bash
cd /Users/rico/sports-models/nba_app_api

# Copy latest picks
cp ../nba/nba_picks_tracking.json .

# Check if there are changes
if git diff --quiet nba_picks_tracking.json; then
    echo "No changes to picks data"
    exit 0
fi

# Commit and push
git add nba_picks_tracking.json
git commit -m "Update NBA picks - $(date '+%Y-%m-%d %H:%M')"
git push origin main

echo "✅ API data updated and deployed!"
```

Make it executable:
```bash
chmod +x /Users/rico/sports-models/nba_app_api/update_api_data.sh
```

Run it after your model updates:
```bash
/Users/rico/sports-models/nba_app_api/update_api_data.sh
```

---

## 🆘 Troubleshooting

### Build Fails
**Check Logs**: Look for red error messages in Render dashboard
- Docker errors? Check Dockerfile syntax
- Python errors? Check requirements.txt versions
- File not found? Make sure all files are committed to git

### API Returns 404
**Check file paths**:
```bash
cd /Users/rico/sports-models/nba_app_api
ls -la nba_picks_tracking.json
```
Make sure the file exists and is committed to git.

### API Works But No Data
**Check JSON file**:
```bash
cat nba_picks_tracking.json | head -20
```
Make sure it has valid JSON with picks array.

### Free Tier Sleep
Render's free tier sleeps after 15 minutes of inactivity:
- First request after sleep takes 30-60 seconds
- Consider upgrading to $7/month if this is annoying
- Or add a cron job to ping every 10 minutes

---

## 📊 Monitoring Your API

### Render Dashboard
- Visit https://dashboard.render.com
- Click on your service
- View:
  - Deployment history
  - Logs (live and historical)
  - Metrics (requests, response times)
  - Events

### Check API Health
Create a simple check script `check_api.sh`:
```bash
#!/bin/bash
URL="https://courtside-analytics-api.onrender.com/stats"
echo "Checking API..."
curl -s $URL | python3 -m json.tool
```

---

## 🎯 Next Steps After Deployment

1. ✅ Verify all endpoints work
2. ✅ Test iOS app with production API
3. ✅ Set up automated data updates
4. ✅ Monitor API in Render dashboard
5. 🚀 Continue with iOS app development
6. 🚀 Add RevenueCat subscriptions
7. 🚀 TestFlight beta testing
8. 🚀 App Store submission

---

## 💰 Cost Breakdown

| Service | Free Tier | Paid |
|---------|-----------|------|
| Render Web Service | ✅ Free (750 hrs/month) | $7/month (no sleep) |
| GitHub (Private) | ✅ Free | N/A |
| Total | **$0/month** | $7/month (optional) |

---

## 🔐 Security Notes

1. **Repository is PRIVATE** - Keep it that way!
2. **No API keys in code** - Environment variables only
3. **CORS configured** - Only allow your iOS app domain in production
4. **HTTPS only** - Render provides free SSL

---

## 🏁 Summary Checklist

Before you start:
- [ ] GitHub account created
- [ ] Render account created
- [ ] API tested locally

Deployment:
- [ ] Git repo initialized
- [ ] Code pushed to GitHub
- [ ] Render connected to GitHub
- [ ] Web service created
- [ ] Build successful
- [ ] Endpoints tested
- [ ] iOS app updated with production URL
- [ ] App tested with production API

Post-deployment:
- [ ] Data update process established
- [ ] Monitoring set up
- [ ] Ready to continue iOS development!

---

**You're done! Your NBA Analytics API is now live and accessible worldwide! 🎉**

Your URL: `https://courtside-analytics-api.onrender.com`
