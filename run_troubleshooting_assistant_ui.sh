#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# troubleshooting_assistant_ui/app.py reads no secrets of its own —
# it reuses ai_runtime.yml (host/port/model, no credential) and
# resource_priority.yml, both already governed, unencrypted files.
# Sourced anyway, the same reasoning run_priority_ui.sh and
# run_network_discovery_ui.sh already document: a future secret this
# screen does need has one obvious place to go.
if [ -f "$AISTACK_REPO_ROOT/.env.troubleshooting-assistant-ui" ]; then
    set -a
    source "$AISTACK_REPO_ROOT/.env.troubleshooting-assistant-ui"
    set +a
fi

# fastapi and uvicorn stay out of the governed venv on purpose
# (decision #9, 2026-08-29 —
# see troubleshooting_assistant_ui/requirements.txt). Called by path
# rather than left to PATH order — the gap run_selection_ui.sh hit
# 2026-09-03, when a terminal with .venv already ahead on PATH ran
# uvicorn's absence as an error instead of uvicorn.
WEB_VENV="$AISTACK_REPO_ROOT/.venv-troubleshooting-assistant-ui"

if [ ! -x "$WEB_VENV/bin/python3" ]; then
    echo "AIStack: $WEB_VENV is missing." >&2
    echo "AIStack: run scripts/setup_troubleshooting_assistant_ui_env.sh once to create it." >&2
    exit 1
fi

# Port 8185 — the next free one after network_discovery_ui's 8184
# (claude/PLAN-TROUBLESHOOTING-ASSISTANT-UI-2026-09-18.md). Bound to
# 0.0.0.0, same as priority_ui/selection_ui/network_discovery_ui —
# reachable from anywhere on the owner's LAN. "LAN-only" here comes
# from never adding an NPM Proxy Host for this port, not from the
# bind address — network_discovery_ui's own launcher already
# documents the 127.0.0.1 mistake this avoids repeating. Confirm
# nothing else already holds port 8185 before installing this as a
# service:
#
#   ss -ltnp | grep :8185
"$WEB_VENV/bin/python3" -m uvicorn troubleshooting_assistant_ui.app:app --host 0.0.0.0 --port 8185
