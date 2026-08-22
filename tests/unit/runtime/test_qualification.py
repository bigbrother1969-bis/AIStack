from datetime import datetime, timezone

import pytest

from aistack.contracts.runtime_observation import (
    LogEntry,
    RuntimeObservation,
)
from aistack.contracts.signature import Signature, SignatureCatalogue
from aistack.runtime.qualification import matches, qualify


NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)


def signature(**overrides) -> Signature:
    declared = {
        "identifier": "OPS-0001/S-001",
        "pattern": "AUTH_FAILED",
        "case_sensitive": True,
        "interpretation": "OpenVPN reports an AUTH_FAILED error.",
        "remediation": "Check the VPN credentials the container uses.",
        "depth": 100,
        "confidence": "Declared",
        "grounding": "unknown",
    }
    declared.update(overrides)
    return Signature(**declared)


def observation(lines: list[str], depth: int = 100) -> RuntimeObservation:
    last = len(lines) - 1
    return RuntimeObservation(
        subject="gluetun",
        provider="aistack.provider.docker",
        collected_at=NOW,
        depth=depth,
        entries=tuple(
            LogEntry(offset=last - i, text=t) for i, t in enumerate(lines)
        ),
    )


def catalogue(*signatures) -> SignatureCatalogue:
    return SignatureCatalogue(artifact="OPS-0001", signatures=signatures)


# --------------------------------------------------------------------
# Comparison is declared, not decided here
# --------------------------------------------------------------------


def test_a_case_sensitive_pattern_does_not_match_a_different_case():

    assert matches(signature(), LogEntry(0, "x AUTH_FAILED y"))
    assert not matches(signature(), LogEntry(0, "x auth_failed y"))


def test_a_case_insensitive_pattern_matches_either():

    rule = signature(pattern="connection refused", case_sensitive=False)

    assert matches(rule, LogEntry(0, "Connection Refused by peer"))
    assert matches(rule, LogEntry(0, "connection refused"))


# --------------------------------------------------------------------
# One finding per signature, carrying everything it saw
# --------------------------------------------------------------------


def test_a_signature_that_fires_produces_one_finding_citing_its_evidence():

    findings = qualify(
        observation(["quiet", "AUTH_FAILED", "quiet again"]),
        catalogue(signature()),
    )

    assert len(findings) == 1
    assert findings[0].subject == "gluetun"
    assert findings[0].signature == "OPS-0001/S-001"
    assert [e.text for e in findings[0].evidence] == ["AUTH_FAILED"]


def test_forty_matching_lines_are_one_condition_not_forty_findings():
    """
    A pattern present forty times is one condition observed forty
    times. Forty findings would report the volume as if it were
    the number of problems.
    """

    findings = qualify(
        observation(["AUTH_FAILED"] * 40),
        catalogue(signature()),
    )

    assert len(findings) == 1
    assert len(findings[0].evidence) == 40


def test_nothing_is_truncated():
    """
    A cap applied quietly would make a report read as complete
    when it was not.
    """

    findings = qualify(
        observation(["AUTH_FAILED"] * 100),
        catalogue(signature()),
    )

    assert len(findings[0].evidence) == 100


def test_a_signature_that_does_not_fire_produces_nothing():

    assert qualify(observation(["all quiet"]), catalogue(signature())) == []


def test_each_signature_is_evaluated_independently():

    findings = qualify(
        observation(["AUTH_FAILED", "TLS Error"]),
        catalogue(
            signature(),
            signature(identifier="OPS-0001/S-003", pattern="TLS Error"),
        ),
    )

    assert [f.signature for f in findings] == [
        "OPS-0001/S-001",
        "OPS-0001/S-003",
    ]


# --------------------------------------------------------------------
# The window is the signature's, and it is honoured
# --------------------------------------------------------------------


def test_a_line_outside_a_signature_window_does_not_fire_it():
    """
    The signature declares a window of two lines. The match sits
    three lines back and is outside it.
    """

    shallow = signature(depth=2)

    findings = qualify(
        observation(["AUTH_FAILED", "a", "b"], depth=100),
        catalogue(shallow),
    )

    assert findings == []


def test_a_line_inside_the_window_fires():

    findings = qualify(
        observation(["a", "AUTH_FAILED", "b"], depth=100),
        catalogue(signature(depth=2)),
    )

    assert len(findings) == 1


def test_an_observation_shallower_than_the_catalogue_is_refused():
    """
    A signature declaring two thousand lines against an
    observation of one hundred would silently not fire, and
    *absent* would be indistinguishable from *out of range*.
    """

    with pytest.raises(ValueError, match="could not fire"):
        qualify(
            observation(["AUTH_FAILED"], depth=100),
            catalogue(signature(depth=2000)),
        )


# --------------------------------------------------------------------
# What the finding carries
# --------------------------------------------------------------------


def test_the_finding_copies_the_wording_that_fired():
    """
    Interpretation and remediation are copied at qualification,
    not looked up later. A finding read in six months states what
    the rule said when it fired.
    """

    rule = signature(interpretation="then", remediation="do this")

    finding = qualify(observation(["AUTH_FAILED"]), catalogue(rule))[0]

    assert finding.interpretation == "then"
    assert finding.remediation == "do this"


def test_the_finding_carries_the_confidence_and_grounding_declared():

    finding = qualify(observation(["AUTH_FAILED"]), catalogue(signature()))[0]

    assert finding.confidence == "Declared"
    assert finding.grounding == "unknown"


def test_an_empty_catalogue_qualifies_nothing():

    assert qualify(observation(["AUTH_FAILED"]), catalogue()) == []
