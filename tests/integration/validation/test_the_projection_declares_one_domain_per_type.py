from aistack.integrity.checks.classification_coherence import (
    ClassificationCoherenceCheck,
    domains_by_type,
)


def test_no_declared_type_maps_to_two_domains(projection):
    """
    STD-0100: a declared `type` determines its `domain`.

    The rule was written into a C2 standard on 2026-08-22 from a
    measurement over 63 artifacts and 16 types, and enforced by
    nothing until this test — a day during which any commit could
    have made it false without anyone learning of it. That is
    GOV-0002/OS-004.
    """

    findings = ClassificationCoherenceCheck().evaluate(projection)

    assert findings == [], [f.subjects for f in findings]


def test_the_rule_is_measured_over_a_heritage_that_can_break_it(
    projection,
):
    """
    The test above passes on an empty bundle, on a bundle whose
    artifacts declare no type, and on a heritage of one artifact.

    So this one states what was actually measured: 65 artifacts,
    19 distinct types on 2026-08-23 — against 63 and 16 the day
    before. The figures are floors, not equalities: the heritage
    is meant to grow, and a test that broke on the sixty-sixth
    artifact would be a test of the calendar.

    What it protects is the ability of the rule to be false. If a
    refactor made `declared_type` stop reaching the bundle, every
    type would collapse to `unknown`, the check above would go on
    passing, and it would be verifying nothing.
    """

    observed = domains_by_type(projection)

    assert len(projection.artifacts) >= 65
    assert len(observed) >= 19
