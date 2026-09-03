import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest

from aistack.providers.jellyfin import JellyfinProvider


KEY = "a-key-that-is-not-a-secret-here"


class Daemon:
    """
    A Jellyfin that answers on a real socket — same reasoning as
    `SyncthingProvider`'s own test daemon: a stub passed in as a
    callable would have tested the code around the call and not the
    call. This exercises the header, the timeout and the status
    codes.
    """

    def __init__(self):
        self.answer: object = []
        self.status: int = 200
        self.seen: list[tuple[str, str]] = []
        self.delay = 0.0


@pytest.fixture
def daemon():
    return Daemon()


@pytest.fixture
def url(daemon):
    state = daemon

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):
            parsed = urlparse(self.path)

            state.seen.append(
                (parsed.path, self.headers.get("X-Emby-Token", ""))
            )

            if state.delay:
                import time

                time.sleep(state.delay)

            body = json.dumps(state.answer).encode()

            self.send_response(state.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

        def handle_one_request(self):
            try:
                super().handle_one_request()
            except OSError:
                self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{server.server_port}"

    server.shutdown()
    server.server_close()


def closed_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def test_sessions_are_returned_exactly_as_the_daemon_answered_them(
    daemon, url
):
    """
    The provider observes and does not qualify — same rule as
    `SyncthingProvider`. Whatever Jellyfin's real session shape
    turns out to be, it arrives here unfiltered.
    """

    daemon.answer = [
        {
            "Id": "session-1",
            "UserName": "fabrice",
            "NowPlayingItem": {"Name": "A Film"},
            "PlayState": {"IsPaused": False},
        },
        {"Id": "session-2", "UserName": "someone-idle"},
    ]

    observed = JellyfinProvider(url, KEY).collect()["jellyfin"]

    assert observed["reachable"] is True
    assert observed["sessions"] == daemon.answer

    assert [path for path, _ in daemon.seen] == ["/Sessions"]


def test_the_key_travels_in_the_header_and_nowhere_else(daemon, url):
    """
    No secret reaches a governed artifact through this provider: it
    reads no environment and no file, and the key never enters the
    URL, where it would land in the daemon's access log.
    """

    JellyfinProvider(url, KEY).collect()

    path, header = daemon.seen[0]

    assert header == KEY
    assert KEY not in path


def test_an_unreachable_daemon_is_a_state_and_not_an_error():
    observed = JellyfinProvider(
        f"http://127.0.0.1:{closed_port()}", KEY
    ).collect()["jellyfin"]

    assert observed["reachable"] is False
    assert "could not be reached" in observed["unreachable_reason"]
    assert observed["sessions"] == []


def test_a_rejected_key_says_so_rather_than_looking_like_a_network_fault(
    daemon, url
):
    daemon.status = 401

    observed = JellyfinProvider(url, KEY).collect()["jellyfin"]

    assert observed["reachable"] is False
    assert "status 401" in observed["unreachable_reason"]


def test_a_missing_key_asks_nothing_and_says_why(daemon, url):
    observed = JellyfinProvider(url, "").collect()["jellyfin"]

    assert observed["reachable"] is False
    assert "no API key" in observed["unreachable_reason"]
    assert daemon.seen == []


def test_a_slow_daemon_is_given_up_on_rather_than_waited_for(daemon, url):
    daemon.delay = 0.5

    observed = JellyfinProvider(url, KEY, timeout=0.05).collect()["jellyfin"]

    assert observed["reachable"] is False
    assert "did not answer within" in observed["unreachable_reason"]


def test_no_sessions_playing_is_an_empty_list_not_an_error(daemon, url):
    daemon.answer = []

    observed = JellyfinProvider(url, KEY).collect()["jellyfin"]

    assert observed["reachable"] is True
    assert observed["sessions"] == []


def test_the_observation_names_what_it_looked_at(daemon, url):
    observed = JellyfinProvider(url, KEY).collect()

    assert observed["provider"]["id"] == "aistack.provider.jellyfin"
    assert observed["jellyfin"]["url"] == url
