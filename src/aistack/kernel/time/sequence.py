from __future__ import annotations

from pathlib import Path

from aistack.history.query import available_instants
from aistack.kernel.time.version import VersionId


def next_version_from_history(generated_dir: Path, subject: str) -> VersionId:
    """
    The `VersionId` a write to `subject` is about to become — J3
    step 3 (`claude/PLAN-J3-TIME-FOUNDATION-2026-09-10.md`).

    **Durable across process restarts, without a second counter to
    keep in sync.** `VersionSequence` (`kernel/time/version.py`) is
    in-memory only — exactly wrong for `FileTraceRepository`/
    `decision_history.record_decision`, each invoked from a
    short-lived CLI process that would otherwise start counting from
    1 on every run. This reads the count already on disk instead:
    `aistack.history.query.available_instants` (the same read side
    `aistack.cli.history_query` already exposes) counts how many
    times `subject` has been historicised under `generated_dir` —
    that count, plus one, is the version this write is about to add.
    The filesystem history is the only ledger; nothing here
    duplicates it.

    **Not safe against concurrent writers to the same subject** — two
    processes calling this before either has written would compute
    the same sequence number. Acceptable for the same reason
    `write_artifact_with_history`'s own collision suffix exists for a
    narrower case (same-second writes) rather than a lock: every
    caller today (`FileTraceRepository`, `decision_history`) runs from
    a single CLI invocation or monitor loop, never two processes
    racing to historicise the same subject at once.
    """

    sequence = len(available_instants(generated_dir, subject)) + 1

    return VersionId(subject=subject, sequence=sequence)
