import re

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


# A note under `claude/` is a working note — an AI session record or a
# plan, kept outside the projection, with no owner and no version
# (GOV-0002 § Purpose). Citing one by its backtick-quoted path names
# where a fact or a decision was first written down. STD-0100 § *A
# `claude/` note is provenance, not the only place that states it*
# permits exactly that and forbids the note from being the only place
# that states it.
#
# A bare `claude/` (no path, no `.md`) names the directory, the way
# GOV-0002 § Purpose itself does, and is not a citation of one note —
# the pattern requires a `.md` path so that sentence is not matched.
NOTE = re.compile(r"`claude/[^`]+\.md`")


def note_citations(content: str) -> list[tuple[int, str]]:
    """
    Every line citing a `claude/` note by its backtick-quoted path.

    A block quotation is not a citation: STD-0100 prints a retired,
    hypothetical example of the defect this pattern names, and a
    check reporting its own worked example would be indistinguishable
    from one that found a real occurrence — the same reasoning
    `undated_assertions.is_quoted` applies to `>` already.
    """

    found: list[tuple[int, str]] = []

    for number, line in enumerate(content.splitlines(), 1):

        if line.lstrip().startswith(">"):
            continue

        if NOTE.search(line):
            found.append((number, line.strip()))

    return found


class ClaudeNoteReferenceCheck(IntegrityCheck):
    """
    Observe lines that cite a `claude/` working note by path.

    STD-0100 permits a `claude/` citation as provenance and forbids
    it from being the only place that states what it names — a
    reader handed the Context Bundle alone cannot open a note outside
    the projection, and a fact that lives only there is not
    derivable from the heritage it is part of (`FDN-0003` Article
    12). Until `GOV-0002/OS-069` (2026-09-23), `ENG-TEST-0002` cited
    decision #9 from `claude/PLAN-UI-SELECTION-2026-08-29.md` as its
    only statement, which is exactly the shape this check exists to
    surface.

    **The severity is `OBSERVATION`, the design `undated-assertions`
    and `reference-integrity` already use.** Whether a given citation
    is the sole statement of what it names is a reading — it asks
    what the rest of the artifact says, not what the line itself
    says — and `STD-0300` § 8 is explicit that a scenario requiring
    that judgement is not yet a criterion. A `WARNING` would make
    `clean: False` on a citation that already restates its fact in
    the surrounding prose, which is the ordinary case. What is
    derivable is where to look.

    **Audited by hand on 2026-09-25, `GOV-0002/OS-070`: 44 citations
    across 9 artifacts, none the sole statement.** `GOV-0002` alone
    carries 24, each inside an *Observed* paragraph that states the
    fact the note is cited for; `OPS-0004` through `OPS-0008` each
    close on *"records the exchange that produced each value"*,
    naming the note for the interview it records rather than for a
    value found nowhere else. This check exists so that audit does
    not have to be repeated by hand: the next citation it lists is
    the one to read.
    """

    @property
    def name(self) -> str:
        return "claude-note-references"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        subjects: list[str] = []

        for artifact in bundle.artifacts:

            for number, line in note_citations(artifact.content):

                excerpt = line if len(line) <= 90 else line[:87] + "…"

                subjects.append(
                    f"{artifact.source}:{number} — {excerpt}"
                )

        if not subjects:
            return []

        return [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.OBSERVATION,
                summary=(
                    f"{len(subjects)} line(s) cite a `claude/` note by "
                    f"path; STD-0100 permits this as provenance only, "
                    f"never as the sole statement of a fact or decision"
                ),
                affected=len(subjects),
                total=len(bundle.artifacts),
                unit="lines",
                subjects=tuple(sorted(subjects)),
            )
        ]
