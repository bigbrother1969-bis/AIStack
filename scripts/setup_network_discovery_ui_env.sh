#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------
# Create or refresh the dedicated environment for network_discovery_ui.
#
# Mirrors scripts/setup_priority_ui_env.sh exactly, same reasoning:
# deliberately separate from bin/aistack_env.sh and
# scripts/dev-env.sh — fastapi/uvicorn/jinja2 are not part of the
# environment this heritage is verified on (decision #9,
# 2026-08-29). This script touches neither PYTHONPATH nor the
# interpreter check; it only creates .venv-network-discovery-ui and
# installs into it.
#
# Run once, and again whenever network_discovery_ui/requirements.txt
# changes. run_network_discovery_ui.sh calls this environment by path
# and tells you to run this script if it is missing — it does not
# run it for you, so that a launcher never silently installs
# packages.
# ------------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB_VENV="$REPO_ROOT/.venv-network-discovery-ui"

python3 -m venv "$WEB_VENV"

"$WEB_VENV/bin/pip" install --upgrade pip
"$WEB_VENV/bin/pip" install -r "$REPO_ROOT/network_discovery_ui/requirements.txt"

echo "network_discovery_ui environment ready at $WEB_VENV"
