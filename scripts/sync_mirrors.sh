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

# Publish to one mirror and report what reached it.
#
# Until 2026-08-21 this script ended on "Synchronization
# completed" with the same satisfaction whether it had pushed
# three commits or nothing at all. That sentence reports that
# the script ran, which was never in doubt; it does not report
# that the mirror moved, which is the only thing anyone runs it
# to find out. A mirror silently stuck three commits behind
# looked exactly like a mirror up to date.
#
# The remote ref is read before the push and compared after, so
# the message states a fact about the mirror rather than about
# the script.
publish() {
    local remote="$1"

    local before
    before="$(git ls-remote "$remote" \
        "refs/heads/$REFERENCE_BRANCH" | cut -f1)"

    git push "$remote" "$REFERENCE_BRANCH" --tags

    local after
    after="$(git rev-parse "$REFERENCE_BRANCH")"

    if [ -z "$before" ]; then
        echo "  $remote: branch created at $(git rev-parse --short "$after")"
        return
    fi

    if [ "$before" = "$after" ]; then
        echo "  $remote: already at $(git rev-parse --short "$after") — nothing published"
        return
    fi

    if ! git cat-file -e "$before^{commit}" 2>/dev/null; then
        # The mirror held a commit this clone has never seen.
        # Saying what moved is impossible; saying that is not.
        echo "  $remote: moved to $(git rev-parse --short "$after")" \
             "from an unknown commit ${before:0:7}" >&2
        return
    fi

    echo "  $remote: published $(git rev-list --count "$before..$after") commit(s)"
    git log --oneline "$before..$after" | sed 's/^/    /'
}

echo "===== $(date '+%F %T') ====="

BEFORE_PULL="$(git rev-parse "$REFERENCE_BRANCH")"

echo "Pulling from Gitea (SPOT)..."
git pull --ff-only origin "$REFERENCE_BRANCH"

AFTER_PULL="$(git rev-parse "$REFERENCE_BRANCH")"

if [ "$BEFORE_PULL" = "$AFTER_PULL" ]; then
    echo "  local clone already at $(git rev-parse --short "$AFTER_PULL")"
else
    echo "  local clone advanced to $(git rev-parse --short "$AFTER_PULL")"
fi

echo "Publishing to GitHub..."
publish github

echo "Publishing to Codeberg..."
publish codeberg

echo "Synchronization completed at $(git rev-parse --short "$REFERENCE_BRANCH")."
