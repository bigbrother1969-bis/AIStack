#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# The only branch this script may publish.
# Mirrors must never receive anything but the reference branch.
REFERENCE_BRANCH="main"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if [ "$CURRENT_BRANCH" != "$REFERENCE_BRANCH" ]; then
    echo "Refusing to synchronize." >&2
    echo "  current branch  : $CURRENT_BRANCH" >&2
    echo "  expected branch : $REFERENCE_BRANCH" >&2
    echo "Publishing from a working branch would merge it into the SPOT." >&2
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo "Refusing to synchronize: working tree is not clean." >&2
    git status --short >&2
    exit 1
fi

echo "===== $(date '+%F %T') ====="

echo "Pulling from Gitea (SPOT)..."
git pull --ff-only origin "$REFERENCE_BRANCH"

echo "Publishing to GitHub..."
git push github "$REFERENCE_BRANCH" --tags

echo "Publishing to Codeberg..."
git push codeberg "$REFERENCE_BRANCH" --tags

echo "Synchronization completed."
