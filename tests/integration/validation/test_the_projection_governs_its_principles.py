from aistack.integrity.checks.principle_identifiers import (
    PrincipleIdentifierCheck,
    cited_identifiers,
    registered_identifiers,
    registry_of,
)


def test_every_principle_carries_the_governed_form(projection):
    """
    STD-0102: a principle is `<DOMAIN>-P-NNN`, an artifact is
    `<DOMAIN>-NNNN`, and the `P` is what keeps `FDN-011` from
    being read as `FDN-0011`.

    The renumbering of 2026-08-21 missed the Operations family —
    four principles and one citation — and the gap survived a day
    because nothing read the registry. GOV-0002/OS-005.
    """

    findings = PrincipleIdentifierCheck().evaluate(projection)

    assert findings == [], [f.subjects for f in findings]


def test_the_projection_carries_the_registry(projection):
    """
    The test above answers *unverified* rather than *failing*
    when FDN-0012 is absent — deliberately, because a partial
    bundle may legitimately not carry it.

    This repository's own projection is not a partial bundle, and
    a projection of this heritage without its principles registry
    would be a defect of the projection. That is asserted here,
    where the question has an answer, rather than turned into a
    warning that would fire on every selective bundle.
    """

    assert registry_of(projection) is not None


def test_the_registry_is_read_and_not_merely_parsed(projection):
    """
    The two tests above pass on a registry whose table nobody
    could read: zero rows means zero malformed rows, and zero
    declarations means every citation is reported — except that
    with zero citations found, nothing is reported either.

    So the figures are stated. 49 principles across six domains,
    102 citations of them, measured 2026-08-23. Floors, not
    equalities: the registry is meant to grow, and a test that
    broke on the fiftieth principle would be a test of the
    calendar.
    """

    registered = registered_identifiers(registry_of(projection).content)

    assert len(registered) >= 49
    assert len({r.split("-")[0] for r in registered}) >= 6

    cited = cited_identifiers(projection)

    assert sum(len(sources) for sources in cited.values()) >= 49
