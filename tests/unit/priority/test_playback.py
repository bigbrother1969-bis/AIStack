from aistack.priority.playback import has_active_playback


def test_no_sessions_is_no_playback():
    assert has_active_playback([]) is False


def test_a_session_with_nothing_playing_is_not_playback():
    """
    Most sessions `/Sessions` lists are a connected client sitting
    idle, not a person watching. `NowPlayingItem` absent is the
    provider's honest report of that, not a value to second-guess.
    """

    assert has_active_playback([{"Id": "idle-client"}]) is False


def test_a_session_playing_and_not_paused_is_playback():
    sessions = [
        {
            "Id": "session-1",
            "NowPlayingItem": {"Name": "A Film"},
            "PlayState": {"IsPaused": False},
        }
    ]

    assert has_active_playback(sessions) is True


def test_a_paused_session_is_not_playback():
    sessions = [
        {
            "Id": "session-1",
            "NowPlayingItem": {"Name": "A Film"},
            "PlayState": {"IsPaused": True},
        }
    ]

    assert has_active_playback(sessions) is False


def test_a_playing_session_with_no_play_state_at_all_is_playback():
    """
    `PlayState` missing entirely is not the same fact as
    `IsPaused: true` — a session already carrying `NowPlayingItem`
    is playing something, and the absence of the field that would
    say otherwise is not read as that field saying so.
    """

    sessions = [{"Id": "session-1", "NowPlayingItem": {"Name": "A Film"}}]

    assert has_active_playback(sessions) is True


def test_a_playing_session_with_is_paused_absent_from_play_state_is_playback():
    sessions = [
        {
            "Id": "session-1",
            "NowPlayingItem": {"Name": "A Film"},
            "PlayState": {"PositionTicks": 12345},
        }
    ]

    assert has_active_playback(sessions) is True


def test_one_idle_session_among_others_does_not_hide_a_playing_one():
    sessions = [
        {"Id": "idle-client"},
        {
            "Id": "watching",
            "NowPlayingItem": {"Name": "A Film"},
            "PlayState": {"IsPaused": False},
        },
    ]

    assert has_active_playback(sessions) is True


def test_all_sessions_paused_is_not_playback():
    sessions = [
        {
            "Id": "session-1",
            "NowPlayingItem": {"Name": "A Film"},
            "PlayState": {"IsPaused": True},
        },
        {
            "Id": "session-2",
            "NowPlayingItem": {"Name": "Another Film"},
            "PlayState": {"IsPaused": True},
        },
    ]

    assert has_active_playback(sessions) is False


def test_a_now_playing_item_that_is_an_empty_object_is_still_playback():
    """
    `NowPlayingItem` truthy is the signal, not any particular key
    inside it — Jellyfin's own field set for it is not this
    project's to assume beyond "present means something is loaded".
    """

    sessions = [{"NowPlayingItem": {}, "PlayState": {"IsPaused": False}}]

    # An empty dict is falsy in Python — this documents that edge
    # rather than leaving it to accident: a `NowPlayingItem` with no
    # fields at all reads the same as none, on the current check.
    assert has_active_playback(sessions) is False
