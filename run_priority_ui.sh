#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# priority_ui/app.py reads no secrets of its own today — a jellyfin
# detector's key still lives in JELLYFIN_API_KEY, read by the
# monitor process, never by this screen — but this file is sourced
# anyway, the same way run_selection_ui.sh sources
# .env.selection-ui, so a future secret this screen does need has
# one obvious place to go rather than a second convention invented
# for it.
if [ -f "$AISTACK_REPO_ROOT/.env.priority-ui" ]; then
    set -a
    source "$AISTACK_REPO_ROOT/.env.priority-ui"
    set +a
fi

# fastapi and uvicorn stay out of the governed venv on purpose
# (decision #9, 2026-08-29 — see priority_ui/requirements.txt).
# Called by path rather than left to PATH order — the gap
# run_selection_ui.sh hit 2026-09-03, when a terminal with .venv
# already ahead on PATH ran uvicorn's absence as an error instead of
# uvicorn.
WEB_VENV="$AISTACK_REPO_ROOT/.venv-priority-ui"

if [ ! -x "$WEB_VENV/bin/python3" ]; then
    echo "AIStack: $WEB_VENV is missing." >&2
    echo "AIStack: run scripts/setup_priority_ui_env.sh once to create it." >&2
    exit 1
fi

# Port 8182 — the next free one after the Selection UI's 8181
# (claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md). Confirm
# nothing else already holds it before installing this as a service,
# the same check the Selection UI's own systemd unit documents:
#
#   ss -ltnp | grep :8182
"$WEB_VENV/bin/python3" -m uvicorn priority_ui.app:app --host 0.0.0.0 --port 8182
