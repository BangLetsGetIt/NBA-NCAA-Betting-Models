#!/bin/bash
# Wrapper to run the NBA Props Bot easily
# Usage: ./cheat_sheet.sh "https://youtu.be/..."

if [ -z "$1" ]; then
    echo "❌ Please provide a YouTube URL."
    echo "Usage: ./cheat_sheet.sh \"https://youtube.com/...\""
    exit 1
fi

python3 /Users/rico/sports-models/nba_props_bot.py "$1"
