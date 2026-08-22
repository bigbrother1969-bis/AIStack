from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class LogEntry:
    """
    One line of a container's log, carrying its position.

    The position is what makes a finding citable. STD-0300 § VS-4
    criterion 4.9 requires that no finding be emitted without at
    least one evidence reference, and a reference to "the logs"
    references nothing. `offset` counts back from the newest line
    read: 0 is the most recent, 1 the one before it.

    The text is kept verbatim. Normalization here means giving
    each line an identity, not rewriting it — a signature that
    matched a line the heritage had already reworded would be
    citing something that never appeared on the host.
    """

    offset: int
    text: str

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError(
                f"a log entry offset counts back from the newest "
                f"line and cannot be negative: {self.offset}"
            )


@dataclass(frozen=True)
class RuntimeObservation:
    """
    What was observed of one running subject, in canonical form.

    ARC-P-013 requires that evaluation consume canonical
    knowledge models and never raw technical output. The
    experimenter this replaces matched substrings against an
    undifferentiated blob of text; a qualifier reading this model
    receives identified entries it can point back at.

    ARC-P-012 places the boundary: a provider produces this and
    concludes nothing. No field here says whether anything is
    wrong.

    `depth` is the number of lines that were read, and it is
    recorded rather than assumed. A signature declaring a window
    deeper than what was collected cannot fire, and the
    difference between *absent* and *out of range* is only
    visible if the depth travelled with the observation.
    """

    subject: str
    provider: str
    collected_at: datetime
    depth: int
    entries: tuple[LogEntry, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
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
