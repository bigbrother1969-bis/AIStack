from aistack.priority.detectors.cpu_threshold import (
    CpuStreakState,
    resolve_cpu_active,
)


def test_below_threshold_is_never_active():
    active, state = resolve_cpu_active(
        usage_percent=10.0,
        threshold_percent=50.0,
        sustained_seconds=15.0,
        now=100.0,
        state=CpuStreakState(),
    )

    assert active is False
    assert state.above_since is None


def test_crossing_the_threshold_starts_a_streak_but_is_not_yet_active():
    active, state = resolve_cpu_active(
        usage_percent=60.0,
        threshold_percent=50.0,
        sustained_seconds=15.0,
        now=100.0,
        state=CpuStreakState(),
    )

    assert active is False
    assert state.above_since == 100.0


def test_a_streak_carried_from_an_earlier_poll_does_not_restart():
    """
    `above_since` is the moment the container first crossed the
    threshold, not the moment it was last checked — the same
    reasoning `resolve_boosted`'s own `last_playing_at` follows for
    the grace window.
    """

    active, state = resolve_cpu_active(
        usage_percent=60.0,
        threshold_percent=50.0,
        sustained_seconds=15.0,
        now=110.0,
        state=CpuStreakState(above_since=100.0),
    )

    assert active is False
    assert state.above_since == 100.0


def test_active_once_the_streak_reaches_sustained_seconds():
    active, state = resolve_cpu_active(
        usage_percent=60.0,
        threshold_percent=50.0,
        sustained_seconds=15.0,
        now=115.0,
        state=CpuStreakState(above_since=100.0),
    )

    assert active is True
    assert state.above_since == 100.0


def test_a_reading_below_threshold_resets_the_streak_entirely():
    active, state = resolve_cpu_active(
        usage_percent=10.0,
        threshold_percent=50.0,
        sustained_seconds=15.0,
        now=112.0,
        state=CpuStreakState(above_since=100.0),
    )

    assert active is False
    assert state.above_since is None


def test_exactly_at_the_threshold_counts_as_above():
    active, state = resolve_cpu_active(
        usage_percent=50.0,
        threshold_percent=50.0,
        sustained_seconds=15.0,
        now=100.0,
        state=CpuStreakState(),
    )

    assert state.above_since == 100.0
