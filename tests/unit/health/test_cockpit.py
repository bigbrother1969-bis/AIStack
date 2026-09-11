import pytest

from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_reading import StorageReading
from aistack.health.cockpit import HealthCockpit, HealthDomain


def a_finding() -> RuntimeFinding:
    return RuntimeFinding(
        subject="/",
        signature="OPS-0004",
        interpretation="short on space",
        remediation="free some up",
        confidence="Measured",
        grounding="unknown",
        evidence=(
            CitedReading(
                provider="aistack.provider.storage",
                reading=StorageReading(
                    mount="/", total_bytes=100, used_bytes=99, free_bytes=1
                ),
            ),
        ),
        qualifications=("OPS-0004/deployment-misconfiguration",),
    )


# --------------------------------------------------------------------
# HealthDomain
# --------------------------------------------------------------------


def test_a_domain_names_no_domain_is_refused():
    with pytest.raises(ValueError, match="names no domain"):
        HealthDomain(name="", instrumented=False, note="why")


def test_a_not_instrumented_domain_requires_a_note():
    with pytest.raises(ValueError, match="without saying why"):
        HealthDomain(name="Services", instrumented=False)


def test_a_not_instrumented_domain_may_not_carry_findings():
    with pytest.raises(ValueError, match="only an instrumented domain"):
        HealthDomain(
            name="Stockage",
            instrumented=False,
            note="why",
            findings=(a_finding(),),
        )


def test_an_instrumented_domain_needs_no_note():
    domain = HealthDomain(name="Stockage", instrumented=True)

    assert domain.note == ""
    assert domain.findings == ()


def test_an_instrumented_domain_may_carry_findings():
    domain = HealthDomain(name="Stockage", instrumented=True, findings=(a_finding(),))

    assert len(domain.findings) == 1


# --------------------------------------------------------------------
# HealthCockpit
# --------------------------------------------------------------------


def test_an_empty_cockpit_declares_no_domain():
    assert HealthCockpit().domains == ()


def test_a_cockpit_carries_every_domain_given_to_it():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True),
            HealthDomain(name="Services", instrumented=False, note="why"),
        )
    )

    assert [domain.name for domain in cockpit.domains] == ["Stockage", "Services"]
