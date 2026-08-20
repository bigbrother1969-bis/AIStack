#!/bin/bash

set -euo pipefail

# Repository root, derived from this script's own location.
# Overridable for a deployment that lives elsewhere.
#
# A machine path is not governed knowledge — same reason the
# Context Bundle transfer target was taken out of the repo.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

ROOT="${AISTACK_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

LOG_DIR="$ROOT/logs"

LOG_FILE="$LOG_DIR/context_bundle_sync.log"


mkdir -p "$LOG_DIR"


echo "===== Context Bundle Sync $(date -Iseconds) =====" >> "$LOG_FILE"


cd "$ROOT"


python3 scripts/export_project_sources.py \
    >> "$LOG_FILE" 2>&1


echo "===== Completed $(date -Iseconds) =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
