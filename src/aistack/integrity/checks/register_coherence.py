from collections import defaultdict
import re

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


REGISTER = "GOV-0002"

RESOLVED_SECTION = "Resolved"

SECTION = re.compile(r"^#\s+(?!GOV-)(.+?)\s*$")

ENTRY = re.compile(r"^####\s+GOV-0002/(OS-\d+)\s+—")

# `**Nature** `contract-debt` · **Opened** … · **State** open`
NATURE = re.compile(r"\*\*Nature\*\*\s+`([^`]+)`")

STATE = re.compile(r"\*\*State\*\*\s+(\w+)")

# The register documents its own entry form under "How an entry is
# written", using OS-000. It is a template, not an entry.
TEMPLATE = "OS-000"


class RegisterEntry:
    """One entry, and the three facts this check compares."""

    def __init__(self, identifier: str, section: str):
        self.id = identifier
        self.section = section
        self.nature: str | None = None
        self.state: str | None = None

    @property
    def is_resolved(self) -> bool:
        return self.state == "resolved"

    @property
    def sits_in_resolved(self) -> bool:
        return self.section == RESOLVED_SECTION


def read_entries(content: str) -> list[RegisterEntry]:
    """
    Every entry of the register, with the section holding it.

    Read positionally, like `principle-identifiers` reads FDN-0012:
    an entry is found by its heading, and its section by the last
    `#` heading above it. A reader that looked only for well-formed
    entries would not see a malformed one at all.
    """

    entries: list[RegisterEntry] = []
    section = ""
    current: RegisterEntry | None = None

    for line in content.splitlines():

        heading = SECTION.match(line)

        if heading:
            section = heading.group(1)
            current = None
            continue

        found = ENTRY.match(line)

        if found:
            if found.group(1) == TEMPLATE:
                current = None
                continue
            current = RegisterEntry(found.group(1), section)
            entries.append(current)
            continue

        if current is None:
            continue

        if current.nature is None:
            nature = NATURE.search(line)
            if nature:
                current.nature = nature.group(1)

        if current.state is None:
            state = STATE.search(line)
            if state:
                current.state = state.group(1)

    return entries


class RegisterCoherenceCheck(IntegrityCheck):
    """
    Observe a register that contradicts itself.

    GOV-0002 states each entry's condition twice: once in the
    `**State**` field, and once by the section the entry sits in.
    Two statements of one fact drift, and this one drifted twice
    in two days:

    - 2026-08-23, OS-023 and OS-024 were filed under *Defects*
      while declaring `non-conforming`;
    - 2026-08-27, OS-029 was filed under *Resolved* while
      declaring `State open` — an entry announcing itself as open
      inside the section for closed ones.

    Both were found by a human reading the file. Neither would
    have survived this check.

    Two rules, and neither needs a vocabulary this module would
    have to restate:

    - **an entry's state and its section agree.** `resolved`
      belongs under *Resolved* and nothing else does.
    - **the open sections are homogeneous.** Every open entry in
      one section declares the same nature as its neighbours.
      This deliberately does not map natures to section names:
      that mapping exists in the register's prose, and a second
      copy here would be one more pair of projections to drift
      apart — the defect STD-0100 names for the classification
      vocabulary.

    The severity is `WARNING`. A register whose own two statements
    of one fact disagree is not a state of the work; it is the
    record of the work being wrong about itself, and this register
    is the primary record of conditions no artifact states about
    itself.
    """

    @property
    def name(self) -> str:
        return "register-coherence"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        register = next(
            (a for a in bundle.artifacts if a.id == REGISTER), None
        )

        if register is None:
            # Not a silent pass, and not a warning: a partial
            # bundle may legitimately carry no register. Same
            # answer `principle-identifiers` gives to a projection
            # without FDN-0012.
            return [
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{REGISTER} is absent from this bundle; "
                        f"its entries are unverified, not coherent"
                    ),
                    affected=len(bundle.artifacts),
                    total=len(bundle.artifacts),
                )
            ]

        entries = read_entries(register.content)

        misplaced = [
            f"{entry.id} declares {entry.state} and sits under "
            f"{entry.section or 'no section'}"
            for entry in entries
            if entry.is_resolved != entry.sits_in_resolved
        ]

        by_section: dict[str, list[RegisterEntry]] = defaultdict(list)

        for entry in entries:
            if not entry.sits_in_resolved:
                by_section[entry.section].append(entry)

        mixed: list[str] = []

        for section, held in sorted(by_section.items()):

            natures = {entry.nature for entry in held}

            if len(natures) < 2:
                continue

            written = " · ".join(
                f"{nature} ({', '.join(sorted(e.id for e in held if e.nature == nature))})"
                for nature in sorted(natures, key=lambda n: n or "")
            )

            mixed.append(f"{section} → {written}")

        findings: list[IntegrityFinding] = []

        if misplaced:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.WARNING,
                    summary=(
                        f"{len(misplaced)} register entr(y/ies) "
                        f"declare a state their section contradicts"
                    ),
                    affected=len(misplaced),
                    total=len(entries),
                    unit="entries",
                    subjects=tuple(sorted(misplaced)),
                )
            )

        if mixed:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.WARNING,
                    summary=(
                        f"{len(mixed)} open section(s) hold entries "
                        f"of more than one nature"
                    ),
                    affected=len(mixed),
                    total=len(by_section),
                    unit="sections",
                    subjects=tuple(sorted(mixed)),
                )
            )

        return findings
