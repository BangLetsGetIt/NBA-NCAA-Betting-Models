#!/bin/bash

# NFL Models Runner
# Runs all NFL models including props and main model

echo "=========================================="
echo "🏈 Running All NFL Models"
echo "=========================================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NFL_DIR="$SCRIPT_DIR/nfl"

# Change to NFL directory
cd "$NFL_DIR" || exit 1

# Track start time
START_TIME=$(date +%s)

# Fetch latest player stats
echo "📊 Fetching latest NFL player stats..."
python3 fetch_nfl_player_stats.py
FETCHER_EXIT=$?
if [ $FETCHER_EXIT -ne 0 ]; then
    echo "⚠️  Stats fetching had errors (using cached data)"
fi

echo ""
echo "----------------------------------------"
echo ""

# Run NFL main model
echo "📊 Running NFL Main Model..."
python3 nfl_model_IMPROVED.py
MAIN_EXIT=$?

if [ $MAIN_EXIT -ne 0 ]; then
    echo "⚠️  NFL Main Model had errors (exit code: $MAIN_EXIT)"
fi

echo ""
echo "----------------------------------------"
echo ""

# Run NFL Receptions Props Model
echo "📊 Running NFL Receptions Props Model..."
python3 nfl_receptions_props_model.py
REC_EXIT=$?

if [ $REC_EXIT -ne 0 ]; then
    echo "⚠️  NFL Receptions Props Model had errors (exit code: $REC_EXIT)"
fi

echo ""
echo "----------------------------------------"
echo ""

# Run NFL Rushing Yards Props Model
echo "📊 Running NFL Rushing Yards Props Model..."
python3 nfl_rushing_yards_props_model.py
RUSH_EXIT=$?

if [ $RUSH_EXIT -ne 0 ]; then
    echo "⚠️  NFL Rushing Yards Props Model had errors (exit code: $RUSH_EXIT)"
fi

echo ""
echo "----------------------------------------"
echo ""


# Run NFL Receiving Yards Props Model
echo "📊 Running NFL Receiving Yards Props Model..."
python3 nfl_receiving_yards_props_model.py
REC_YDS_EXIT=$?

if [ $REC_YDS_EXIT -ne 0 ]; then
    echo "⚠️  NFL Receiving Yards Props Model had errors (exit code: $REC_YDS_EXIT)"
fi

echo ""
echo "----------------------------------------"
echo ""

# Run NFL Passing Yards Props Model
echo "📊 Running NFL Passing Yards Props Model..."
python3 nfl_passing_yards_props_model.py
PASS_YDS_EXIT=$?

if [ $PASS_YDS_EXIT -ne 0 ]; then
    echo "⚠️  NFL Passing Yards Props Model had errors (exit code: $PASS_YDS_EXIT)"
fi

echo ""
echo "----------------------------------------"
echo ""

# Run NFL Anytime TD Model
echo "📊 Running NFL Anytime TD Model..."
python3 atd_model.py
ATD_EXIT=$?

if [ $ATD_EXIT -ne 0 ]; then
    echo "⚠️  NFL Anytime TD Model had errors (exit code: $ATD_EXIT)"
fi
echo ""
echo "=========================================="
echo "✅ NFL Models Execution Complete"
echo "=========================================="

# Calculate total time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

echo ""
echo "⏱️  Total execution time: ${MINUTES}m ${SECONDS}s"
echo ""

# Summary
echo "📋 Execution Summary:"
echo "  • NFL Main Model: $([ $MAIN_EXIT -eq 0 ] && echo '✅' || echo '❌')"
echo "  • Receptions Props: $([ $REC_EXIT -eq 0 ] && echo '✅' || echo '❌')"
echo "  • Rushing Yards Props: $([ $RUSH_EXIT -eq 0 ] && echo '✅' || echo '❌')"
echo "  • Receiving Yards Props: $([ $REC_YDS_EXIT -eq 0 ] && echo '✅' || echo '❌')"
echo "  • Passing Yards Props: $([ $PASS_YDS_EXIT -eq 0 ] && echo '✅' || echo '❌')"
echo "  • Anytime TD Props: $([ $ATD_EXIT -eq 0 ] && echo '✅' || echo '❌')"
echo ""

# Exit with error if any model failed
if [ $MAIN_EXIT -ne 0 ] || [ $REC_EXIT -ne 0 ] || [ $RUSH_EXIT -ne 0 ] || [ $REC_YDS_EXIT -ne 0 ] || [ $PASS_YDS_EXIT -ne 0 ] || [ $ATD_EXIT -ne 0 ]; then
    exit 1
fi

# Auto-push to GitHub if all models succeeded
echo ""
echo "=========================================="
echo "📤 Pushing updates to GitHub..."
echo "=========================================="
cd "$SCRIPT_DIR"
if [ -f "auto_push.sh" ]; then
    bash auto_push.sh
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Successfully pushed to GitHub!"
    else
        echo ""
        echo "⚠️  Push to GitHub had issues. You may want to push manually."
    fi
fi

exit 0

