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


def declares_implementation(content: str) -> bool:
    """
    Whether the artifact carries the section at all.

    Separate from having rows, because the two say different
    things. A section with no rows is a decision whose author
    described its state some other way; **no section is a
    decision nobody has asked about since the day it was
    accepted**, and until 2026-08-27 nothing here could tell that
    from a decision fully implemented.
    """

    return any(
        line.strip() == SECTION for line in content.splitlines()
    )


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

    **Two findings, and the second was the larger half.** Measured
    2026-08-27 across nine accepted ADRs: one carried a table, two
    carried the same knowledge in prose — ADR-0003 (*four of the
    five criteria […] have no strategy yet*) and ADR-0005 (*The
    migration below has not happened*) — and six declared nothing
    at all.

    A check reading only tables would have reported zero on that
    heritage and read as coverage. **An accepted decision silent
    about its implementation is not a decision that was
    implemented**, and until STD-0100 v2.6 nothing could tell the
    two apart. The owner decided on 2026-08-27 that an accepted
    decision declares its implementation state in a form this
    heritage can read; this reports the ones that do not.

    **The two findings do not carry the same severity, decided
    2026-08-27 by the owner**, and the reason is STD-P-002:

    - *an accepted decision declaring no implementation state*
      is a governance gap that STD-0100 v2.6 forbids. It is a
      `WARNING`, **raised on 2026-08-28 in the commit that brought
      the count to 0 of 9** and not before — a check turned red
      earlier would have enforced a rule by blocking publication
      of its own fix, since OPS-0002 § 1 makes `clean: True` a
      condition of publishing. From here the rule bites on the
      next accepted decision that declares nothing, which is what
      it was written for;
    - *an implementation row in no terminal state* stays
      `OBSERVATION`, permanently. Specification precedes
      implementation, so an unfinished row is the ordinary state
      of work rather than a fault, and a row left `unqualified` is
      FDN-0003 Article 12 working: the absence of a decision made
      visible.

    **The split was decided on a consequence rather than a
    preference.** Raised together, an unfinished row would make
    `clean: False` for as long as it stayed open, so every
    publication would need the OPS-0002 § 1 exception and an open
    register entry per row — which is pressure to delete the rows,
    and a table holding only `done` asserts that a decision is
    fully implemented. The severity that punished honesty would
    have bought silence.

    That sequencing produced a rule of its own: OPS-0002 § 1 now
    admits a warning an open register entry names, so the next
    check to be raised does not have to be raised last.
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

        unfinished: list[str] = []
        undeclared: list[str] = []

        for artifact in decisions:

            rows = implementation_rows(artifact.content)

            # `if/else` rather than an early `continue`: with no
            # rows the loop below runs zero times anyway, so a
            # `continue` there was dead — it survived its mutation
            # because nothing could tell it from its own absence.
            # The exclusivity is real and is now structural.
            if not rows:
                undeclared.append(
                    f"{artifact.id} — "
                    + (
                        "the section carries no readable table"
                        if declares_implementation(artifact.content)
                        else "no implementation state is declared"
                    )
                )

            else:
                for step, state in rows:

                    if is_terminal(state):
                        continue

                    unfinished.append(
                        f"{artifact.id} — {step} → {state}"
                    )

        findings: list[IntegrityFinding] = []

        if undeclared:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.WARNING,
                    summary=(
                        f"{len(undeclared)} accepted decision(s) "
                        f"declare no implementation state this "
                        f"heritage can read"
                    ),
                    affected=len(undeclared),
                    total=len(decisions),
                    unit="decisions",
                    subjects=tuple(sorted(undeclared)),
                )
            )

        if unfinished:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(unfinished)} implementation row(s) of "
                        f"an accepted decision are in no terminal "
                        f"state ({' · '.join(TERMINAL)})"
                    ),
                    affected=len(unfinished),
                    total=len(decisions),
                    unit="rows",
                    subjects=tuple(sorted(unfinished)),
                )
            )

        return findings
