from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackupThreshold:
    """
    One backup location's own declared staleness threshold —
    `OPS-0006`, not a value this heritage chose. `GOV-P-001`: the
    owner states the number; this type only shapes it so
    `find_backup_gaps` can compare a reading against it without
    inventing what "too old" means for a backup no case has named a
    value for.

    Unlike `StorageThreshold`, this domain declares only one kind:
    `OPS-0006` names age, not size or percentage — the owner's own
    scoping of `PLAN-J7`'s fourth domain to "the backup file exists,
    and is not too old" (existence and freshness only; periodic
    restore tests and documentation currency are named out of scope,
    `OPS-0006` § *Out of scope*). So `BackupThreshold` carries no
    `kind` field the way `StorageThreshold` does — there is only one.

    `max_age_hours` is the unit this type stores in, even though the
    owner declared it in days ("7 jours") — `load_backup_thresholds_yaml`
    converts once at load time, the same `_BYTES_PER_GB`-style
    single-point conversion `load_storage_thresholds_yaml` already
    holds for `free_gb` → bytes.
    """

    path: str
    max_age_hours: float

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ValueError(
                "a backup threshold is about one path; this one names none"
            )

        if self.max_age_hours <= 0:
            raise ValueError(
                f"{self.path} declares a non-positive staleness threshold: "
                f"{self.max_age_hours} hours"
            )


@dataclass(frozen=True)
class HostBackupThresholds:
    """
    One host's own declared backup thresholds.

    Mirrors `HostStorageThresholds`: `OPS-0006` scopes every threshold
    to the host it was declared for — the owner confirmed the
    WordPress backup script, and this domain's v1 scope, run on
    GIGABYTE (`OPS-0006` § *Declared thresholds*), not on every host
    that could in principle mount `/media/BACKUP`. `host` is matched
    against `socket.gethostname()` by the caller
    (`aistack.cli.runtime_diagnose`), not by this type.
    """

    host: str
    thresholds: tuple[BackupThreshold, ...]

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("a host's backup thresholds name no host")


@dataclass(frozen=True)
class BackupThresholdRegister:
    """
    Every host's declared backup thresholds, as `OPS-0006`'s YAML
    file loads it
    (`aistack.providers.filesystem.yaml.load_backup_thresholds_yaml`).

    `for_host` mirrors `StorageThresholdRegister.for_host` exactly: a
    pure derivation from data already held, and a host with no entry
    returns `()` — "not declared for this host", not "declared as
    nothing to check", the same `FDN-0003` Article 12 absence
    `find_backup_gaps` already holds for a path with no threshold at
    all.
    """

    hosts: tuple[HostBackupThresholds, ...]

    def for_host(self, hostname: str) -> tuple[BackupThreshold, ...]:
        for entry in self.hosts:
            if entry.host == hostname:
                return entry.thresholds

        return ()
