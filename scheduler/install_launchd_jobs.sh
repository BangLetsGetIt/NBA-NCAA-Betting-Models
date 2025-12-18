#!/bin/bash
set -euo pipefail

# Installs and loads launchd jobs for sports-models.
# This enables automatic overnight grading + HTML refresh without manual runs.

REPO_DIR="/Users/rico/sports-models"
PLISTS_DIR="${REPO_DIR}/scheduler/plists"
LAUNCH_AGENTS_DIR="/Users/rico/Library/LaunchAgents"

mkdir -p "${LAUNCH_AGENTS_DIR}"

echo "Installing launchd jobs into: ${LAUNCH_AGENTS_DIR}"

# Disable legacy schedulers that either (a) don't run often enough for fast grading,
# or (b) auto-push / point to non-repo paths.
LEGACY_PLISTS=(
  "${LAUNCH_AGENTS_DIR}/com.rico.nba3ptprops.plist"
  "${LAUNCH_AGENTS_DIR}/com.rico.nbareboundsprops.plist"
  "${LAUNCH_AGENTS_DIR}/com.rico.nbaassistsprops.plist"
  "${LAUNCH_AGENTS_DIR}/com.ricosoloco.nbamodel.plist"
  "${LAUNCH_AGENTS_DIR}/com.ricosoloco.nflmodel.plist"
)

echo "Disabling legacy schedulers (best effort)..."
for legacy in "${LEGACY_PLISTS[@]}"; do
  if [[ -f "$legacy" ]]; then
    echo " - Unload: $(basename "$legacy")"
    launchctl unload "$legacy" 2>/dev/null || true
  fi
done

echo ""
echo "Loading sports-models schedulers..."
for plist in "${PLISTS_DIR}"/*.plist; do
  base="$(basename "$plist")"
  dest="${LAUNCH_AGENTS_DIR}/${base}"
  echo " - Copy: ${base}"
  cp "$plist" "$dest"
  # Best-effort reload
  launchctl unload "$dest" 2>/dev/null || true
  launchctl load "$dest"
done

echo ""
echo "✅ Installed + loaded jobs:"
launchctl list | grep -E "com\\.rico\\.sportsmodels\\." || true

echo ""
echo "Tip: logs are written under:"
echo " - ${REPO_DIR}/nba/logs/"
echo " - ${REPO_DIR}/nfl/logs/"

