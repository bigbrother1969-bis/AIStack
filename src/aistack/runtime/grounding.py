from __future__ import annotations

from aistack.contracts.lifecycle import INTERMITTENT, LifecycleRegister
from aistack.contracts.runtime_finding import RuntimeFinding


def ground_findings(
    findings: list[RuntimeFinding] | tuple[RuntimeFinding, ...],
    register: LifecycleRegister,
) -> tuple[RuntimeFinding, ...]:
    """
    Add the owner's own lifecycle context to a finding, where one has
    been declared. `STD-0300` § VS-4 criterion 4.7, advanced
    2026-09-04.

    `qualify()` produces `grounding: unknown` for every signature in
    `OPS-0001`, and `test_every_governed_signature_declares_its_
    grounding_as_unknown` in this heritage's own test suite asserts
    that stays true — the general remediation genuinely presupposes
    a dependency policy this heritage does not declare, for any of
    the four signatures, and that stays honestly unresolved here.

    **This does not ground the signature. It grounds the finding.**
    Where the owner has declared, through `LifecycleRegister`, that
    the *subject* a finding is about is stopped and started on
    purpose, that is real, stated, applicable knowledge about this
    one finding that the general signature cannot carry — a
    declaration names one container, and a signature is written
    before any container exists to name. Citing it here, at the
    finding, is where it belongs.

    **Nothing is removed or replaced.** The signature's own
    interpretation and remediation survive verbatim, because the
    lifecycle declaration does not prove the evidence is harmless —
    `frigate` stopping on purpose does not mean every future finding
    about `frigate` is the same shutdown transition. What is added
    is the fact a reader needs to judge that for themselves: the
    container is declared intermittent, by whom, and why, before the
    original remediation is spent chasing it. A blanket suppression
    would be exactly the silent hiding `ADR-0009` and this finding
    type's own contract (`RuntimeFinding.evidence` may not be empty)
    exist to prevent.

    A finding whose subject carries no declaration is returned
    unchanged — `LifecycleRegister.for_container` returning `None`
    is a real absence, not a `continuous` this function would be
    inventing.
    """

    grounded: list[RuntimeFinding] = []

    for finding in findings:
        declaration = register.for_container(finding.subject)

        if declaration is None or declaration.expected != INTERMITTENT:
            grounded.append(finding)
            continue

        grounded.append(
            RuntimeFinding(
                subject=finding.subject,
                signature=finding.signature,
                interpretation=finding.interpretation,
                remediation=(
                    f"{finding.remediation} Before acting on that: "
                    f"{declaration.container} is declared intermittent by "
                    f"its owner ({declaration.reason}) — confirm this "
                    f"evidence is not simply that declared stop or start "
                    f"before treating it as a fault."
                ),
                confidence=finding.confidence,
                grounding=f"{register.artifact}/{declaration.container}",
                evidence=finding.evidence,
            )
        )

    return tuple(grounded)
