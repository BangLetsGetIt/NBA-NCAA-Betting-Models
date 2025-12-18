#!/bin/bash

# NBA Points Props Model Automation Script
# Runs the points props model with error handling

# Exit on error and make pipe return the exit code of the first failing command
set -e
set -o pipefail

# Set PATH to include Python 3.13 installation
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"

# Navigate to NBA Model folder
cd "/Users/rico/sports-models/nba"

# Create logs directory if it doesn't exist
mkdir -p logs

# Set log file with timestamp
LOG_FILE="logs/nba_points_props_$(date +%Y%m%d_%H%M%S).log"

echo "==========================================" | tee "$LOG_FILE"
echo "NBA Points Props Model Run: $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found!" | tee -a "$LOG_FILE"
    exit 1
fi

# Run the model
echo "Running NBA Points Props model..." | tee -a "$LOG_FILE"
python3 nba_points_props_model.py 2>&1 | tee -a "$LOG_FILE"

# Check exit code
if [ $? -eq 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "✅ Model completed successfully!" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"

    # Auto-push to GitHub
    echo "" | tee -a "$LOG_FILE"
    echo "📤 Pushing updates to GitHub..." | tee -a "$LOG_FILE"
    cd /Users/rico/sports-models && bash auto_push.sh 2>&1 | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "❌ Model failed! Check log above." | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    exit 1
fi
