#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# AIStack's single web process (ADR-0012), which replaced
# `run_console.sh` on 2026-10-03.
#
# Regenerate the console — `console.html` and one `console.<code>.html`
# per other declared language (ADR-0010) — every time this launcher
# starts. `console_links.yml` is read fresh, so a systemd restart is
# enough to pick up an edited declaration.
"$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.console_render

# One process, two listeners, both read from
# `src/aistack/instance/definitions/instance_config.yml`:
#
#   - `service_ports.console` (8183), the public listener — the only
#     port the Nginx Proxy Manager entry for aistack.persiaut-family.fr
#     points at. It answers the console, Architecture, Health and
#     Settings, nothing else;
#   - `service_ports.web_lan`, the LAN listener — never a Proxy Host.
#     It answers every route, including each screen as it moves into
#     the application through 1.7's first tranche.
#
# Secrets the screens read from the environment (the Selection UI's
# `SYNCTHING_API_KEY` since 2026-10-03), in one file never committed,
# replacing each screen's own `.env.<screen>`.
if [ -f "$AISTACK_REPO_ROOT/.env.web" ]; then
    set -a
    source "$AISTACK_REPO_ROOT/.env.web"
    set +a
fi

# The governed venv, no dedicated one: the web packages are this
# heritage's own dependencies since decision #9 was revoked for tests
# (GOV-0002/OS-084).
exec "$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.web.server \
    --generated-dir "$AISTACK_REPO_ROOT/reports/generated"
