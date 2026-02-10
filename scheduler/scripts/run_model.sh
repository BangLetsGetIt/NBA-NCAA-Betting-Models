#!/bin/bash
set -euo pipefail

# Generic scheduler runner for sports-models.
#
# Usage:
#   run_model.sh <working_dir> <python_script> <log_dir> <log_prefix>
#
# Example:
#   run_model.sh "/Users/rico/Dev/sports-models/nba" "nba_points_props_model.py" "/Users/rico/Dev/sports-models/nba/logs" "nba_points_props"

WORKING_DIR="${1:-}"
PY_SCRIPT="${2:-}"
LOG_DIR="${3:-}"
LOG_PREFIX="${4:-model}"
REPO_DIR="/Users/rico/Dev/sports-models"

if [[ -z "$WORKING_DIR" || -z "$PY_SCRIPT" || -z "$LOG_DIR" ]]; then
  echo "Usage: $0 <working_dir> <python_script> <log_dir> <log_prefix>"
  exit 2
fi

# Ensure Python 3.13 is on PATH (repo already expects this).
export PATH="/Library/Frameworks/Python.framework/Versions/3.13/bin:$PATH"
export PYTHONUNBUFFERED=1

# Load environment variables from .env file
if [[ -f "${REPO_DIR}/.env" ]]; then
  export $(grep -v '^#' "${REPO_DIR}/.env" | xargs)
fi

mkdir -p "$LOG_DIR"

TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/${LOG_PREFIX}_scheduler_${TS}.log"

{
  echo "============================================================"
  echo "Scheduler run: ${LOG_PREFIX}"
  echo "Time: $(date)"
  echo "Working dir: ${WORKING_DIR}"
  echo "Script: ${PY_SCRIPT}"
  echo "============================================================"
} >> "$LOG_FILE"

cd "$WORKING_DIR"

# Run the python script
python3 "$PY_SCRIPT" >> "$LOG_FILE" 2>&1

echo "✅ Completed: ${LOG_PREFIX} at $(date)" >> "$LOG_FILE"

# Generate NCAAB analysis report if this is an NCAAB model run
if [[ "$PY_SCRIPT" == *"ncaab"* ]]; then
  echo "" >> "$LOG_FILE"
  echo "📊 Generating NCAAB Analysis Report..." >> "$LOG_FILE"
  if python3 generate_analysis_report.py >> "$LOG_FILE" 2>&1; then
    echo "✅ NCAAB Analysis Report generated" >> "$LOG_FILE"
  else
    echo "⚠️ NCAAB Analysis Report generation failed" >> "$LOG_FILE"
  fi
fi

# Auto-push updated outputs to GitHub (best effort).
# This keeps scheduled runs fully automated across all models.
{
  echo ""
  echo "📤 Auto-pushing model outputs to GitHub..."
} >> "$LOG_FILE"

if bash "${REPO_DIR}/auto_push.sh" >> "$LOG_FILE" 2>&1; then
  echo "✅ Auto-push succeeded at $(date)" >> "$LOG_FILE"
else
  echo "⚠️ Auto-push failed at $(date) (see log for details)" >> "$LOG_FILE"
fi

