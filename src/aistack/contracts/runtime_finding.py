from dataclasses import dataclass

from aistack.contracts.runtime_observation import LogEntry


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
    evidence: tuple[LogEntry, ...]

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
