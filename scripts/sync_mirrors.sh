#!/usr/bin/env bash
#
# Publish the reference branch of the SPOT to every mirror.
#
# ---------------------------------------------------------------
# Why the whole script is one function invoked on the last line
# ---------------------------------------------------------------
#
# Bash reads a script from the file as it executes it, keeping a
# byte offset. This script pulls from the SPOT, and the SPOT holds
# this script — so a run that delivers an improvement to
# `sync_mirrors.sh` rewrites the file bash is still reading. On
# 2026-08-21 the run that delivered this script's own improvement
# printed the old message, because bash had already read the old
# bytes. That was harmless. Had the file grown or shrunk, bash
# would have resumed at an offset now pointing into the middle of
# a different line, and executed whatever that turned out to be.
#
# Wrapping everything in a function and calling it on the final
# line means bash must parse the entire file before running any of
# it, and has nothing left to read once `main` starts. The `exit`
# guarantees it never tries. GOV-0002/OS-010.
#
# The defect is not reproducible at this file's size — bash reads
# it in one chunk — and the test suite says so rather than
# pretending to observe it.

set -euo pipefail

main() {

    local SCRIPT_DIR PROJECT_ROOT
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

    cd "$PROJECT_ROOT"

    # The only branch this script may publish.
    # Mirrors must never receive anything but the reference branch.
    local REFERENCE_BRANCH="main"

    local CURRENT_BRANCH
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

    local BEFORE_PULL AFTER_PULL
    BEFORE_PULL="$(git rev-parse "$REFERENCE_BRANCH")"

    # The pull is the one step that may still stop the run. If the
    # SPOT is unreachable this clone does not know what it would be
    # publishing, and a mirror is not a place to guess.
    echo "Pulling from Gitea (SPOT)..."
    git pull --ff-only origin "$REFERENCE_BRANCH"

    AFTER_PULL="$(git rev-parse "$REFERENCE_BRANCH")"

    if [ "$BEFORE_PULL" = "$AFTER_PULL" ]; then
        echo "  local clone already at $(git rev-parse --short "$AFTER_PULL")"
    else
        echo "  local clone advanced to $(git rev-parse --short "$AFTER_PULL")"
    fi

    # ---------------------------------------------------------------
    # Every mirror is attempted, whatever the others did
    # ---------------------------------------------------------------
    #
    # On 2026-08-21 GitHub rate-limited the host, `set -e` ended the
    # run, and Codeberg — reachable throughout — was never published.
    # One mirror is not a dependency of another, and a script that
    # treats them as a chain makes a transient failure at the first
    # into a silent gap at the second. GOV-0002/OS-009.
    #
    # The run still fails: every failure is named at the end and the
    # exit code says so. What changes is that it fails *after*
    # having done everything it could do.

    local -a MIRRORS=(github codeberg)
    local -a FAILED=()
    local remote

    for remote in "${MIRRORS[@]}"; do

        echo "Publishing to $remote..."

        if publish "$remote" "$REFERENCE_BRANCH"; then
            continue
        fi

        FAILED+=("$remote")
        echo "  $remote: not published" >&2
    done

    local at
    at="$(git rev-parse --short "$REFERENCE_BRANCH")"

    if [ ${#FAILED[@]} -eq 0 ]; then
        echo "Synchronization completed at $at."
        exit 0
    fi

    echo "Synchronization incomplete at $at:" \
         "${#FAILED[@]} of ${#MIRRORS[@]} mirror(s) did not receive it" \
         "— ${FAILED[*]}" >&2
    exit 1
}

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
#
# **Every failure is returned, never raised.** The caller runs
# this inside an `if`, which suspends `set -e` for everything it
# calls — so a `git push` that fails no longer ends the run, and
# would otherwise fall through to the lines below and announce a
# publication that did not happen.
publish() {
    local remote="$1"
    local branch="$2"

    local before
    if ! before="$(git ls-remote "$remote" "refs/heads/$branch" | cut -f1)"
    then
        echo "  $remote: unreachable; its state is unknown" >&2
        return 1
    fi

    if ! git push "$remote" "$branch" --tags; then
        if [ -n "$before" ]; then
            echo "  $remote: push refused;" \
                 "the mirror is unchanged at ${before:0:7}" >&2
        else
            echo "  $remote: push refused; the mirror has no $branch" >&2
        fi
        return 1
    fi

    local after
    after="$(git rev-parse "$branch")"

    if [ -z "$before" ]; then
        echo "  $remote: branch created at $(git rev-parse --short "$after")"
        return 0
    fi

    if [ "$before" = "$after" ]; then
        echo "  $remote: already at $(git rev-parse --short "$after") — nothing published"
        return 0
    fi

    if ! git cat-file -e "$before^{commit}" 2>/dev/null; then
        # The mirror held a commit this clone has never seen.
        # Saying what moved is impossible; saying that is not.
        echo "  $remote: moved to $(git rev-parse --short "$after")" \
             "from an unknown commit ${before:0:7}" >&2
        return 0
    fi

    echo "  $remote: published $(git rev-list --count "$before..$after") commit(s)"
    git log --oneline "$before..$after" | sed 's/^/    /'
    return 0
}

# Both commands on one line, deliberately. Bash parses a whole
# line before running it, so even if `main` ever returned instead
# of exiting, the `exit` is already in memory and bash reads no
# further byte of a file the pull may have replaced.
main "$@"; exit $?
