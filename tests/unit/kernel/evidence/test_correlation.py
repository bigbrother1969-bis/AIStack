"""
`Correlation` and its recognized producer, `correlate_findings` —
J4, Evidence and Observation Foundation.
"""

from __future__ import annotations

from aistack.contracts.correlated_finding import CorrelatedFinding
from aistack.kernel.evidence import Correlation
from aistack.runtime.correlation import correlate_findings


def test_a_correlated_finding_is_a_correlation():
    finding = CorrelatedFinding(
        container="jellyfin",
        container_command="jellyfin",
        container_reference="docker ps --no-trunc",
        process_command="jellyfin",
        process_reference="docker top jellyfin",
        deployment_command=None,
        deployment_reference=None,
    )

    assert isinstance(finding, Correlation)


def test_correlate_findings_produces_the_correlation_contract():
    """
    `correlate_findings` is declared the recognized producer of
    `Correlation` without a line of its own code changing
    (`kernel/evidence/correlation.py`). This calls the real,
    unmodified function and checks what actually comes back, rather
    than trusting the docstring's claim.
    """

    result = correlate_findings(
        containers=["jellyfin"],
        container_commands={"jellyfin": "jellyfin"},
        processes={"jellyfin": "jellyfin"},
        deployment_definitions={},
    )

    assert len(result) == 1
    assert all(isinstance(item, Correlation) for item in result)
