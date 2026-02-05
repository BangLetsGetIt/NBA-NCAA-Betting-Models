#!/bin/bash

# NBA Model Automation Script
# Runs the improved NBA betting model with error handling

# Exit on error and make pipe return the exit code of the first failing command
set -e
set -o pipefail

# Set PATH to include Python 3.13 installation
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"

# Navigate to NBA Model folder
cd "/Users/rico/Dev/sports-models/nba"

# Create logs directory if it doesn't exist
mkdir -p logs

# Set log file with timestamp
LOG_FILE="logs/nba_model_$(date +%Y%m%d_%H%M%S).log"

echo "==========================================" | tee "$LOG_FILE"
echo "NBA Model Run: $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!" | tee -a "$LOG_FILE"
    echo "Please create .env file with ODDS_API_KEY" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found!" | tee -a "$LOG_FILE"
    exit 1
fi

# Run the model
echo "Running NBA model..." | tee -a "$LOG_FILE"
python3 nba_model_IMPROVED.py 2>&1 | tee -a "$LOG_FILE"

# Check exit code
if [ $? -eq 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "✅ Model completed successfully!" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"

    # Generate Deep Dive Analysis Report
    echo "" | tee -a "$LOG_FILE"
    echo "📊 Updating Analysis Dashboard..." | tee -a "$LOG_FILE"
    python3 generate_nba_analysis_report.py 2>&1 | tee -a "$LOG_FILE"

    # Update Best Plays & Overall Dashboard
    echo "" | tee -a "$LOG_FILE"
    echo "🔥 Updating Best Plays & Analytics..." | tee -a "$LOG_FILE"
    
    # Switch to root directory for bot
    cd "/Users/rico/Dev/sports-models"
    
    # Run bot (using absolute path to log file)
    if python3 best_plays_bot.py 2>&1 | tee -a "nba/$LOG_FILE"; then
        echo "✅ Best Plays updated" | tee -a "nba/$LOG_FILE"
    else
        echo "⚠️ Best Plays update warning" | tee -a "nba/$LOG_FILE"
    fi
    
    # Return to NBA dir
    cd "/Users/rico/Dev/sports-models/nba"

    # Auto-push to GitHub
    echo "" | tee -a "$LOG_FILE"
    echo "📤 Pushing updates to GitHub..." | tee -a "$LOG_FILE"
    /Users/rico/Dev/sports-models/auto_push.sh 2>&1 | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "❌ Model failed! Check log above." | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    exit 1
fi
