from dataclasses import dataclass

from aistack.contracts.runtime_observation import LogEntry


@dataclass(frozen=True)
class MatchedLine:
    """
    One log line, and where in it the signature was found.

    The position lives here rather than on `LogEntry` because it
    is not a property of the line. It is a property of the
    *encounter* between a declared rule and that line: the same
    line matched by two signatures has two positions, and a line
    a provider collected has none at all. `ARC-P-012` puts the
    provider on the far side of that boundary — it observes and
    concludes nothing, so it has nothing to say about a match.

    **`match_at` may be `None`, and it means one specific
    thing:** the pattern was found and its position in the
    original text could not be determined. That happens when a
    case-insensitive comparison folds characters whose folded
    length differs from the original — `ß` folds to `ss` — so an
    index into the folded text points somewhere else in the line
    the container printed. Reporting that index would centre an
    extract on the wrong characters and call it evidence.

    It is `None` rather than zero, because zero is a real
    position. FDN-0003 Article 12: the undetermined is declared,
    not replaced by a plausible default.
    """

    entry: LogEntry
    match_at: int | None = None

    def __post_init__(self) -> None:
        if self.match_at is not None and self.match_at < 0:
            raise ValueError(
                f"a match position is an index into the line: "
                f"{self.match_at}; use None when it could not be "
                f"determined"
            )

        if (
            self.match_at is not None
            and self.match_at > len(self.entry.text)
        ):
            raise ValueError(
                f"a match at {self.match_at} in a line of "
                f"{len(self.entry.text)} characters points outside "
                f"the evidence it cites"
            )


@dataclass(frozen=True)
class RuntimeFinding:
    """
    One qualified statement about a running subject.

    This is not an `IntegrityFinding`, and the difference is not
    symmetry. An `IntegrityFinding` speaks about the governed
    heritage, counts artifacts, and its contract states that "it
    proposes no remediation". A runtime finding speaks about the
    system the heritage describes, and STD-0300 § VS-4 criterion
    4.7 *requires* it to recommend one. Reusing the first would
    have broken its own declared contract.

    **`evidence` may not be empty, and that is enforced here
    rather than asked for.** Criterion 4.9 — no finding without
    at least one evidence reference — is a property of the type,
    so a finding that cannot cite what it saw cannot be
    constructed. This heritage spent two days on rules that were
    declared and enforced by nothing; this one is enforced by the
    constructor.

    `signature` carries the identifier of the rule that produced
    the finding — `OPS-0001/S-003`. That is criterion 4.7's
    citation, and it is why the rule had to be declared and
    identified rather than written into a function.

    Each piece of evidence is a `MatchedLine`: the line, and
    where the pattern was found in it. The position exists so a
    report can show what fired the rule. On 2026-08-22 the first
    complete run produced eleven `frigate` lines carrying three
    timestamps each, and the report's extract stopped before
    `connection refused` — everything about the evidence except
    what it proved.

    `interpretation` and `remediation` are copied from the
    signature at the moment of qualification, not looked up
    later. A finding read six months from now states what the
    rule said when it fired, not what the rule says today.

    Nothing here classifies the finding four ways. Criterion 4.5
    asks for that and this type does not attempt it: inventing a
    four-term vocabulary would be authoring governed knowledge,
    which GOV-P-001 forbids.
    """

    subject: str
    signature: str
    interpretation: str
    remediation: str
    confidence: str
    grounding: str
    evidence: tuple[MatchedLine, ...]

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError(
                "a finding is about a subject; this one names none"
            )

        if not self.signature.strip():
            raise ValueError(
                "a finding cites the signature that produced it "
                "(STD-0300 § VS-4, criterion 4.7)"
            )

        if not self.evidence:
            raise ValueError(
                f"{self.signature} produced a finding about "
                f"{self.subject!r} citing no evidence; STD-0300 § VS-4 "
                f"criterion 4.9 forbids it"
            )

        # An annotation is not a check. `tuple[MatchedLine, ...]`
        # accepted bare `LogEntry` objects without complaint when
        # this type changed on 2026-08-23, and every caller that
        # had not been updated kept passing — a declaration that
        # asserts a protection and delivers none, in the contract
        # written to stop exactly that.
        wrong = [
            type(item).__name__
            for item in self.evidence
            if not isinstance(item, MatchedLine)
        ]

        if wrong:
            raise ValueError(
                f"{self.signature} cites evidence of type "
                f"{sorted(set(wrong))}; a finding cites MatchedLine, "
                f"which carries the line and where the pattern was "
                f"found in it"
            )
