"""
`evaluate_quarantine` — quarantined code as technical debt (`OPS-0012`,
`OPS-0004`'s eighth reference case, decided by the owner 2026-10-05:
"c'est aussi de la gouvernance de gérer le code mort et obsolète. Ça
rentre dans la dette technique").

One finding per quarantined item, whatever its state: code waiting to
be deleted is debt until it is deleted. **Technical debt alone**: dead
code costs no energy at run time and misconfigures no deployment, so
the other three `OPS-0004` terms do not apply.

**Not a health domain.** The findings feed the "Dette technique" card
only, as one more group of findings beside the domains' own: the seven
domains `OPS-0008` weighs describe the host, and the quarantine
describes AIStack's own code.
"""

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.finding_message import FindingMessage, part
from aistack.contracts.quarantine_reading import READY, USED, QuarantineReading
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.quarantine.status import EntryStatus

TECHNICAL_DEBT = "OPS-0004/technical-debt"
QUARANTINE_QUALIFICATIONS = (TECHNICAL_DEBT,)

QUARANTINE_SOURCE = "aistack.quarantine.status.read_statuses"
SIGNATURE = "OPS-0012"


def reading_of(status: EntryStatus) -> QuarantineReading:
    return QuarantineReading(
        entry=status.entry.id,
        paths=status.entry.paths,
        since=status.entry.since,
        review_after=status.entry.review_after,
        state=status.state,
        uses=len(status.hits),
        last_use=status.hits[-1].at if status.hits else "",
    )


def evaluate_quarantine(found: Sequence[EntryStatus]) -> tuple[RuntimeFinding, ...]:
    return tuple(_finding(reading_of(status)) for status in found)


def _finding(reading: QuarantineReading) -> RuntimeFinding:
    what = ", ".join(reading.paths)
    values = {
        "entry": reading.entry,
        "paths": what,
        "since": str(reading.since),
        "review": str(reading.review_after),
        "uses": str(reading.uses),
        "last": reading.last_use,
    }
    if reading.state == USED:
        key = "used"
        interpretation = (
            f"{reading.entry} ({what}) is in quarantine since {reading.since} "
            f"but was used {reading.uses} time(s), last on {reading.last_use}: "
            f"it is not dead code."
        )
        remediation = (
            f"Take {reading.entry} out of src/aistack/quarantine/register.yml "
            f"and remove its tripwires: the code is still used."
        )
    elif reading.state == READY:
        key = "ready"
        interpretation = (
            f"{reading.entry} ({what}) has been in quarantine since "
            f"{reading.since} and was never used before its review date, "
            f"{reading.review_after}."
        )
        remediation = (
            f"Delete {reading.entry}'s files with the amendments the register "
            f"lists, then remove the entry."
        )
    else:
        key = "watched"
        interpretation = (
            f"{reading.entry} ({what}) is dead code in quarantine since "
            f"{reading.since}; no use recorded so far."
        )
        remediation = f"Nothing before {reading.review_after}, its review date."

    return RuntimeFinding(
        subject=reading.entry,
        signature=SIGNATURE,
        interpretation=interpretation,
        remediation=remediation,
        confidence="Measured",
        grounding=f"{SIGNATURE}/{reading.entry}",
        evidence=(CitedReading(provider=QUARANTINE_SOURCE, reading=reading),),
        qualifications=QUARANTINE_QUALIFICATIONS,
        # The same sentences as catalog keys (ADR-0010 § 4): the action
        # plan shows them in its reader's language.
        message=FindingMessage(
            interpretation=(part(f"findings.quarantine.{key}.interpretation", **values),),
            remediation=(part(f"findings.quarantine.{key}.remediation", **values),),
        ),
    )
