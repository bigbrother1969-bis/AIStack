from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Where a quarantined item stands (`OPS-0012`), the same three states
# `aistack.quarantine.status` computes.
WATCHED = "watched"
USED = "used"
READY = "ready"
STATES = (WATCHED, USED, READY)


@dataclass(frozen=True)
class QuarantineReading:
    """
    One quarantined item, as the health page's technical-debt card
    reads it (`OPS-0012`, `OPS-0004`'s eighth reference case, decided by
    the owner 2026-10-05: "c'est aussi de la gouvernance de gérer le
    code mort et obsolète. Ça rentre dans la dette technique").

    `entry` is the register's identifier (`Q-001`), `paths` what it
    holds, `review_after` the date it may be deleted from, `uses` how
    many uses its tripwires recorded and `last_use` when the last one
    was — empty when there was none.

    **`used` wins over `ready`.** An item used even once is not dead
    code, whatever the date: it leaves the quarantine rather than being
    deleted.
    """

    entry: str
    paths: tuple[str, ...]
    since: date
    review_after: date
    state: str
    uses: int = 0
    last_use: str = ""

    def __post_init__(self) -> None:
        if not self.entry.strip() or not self.paths:
            raise ValueError("a quarantine reading names its entry and what it holds")
        if self.state not in STATES:
            raise ValueError(f"unknown quarantine state {self.state!r}; OPS-0012 names {STATES}")
        if self.uses < 0:
            raise ValueError(f"{self.entry}: a count of uses is never negative")
        if (self.state == USED) != (self.uses > 0):
            raise ValueError(f"{self.entry}: an item is `used` exactly when a use was recorded")
