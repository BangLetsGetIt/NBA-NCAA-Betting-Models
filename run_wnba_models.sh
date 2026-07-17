#!/bin/bash
# Run WNBA Models - Manual Execution

export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"
set +e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     🏀 RUNNING WNBA MODELS - MANUAL EXECUTION 🏀        ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

START_TIME=$(date +%s)

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
    if python3 "$model_file" 2>&1; then
        local dur=$(( $(date +%s) - model_start ))
        echo -e "${GREEN}✅ $model_name completed (${dur}s)${NC}"
        echo ""
        cd "$SCRIPT_DIR"
        return 0
    else
        local dur=$(( $(date +%s) - model_start ))
        echo -e "${RED}❌ $model_name failed (${dur}s)${NC}"
        echo ""
        cd "$SCRIPT_DIR"
        return 1
    fi
}

SUCCESS_COUNT=0
FAIL_COUNT=0
TOTAL_MODELS=9

for entry in \
    "WNBA Team Model (ML/Spread/Totals):wnba/wnba_model.py" \
    "WNBA Points Props:wnba/wnba_points_props_model.py" \
    "WNBA Rebounds Props:wnba/wnba_rebounds_props_model.py" \
    "WNBA Assists Props:wnba/wnba_assists_props_model.py" \
    "WNBA 3PT Props:wnba/wnba_3pt_props_model.py" \
    "WNBA PRA Props:wnba/wnba_pra_props_model.py" \
    "WNBA Pts+Reb Props:wnba/wnba_points_rebounds_props_model.py" \
    "WNBA Pts+Ast Props:wnba/wnba_points_assists_props_model.py" \
    "WNBA Reb+Ast Props:wnba/wnba_rebounds_assists_props_model.py"
do
    name="${entry%%:*}"
    path="${entry##*:}"
    if run_model "$name" "$path"; then
        ((SUCCESS_COUNT++))
    else
        ((FAIL_COUNT++))
    fi
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    📊 EXECUTION SUMMARY                   ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✅ Successful: ${SUCCESS_COUNT}/${TOTAL_MODELS}${NC}"
[ $FAIL_COUNT -gt 0 ] && echo -e "${RED}❌ Failed: ${FAIL_COUNT}/${TOTAL_MODELS}${NC}"
echo -e "${BLUE}⏱  Total Time: ${MINUTES}m ${SECONDS}s${NC}"
echo ""

if [ $SUCCESS_COUNT -gt 0 ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔥 Generating Best Plays...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    cd "$SCRIPT_DIR"
    python3 best_plays_bot.py 2>&1 && echo -e "${GREEN}✅ Best Plays updated${NC}" || echo -e "${YELLOW}⚠️  Best Plays failed${NC}"
    echo ""

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📤 Pushing to GitHub...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    bash auto_push.sh 2>&1 && echo -e "${GREEN}✅ Pushed to GitHub${NC}" || echo -e "${YELLOW}⚠️  Push failed${NC}"

    [ $FAIL_COUNT -eq 0 ] && echo -e "${GREEN}🎉 All WNBA models completed!${NC}" || echo -e "${YELLOW}⚠️  ${FAIL_COUNT} model(s) failed.${NC}"
    exit 0
else
    echo -e "${RED}❌ All models failed.${NC}"
    exit 1
fi
