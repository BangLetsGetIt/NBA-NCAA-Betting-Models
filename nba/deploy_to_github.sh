#!/bin/bash
# Quick Deploy to GitHub Pages
# Run this script to share your dashboard publicly

echo "🚀 NBA Dashboard - GitHub Pages Deployment"
echo "=========================================="
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📝 Initializing git repository..."
    git init
    echo ""
fi

# Check if remote exists
if ! git remote | grep -q "origin"; then
    echo "❓ Enter your GitHub repository URL:"
    echo "   (Format: https://github.com/USERNAME/REPO.git)"
    read -p "URL: " repo_url
    
    git remote add origin "$repo_url"
    echo "✅ Remote added!"
    echo ""
fi

# Add and commit files
echo "📦 Adding files..."
git add nba_tracking_dashboard.html nba_model_output.html
git add nba_model_COMPLETE_WORKING.py
git add *.md

echo "💾 Committing changes..."
git commit -m "Update NBA picks dashboard - $(date '+%Y-%m-%d %H:%M')"

echo "⬆️  Pushing to GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "📍 Next Steps:"
echo ""
echo "1. Go to your GitHub repository"
echo "2. Click 'Settings' tab"
echo "3. Scroll to 'Pages' section"
echo "4. Under 'Source', select 'main' branch"
echo "5. Click 'Save'"
echo ""
echo "Your dashboard will be live at:"
echo "https://YOUR_USERNAME.github.io/YOUR_REPO/nba_tracking_dashboard.html"
echo ""
echo "🔄 To update in the future, just run this script again!"
echo ""
