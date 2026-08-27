from aistack.integrity.checks.register_coherence import (
    REGISTER,
    RegisterCoherenceCheck,
    read_entries,
)


def register_of(projection):
    return next(
        (a for a in projection.artifacts if a.id == REGISTER), None
    )


def test_every_entry_sits_where_its_state_says(projection):
    """
    GOV-0002 states each entry's condition twice — in its
    `**State**` field and by the section holding it — and the two
    drifted twice in two days.

    On 2026-08-23 OS-023 and OS-024 were filed under *Defects*
    while declaring `non-conforming`. On 2026-08-27 OS-029 was
    filed under *Resolved* while declaring `State open`. Both were
    found by a human reading the file.
    """

    findings = RegisterCoherenceCheck().evaluate(projection)

    assert findings == [], [f.subjects for f in findings]


def test_the_register_is_read_and_not_merely_parsed(projection):
    """
    The test above passes on a register nobody could read: zero
    entries means zero incoherent ones.

    So the figures are stated. 29 entries and all six declared
    natures, measured 2026-08-27. Floors, not equalities — the
    register is meant to grow, and a test that broke on the
    thirtieth entry would be a test of the calendar.
    """

    entries = read_entries(register_of(projection).content)

    assert len(entries) >= 29

    natures = {entry.nature for entry in entries}

    assert len(natures) >= 6
    assert None not in natures


def test_the_projection_carries_the_register(projection):
    """
    The check answers *unverified* rather than *failing* when
    GOV-0002 is absent, because a partial bundle may legitimately
    carry none. This repository's own projection is not a partial
    bundle.
    """

    assert register_of(projection) is not None
