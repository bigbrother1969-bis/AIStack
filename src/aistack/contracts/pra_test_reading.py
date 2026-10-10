from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SUCCESS = "success"
FAILED = "failed"

STATUSES = (SUCCESS, FAILED)


@dataclass(frozen=True)
class PraTestReading:
    """
    One service's last recorded restore test (OPS-0009).

    Not a live observation: restore tests are done by hand and recorded
    in a YAML file, loaded by `aistack.pra.yaml.load_pra_tests_yaml`. A
    reading, not a verdict: `find_pra_test_gaps` judges it.

    `status is None` means never tested. Otherwise it is `SUCCESS` or
    `FAILED`, and `tested_at` (with optional `rto_minutes`) is set.
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
