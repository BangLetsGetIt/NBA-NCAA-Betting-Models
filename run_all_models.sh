#!/bin/bash
# Run All Models - Manual Execution
# Runs NBA, Rebounds, Assists, 3PT, Points, and NCAAB models at once
# Perfect for late-night head starts on picks!

# Set PATH to include Python 3.13 installation
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"

# Don't exit on error - let all models run even if one fails
set +e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🏀 RUNNING ALL MODELS - MANUAL EXECUTION 🏀         ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track timing
START_TIME=$(date +%s)

# Function to run a model with error handling
run_model() {
    local model_name=$1
    local model_path=$2
    local model_dir=$(dirname "$model_path")
    local model_file=$(basename "$model_path")
    local model_start=$(date +%s)
    
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ Running: ${model_name}${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    cd "$SCRIPT_DIR/$model_dir"
    
    if [ ! -f "$model_file" ]; then
        echo -e "${RED}❌ Error: $model_file not found${NC}"
        return 1
    fi
    
    # Run the model
    if python3 "$model_file" 2>&1; then
        local model_end=$(date +%s)
        local model_duration=$((model_end - model_start))
        echo -e "${GREEN}✅ $model_name completed successfully (${model_duration}s)${NC}"
        echo ""
        return 0
    else
        local model_end=$(date +%s)
        local model_duration=$((model_end - model_start))
        echo -e "${RED}❌ $model_name failed (${model_duration}s)${NC}"
        echo ""
        return 1
    fi
}

# Track results
SUCCESS_COUNT=0
FAIL_COUNT=0

# Pre-populate NBA stats caches via shared engine (uses leagueleaders + BDL, avoids stats.nba.com)
echo "Pre-populating NBA stats caches..."
cd "$SCRIPT_DIR/nba"
python3 -c "
from nba_props_shared import NBAPropsEngine
for pt in ['points', 'rebounds', 'assists', 'threes']:
    try:
        e = NBAPropsEngine(pt)
        e.get_player_stats()
        e.get_opponent_factors()
    except Exception as ex:
        print(f'  Cache warm error for {pt}: {ex}')
" 2>&1 || true
cd "$SCRIPT_DIR"

# Run NBA Model
if run_model "NBA Model" "nba/nba_model_IMPROVED.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run Rebounds Model
if run_model "NBA Rebounds Props" "nba/nba_rebounds_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run Assists Model
if run_model "NBA Assists Props" "nba/nba_assists_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run 3PT Model
if run_model "NBA 3PT Props" "nba/nba_3pt_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run Points Model
if run_model "NBA Points Props" "nba/nba_points_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run PRA Combo Model
if run_model "NBA PRA Props" "nba/nba_pra_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run Points+Rebounds Combo Model
if run_model "NBA P+R Props" "nba/nba_points_rebounds_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run Points+Assists Combo Model
if run_model "NBA P+A Props" "nba/nba_points_assists_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run Rebounds+Assists Combo Model
if run_model "NBA R+A Props" "nba/nba_rebounds_assists_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run NCAAB Model
if run_model "NCAAB Model" "ncaa/ncaab_model_2ndFINAL.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run CBB Props Models
if run_model "CBB Points Props" "ncaa/cbb_points_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

if run_model "CBB Rebounds Props" "ncaa/cbb_rebounds_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

if run_model "CBB Assists Props" "ncaa/cbb_assists_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

if run_model "CBB 3PT Props" "ncaa/cbb_3pt_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

if run_model "CBB PRA Props" "ncaa/cbb_pra_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

if run_model "CBB P+R Props" "ncaa/cbb_points_rebounds_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

if run_model "CBB P+A Props" "ncaa/cbb_points_assists_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

if run_model "CBB R+A Props" "ncaa/cbb_rebounds_assists_props_model.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Run UFC Model
if run_model "UFC Model" "ufc/ufc_model_runner.py"; then
    ((SUCCESS_COUNT++))
else
    ((FAIL_COUNT++))
fi

# Calculate total time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Summary
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    📊 EXECUTION SUMMARY                   ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Successful: ${SUCCESS_COUNT}/7${NC}"
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}❌ Failed: ${FAIL_COUNT}/7${NC}"
fi
echo -e "${BLUE}⏱  Total Time: ${MINUTES}m ${SECONDS}s${NC}"
echo ""

# Output file locations
echo -e "${YELLOW}📁 Generated Files:${NC}"
echo "  • NBA: nba/nba_model_output.html"
echo "  • Rebounds: nba/nba_rebounds_props.html"
echo "  • Assists: nba/nba_assists_props.html"
echo "  • 3PT: nba/nba_3pt_props.html"
echo "  • Points: nba/nba_points_props.html"
echo "  • NCAAB: ncaa/ncaab_model_output.html"
echo "  • UFC: ufc/ufc_dashboard.html"
echo ""

