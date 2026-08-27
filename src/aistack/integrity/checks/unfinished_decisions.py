import re

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


ADR = "ADR"

ACCEPTED = "Accepted"

SECTION = "## Implementation state"

# `| Step | State |` — two cells, nothing else.
ROW = re.compile(r"^\|(?P<step>[^|]+)\|(?P<state>[^|]+)\|\s*$")

SEPARATOR = re.compile(r"^\|[\s:|-]+\|\s*$")

EMPHASIS = "*`_"

# What discharges a row. Read as the first word of the state
# cell: `done — 2026-08-22`, `**abandoned — 2026-08-27** — see § 6`.
#
# The vocabulary is short on purpose. A row saying anything else —
# `not started`, `in progress`, `blocked`, `partial`, or a
# sentence — is a row somebody has to read again, which is the
# whole subject.
TERMINAL = ("done", "abandoned", "superseded")


def plain(cell: str) -> str:
    """A table cell without its emphasis."""

    return cell.strip().strip(EMPHASIS).strip()


def is_terminal(state: str) -> bool:
    return plain(state).lower().startswith(TERMINAL)


def implementation_rows(content: str) -> list[tuple[str, str]]:
    """
    The rows of the first table under `## Implementation state`.

    **The first table, and the stopping rule is not decoration.**
    ADR-0009 carries a second table inside the same section, under
    a `###` heading — *What the retirement delivered* — whose cells
    are commands rather than states. A parser that collected every
    row of the section would read `python3 -m aistack.cli.
    runtime_diagnose` as a step in a non-terminal state and report
    it forever.

    Read positionally, like `principle-identifiers` reads FDN-0012
    and `register-coherence` reads this register: the header row
    is whatever precedes the separator, and the body ends at the
    first line that is not a row. A parser that looked only for
    well-formed rows would not see a malformed one at all.
    """

    rows: list[tuple[str, str]] = []
    inside = False
    in_body = False

    for line in content.splitlines():

        if line.startswith("## "):

            # The first `## Implementation state` section is the
            # answer, including when that answer is nothing. A
            # reset of `in_body` was written here and removed: it
            # survived its mutation, because this break makes the
            # state unable to leak into a second section in the
            # first place.
            if inside:
                break

            inside = line.strip() == SECTION
            continue

        if not inside:
            continue

        if SEPARATOR.match(line):
            in_body = True
            continue

        found = ROW.match(line)

        if not in_body:
            continue

        if found is None:
            break

        rows.append(
            (plain(found.group("step")), found.group("state").strip())
        )

    return rows


class UnfinishedDecisionCheck(IntegrityCheck):
    """
    Observe an accepted decision whose implementation table still
    holds a row nobody has closed.

    ADR-0009 was accepted on 2026-08-22 carrying a row that read
    *not built, and not a blocker*, and it read that for five days
    while nothing surfaced it. The register did not know: a table
    cell is not an entry, and `docs/99-meta/roadmap/` — where
    intentions belong — is outside the projection. It took
    retiring a container for someone to notice
    (GOV-0002/OS-035).

    **Restricted to `Accepted` ADRs.** A proposed decision is
    allowed to be unimplemented; that is what proposing means. An
    accepted one whose implementation is unfinished is an open
    state of the system filed somewhere the register cannot see.

    **`OBSERVATION`, and the severity is the design.** An
    unfinished row is not a fault — STD-P-002 puts specification
    before implementation, so a decision necessarily precedes its
    code. What is wrong is nobody being told. A `WARNING` would
    make `clean: False` on a heritage doing exactly what its own
    principle prescribes.

    **What this check does not reach, measured 2026-08-27 and
    stated rather than left to be discovered:** of nine accepted
    ADRs, one carries an implementation table, two carry the same
    knowledge in prose — ADR-0003 (*four of the five criteria […]
    have no strategy yet*) and ADR-0005 (*The migration below has
    not happened*) — and six declare nothing at all about their
    implementation. This check sees the first. GOV-0002/OS-038
    carries the other eight, because a check whose blind spot is
    known and unwritten is worse than no check: it reads as
    coverage.
    """

    @property
    def name(self) -> str:
        return "unfinished-decisions"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        decisions = [
            artifact
            for artifact in bundle.artifacts
            if artifact.declared_type == ADR
            and artifact.status == ACCEPTED
        ]

        subjects: list[str] = []

        for artifact in decisions:

            for step, state in implementation_rows(artifact.content):

                if is_terminal(state):
                    continue

                subjects.append(f"{artifact.id} — {step} → {state}")

        if not subjects:
            return []

        return [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.OBSERVATION,
                summary=(
                    f"{len(subjects)} implementation row(s) of an "
                    f"accepted decision are in no terminal state "
                    f"({' · '.join(TERMINAL)})"
                ),
                affected=len(subjects),
                total=len(decisions),
                unit="rows",
                subjects=tuple(sorted(subjects)),
            )
        ]
