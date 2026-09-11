#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# Regenerate `console.html` (and refresh the three symlinks
# `aistack.cli.console_render` maintains under
# `reports/generated/public/`) every time this launcher starts —
# `console_links.yml` is read fresh, so a systemd restart is enough
# to pick up an edited declaration without a separate manual step.
#
# The governed venv, not a dedicated one: unlike Priority UI and
# Selection UI, this screen needs no FastAPI/uvicorn (decision #9,
# 2026-08-29 is about *those* — this launcher serves static files
# with the standard library's own `http.server`), so it runs on the
# same interpreter every other `aistack.cli.*` command already does.
"$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.console_render

# Port 8183 — the next free one after Priority UI's 8182, itself the
# next free one after Selection UI's 8181
# (claude/PLAN-J11-CONSOLE-2026-09-11.md § 4). Confirm nothing else
# already holds it before installing this as a service, the same
# check the other two units document:
#
#   ss -ltnp | grep :8183
"$AISTACK_REPO_ROOT/.venv/bin/python3" -m http.server 8183 \
    --directory "$AISTACK_REPO_ROOT/reports/generated/public"
