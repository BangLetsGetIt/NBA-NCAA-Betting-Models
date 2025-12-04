#!/bin/bash

# NBA 3PT Props Model Runner with Auto Git Push
# This script runs the 3PT props model and automatically commits/pushes to GitHub

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "========================================"
echo "NBA 3PT Props Model - Starting"
echo "========================================"

# Run the 3PT props model
python3 nba_3pt_props_model.py

# Check if model ran successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "Model completed successfully"
    echo "Pushing to GitHub..."
    echo "========================================"

    # Change to the repo root
    cd /Users/rico/sports-models

    # Add the 3PT model files
    git add nba/nba_3pt_props.html
    git add nba/nba_3pt_props_tracking.json

    # Check if there are changes to commit
    if git diff --staged --quiet; then
        echo "No changes to commit"
    else
        # Create commit with timestamp
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
        git commit -m "Update 3PT props model - $TIMESTAMP"

        # Push to GitHub
        git push

        if [ $? -eq 0 ]; then
            echo "✓ Successfully pushed to GitHub"
        else
            echo "✗ Failed to push to GitHub"
            exit 1
        fi
    fi
else
    echo "✗ Model execution failed"
    exit 1
fi

echo ""
echo "========================================"
echo "✓ Complete!"
echo "========================================"
