#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# aistack.priority.* and aistack.providers.jellyfin read secrets
# from the process environment by name only (GOV-P-001: no secret
# passes through a governed artifact). This file is never
# committed — .gitignore has carried it since this script was
# written — and is where JELLYFIN_API_KEY belongs for a local run:
# plain KEY=value lines, shell-sourceable, same convention as
# .env.selection-ui.
if [ -f "$AISTACK_REPO_ROOT/.env.resource-priority" ]; then
    set -a
    source "$AISTACK_REPO_ROOT/.env.resource-priority"
    set +a
fi

# Unlike selection_ui/app.py, this monitor is governed heritage:
# aistack.priority and aistack.providers.jellyfin are verified by
# the governed suite under .venv (decision #9 excludes only the
# four web dependencies selection_ui needs, not this feature), so
# it runs there rather than in a second, unverified environment.
exec "$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.resource_priority_monitor "$@"
