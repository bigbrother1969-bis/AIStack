from __future__ import annotations

from dataclasses import dataclass


ANY_HOST = "*"


@dataclass(frozen=True)
class BackupThreshold:
    """
    One backup directory's declared staleness threshold (OPS-0006).

    Only age is checked, so there is no `kind` field. The YAML declares
    days; `load_backup_thresholds_yaml` converts to hours once at load.
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
    One host's declared backup thresholds. The caller matches `host`
    against the local hostname.
    """

    host: str
    thresholds: tuple[BackupThreshold, ...]

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError("a host's backup thresholds name no host")


@dataclass(frozen=True)
class BackupThresholdRegister:
    """
    Every host's declared backup thresholds, as loaded by
    `aistack.providers.filesystem.yaml.load_backup_thresholds_yaml`.

    `for_host` returns `()` for a host with no entry and no `"*"` entry:
    nothing is declared for it.
    """

    hosts: tuple[HostBackupThresholds, ...]

    def for_host(self, hostname: str) -> tuple[BackupThreshold, ...]:
        for entry in self.hosts:
            if entry.host == hostname:
                return entry.thresholds

        # `host: "*"` matches any host the file does not name; a new
        # installation ships it before it knows its own hostname.
        for entry in self.hosts:
            if entry.host == ANY_HOST:
                return entry.thresholds

        return ()
