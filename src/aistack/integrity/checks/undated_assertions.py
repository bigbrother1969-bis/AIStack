import re

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


# The words STD-0100 v2.5 asks to date. Four of the six it listed
# until 2026-08-27: `still` and `remains` were measured and
# removed, because they overwhelmingly carry timeless statements —
# *the repository remains the authoritative source* hides no date.
MARKERS = ("today", "currently", "not yet", "for now")

MARKER = re.compile(
    r"\b(" + "|".join(m.replace(" ", r"\s+") for m in MARKERS) + r")\b",
    re.I,
)

# A date, or a commit hash in backticks. Either discharges the
# rule: the sentence says when it was true.
DATED = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|`[0-9a-f]{7,40}`")

QUOTING = ("*", "`", '"')


def is_quoted(line: str, at: int) -> bool:
    """
    Whether the marker sits inside a quotation.

    A quotation is not an assertion. This heritage quotes its own
    retired sentences on purpose — STD-0100 prints
    *"which it does not today"* as the example of the defect it
    forbids — and a check that read those as defects would report
    a standard for teaching its own rule.

    Detected by parity: an odd count of `*`, a backtick or a
    quote before the marker means the marker is inside one. A
    line beginning with `>` is a block quotation entire.

    **This is why no artifact is excluded by name.** The register
    quotes the marker list too, and excluding a file for being
    noisy would be the check adapting to the data rather than to
    the rule.
    """

    if line.lstrip().startswith(">"):
        return True

    before = line[:at]

    return any(before.count(char) % 2 == 1 for char in QUOTING)


def undated_lines(content: str) -> list[tuple[int, str]]:
    """Every line asserting something without saying when."""

    found: list[tuple[int, str]] = []

    for number, line in enumerate(content.splitlines(), 1):

        marker = MARKER.search(line)

        if marker is None:
            continue

        if DATED.search(line):
            continue

        if is_quoted(line, marker.start()):
            continue

        found.append((number, line.strip()))

    return found


class UndatedAssertionCheck(IntegrityCheck):
    """
    Observe sentences that mean "at the time of writing" and do
    not say when that was.

    STD-0100 v2.3 states the rule: an assertion about the code
    carries its date and its commit. GOV-0002/OS-017 recorded six
    occurrences in three C2 artifacts over two days, two of them
    *inside the documents that state the rule*, and the owner
    decided on 2026-08-23 that the pattern check was worth its
    false positives.

    **It publishes `OBSERVATION`, and that is the whole design.**
    Whether a sentence carrying a marker has gone stale is not
    derivable — OS-017 says so in its own text. What is derivable
    is where to look. A `WARNING` would make `clean: False` on
    prose that is perfectly correct, and the report would be
    obeyed by deletion rather than read.

    **The precision is known and stated rather than hoped for.**
    Measured 2026-08-27 across 66 artifacts: 20 lines, of which
    roughly a third are assertions that have gone or could go
    stale, and the rest are rhetoric — *Ollama today and another
    engine tomorrow* — or definitions. A reader scans twenty lines
    and decides. That is the instrument this check is: it does not
    know which sentences are wrong, and it does not pretend to.
    """

    @property
    def name(self) -> str:
        return "undated-assertions"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        subjects: list[str] = []

        for artifact in bundle.artifacts:

            for number, line in undated_lines(artifact.content):

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
                    f"{len(subjects)} line(s) assert something "
                    f"about a moving system without saying when "
                    f"({' · '.join(MARKERS)})"
                ),
                affected=len(subjects),
                total=len(bundle.artifacts),
                unit="lines",
                subjects=tuple(sorted(subjects)),
            )
        ]
