#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "===== $(date '+%F %T') ====="

echo "Pulling from Gitea (SPOT)..."
git pull origin main

echo "Publishing to GitHub..."
git push github main --tags

echo "Publishing to Codeberg..."
git push codeberg main --tags

echo "Synchronization completed."
