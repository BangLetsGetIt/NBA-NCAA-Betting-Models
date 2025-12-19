#!/bin/bash
# Run NBA Models - Manual Execution
# Runs all NBA models: Main, Rebounds, Assists, 3PT, and Points props
# Perfect for running all NBA models at once!

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
echo -e "${BLUE}║     🏀 RUNNING NBA MODELS - MANUAL EXECUTION 🏀         ║${NC}"
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

# Run NBA Model
if run_model "NBA Model" "nba/nba_model_IMPROVED.py"; then
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
echo -e "${GREEN}✅ Successful: ${SUCCESS_COUNT}/6${NC}"
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}❌ Failed: ${FAIL_COUNT}/6${NC}"
fi
echo -e "${BLUE}⏱  Total Time: ${MINUTES}m ${SECONDS}s${NC}"
echo ""

# Output file locations
echo -e "${YELLOW}📁 Generated Files:${NC}"
echo "  • NBA: nba/nba_model_output.html"
echo "  • NCAAB: ncaa/ncaab_model_output.html"
echo "  • Rebounds: nba/nba_rebounds_props.html"
echo "  • Assists: nba/nba_assists_props.html"
echo "  • 3PT: nba/nba_3pt_props.html"
echo "  • Points: nba/nba_points_props.html"
echo ""

if [ $SUCCESS_COUNT -gt 0 ]; then
    if [ $FAIL_COUNT -eq 0 ]; then
        echo -e "${GREEN}🎉 All NBA models completed successfully!${NC}"
    else
        echo -e "${GREEN}✅ ${SUCCESS_COUNT} model(s) completed successfully!${NC}"
        echo -e "${YELLOW}⚠️  ${FAIL_COUNT} model(s) failed. Check errors above.${NC}"
    fi
    echo ""
    
    # Auto-push to GitHub - push successful outputs even if some models failed
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
    
    exit 0
else
    echo -e "${RED}❌ All models failed. No outputs generated.${NC}"
    echo -e "${YELLOW}⚠️  Skipping GitHub push - no successful outputs to push.${NC}"
    exit 1
fi
