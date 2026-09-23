from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PraTestThreshold:
    """
    One declared service's own restore-test staleness threshold —
    `OPS-0009`, not a value this heritage chose. `GOV-P-001`: the
    owner states the number (90 days, 2026-09-23 — a quarterly rhythm,
    her own choice over the tighter 180-day alternative examined with
    her); this type only shapes it so `find_pra_test_gaps` can compare
    a reading against it without inventing what "too old" means for a
    restore test no case had named a value for before this gap was
    reopened.

    **One value for every declared service, not one per service.**
    Unlike `BackupThreshold` (`OPS-0006` names a different staleness
    window per backup path from the start), the owner declared a
    single flat threshold across all five services `OPS-0009` names
    (2026-09-23) — this type still carries `service` so
    `PraTestThresholdRegister` can be looked up the same way
    `BackupThresholdRegister`/`StorageThresholdRegister` already are,
    leaving room for a future per-service value without a reshape, but
    `load_pra_tests_yaml` populates every entry from the one declared
    number today.
    """

    service: str
    max_age_days: float

    def __post_init__(self) -> None:
        if not self.service.strip():
            raise ValueError(
                "a PRA test threshold is about one service; this one "
                "names none"
            )

        if self.max_age_days <= 0:
            raise ValueError(
                f"{self.service} declares a non-positive staleness "
                f"threshold: {self.max_age_days} days"
            )


@dataclass(frozen=True)
class PraTestThresholdRegister:
    """
    Every declared service's restore-test threshold, as `OPS-0009`'s
    YAML file loads it (`aistack.pra.yaml.load_pra_tests_yaml`).

    `for_service` mirrors `BackupThresholdRegister.for_host` in shape
    — a pure lookup over data already held. A service absent here is
    `FDN-0003` Article 12's kind of declared absence ("not one of the
    services this render checks"), the same "not measured is not
    zero" convention `find_backup_gaps` already holds for a path with
    no declared threshold.
    """

    thresholds: tuple[PraTestThreshold, ...]

    def for_service(self, name: str) -> PraTestThreshold | None:
        for entry in self.thresholds:
            if entry.service == name:
                return entry

        return None
