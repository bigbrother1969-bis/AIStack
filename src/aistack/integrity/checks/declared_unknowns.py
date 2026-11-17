import re

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


# `FDN-0003` Article 12: *"The absence of validated knowledge is a
# governed state... The absence of knowledge must remain visible."*
# `FDN-0009` § *Uncertainty in Collaboration* names the state
# **Unknown** as *"absent from the governed heritage, and declared as
# such"* — declared, not merely absent. These are the phrasings this
# heritage already uses to declare one: measured across the six
# artifacts that state one before this check existed (`GOV-0001`,
# `ARCH-0012`, `ARCH-0013`, `FDN-0005`, `FDN-0009`, `STD-0300`), not
# invented for the check.
MARKERS = (
    ("not-verified", re.compile(r"\bnot verified\b")),
    ("grounding-unknown", re.compile(r"`grounding:\s*unknown`")),
    ("recorded-as-lost", re.compile(r"\brecorded as lost\b")),
    ("does-not-decide", re.compile(r"\bdoes not decide\b")),
    ("keeps-no-definition", re.compile(r"\bkeeps no definition\b")),
)

# An `Open Points` (or `Open Point`) heading names a whole section as
# undecided — the strongest form of the declaration. Matched as a
# heading line rather than as a substring: `undated_assertions` and
# `claude_note_references` already show that "open point" also occurs
# in prose *about* the pattern, which is not itself an instance of it.
OPEN_POINTS_HEADING = re.compile(r"^#{1,3}\s*Open Points?\s*$")

QUOTING = ("*", "`", '"')


def is_quoted(line: str, at: int) -> bool:
    """
    Whether the marker sits inside a quotation.

    Identical reasoning to `undated_assertions.is_quoted`: this
    heritage quotes its own vocabulary when describing it — this very
    check's own docstring and `STD-0300`'s explanatory prose both name
    every marker above in backticks or italics — and a line stating
    what the markers *are* is not an instance of one. Detected by
    parity, line-scoped: an odd count of `*`, a backtick or a quote
    before the marker means it sits inside one. A line beginning with
    `>` is a block quotation entire.
    """

    if line.lstrip().startswith(">"):
        return True

    before = line[:at]

    return any(before.count(char) % 2 == 1 for char in QUOTING)


def declared_unknowns(content: str) -> list[tuple[int, str]]:
    """Every line declaring an unknown by one of this heritage's own markers."""

    found: list[tuple[int, str]] = []

    for number, line in enumerate(content.splitlines(), 1):

        stripped = line.strip()

        if OPEN_POINTS_HEADING.match(stripped):
            found.append((number, stripped))
            continue

        for _label, marker in MARKERS:

            match = marker.search(line)

            if match is None:
                continue

            if is_quoted(line, match.start()):
                continue

            found.append((number, line.strip()))
            break

    return found


class DeclaredUnknownCheck(IntegrityCheck):
    """
    Observe every line declaring an unknown by this heritage's own markers.

    `STD-0300` criterion 2.4, reworded 2026-09-25 (`GOV-0002/OS-071`),
    asks two agents of different models to cover the same canonical set
    of declared unknowns rather than agree on a free-text list — the
    interactive judgement § 8 of the same suite excludes. This check is
    the extraction that reformulation left to build: it publishes the
    set a Boot Report's own declared uncertainties can be measured
    against.

    **The severity is `OBSERVATION`, for the reason § 8 states and
    `claude_note_references` already applies.** A line carrying one of
    these markers is derivable by pattern; whether the condition it
    names is still open, or has since been resolved by a `GOV-0002`
    entry whose text sits elsewhere in the heritage, is a reading —
    exactly the comparison a criterion may not require. `FDN-0010` §
    *Provenance* is the clearest case in this heritage: its original
    *"does not decide the overlap"* sentence is kept verbatim beside
    the dated note that resolved `GOV-0002/OS-062`, per § *What a
    closure must carry* — this check reports the line precisely
    because the resolution does not delete it. A `WARNING` would make
    `clean: False` on a condition already qualified; what is derivable
    is where to look, not whether looking is still owed an answer.

    **Coverage, not precision, is what this check measures.** It finds
    every line matching a known marker; it does not decide whether the
    heritage's own list of markers is complete, and a marker this
    heritage has not yet used to declare an unknown will not be found
    until it is added here — the same limit `undated-assertions`
    states about its own four words.
    """

    @property
    def name(self) -> str:
        return "declared-unknowns"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        subjects: list[str] = []

        for artifact in bundle.artifacts:

            for number, line in declared_unknowns(artifact.content):

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
                    f"{len(subjects)} line(s) declare an unknown by one "
                    f"of this heritage's own markers (Open Points "
                    f"heading, `not verified`, `grounding: unknown`, "
                    f"recorded as lost, does not decide, keeps no "
                    f"definition)"
                ),
                affected=len(subjects),
                total=len(bundle.artifacts),
                unit="lines",
                subjects=tuple(sorted(subjects)),
            )
        ]