# Grade pending picks to ensure fresh data for reports
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}⚖️  Grading Pending Picks...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR"
if python3 auto_grader.py --grade-only 2>&1; then
    echo -e "${GREEN}✅ Auto-grader completed successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Auto-grader had issues (non-critical)${NC}"
    echo ""
fi


# Always generate reports, even if some models failed
# Reports will use whatever data is available from successful models
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Generating Auto-Bet Teams Report...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR"
if python3 generate_auto_bet_report.py 2>&1; then
    echo -e "${GREEN}✅ Auto-Bet Teams Report generated successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Auto-Bet Teams Report generation failed${NC}"
    echo ""
fi

# Generate Best Plays Report
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔥 Generating Best Plays Report...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR"
if python3 best_plays_bot.py 2>&1; then
    echo -e "${GREEN}✅ Best Plays Report generated successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Best Plays Report generation failed${NC}"
    echo ""
fi

# Generate NBA Analysis Report
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Generating NBA Analysis Report...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR/nba"
if python3 generate_nba_analysis_report.py 2>&1; then
    echo -e "${GREEN}✅ NBA Analysis Report generated successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  NBA Analysis Report generation failed${NC}"
    echo ""
fi
cd "$SCRIPT_DIR"

# Generate NCAAB Analysis Report
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Generating NCAAB Analysis Report...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR/ncaa"
if python3 generate_analysis_report.py 2>&1; then
    echo -e "${GREEN}✅ NCAAB Analysis Report generated successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  NCAAB Analysis Report generation failed${NC}"
    echo ""
fi
cd "$SCRIPT_DIR"

# Update Fighter Stats (UFC)
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🥊 Updating UFC Fighter Stats...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if python3 update_fighter_stats.py 2>&1; then
    echo -e "${GREEN}✅ UFC Fighter Stats updated successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  UFC Fighter Stats update failed${NC}"
    echo ""
fi

# Generate UFC Dashboard (Force Update)
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Generating UFC Dashboard...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if python3 generate_ufc_dash.py 2>&1; then
    echo -e "${GREEN}✅ UFC Dashboard generated successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  UFC Dashboard generation failed${NC}"
    echo ""
fi

# Generate Comprehensive Analytics Dashboard (FINAL - aggregates all data)
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Generating Comprehensive Analytics Dashboard...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR"
if python3 generate_analytics_dashboard.py 2>&1; then
    echo -e "${GREEN}✅ Comprehensive Analytics Dashboard generated successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Comprehensive Analytics Dashboard generation failed${NC}"
    echo ""
fi

# Generate Daily Recap
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📅 Generating Daily Recap...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR"
if python3 generate_daily_recap.py 2>&1; then
    echo -e "${GREEN}✅ Daily Recap generated!${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Daily Recap generation failed${NC}"
    echo ""
fi

# Build Parlay Entry
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🎯 Building Parlay Entry...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR"
if python3 parlay_builder.py 2>&1; then
    echo -e "${GREEN}✅ Parlay Entry built successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Parlay Builder had issues (non-critical)${NC}"
    echo ""
fi

# Generate YouTube & Social Content
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📱 Generating YouTube & Social Content...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$SCRIPT_DIR"
if python3 content_generator.py --type all 2>&1; then
    echo -e "${GREEN}✅ Content generated successfully${NC}"
    echo ""
else
    echo -e "${YELLOW}⚠️  Content Generator had issues (non-critical)${NC}"
    echo ""
fi

# Only push to GitHub if at least one model succeeded
if [ $SUCCESS_COUNT -gt 0 ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📤 Pushing updates to GitHub...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    cd "$SCRIPT_DIR"
    if [ -f "auto_push.sh" ]; then
        bash auto_push.sh 2>&1
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✅ Successfully pushed to GitHub!${NC}"
        else
            echo ""
            echo -e "${YELLOW}⚠️  Push to GitHub had issues. You may want to push manually.${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  auto_push.sh not found. Skipping GitHub push.${NC}"
    fi
    
    if [ $FAIL_COUNT -eq 0 ]; then
        echo ""
        echo -e "${GREEN}🎉 All models completed successfully and pushed to GitHub!${NC}"
        exit 0
    else
        echo ""
        echo -e "${YELLOW}⚠️  Some models failed, but successful models were pushed to GitHub.${NC}"
        echo -e "${YELLOW}⚠️  Check errors above for failed models.${NC}"
        exit 1
    fi
else
    echo ""
    echo -e "${RED}❌ All models failed. Skipping GitHub push.${NC}"
    echo -e "${RED}❌ Check errors above and try again.${NC}"
    exit 1
fi


