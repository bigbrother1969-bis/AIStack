#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------
# Create or refresh the dedicated environment for
# troubleshooting_assistant_ui.
#
# Mirrors scripts/setup_network_discovery_ui_env.sh exactly, same
# reasoning: deliberately separate from bin/aistack_env.sh and
# scripts/dev-env.sh — fastapi/uvicorn/jinja2 are not part of the
# environment this heritage is verified on (decision #9,
# 2026-08-29). This script touches neither PYTHONPATH nor the
# interpreter check; it only creates
# .venv-troubleshooting-assistant-ui and installs into it.
#
# Run once, and again whenever
# troubleshooting_assistant_ui/requirements.txt changes.
# run_troubleshooting_assistant_ui.sh calls this environment by path
# and tells you to run this script if it is missing — it does not
# run it for you, so that a launcher never silently installs
# packages.
# ------------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB_VENV="$REPO_ROOT/.venv-troubleshooting-assistant-ui"

python3 -m venv "$WEB_VENV"

"$WEB_VENV/bin/pip" install --upgrade pip
"$WEB_VENV/bin/pip" install -r "$REPO_ROOT/troubleshooting_assistant_ui/requirements.txt"

echo "troubleshooting_assistant_ui environment ready at $WEB_VENV"
