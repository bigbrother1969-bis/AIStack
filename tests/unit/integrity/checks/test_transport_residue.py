from aistack.integrity.checks.transport_residue import (
    TransportResidueCheck,
)


def test_governed_locations_yield_nothing(make_artifact, make_bundle):

    bundle = make_bundle([
        make_artifact(source="/srv/x/docs/00-foundation/FDN-0001.md"),
    ])

    assert TransportResidueCheck().evaluate(bundle) == []


def test_transit_locations_are_reported(make_artifact, make_bundle):
    """
    A mandatory AI runtime policy currently lives in
    docs/incoming/, outside the governed heritage.
    """

    bundle = make_bundle([
        make_artifact(source="/srv/x/docs/incoming/AI_PROTOCOL.md"),
        make_artifact(source="/srv/x/docs/99-meta/integration/patch.md"),
        make_artifact(source="/srv/x/docs/00-foundation/FDN-0001.md"),
    ])

    findings = TransportResidueCheck().evaluate(bundle)

    assert len(findings) == 1
    assert findings[0].affected == 2


def test_a_relative_source_is_read_like_an_absolute_one(
    make_artifact, make_bundle
):
    """
    `GOV-0002/OS-096`: a source is relative to the root of the
    heritage, and the locations start with a separator. Without the
    one the check puts in front, `docs/incoming/x.md` matched
    nothing and the check reported nothing, silently.

    A bundle generated before OS-096 holds absolute sources and is
    still read; and a directory that merely ends the same way is not
    a transit location.
    """

    bundle = make_bundle([
        make_artifact(source="docs/incoming/AI_PROTOCOL.md"),
        make_artifact(source="docs/99-meta/integration/patch.md"),
        make_artifact(source="/srv/x/docs/incoming/old.md"),
        make_artifact(source="mydocs/incoming/not-transit.md"),
        make_artifact(source="docs/00-foundation/FDN-0001.md"),
    ])

    findings = TransportResidueCheck().evaluate(bundle)

    assert len(findings) == 1
    assert findings[0].affected == 3
    assert "mydocs/incoming/not-transit.md" not in findings[0].subjects
