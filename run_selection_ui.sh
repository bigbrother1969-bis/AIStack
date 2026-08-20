#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/bin/aistack_env.sh"

python3 -m uvicorn selection_ui.app:app --host 0.0.0.0 --port 8181
