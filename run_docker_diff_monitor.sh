#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# No secrets to source — the same reasoning `run_docker_events_monitor
# .sh`'s own comment already gives for its own stream: this monitor
# reads no API key from the environment; it only calls `docker diff`
# (and `docker ps`/`docker inspect`, via `aistack.providers.docker
# .identity`) and writes to `reports/generated/`.
#
# Governed heritage, verified by the governed suite under `.venv`, the
# same reasoning `run_docker_events_monitor.sh`'s own comment already
# gives for running there rather than in a second, unverified
# environment.
exec "$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.docker_diff_monitor "$@"
