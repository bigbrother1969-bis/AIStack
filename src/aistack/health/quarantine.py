"""
The quarantine as the health page reads it (`OPS-0012`): the findings
the "Dette technique" card counts, and the readings its line shows.
Shared by `health_render` and `console_render`, so both cards compute
the same score.
"""

from __future__ import annotations

from datetime import date

from aistack.contracts.quarantine_reading import QuarantineReading
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.quarantine.status import read_statuses
from aistack.runtime.evaluate_quarantine import evaluate_quarantine, reading_of


def quarantine_findings(
    today: date,
) -> tuple[tuple[RuntimeFinding, ...], tuple[QuarantineReading, ...], str]:
    """`(findings, readings, "")`, or `((), (), note)` when the register
    cannot be read — named on the page, never a failed page."""

    try:
        found = read_statuses(today)
    except (OSError, ValueError) as error:
        return (), (), f"quarantine register not readable ({error})"
    return evaluate_quarantine(found), tuple(reading_of(status) for status in found), ""
