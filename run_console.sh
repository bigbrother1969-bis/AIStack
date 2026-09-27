#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# Regenerate the console — `console.html` and, since 2026-09-27, one
# `console.<code>.html` per other declared language (ADR-0010) — every
# time this launcher starts. `console_links.yml` is read fresh, so a
# systemd restart is enough to pick up an edited declaration without a
# separate manual step.
#
# The governed venv, not a dedicated one: unlike Priority UI and
# Selection UI, this screen needs no FastAPI/uvicorn (decision #9,
# 2026-08-29 is about *those* — this launcher serves its pages with a
# standard-library server, `aistack.console.server`), so it runs on the
# same interpreter every other `aistack.cli.*` command already does.
"$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.console_render

# Port 8183 — the next free one after Priority UI's 8182, itself the
# next free one after Selection UI's 8181
# (claude/PLAN-J11-CONSOLE-2026-09-11.md § 4). Unchanged on 2026-09-27,
# so the reverse proxy entry for aistack.persiaut-family.fr needs no
# change. Confirm nothing else already holds it before installing this
# as a service, the same check the other two units document:
#
#   ss -ltnp | grep :8183
#
# **Served by aistack.console.server since 2026-09-27, not
# `python -m http.server`** (ADR-0010 § 5): a static file server cannot
# carry the interface language a visitor chose, nor the Settings page
# where they choose it. Still the standard library, still the governed
# interpreter — no dedicated environment, unlike the four mini-apps.
# It serves `reports/generated/` through a closed list of three pages
# plus Settings, never the directory itself.
"$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.console.server \
    --port 8183 \
    --generated-dir "$AISTACK_REPO_ROOT/reports/generated"
