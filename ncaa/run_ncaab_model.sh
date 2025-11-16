#!/bin/bash

# NCAA Basketball Model Automation Script

# Set PATH to include Python 3.13 installation
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"

cd "/Users/rico/sports-models/ncaa"

mkdir -p logs
LOG_FILE="logs/ncaab_model_$(date +%Y%m%d_%H%M%S).log"

echo "==========================================" | tee "$LOG_FILE"
echo "NCAA Model Run: $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!" | tee -a "$LOG_FILE"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found!" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Running NCAA Basketball model..." | tee -a "$LOG_FILE"
python3 ncaab_model_FINAL.py 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "✅ NCAA Model completed successfully!" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"

    # Auto-push to GitHub
    echo "" | tee -a "$LOG_FILE"
    echo "📤 Pushing updates to GitHub..." | tee -a "$LOG_FILE"
    /Users/rico/sports-models/auto_push.sh 2>&1 | tee -a "$LOG_FILE"

    exit 0
else
    echo "" | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    echo "❌ NCAA Model failed! Check log above." | tee -a "$LOG_FILE"
    echo "==========================================" | tee -a "$LOG_FILE"
    exit 1
fi
