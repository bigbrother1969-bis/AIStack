#!/usr/bin/env bash
set -euo pipefail

source /srv/aistack/AISTack/bin/aistack_env.sh

python3 -m examples.render_engine.render_demo
