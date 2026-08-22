from datetime import datetime

import pytest

from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.runtime_observation import (
    LogEntry,
    RuntimeObservation,
)
from aistack.contracts.signature import Signature, SignatureCatalogue
from aistack.contracts.undeclared import UNDECLARED


def entry(offset: int = 0, text: str = "AUTH_FAILED") -> LogEntry:
    return LogEntry(offset=offset, text=text)


def signature(**overrides) -> Signature:
    declared = {
        "identifier": "OPS-0001/S-001",
        "pattern": "AUTH_FAILED",
        "case_sensitive": True,
        "interpretation": "OpenVPN reports an authentication failure.",
        "remediation": "Check the VPN credentials used by the container.",
        "depth": 100,
        "confidence": "Declared",
    }
    declared.update(overrides)
    return Signature(**declared)


# --------------------------------------------------------------------
# A finding cannot exist without evidence
# --------------------------------------------------------------------


def finding(**overrides) -> RuntimeFinding:
    declared = {
        "subject": "gluetun",
        "signature": "OPS-0001/S-001",
        "interpretation": "OpenVPN reports an authentication failure.",
        "remediation": "Check the VPN credentials used by the container.",
        "confidence": "Declared",
        "grounding": UNDECLARED,
        "evidence": (entry(),),
    }
    declared.update(overrides)
    return RuntimeFinding(**declared)


def test_a_finding_without_evidence_cannot_be_constructed():
    """
    STD-0300 § VS-4 criterion 4.9 as a property of the type.

    The heritage carried several rules that were declared and
    enforced by nothing — STD-0002, ENG-TEST-0002, the
    `type`-to-`domain` rule. This one is enforced by the
    constructor, so the criterion cannot be met "in principle".
    """

    with pytest.raises(ValueError, match="4.9"):
        finding(evidence=())


def test_a_finding_cites_the_signature_that_produced_it():

    with pytest.raises(ValueError, match="4.7"):
        finding(signature="  ")


def test_a_finding_names_its_subject():

    with pytest.raises(ValueError, match="subject"):
        finding(subject="")


def test_a_finding_is_immutable():

    with pytest.raises(Exception):
        finding().subject = "other"


def test_a_finding_carries_the_wording_that_fired_not_a_reference():
    """
    Interpretation and remediation are copied, not looked up. A
    finding read later states what the rule said when it fired.
    """

    f = finding()

    assert f.interpretation
    assert f.remediation
    assert not hasattr(f, "catalogue")


# --------------------------------------------------------------------
# A signature declares everything it needs, including its absence
# --------------------------------------------------------------------


def test_grounding_defaults_to_undeclared_and_nothing_else_does():
    """
    Six fields are required with no default. `grounding` is the
    single exception, because a remediation may rest on a rule
    the heritage has not written — a governed state under Article
    12, and one that can be counted.
    """

    assert signature().grounding == UNDECLARED

    for missing in (
        "identifier",
        "pattern",
        "case_sensitive",
        "interpretation",
        "remediation",
        "depth",
        "confidence",
    ):
        declared = {
            "identifier": "x",
            "pattern": "y",
            "case_sensitive": True,
            "interpretation": "z",
            "remediation": "w",
            "depth": 1,
            "confidence": "Declared",
        }
        del declared[missing]

        with pytest.raises(TypeError):
            Signature(**declared)


@pytest.mark.parametrize("field", ["identifier", "pattern", "interpretation", "remediation"])
def test_an_empty_declaration_is_refused(field):

    with pytest.raises(ValueError, match=field):
        signature(**{field: "   "})


@pytest.mark.parametrize("depth", [0, -1])
def test_a_signature_declares_a_window_with_meaning(depth):

    with pytest.raises(ValueError, match="window"):
        signature(depth=depth)


# --------------------------------------------------------------------
# A catalogue is a policy register
# --------------------------------------------------------------------


def test_two_signatures_may_not_share_an_identifier():
    """
    A finding cites a signature by name. A name designating two
    rules designates neither, and criterion 4.7's citation would
    stop being traceable.
    """

    with pytest.raises(ValueError, match="OPS-0001/S-001"):
        SignatureCatalogue(
            artifact="OPS-0001",
            signatures=(signature(), signature(pattern="TLS Error")),
        )


def test_a_catalogue_is_declared_by_an_artifact():

    with pytest.raises(ValueError, match="artifact"):
        SignatureCatalogue(artifact="")


def test_the_deepest_window_is_what_collection_must_read():
    """
    Collection happens once at the deepest declared window; each
    signature then evaluates its own. One Docker call, not one
    per rule.
    """

    catalogue = SignatureCatalogue(
        artifact="OPS-0001",
        signatures=(
            signature(identifier="OPS-0001/S-001", depth=100),
            signature(identifier="OPS-0001/S-002", depth=2000),
            signature(identifier="OPS-0001/S-003", depth=50),
        ),
    )

    assert catalogue.deepest == 2000


def test_an_empty_catalogue_reads_nothing():

    assert SignatureCatalogue(artifact="OPS-0001").deepest == 0


# --------------------------------------------------------------------
# An observation states what it saw, and how far it looked
# --------------------------------------------------------------------


def observation(**overrides) -> RuntimeObservation:
    declared = {
        "subject": "gluetun",
        "provider": "aistack.provider.docker",
        "collected_at": datetime(2026, 8, 22, 12, 0, 0),
        "depth": 100,
        "entries": (entry(),),
    }
    declared.update(overrides)
    return RuntimeObservation(**declared)


def test_an_observation_carries_the_depth_it_read():
    """
    A signature declaring a window deeper than what was collected
    cannot fire. Without the depth travelling alongside, *absent*
    and *out of range* would be the same result.
    """

    assert observation().depth == 100


def test_an_observation_cannot_carry_more_entries_than_it_read():

    with pytest.raises(ValueError, match="depth"):
        observation(depth=1, entries=(entry(0), entry(1)))


def test_an_observation_names_its_subject():

    with pytest.raises(ValueError, match="subject"):
        observation(subject="")


def test_a_log_entry_offset_counts_back_from_the_newest_line():

    assert entry(offset=0).offset == 0

    with pytest.raises(ValueError, match="negative"):
        LogEntry(offset=-1, text="x")


def test_an_observation_states_nothing_about_correctness():
    """
    ARC-P-012: a provider observes and collects; it never decides.
    No field of this contract says whether anything is wrong.
    """

    fields = set(vars(observation()))

    assert not fields & {
        "healthy",
        "severity",
        "status",
        "issue",
        "diagnosis",
        "recommendation",
    }
