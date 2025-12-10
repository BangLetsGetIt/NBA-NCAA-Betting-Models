# 🚀 DEPLOY NOW - Quick Start

Everything is ready. Follow these steps EXACTLY.

---

## ⚡ STEP 1: Create GitHub Repository (2 minutes)

1. **Go to**: https://github.com/new

2. **Fill in**:
   - Repository name: `courtside-analytics-api`
   - Description: `NBA Analytics API Backend`
   - **IMPORTANT**: Select **PRIVATE** (keep your picks data secret!)
   - **Do NOT** check any boxes (no README, no .gitignore, no license)

3. **Click**: "Create repository"

4. **Keep this page open** - you'll need the URL in Step 2

---

## ⚡ STEP 2: Push Code to GitHub (1 minute)

Open Terminal and copy/paste these commands ONE BY ONE:

```bash
cd /Users/rico/sports-models/nba_app_api
```

```bash
git init
```

```bash
git add .
```

```bash
git commit -m "Initial commit: NBA Analytics API with real data"
```

**STOP HERE** - Now replace `YOUR-USERNAME` below with your actual GitHub username, then run:

```bash
git remote add origin https://github.com/YOUR-USERNAME/courtside-analytics-api.git
```

```bash
git branch -M main
```

```bash
git push -u origin main
```

**Note**: When prompted for password, use a GitHub Personal Access Token:
- Go to: https://github.com/settings/tokens/new
- Note: "Render deployment"
- Expiration: 90 days (or longer)
- Select scopes: Check `repo` (all repo permissions)
- Click "Generate token"
- **Copy the token** and use it as your password

---

## ⚡ STEP 3: Deploy to Render (5 minutes)

### 3.1 Create Render Account
1. Go to: https://render.com
2. Click "Get Started for Free"
3. Sign up with GitHub (easiest)
4. Authorize Render to access your repositories

### 3.2 Create Web Service
1. Go to: https://dashboard.render.com
2. Click **"New +"** button (top right)
3. Select **"Web Service"**
4. Click **"Connect account"** next to GitHub
5. Find and click **"Connect"** next to `courtside-analytics-api`

### 3.3 Configure Service
Fill in EXACTLY:

```
Name: courtside-analytics-api
Region: Oregon (or closest to you)
Branch: main
Root Directory: (leave blank)
Runtime: Docker
Instance Type: Free
```

### 3.4 Deploy
1. Click **"Create Web Service"** (bottom of page)
2. Wait 5-10 minutes - watch the logs
3. When you see "Your service is live 🎉" - YOU'RE DONE!

---

## ✅ STEP 4: Test Your API (1 minute)

You'll get a URL like: `https://courtside-analytics-api.onrender.com`

**Test it** - Click these links in your browser:

1. **Health check**:
   ```
   https://YOUR-APP-NAME.onrender.com/
   ```
   Should show: `{"name": "CourtSide Analytics API", "status": "operational"}`

2. **Your picks**:
   ```
   https://YOUR-APP-NAME.onrender.com/picks/pending
   ```
   Should show your NBA picks in JSON format

3. **Interactive docs**:
   ```
   https://YOUR-APP-NAME.onrender.com/docs
   ```
   Should show Swagger UI with all endpoints

---

## 🎉 YOU'RE DONE!

Your API is now live at: `https://YOUR-APP-NAME.onrender.com`

---

## 🔄 Update Data Daily (After Your Model Runs)

When your NBA model updates picks, run this script:

```bash
cd /Users/rico/sports-models/nba_app_api
./update_api_data.sh
```

This will:
1. Copy latest picks from `../nba/nba_picks_tracking.json`
2. Commit to git
3. Push to GitHub
4. Trigger automatic Render deployment (takes 2-3 minutes)

---

## 📱 Connect Your iOS App

In your iOS app's `Config.swift`, update:

```swift
static let apiBaseURL = "https://YOUR-APP-NAME.onrender.com"
```

Replace `YOUR-APP-NAME` with your actual Render URL.

---

## 🆘 Need Help?

### Build failed?
- Check the logs in Render dashboard for red errors
- Most common: forgot to push all files to GitHub

### Can't push to GitHub?
- Make sure you're using a Personal Access Token (not password)
- Check token has `repo` permissions

### API returns 404?
- Check that `nba_picks_tracking.json` exists:
  ```bash
  ls -la /Users/rico/sports-models/nba_app_api/nba_picks_tracking.json
  ```

### Still stuck?
- Read the full guide: `DEPLOYMENT_GUIDE.md`
- Check Render docs: https://render.com/docs
- Check build logs in Render dashboard

---

## 📊 What You Just Did

✅ Created a private GitHub repository
✅ Pushed your NBA API code with REAL data
✅ Deployed to Render's free tier
✅ Got a public HTTPS URL for your API
✅ Set up automatic deployments (git push = auto-deploy)

**Total cost: $0/month**

**Time to deploy: ~10 minutes**

---

## 🎯 Next Steps

1. ✅ Test all API endpoints
2. 📱 Update iOS app to use production URL
3. 🧪 Test iOS app with live data
4. 🔄 Automate data updates
5. 🚀 Continue iOS development
6. 💰 Add RevenueCat subscriptions
7. 📲 TestFlight beta
8. 🏆 App Store submission

You're making amazing progress! 🎉
