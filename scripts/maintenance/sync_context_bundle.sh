#!/bin/bash

set -e


ROOT="/srv/aistack/AISTack"

LOG_DIR="$ROOT/logs"

LOG_FILE="$LOG_DIR/context_bundle_sync.log"


mkdir -p "$LOG_DIR"


echo "===== Context Bundle Sync $(date -Iseconds) =====" >> "$LOG_FILE"


cd "$ROOT"


python scripts/export_project_sources.py \
    >> "$LOG_FILE" 2>&1


echo "===== Completed $(date -Iseconds) =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
