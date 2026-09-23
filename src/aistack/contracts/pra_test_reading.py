from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SUCCESS = "success"
FAILED = "failed"

STATUSES = (SUCCESS, FAILED)


@dataclass(frozen=True)
class PraTestReading:
    """
    One declared service's own last-known restore-test state, as of
    one render.

    `PLAN-J11` § 11.9.1's third and last named gap ("tests PRA"),
    closed 2026-09-23 — the owner's own stated requirement, restated
    when this gap was reopened: "effectuer des tests à intervalles
    réguliers qui démontrent que les systèmes de backup fonctionnent."
    `OPS-0006` (2026-09-11) had named this out of scope for v1
    ("periodic restore tests... are named out of scope") — this type
    is what reopens it, on the owner's own explicit decision
    (2026-09-23), not a silent widening of that boundary.

    **Not a live observation — a declared record, read as one.**
    Every other `*Reading` this heritage holds (`StorageReading`,
    `ContainerStateReading`, `BackupReading`, `GpuReading`) is
    collected from a real system a Provider actually reached at
    render time. A restore test is not: the owner performs it by
    hand, and there is no automatic artifact left behind by the act
    of restoring — so, on the owner's own explicit choice (2026-09-23,
    "AIStack observe/qualifie un fichier tenu à la main"), this
    reading is loaded directly from `OPS-0009`'s declared YAML
    (`aistack.pra.yaml.load_pra_tests_yaml`) rather than collected by
    a `Provider` class reaching a live system — there is nothing live
    for one to reach. `ARC-P-012`'s boundary still applies exactly:
    this type states what the file says, and concludes nothing about
    whether it is a problem — that is `find_pra_test_gaps`'s job,
    against `OPS-0009`'s declared threshold, the same separation
    `BackupReading`/`find_backup_gaps` already hold.

    `status is None` states "this service has never been tested" —
    the same "absence stated as a fact, not smoothed into a verdict"
    `BackupReading.newest_file_mtime is None` already holds for "no
    backup file found". `status` otherwise names which of
    `OPS-0009`'s two possible outcomes the owner recorded
    (`SUCCESS`/`FAILED`) — the same closed, already-real vocabulary
    the legacy `homelab_documentation` engine's own
    `runtime/pra_tests.json` already carries (`status: success|failed`
    — found and read, not invented, 2026-09-23), reused here rather
    than declared afresh. `tested_at`/`rto_minutes` are only ever set
    together with a `status`; a service never tested carries neither.
    """

    service: str
    observed_at: datetime
    status: str | None = None
    tested_at: datetime | None = None
    rto_minutes: int | None = None

    def __post_init__(self) -> None:
        if not self.service.strip():
            raise ValueError(
                "a PRA test reading is about one service; this one names none"
            )

        if self.status is not None and self.status not in STATUSES:
            raise ValueError(
                f"{self.service} cites {self.status!r} as its last test's "
                f"status; only {STATUSES} are declared in OPS-0009"
            )

        if self.status is None:
            if self.tested_at is not None or self.rto_minutes is not None:
                raise ValueError(
                    f"{self.service} names no test status, but carries a "
                    f"test date or an RTO — a service never tested carries "
                    f"neither"
                )
            return

        if self.tested_at is None:
            raise ValueError(
                f"{self.service} names a test status ({self.status!r}) but "
                f"no test date"
            )

        if self.tested_at > self.observed_at:
            raise ValueError(
                f"{self.service} reports a test date "
                f"({self.tested_at.isoformat()}) newer than the moment it "
                f"was observed ({self.observed_at.isoformat()})"
            )

        if self.rto_minutes is not None and self.rto_minutes < 0:
            raise ValueError(
                f"{self.service} declares a negative RTO: {self.rto_minutes} "
                f"minutes"
            )
