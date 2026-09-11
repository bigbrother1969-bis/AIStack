"""
`evaluate_services` — the Services-domain analogue of
`evaluate_storage`, citing `OPS-0004`'s third reference incident's
three confirmed qualifications from a `ContainerDistress` already
confirmed by `find_container_distress`.
"""

from __future__ import annotations

from aistack.contracts.container_distress import RESTARTING, ContainerDistress
from aistack.contracts.container_health import ContainerHealth
from aistack.contracts.container_state_reading import ContainerStateReading
from aistack.contracts.runtime_finding import CitedReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.runtime.evaluate_services import (
    DEPLOYMENT_MISCONFIGURATION,
    DOCKER_PROVIDER,
    SUSTAINABILITY_ANOMALY,
    TECHNICAL_DEBT,
    evaluate_services,
)


def restarting(container: str = "gluetun") -> ContainerDistress:
    return ContainerDistress(
        reading=ContainerStateReading(
            container=container,
            state="restarting",
            health=ContainerHealth.UNDECLARED,
        ),
        reasons=(RESTARTING,),
    )


def test_no_distress_yields_no_findings():

    assert evaluate_services([]) == ()


def test_a_distress_is_qualified_with_all_three_confirmed_qualifications():

    findings = evaluate_services([restarting()])

    assert len(findings) == 1
    assert findings[0].qualifications == (
        TECHNICAL_DEBT,
        SUSTAINABILITY_ANOMALY,
        DEPLOYMENT_MISCONFIGURATION,
    )


def test_energy_inefficiency_is_never_cited():
    """
    The owner explicitly excluded energy inefficiency for this
    incident (`OPS-0004` § Third reference incident) — it must never
    appear, not even alongside the three that were confirmed.
    """

    findings = evaluate_services([restarting()])

    assert "OPS-0004/energy-inefficiency" not in findings[0].qualifications


def test_the_finding_subject_is_the_distressed_container():

    findings = evaluate_services([restarting(container="gluetun")])

    assert findings[0].subject == "gluetun"


def test_the_finding_cites_ops_0004_as_its_signature():

    findings = evaluate_services([restarting()])

    assert findings[0].signature == "OPS-0004"


def test_the_confidence_reflects_a_measured_reading():

    findings = evaluate_services([restarting()])

    assert findings[0].confidence == "Measured"


def test_the_finding_starts_ungrounded_like_any_other():

    findings = evaluate_services([restarting()])

    assert findings[0].grounding == UNDECLARED


def test_the_evidence_cites_the_docker_provider_and_the_reading():

    distress = restarting()
    findings = evaluate_services([distress])

    evidence = findings[0].evidence
    assert len(evidence) == 1
    assert isinstance(evidence[0], CitedReading)
    assert evidence[0].provider == DOCKER_PROVIDER
    assert evidence[0].reading == distress.reading


def test_the_interpretation_names_the_reasons_and_the_observed_state():

    findings = evaluate_services([restarting()])

    interpretation = findings[0].interpretation
    assert "restarting" in interpretation
    assert "state='restarting'" in interpretation


def test_one_finding_per_distressed_container():

    findings = evaluate_services([restarting("gluetun"), restarting("jellyfin")])

    assert {f.subject for f in findings} == {"gluetun", "jellyfin"}
