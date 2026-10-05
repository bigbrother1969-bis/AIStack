#!/usr/bin/env bash
set -euo pipefail

# OPS-0012: in quarantine until 2026-11-16 — any run is recorded.
source "$(cd "$(dirname "$0")" && pwd)/scripts/quarantine_tripwire.sh"
quarantine_tripwire run_render_demo.sh

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

python3 -m examples.render_engine.render_demo
