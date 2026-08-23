from __future__ import annotations

from aistack.contracts.runtime_finding import (
    MatchedLine,
    RuntimeFinding,
)
from aistack.contracts.runtime_observation import (
    LogEntry,
    RuntimeObservation,
)
from aistack.contracts.signature import Signature, SignatureCatalogue


# What `locate` returns when the pattern is present and its
# position in the original text cannot be determined.
FOUND_SOMEWHERE = -1


def locate(signature: Signature, entry: LogEntry) -> int | None:
    """
    Where one declared pattern sits in one log line.

    Returns the index, `FOUND_SOMEWHERE` when the pattern is
    present but its position is not determinable, or `None` when
    it is absent.

    Comparison is a property of the signature, not of this
    function. Three of the four rules the experimenter
    established compared the text as written; the fourth compared
    `logs.lower()`. `Signature.case_sensitive` carries that
    difference, and it has no default so that no rule inherits a
    comparison it never chose.

    **The case-insensitive branch searches the folded text, and
    the folded text can be a different length.** `ß` folds to
    `ss`, and one such character before the match shifts every
    index after it. The comparison stays exact — folding is what
    decides presence — but the index is then a position in a
    string no container printed, so it is refused rather than
    reported. An extract centred on the wrong characters would
    be worse than one centred on nothing.
    """

    if signature.case_sensitive:
        found = entry.text.find(signature.pattern)
        return None if found < 0 else found

    folded = entry.text.casefold()

    found = folded.find(signature.pattern.casefold())

    if found < 0:
        return None

    if len(folded) != len(entry.text):
        return FOUND_SOMEWHERE

    return found


def matches(signature: Signature, entry: LogEntry) -> bool:
    """Whether one declared pattern is present in one log line."""

    return locate(signature, entry) is not None


def qualify(
    observation: RuntimeObservation,
    catalogue: SignatureCatalogue,
) -> list[RuntimeFinding]:
    """
    Qualify one observation against the declared policies.

    This is the only stage of the chain that concludes anything.
    Collection observes (ARC-P-012), normalization identifies,
    and here evidence is read against governed knowledge —
    ADR-0009 § 2 calls it the inversion: the heritage is *read*
    to qualify reality, rather than written from it. The result
    is a disposable report under ENG-P-003, never a Knowledge
    Asset.

    **One finding per signature that fired**, carrying every line
    it matched. Not one finding per line: a pattern present forty
    times is one condition observed forty times, and forty
    findings would report the volume as if it were the number of
    problems.

    Nothing is truncated. A signature matching five hundred lines
    produces a finding citing five hundred, because a cap applied
    quietly would make the report read as complete when it was
    not — and `subjects` elsewhere in this heritage was capped
    once, silently, with the same consequence.

    **A signature is skipped where it means nothing.** The state
    of the subject is observed; whether a rule applies to that
    state is declared by the rule. `frigate` is stopped on
    purpose on this deployment, and the connection refusals an
    nginx prints while its backend goes away are not a fault —
    the detection was exact and the remediation was empty. That
    is an applicability error, not a detection error, and it is
    fixed where applicability is declared.

    A shallower observation than the catalogue requires is
    refused rather than evaluated. A signature declaring a window
    of two thousand lines against an observation of one hundred
    would silently not fire, and *absent* would be
    indistinguishable from *out of range*. The caller collects at
    `catalogue.deepest`; reaching this error means it did not.
    """

    if catalogue.deepest > observation.depth:
        raise ValueError(
            f"{catalogue.artifact} declares a window of "
            f"{catalogue.deepest} lines and the observation of "
            f"{observation.subject!r} reads {observation.depth}: "
            f"some signatures could not fire, and their silence "
            f"would not mean absence"
        )

    findings: list[RuntimeFinding] = []

    for signature in catalogue.signatures:

        if not signature.applies(observation.state):
            continue

        evidence = tuple(
            MatchedLine(
                entry=entry,
                match_at=None if at == FOUND_SOMEWHERE else at,
            )
            for entry, at in (
                (entry, locate(signature, entry))
                for entry in observation.entries
                if entry.offset < signature.depth
            )
            if at is not None
        )

        if not evidence:
            continue

        findings.append(
            RuntimeFinding(
                subject=observation.subject,
                signature=signature.identifier,
                interpretation=signature.interpretation,
                remediation=signature.remediation,
                confidence=signature.confidence,
                grounding=signature.grounding,
                evidence=evidence,
            )
        )

    return findings
