#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

# No secrets to source — unlike `run_resource_priority_monitor.sh`,
# this monitor reads no API key from the environment; it only calls
# `docker events` and writes to `reports/generated/`.
#
# Governed heritage, verified by the governed suite under `.venv`,
# the same reasoning `run_resource_priority_monitor.sh`'s own comment
# already gives for running there rather than in a second,
# unverified environment.
exec "$AISTACK_REPO_ROOT/.venv/bin/python3" -m aistack.cli.docker_events_monitor "$@"
