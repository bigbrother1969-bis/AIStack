from __future__ import annotations

from pathlib import Path

from aistack.history.query import available_instants
from aistack.kernel.time.version import VersionId


def next_version_from_history(generated_dir: Path, subject: str) -> VersionId:
    """
    The `VersionId` the next write to `subject` will get: the number of
    history files already on disk for it, plus one.

    Durable across process restarts, unlike `VersionSequence`. Not safe
    for concurrent writers of the same subject: two processes could get
    the same number. Current callers run one at a time.
    """

    sequence = len(available_instants(generated_dir, subject)) + 1

    return VersionId(subject=subject, sequence=sequence)
