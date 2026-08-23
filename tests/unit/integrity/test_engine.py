from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)
from aistack.integrity.engine import (
    DefaultKnowledgeIntegrityEngine,
    default_checks,
)


class SilentCheck:

    @property
    def name(self):
        return "silent"

    def evaluate(self, bundle):
        return []


class NoisyCheck:

    @property
    def name(self):
        return "noisy"

    def evaluate(self, bundle):
        return [
            IntegrityFinding(
                check="noisy",
                severity=IntegritySeverity.BLOCKING,
                summary="something",
                affected=1,
                total=1,
            )
        ]


def test_report_carries_the_bundle_provenance(make_artifact, make_bundle):

    bundle = make_bundle([make_artifact()])

    report = DefaultKnowledgeIntegrityEngine(
        checks=[SilentCheck()]
    ).evaluate(bundle)

    assert report.bundle_id == "bundle-test"
    assert report.source_commit == "abc1234"
    assert report.artifact_count == 1


def test_a_silent_run_is_clean(make_artifact, make_bundle):

    report = DefaultKnowledgeIntegrityEngine(
        checks=[SilentCheck()]
    ).evaluate(make_bundle([make_artifact()]))

    assert report.findings == ()
    assert report.is_clean


def test_findings_from_every_check_reach_the_report(make_artifact, make_bundle):
    """
    The engine hides nothing: it ranks no finding and drops
    none.
    """

    report = DefaultKnowledgeIntegrityEngine(
        checks=[NoisyCheck(), SilentCheck(), NoisyCheck()]
    ).evaluate(make_bundle([make_artifact()]))

    assert len(report.findings) == 2
    assert len(report.blocking) == 2
    assert not report.is_clean


def test_default_composition_is_stable():

    names = [check.name for check in default_checks()]

    assert names == [
        "structural-integrity",
        "metadata-completeness",
        "projection-fidelity",
        "knowledge-state",
        "classification-declaration",
        "classification-coherence",
        "principle-identifiers",
        "duplicate-titles",
        "transport-residue",
        "contract-debt",
        "reference-integrity",
    ]
