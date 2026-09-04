from datetime import datetime, timezone

from aistack.contracts.runtime_observation import LogEntry, RuntimeObservation
from aistack.runtime.activity_evidence import no_incoming_requests


NOW = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)


def observation(lines: list[str]) -> RuntimeObservation:
    last = len(lines) - 1
    return RuntimeObservation(
        subject="firefly",
        provider="aistack.provider.docker",
        state="running",
        collected_at=NOW,
        depth=100,
        entries=tuple(
            LogEntry(offset=last - i, text=t) for i, t in enumerate(lines)
        ),
    )


def test_a_window_with_no_entries_carries_no_incoming_requests():

    assert no_incoming_requests(observation([])) is True


def test_lines_carrying_no_http_request_shape_read_as_no_incoming_requests():

    lines = [
        "[2026-09-04 13:06:55] production.ERROR: Unauthenticated.",
        "[2026-09-04 13:07:02] production.INFO: AUDIT: Show login form (1.1).",
    ]

    assert no_incoming_requests(observation(lines)) is True


def test_a_real_access_log_line_is_recognised_as_an_incoming_request():
    """
    `firefly`'s own access log, read live during `OPS-0004`'s
    investigation — the exact shape this exists to recognise.
    """

    lines = [
        '82.65.77.38 - - [04/Sep/2026:13:07:08 +0200] "GET /register '
        'HTTP/1.1" 200 2824 "-" "Uptime-Kuma/1.23.17" '
        '"82.65.77.38, 192.168.1.40"',
    ]

    assert no_incoming_requests(observation(lines)) is False


def test_one_request_line_among_many_quiet_ones_is_still_found():

    lines = [
        "[2026-09-04 13:06:55] production.ERROR: Unauthenticated.",
        '82.65.77.38 - - [04/Sep/2026:13:07:08 +0200] "POST /login '
        'HTTP/1.1" 302 430 "-" "curl/8.0" "-"',
        "[2026-09-04 13:07:09] production.INFO: done.",
    ]

    assert no_incoming_requests(observation(lines)) is False


def test_a_non_http_request_line_naming_get_is_not_mistaken_for_one():
    """
    The word "GET" alone, outside the quoted `"METHOD path HTTP/x.y"`
    shape, is not what this recognises — otherwise a line like an
    ordinary sentence mentioning a verb would be misread as traffic.
    """

    lines = ["worker: GET request handler registered"]

    assert no_incoming_requests(observation(lines)) is True
