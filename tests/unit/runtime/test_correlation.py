import pytest

from aistack.contracts.correlated_finding import CorrelatedFinding
from aistack.runtime.correlation import correlate_findings


# --------------------------------------------------------------------
# `CorrelatedFinding` itself
# --------------------------------------------------------------------


def test_a_finding_requires_a_container_name():

    with pytest.raises(ValueError, match="names none"):
        CorrelatedFinding(
            container="",
            container_command="x",
            container_reference="docker ps --no-trunc",
            process_command="x",
            process_reference="docker top x",
            deployment_command=None,
            deployment_reference=None,
        )


def test_a_deployment_command_without_a_reference_is_refused():
    """
    A command with no reference is unverifiable — the whole point
    of 4.2's "each with an observation reference".
    """

    with pytest.raises(ValueError, match="must be declared together"):
        CorrelatedFinding(
            container="x",
            container_command="a",
            container_reference="docker ps --no-trunc",
            process_command="a",
            process_reference="docker top x",
            deployment_command="a",
            deployment_reference=None,
        )


def test_both_deployment_fields_absent_together_is_valid():
    """
    The declared, honest state for most of this deployment's
    containers — nothing invented, nothing raised.
    """

    finding = CorrelatedFinding(
        container="x",
        container_command="a",
        container_reference="docker ps --no-trunc",
        process_command="a",
        process_reference="docker top x",
        deployment_command=None,
        deployment_reference=None,
    )

    assert finding.deployment_command is None


# --------------------------------------------------------------------
# `correlate_findings`
# --------------------------------------------------------------------


def test_a_named_container_is_correlated_from_all_three_maps():

    findings = correlate_findings(
        ["aistack-selection-ui"],
        {"aistack-selection-ui": "uvicorn app:app --reload"},
        {"aistack-selection-ui": "python3 -m uvicorn app:app --reload"},
        {"aistack-selection-ui": ("uvicorn app:app --reload", "Dockerfile.selection-ui:CMD")},
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.container_command == "uvicorn app:app --reload"
    assert finding.process_command == "python3 -m uvicorn app:app --reload"
    assert finding.deployment_command == "uvicorn app:app --reload"
    assert finding.deployment_reference == "Dockerfile.selection-ui:CMD"


def test_a_container_absent_from_deployment_definitions_is_undeclared():

    findings = correlate_findings(["frigate"], {"frigate": "x"}, {"frigate": "y"}, {})

    assert findings[0].deployment_command is None
    assert findings[0].deployment_reference is None


def test_a_container_missing_from_a_collection_reads_as_empty_not_an_error():
    """
    A reference that could not be resolved is a fact about the
    collection worth seeing, not a reason to drop the correlation —
    the same convention `states.get` already carries elsewhere in
    `runtime_diagnose`.
    """

    findings = correlate_findings(["ghost"], {}, {}, {})

    assert findings[0].container_command == ""
    assert findings[0].process_command == ""


def test_only_the_named_containers_are_correlated():

    findings = correlate_findings(
        ["a"],
        {"a": "x", "b": "y"},
        {"a": "x", "b": "y"},
        {},
    )

    assert [f.container for f in findings] == ["a"]


def test_references_are_always_present_even_when_the_reading_is_empty():

    findings = correlate_findings(["a"], {}, {}, {})

    assert findings[0].container_reference == "docker ps --no-trunc"
    assert findings[0].process_reference == "docker top a"


def test_no_containers_named_produces_nothing():

    assert correlate_findings([], {}, {}, {}) == ()
