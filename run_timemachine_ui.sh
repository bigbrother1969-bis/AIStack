#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# timemachine_ui/app.py reads no secrets of its own and writes
# nothing — it only opens the graph read-only
# (OxigraphGraphStore.read_only). Sourced anyway, the same reasoning
# run_network_discovery_ui.sh/run_priority_ui.sh already document: a
# future secret this screen does need has one obvious place to go.
if [ -f "$AISTACK_REPO_ROOT/.env.timemachine-ui" ]; then
    set -a
    source "$AISTACK_REPO_ROOT/.env.timemachine-ui"
    set +a
fi

# fastapi and uvicorn stay out of the governed venv on purpose
# (decision #9, 2026-08-29 — see timemachine_ui/requirements.txt).
# Called by path rather than left to PATH order — the gap
# run_selection_ui.sh hit 2026-09-03, when a terminal with .venv
# already ahead on PATH ran uvicorn's absence as an error instead of
# uvicorn.
WEB_VENV="$AISTACK_REPO_ROOT/.venv-timemachine-ui"

if [ ! -x "$WEB_VENV/bin/python3" ]; then
    echo "AIStack: $WEB_VENV is missing." >&2
    echo "AIStack: run scripts/setup_timemachine_ui_env.sh once to create it." >&2
    exit 1
fi

# Port 8186 — the next free one after the Troubleshooting
# Assistant's 8185. Bound to 0.0.0.0, same as the other four mini-apps
# — reachable from anywhere on the owner's own LAN (his own laptop
# included). "LAN-only" here comes from never adding an NPM Proxy Host
# for this port, not from the bind address — see
# run_network_discovery_ui.sh's own comment for the 2026-09-12
# incident this convention was corrected from. Confirm nothing else
# already holds port 8186 before installing this as a service:
#
#   ss -ltnp | grep :8186
"$WEB_VENV/bin/python3" -m uvicorn timemachine_ui.app:app --host 0.0.0.0 --port 8186
