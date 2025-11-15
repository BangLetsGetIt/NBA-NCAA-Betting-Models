#!/bin/bash

# NBA Model Automation Script
# Runs the improved NBA betting model with error handling

# Navigate to NBA Model folder
cd "/Users/rico/sports-models/nba"

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

    # Auto-push to GitHub
    echo "" | tee -a "$LOG_FILE"
    echo "📤 Pushing updates to GitHub..." | tee -a "$LOG_FILE"
    /Users/rico/sports-models/auto_push.sh 2>&1 | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "❌ Model failed! Check log above." | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    exit 1
fi
