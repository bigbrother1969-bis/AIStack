from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class LogEntry:
    """
    One line of a container's log, with its position so a finding can
    cite it.

    `offset` counts back from the newest line read (0 is the most
    recent). `text` is verbatim. `timestamp` comes from Docker's
    `--timestamps`, kept out of `text` so signatures match what the
    container printed; `None` when unknown.
    """

    offset: int
    text: str
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError(
                f"a log entry offset counts back from the newest "
                f"line and cannot be negative: {self.offset}"
            )


@dataclass(frozen=True)
class RuntimeObservation:
    """
    What was observed of one running subject, in canonical form. A
    provider produces it and concludes nothing.

    `state` is the runtime's state (`running`, `exited`, ...); each
    signature declares the states in which it applies, since a
    container shutting down prints harmless connection refusals.

    `depth` is the number of lines read, so a signature whose window is
    deeper than what was collected can tell "absent" from "out of range".
    """

    subject: str
    provider: str
    state: str
    collected_at: datetime
    depth: int
    entries: tuple[LogEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.state:
            raise ValueError(
                "an observation carries the state of its subject; a "
                "signature declares the states in which it has meaning"
            )

        if not self.subject:
            raise ValueError(
                "an observation without a subject observes nothing"
            )

        if self.depth < 0:
            raise ValueError(
                f"depth is a number of lines read: {self.depth}"
            )

        if len(self.entries) > self.depth:
            raise ValueError(
                f"{len(self.entries)} entries were collected while "
                f"depth declares {self.depth} lines were read"
            )
