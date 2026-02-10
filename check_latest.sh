#!/bin/bash
# Wrapper to check the latest video from @ReallyRico7
# Usage: ./check_latest.sh

echo "📡 Checking for latest video from @ReallyRico7..."
python3 /Users/rico/Dev/sports-models/nba_props_bot.py --latest

if [ $? -eq 0 ]; then
    echo "✅ Done! Infographic is ready at: ~/.gemini/antigravity/brain/1172207d-238e-4514-92d3-84209a148b77/bot_infographic.html"
    echo "💡 Open it in your browser to screenshot."
else
    echo "❌ Something went wrong."
fi
