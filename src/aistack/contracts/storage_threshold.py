from __future__ import annotations

from dataclasses import dataclass

# The threshold kinds OPS-0005 declares.
FREE_BYTES = "free_bytes"
PERCENT_USED = "percent_used"

KINDS = (FREE_BYTES, PERCENT_USED)


ANY_HOST = "*"


@dataclass(frozen=True)
class StorageThreshold:
    """
    One volume's declared alert threshold (OPS-0005).

    `FREE_BYTES` (value in bytes) suits a volume where absolute headroom
    matters, such as an OS root; `PERCENT_USED` (value 0-100) suits a
    media volume. The same percentage leaves very different room on a
    small and a large disk.
    """

    mount: str
    kind: str
    value: float

    def __post_init__(self) -> None:
        if not self.mount.strip():
            raise ValueError(
                "a storage threshold is about one mount; this one "
                "names none"
            )

        if self.kind not in KINDS:
            raise ValueError(
                f"{self.mount} declares an unknown threshold kind "
                f"{self.kind!r}; OPS-0005 declares only {KINDS}"
            )

        if self.value < 0:
            raise ValueError(
                f"{self.mount} declares a negative threshold: {self.value}"
            )


@dataclass(frozen=True)
class HostStorageThresholds:
    """
    One host's declared storage thresholds; the same mount (`/`) can
    have a different threshold on each host. The caller matches `host`
    against the local hostname.
    """

    host: str
    thresholds: tuple[StorageThreshold, ...]

    def __post_init__(self) -> None:
        if not self.host.strip():
            raise ValueError(
                "a host's storage thresholds name no host"
            )


@dataclass(frozen=True)
class StorageThresholdRegister:
    """
    Every host's declared storage thresholds, as loaded by
    `aistack.providers.filesystem.yaml.load_storage_thresholds_yaml`.

    `for_host` returns `()` for a host with no entry and no `"*"` entry.
    """

    hosts: tuple[HostStorageThresholds, ...]

    def for_host(self, hostname: str) -> tuple[StorageThreshold, ...]:
        for entry in self.hosts:
            if entry.host == hostname:
                return entry.thresholds

        # `host: "*"` matches any host the file does not name; a new
        # installation ships it before it knows its own hostname.
        for entry in self.hosts:
            if entry.host == ANY_HOST:
                return entry.thresholds

        return ()
