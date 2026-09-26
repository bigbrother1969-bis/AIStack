from __future__ import annotations

from aistack.contracts.development_flag import DevelopmentFlagFinding
from aistack.contracts.lifecycle import CONTINUOUS, INTERMITTENT, LifecycleRegister
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


def ground_development_flags(
    flags: list[DevelopmentFlagFinding] | tuple[DevelopmentFlagFinding, ...],
    register: LifecycleRegister,
) -> tuple[DevelopmentFlagFinding, ...]:
    """
    Add the owner's own lifecycle context to a development-flag
    finding, where one has been declared. `STD-0300` § VS-4 criterion
    4.3, advanced 2026-09-26.

    **`ground_findings`'s counterpart, for the other finding type
    4.7 does not govern.** `find_development_flags` deliberately does
    not judge "permanent" — its own docstring leaves that reading to
    whoever looks at the finding. `OPS-0003` is exactly the owner's
    own answer to that reading, for the containers it names: this
    function is where it is applied, the same place `ground_findings`
    applies it to a `RuntimeFinding`.

    **Both declared values are cited, unlike `ground_findings`.**
    `ground_findings` only rewrites a finding declared `intermittent`,
    because a `continuous` declaration adds nothing a signature's
    general remediation did not already assume. Here the axis the
    criterion asks about is exactly what `OPS-0003` declares: a
    container declared `continuous` is the owner's own statement that
    this *is* the permanent service 4.3 means, and a reader is owed
    that as much as the opposite reading — citing only the weakening
    case and staying silent on the confirming one would tell half of
    what `OPS-0003` states.

    **A finding about an undeclared container is unchanged**, for the
    same reason `ground_findings` leaves one unchanged: `OPS-0003`
    says nothing about it, and `grounding` staying `UNDECLARED` is
    that absence, not a guess at "permanent" standing in for it.
    """

    grounded: list[DevelopmentFlagFinding] = []

    for flag in flags:
        declaration = register.for_container(flag.container)

        if declaration is None:
            grounded.append(flag)
            continue

        if declaration.expected == INTERMITTENT:
            note = (
                f"{declaration.container} is declared intermittent by its "
                f"owner ({declaration.reason}) — confirm this is not a "
                f"deliberate one-off run before treating it as the "
                f"permanent service the option was left enabled in."
            )
        else:
            assert declaration.expected == CONTINUOUS
            note = (
                f"{declaration.container} is declared continuous by its "
                f"owner ({declaration.reason}) — consistent with the "
                f"permanent service this criterion means."
            )

        grounded.append(
            DevelopmentFlagFinding(
                container=flag.container,
                pattern=flag.pattern,
                interpretation=f"{flag.interpretation} {note}",
                command=flag.command,
                grounding=f"{register.artifact}/{declaration.container}",
            )
        )

    return tuple(grounded)
