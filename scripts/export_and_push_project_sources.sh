#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

LAPTOP_TARGET="${AISTACK_LAPTOP_TARGET:-big-brother@LAPTOP}"
REMOTE_DIR="${AISTACK_LAPTOP_DIR:-Téléchargements/AIStack}"
BUNDLE="context/bundles/AIStack-Project-Sources.zip"

python3 scripts/export_project_sources.py

ssh "$LAPTOP_TARGET" "mkdir -p ~/$REMOTE_DIR"

scp "$BUNDLE" "$LAPTOP_TARGET:~/$REMOTE_DIR/"

scp \
  context/README_AI.md \
  context/AI_PROTOCOL.md \
  context/AI_TRANSACTION_PROTOCOL.md \
  "$LAPTOP_TARGET:~/$REMOTE_DIR/"

echo "Bundle pushed to:"
echo "$LAPTOP_TARGET:~/$REMOTE_DIR/AIStack-Project-Sources.zip"

echo "AI protocol files pushed to:"
echo "$LAPTOP_TARGET:~/$REMOTE_DIR/"
