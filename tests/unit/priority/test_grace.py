from aistack.priority.grace import GraceState, resolve_boosted


def test_playing_now_is_boosted_immediately():
    boosted, state = resolve_boosted(
        playing_now=True, now=100.0, grace_seconds=60.0, state=GraceState()
    )

    assert boosted is True
    assert state.last_playing_at == 100.0


def test_never_seen_playing_and_not_playing_now_is_not_boosted():
    boosted, state = resolve_boosted(
        playing_now=False, now=100.0, grace_seconds=60.0, state=GraceState()
    )

    assert boosted is False
    assert state.last_playing_at is None


def test_just_stopped_stays_boosted_within_the_grace_window():
    state = GraceState(last_playing_at=100.0)

    boosted, next_state = resolve_boosted(
        playing_now=False, now=130.0, grace_seconds=60.0, state=state
    )

    assert boosted is True
    # The window's own start does not move just because a poll
    # found nothing playing — it started when playback was last
    # seen, not when it was last checked.
    assert next_state.last_playing_at == 100.0


def test_the_grace_window_expires_at_exactly_grace_seconds():
    state = GraceState(last_playing_at=100.0)

    boosted, next_state = resolve_boosted(
        playing_now=False, now=160.0, grace_seconds=60.0, state=state
    )

    assert boosted is False
    assert next_state.last_playing_at is None


def test_a_new_session_within_the_grace_window_resets_the_clock():
    """
    A pause-then-resume inside the window is not two separate
    windows — the clock is the last time playback was actually
    seen, and a resume moves it forward like any other "playing".
    """

    state = GraceState(last_playing_at=100.0)

    boosted, next_state = resolve_boosted(
        playing_now=True, now=140.0, grace_seconds=60.0, state=state
    )

    assert boosted is True
    assert next_state.last_playing_at == 140.0


def test_stopping_after_the_window_already_elapsed_stays_unboosted():
    state = GraceState(last_playing_at=None)

    boosted, next_state = resolve_boosted(
        playing_now=False, now=500.0, grace_seconds=60.0, state=state
    )

    assert boosted is False
    assert next_state.last_playing_at is None


def test_a_zero_grace_period_drops_the_boost_on_the_very_next_poll():
    state = GraceState(last_playing_at=100.0)

    boosted, next_state = resolve_boosted(
        playing_now=False, now=100.0001, grace_seconds=0.0, state=state
    )

    assert boosted is False
    assert next_state.last_playing_at is None
