from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageReading:
    """
    One filesystem's own reported capacity, at one point in time.

    ARC-P-012's boundary applies here exactly as it does to
    `ContainerCpuReading`: this is what the filesystem reported,
    concluding nothing about whether it is a problem. Whether a
    volume is short on space is a question for something that reads a
    collection of these against a declared policy —
    `aistack.runtime.storage_shortage.find_storage_shortage`, not this
    type — the same split `find_unexplained_consumption` already
    holds for CPU.

    `mount` names the mount point (`/`, `/media/Films`), not the
    device (`/dev/sdc1`) — a device can move between mounts; the
    mount is what `OPS-0005` declares a threshold against.

    `total_bytes`/`used_bytes`/`free_bytes` need not sum exactly:
    most filesystems reserve blocks (ext4's default 5%, held back
    from ordinary use) that are neither used nor free in the sense
    this type reports — `used_bytes + free_bytes <= total_bytes` is
    the only relationship enforced, never equality.
    """

    mount: str
    total_bytes: int
    used_bytes: int
    free_bytes: int

    def __post_init__(self) -> None:
        if not self.mount.strip():
            raise ValueError(
                "a storage reading is about one mount; this one names none"
            )

        if self.total_bytes < 0 or self.used_bytes < 0 or self.free_bytes < 0:
            raise ValueError(
                f"{self.mount} reports a negative byte count: "
                f"total={self.total_bytes}, used={self.used_bytes}, "
                f"free={self.free_bytes}"
            )

        if self.used_bytes + self.free_bytes > self.total_bytes:
            raise ValueError(
                f"{self.mount} reports {self.used_bytes} used + "
                f"{self.free_bytes} free bytes, exceeding its own "
                f"reported total of {self.total_bytes}"
            )

    @property
    def percent_used(self) -> float:
        """
        `used_bytes` as a percentage of `total_bytes` — 0.0 for a
        volume this reads as having no capacity at all, rather than
        dividing by zero.
        """

        if self.total_bytes == 0:
            return 0.0

        return (self.used_bytes / self.total_bytes) * 100
