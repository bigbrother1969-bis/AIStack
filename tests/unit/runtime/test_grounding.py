from datetime import datetime, timezone

import pytest

from aistack.contracts.lifecycle import LifecycleDeclaration, LifecycleRegister
from aistack.contracts.runtime_finding import MatchedLine, RuntimeFinding
from aistack.contracts.runtime_observation import LogEntry, RuntimeObservation
from aistack.contracts.signature import Signature, SignatureCatalogue
from aistack.runtime.grounding import ground_findings
from aistack.runtime.qualification import qualify


NOW = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)


def finding(subject: str, **overrides) -> RuntimeFinding:
    declared = {
        "subject": subject,
        "signature": "OPS-0001/S-004",
        "interpretation": "The logs contain connection-refused errors.",
        "remediation": (
            "Check the target service, the exposed port, and the Docker "
            "network."
        ),
        "confidence": "Declared",
        "grounding": "unknown",
        "evidence": (
            MatchedLine(entry=LogEntry(offset=0, text="connection refused")),
        ),
    }
    declared.update(overrides)
    return RuntimeFinding(**declared)


def register(*declarations) -> LifecycleRegister:
    return LifecycleRegister(artifact="OPS-0003", declarations=declarations)


FRIGATE = LifecycleDeclaration(
    container="frigate",
    expected="intermittent",
    reason="Stopped most of the time to save resources.",
)


# --------------------------------------------------------------------
# `LifecycleDeclaration` / `LifecycleRegister` themselves
# --------------------------------------------------------------------


def test_a_declaration_requires_a_recognised_expected_value():

    with pytest.raises(ValueError, match="sometimes"):
        LifecycleDeclaration(container="x", expected="sometimes", reason="y")


def test_a_declaration_requires_a_reason():

    with pytest.raises(ValueError, match="no `reason`"):
        LifecycleDeclaration(container="x", expected="intermittent", reason="")


def test_a_register_refuses_two_declarations_for_the_same_container():

    with pytest.raises(ValueError, match="x is declared twice"):
        LifecycleRegister(
            artifact="OPS-0003",
            declarations=(
                LifecycleDeclaration(container="x", expected="intermittent", reason="a"),
                LifecycleDeclaration(container="x", expected="continuous", reason="b"),
            ),
        )


def test_for_container_returns_none_for_an_undeclared_container():

    assert register(FRIGATE).for_container("gluetun") is None


# --------------------------------------------------------------------
# `ground_findings`
# --------------------------------------------------------------------


def test_a_finding_about_an_undeclared_container_is_unchanged():

    original = finding("gluetun")

    grounded = ground_findings([original], register(FRIGATE))

    assert grounded == (original,)


def test_a_finding_about_a_declared_intermittent_container_cites_the_register():

    grounded = ground_findings([finding("frigate")], register(FRIGATE))

    assert len(grounded) == 1
    assert grounded[0].grounding == "OPS-0003/frigate"


def test_the_original_interpretation_and_remediation_survive_verbatim():
    """
    The declaration does not prove the evidence is harmless — it
    is context added for a reader to judge, not a replacement for
    what the signature said. `frigate` stopping on purpose does
    not mean every future finding about it is that same shutdown.
    """

    original = finding("frigate")

    grounded = ground_findings([original], register(FRIGATE))[0]

    assert grounded.interpretation == original.interpretation
    assert original.remediation in grounded.remediation


def test_the_owners_own_reason_reaches_the_remediation():

    grounded = ground_findings([finding("frigate")], register(FRIGATE))[0]

    assert "save resources" in grounded.remediation
    assert "frigate" in grounded.remediation


def test_a_declared_continuous_container_is_not_grounded_as_intermittent():
    """
    `expected: continuous` is a real declaration, not the absence
    of one — but it says the opposite of `frigate`'s, so a finding
    about it is not rewritten as if its subject were intermittent.
    """

    continuous = LifecycleDeclaration(
        container="jellyfin", expected="continuous", reason="Always on."
    )

    original = finding("jellyfin")

    grounded = ground_findings([original], register(continuous))

    assert grounded == (original,)


def test_evidence_is_carried_through_unchanged():

    original = finding("frigate")

    grounded = ground_findings([original], register(FRIGATE))[0]

    assert grounded.evidence == original.evidence


def test_only_the_matching_finding_in_a_batch_is_grounded():

    gluetun_finding = finding("gluetun")
    frigate_finding = finding("frigate")

    grounded = ground_findings(
        [gluetun_finding, frigate_finding], register(FRIGATE)
    )

    assert grounded[0] == gluetun_finding
    assert grounded[1].grounding == "OPS-0003/frigate"


# --------------------------------------------------------------------
# End to end: `qualify()` then `ground_findings()`, the real chain
# --------------------------------------------------------------------


def test_the_frigate_finding_is_grounded_after_qualification():
    """
    The chain a real caller uses: collect, qualify against
    `OPS-0001`, then ground against `OPS-0003`. `S-004`'s own
    `grounding` stays `unknown` at the signature — this proves the
    finding it produces does not.
    """

    refusal = Signature(
        identifier="OPS-0001/S-004",
        pattern="connection refused",
        case_sensitive=False,
        applies_to=("running",),
        interpretation="The logs contain connection-refused errors.",
        remediation="Check the target service, the exposed port, and the Docker network.",
        depth=100,
        confidence="Declared",
        grounding="unknown",
    )

    observation = RuntimeObservation(
        subject="frigate",
        provider="aistack.provider.docker",
        state="running",
        collected_at=NOW,
        depth=100,
        entries=(
            LogEntry(offset=0, text="connect() failed (111: Connection refused)"),
        ),
    )

    findings = qualify(
        observation, SignatureCatalogue(artifact="OPS-0001", signatures=(refusal,))
    )

    assert findings[0].grounding == "unknown"

    grounded = ground_findings(findings, register(FRIGATE))

    assert grounded[0].grounding == "OPS-0003/frigate"
    assert grounded[0].signature == "OPS-0001/S-004"
