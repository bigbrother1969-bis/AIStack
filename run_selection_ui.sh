#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# selection_ui/app.py reads secrets from the process environment by
# name only (GOV-P-001: no secret passes through a governed
# artifact — "il s'authentifie lui-même"). This file is never
# committed, .gitignore has carried it since before this script
# read it, and is where SYNCTHING_API_KEY belongs for a local run —
# plain KEY=value lines, shell-sourceable.
if [ -f "$AISTACK_REPO_ROOT/.env.selection-ui" ]; then
    set -a
    source "$AISTACK_REPO_ROOT/.env.selection-ui"
    set +a
fi

# fastapi, uvicorn, jinja2 and python-multipart stay out of the
# governed venv on purpose (decision #9, 2026-08-29): they are not
# knowledge this heritage is verified on. Called by path rather
# than left to PATH order — a terminal with .venv already ahead on
# PATH ran uvicorn's absence as an error instead of uvicorn, found
# 2026-09-03 the first time this script ran after the screen was
# rewired onto the governed application definition.
WEB_VENV="$AISTACK_REPO_ROOT/.venv-selection-ui"

if [ ! -x "$WEB_VENV/bin/python3" ]; then
    echo "AIStack: $WEB_VENV is missing." >&2
    echo "AIStack: run scripts/setup_selection_ui_env.sh once to create it." >&2
    exit 1
fi

"$WEB_VENV/bin/python3" -m uvicorn selection_ui.app:app --host 0.0.0.0 --port 8181
