#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# network_discovery_ui/app.py reads no secrets of its own — the SSH
# key path env var it declares (AISTACK_NETWORK_SSH_KEY_PATH) is only
# read by aistack.cli.network_docker_discover, never by this screen,
# which only edits the declared list of candidate usernames. Sourced
# anyway, the same reasoning run_priority_ui.sh already documents:
# a future secret this screen does need has one obvious place to go.
if [ -f "$AISTACK_REPO_ROOT/.env.network-discovery-ui" ]; then
    set -a
    source "$AISTACK_REPO_ROOT/.env.network-discovery-ui"
    set +a
fi

# fastapi and uvicorn stay out of the governed venv on purpose
# (decision #9, 2026-08-29 — see network_discovery_ui/requirements.txt).
# Called by path rather than left to PATH order — the gap
# run_selection_ui.sh hit 2026-09-03, when a terminal with .venv
# already ahead on PATH ran uvicorn's absence as an error instead of
# uvicorn.
WEB_VENV="$AISTACK_REPO_ROOT/.venv-network-discovery-ui"

if [ ! -x "$WEB_VENV/bin/python3" ]; then
    echo "AIStack: $WEB_VENV is missing." >&2
    echo "AIStack: run scripts/setup_network_discovery_ui_env.sh once to create it." >&2
    exit 1
fi

# Port 8184 — the next free one after the console's 8183
# (claude/PLAN-J11-CONSOLE-2026-09-11.md § 11). Bound to 127.0.0.1
# only, not 0.0.0.0 — deliberately narrower than
# priority_ui/selection_ui's own 0.0.0.0 binding: this screen writes
# which SSH usernames later get tried, unattended, against every host
# a network scan finds on the LAN, decided with the owner 2026-09-12
# to stay unreachable from anywhere but this machine itself. Confirm
# nothing else already holds port 8184 before installing this as a
# service:
#
#   ss -ltnp | grep :8184
"$WEB_VENV/bin/python3" -m uvicorn network_discovery_ui.app:app --host 127.0.0.1 --port 8184
