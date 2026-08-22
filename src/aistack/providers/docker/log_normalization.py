from __future__ import annotations

from datetime import datetime

from aistack.contracts.runtime_observation import (
    LogEntry,
    RuntimeObservation,
)


def split_timestamp(line: str) -> tuple[datetime | None, str]:
    """
    Separate the prefix `docker logs --timestamps` adds.

    Docker writes RFC 3339 with nanoseconds — more precision than
    `datetime` carries — so the fractional part is truncated to
    microseconds rather than refused. Truncating loses a
    resolution nothing here uses; refusing would lose the age of
    every line.

    A line whose prefix does not parse is returned whole, with no
    timestamp. That happens when the caller collected without
    `--timestamps`, and the honest result is "the age is
    unknown", not a guess.
    """

    head, separator, tail = line.partition(" ")

    if not separator:
        return None, line

    candidate = head

    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    if "." in candidate:
        seconds, _, fraction = candidate.partition(".")
        digits = fraction[:6]
        offset = fraction[len(digits) :].lstrip("0123456789")
        candidate = f"{seconds}.{digits}{offset}"

    try:
        return datetime.fromisoformat(candidate), tail
    except ValueError:
        return None, line


def normalize_log_evidence(
    raw: str,
    *,
    subject: str,
    provider: str,
    depth: int,
    collected_at: datetime,
) -> RuntimeObservation:
    """
    Turn what a container printed into a canonical observation.

    ADR-0008 separates *Evidence* from *Evidence Normalization*,
    and this is the second stage. The first produced a block of
    text; this one gives each line an identity so that a finding
    can point at it — STD-0300 § VS-4 criterion 4.9 asks for an
    evidence reference, and "the logs" references nothing.

    ARC-P-013 is the reason the stage exists at all. The
    experimenter this replaces asked `"AUTH_FAILED" in logs` of
    an undifferentiated blob; a qualifier reading the result of
    this function receives identified entries instead of text.

    The timestamp Docker prefixes with `--timestamps` is split
    off and carried in its own field. Leaving it inside the text
    would make every signature compare against a prefix no
    container printed — and a pattern like `2026` would match
    every line of every log.

    **Nothing else here interprets.** Lines are kept verbatim: no
    trimming of content, no case folding, no filtering. A
    signature that matched a line the pipeline had already
    reworded would cite something that never appeared on the
    host, and comparison is the qualifier's business anyway —
    `Signature.case_sensitive` says how, per rule.

    Offsets count back from the newest line: 0 is the last line
    printed, 1 the one before it. That direction is the useful
    one — a reader asks "how far back did this appear", not
    "which line number was it in a window whose start moves".

    An empty output yields an observation with no entries rather
    than no observation. "Nothing was printed" is a fact about
    the subject; returning nothing would make it
    indistinguishable from "nothing was looked at".
    """

    lines = raw.split("\n")

    if lines and lines[-1] == "":
        # `docker logs` terminates its output with a newline.
        # Splitting on it yields a trailing empty element that no
        # container ever printed.
        lines.pop()

    last = len(lines) - 1

    entries = []

    for index, line in enumerate(lines):
        timestamp, text = split_timestamp(line)
        entries.append(
            LogEntry(
                offset=last - index,
                text=text,
                timestamp=timestamp,
            )
        )

    return RuntimeObservation(
        subject=subject,
        provider=provider,
        collected_at=collected_at,
        depth=depth,
        entries=tuple(entries),
    )
