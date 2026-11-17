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
