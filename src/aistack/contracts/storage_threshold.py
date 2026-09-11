from __future__ import annotations

from dataclasses import dataclass

# The two threshold kinds `OPS-0005` declares — no more without the
# owner naming a third, the same discipline `OPS-0004`'s vocabulary
# holds for qualifications, applied here to threshold *shape* rather
# than to qualification names.
FREE_BYTES = "free_bytes"
PERCENT_USED = "percent_used"

KINDS = (FREE_BYTES, PERCENT_USED)


@dataclass(frozen=True)
class StorageThreshold:
    """
    One volume's own declared alert threshold — `OPS-0005`, not a
    value this heritage chose. `GOV-P-001`: the owner states the
    number; this type only shapes it so `find_storage_shortage` can
    compare a reading against it without inventing what "too full"
    means for a volume no case has named a value for.

    Two kinds, because a percentage does not mean the same thing on
    every volume — `OPS-0005` § *Why two kinds of threshold* is the
    reasoning this type encodes: `FREE_BYTES` for a volume where
    absolute headroom is what matters (an OS volume — the Raspberry's
    15G root and GIGABYTE's 212G root both read "72% occupied" while
    leaving twenty times less room on one of them), `PERCENT_USED`
    for one where relative occupancy is (a media volume).

    `value` is in bytes for `FREE_BYTES`, in percent (0-100) for
    `PERCENT_USED` — never both, and the caller states which by
    naming `kind`, not by the magnitude of the number.
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
