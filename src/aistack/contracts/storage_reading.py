from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StorageReading:
    """
    One filesystem's reported capacity at one point in time.

    A reading, not a verdict: `aistack.runtime.storage_shortage` judges
    it. `mount` is the mount point (`/`, `/media/Films`), not the device,
    since thresholds are declared per mount (OPS-0005).

    Only `used_bytes + free_bytes <= total_bytes` is enforced: reserved
    blocks (ext4 keeps 5% by default) are neither used nor free.
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
        """`used_bytes` as a percentage of `total_bytes`; 0.0 when total is 0."""

        if self.total_bytes == 0:
            return 0.0

        return (self.used_bytes / self.total_bytes) * 100
