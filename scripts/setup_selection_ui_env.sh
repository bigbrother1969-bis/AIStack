#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------
# Create or refresh the dedicated environment for selection_ui.
#
# Deliberately separate from bin/aistack_env.sh and
# scripts/dev-env.sh: those declare and provide the environment
# this heritage is verified on, and fastapi/uvicorn/jinja2/
# python-multipart are not part of it (decision #9, 2026-08-29 —
# see selection_ui/requirements.txt). This script touches neither
# PYTHONPATH nor the interpreter check; it only creates
# .venv-selection-ui and installs into it.
#
# Run once, and again whenever selection_ui/requirements.txt
# changes. run_selection_ui.sh calls this environment by path and
# tells you to run this script if it is missing — it does not run
# it for you, so that a launcher never silently installs packages.
# ------------------------------------------------------------------

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB_VENV="$REPO_ROOT/.venv-selection-ui"

python3 -m venv "$WEB_VENV"

"$WEB_VENV/bin/pip" install --upgrade pip
"$WEB_VENV/bin/pip" install -r "$REPO_ROOT/selection_ui/requirements.txt"

echo "selection_ui environment ready at $WEB_VENV"
