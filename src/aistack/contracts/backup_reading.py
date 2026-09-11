from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BackupReading:
    """
    One backup location's own state, at one point in time: whether any
    backup file was found under it, and how recently.

    `PLAN-J7`'s fourth domain (Sauvegarde / PRA) — the owner's own
    stated requirement: "Vérifier qu'il existe réellement une
    sauvegarde, qu'elle est fonctionnelle et que les backup ne sont
    pas trop vieux." `ARC-P-012`'s boundary applies here exactly as it
    does to `StorageReading`/`ContainerStateReading`: this is what the
    filesystem reported, concluding nothing about whether it is a
    problem. Whether a backup is missing or stale is a question for
    something that reads a collection of these against a declared
    threshold (`aistack.runtime.backup_gap.find_backup_gaps`), not
    this type.

    `path` names the directory checked — the same "this is what the
    threshold is declared against" role `StorageReading.mount` already
    holds. `observed_at` is when this reading was taken;
    `newest_file_mtime` is the most recent modification time among the
    files found under `path`, or `None` when the directory holds no
    file at all — whether because it does not exist, or exists and has
    never received one. Either way, no backup was found, which is the
    fact this type states.

    **A reading, not a verdict.** `newest_file_mtime is None` states
    "no backup file found"; it does not itself say whether that is a
    problem — a fresh install with a first backup still pending reads
    the same way a genuinely broken backup job does. `find_backup_gaps`
    is where that distinction, against a declared threshold, is made.
    """

    path: str
    observed_at: datetime
    newest_file_mtime: datetime | None = None

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ValueError(
                "a backup reading is about one path; this one names none"
            )

        if (
            self.newest_file_mtime is not None
            and self.newest_file_mtime > self.observed_at
        ):
            raise ValueError(
                f"{self.path} reports a backup file newer "
                f"({self.newest_file_mtime.isoformat()}) than the moment "
                f"it was observed ({self.observed_at.isoformat()})"
            )
