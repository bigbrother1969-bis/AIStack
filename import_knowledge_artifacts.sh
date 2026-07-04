#!/usr/bin/env bash
set -euo pipefail

cd /srv/aistack/AISTack

python3 -m tools.knowledge_inbox.import_artifacts
