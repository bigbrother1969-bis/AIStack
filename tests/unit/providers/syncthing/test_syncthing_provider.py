import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from aistack.providers.syncthing import SyncthingProvider


KEY = "a-key-that-is-not-a-secret-here"


class Daemon:
    """
    A Syncthing that answers on a real socket.

    A stub passed in as a callable would have tested the code
    around the call and not the call. This exercises the header,
    the query, the timeout and the status codes — the four things
    that actually break against a daemon, and the four a seam
    would have hidden.
    """

    def __init__(self):
        self.answers: dict[str, object] = {}
        self.status: dict[str, int] = {}
        self.seen: list[tuple[str, dict, str]] = []
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
                (
                    parsed.path,
                    {k: v[0] for k, v in parse_qs(parsed.query).items()},
                    self.headers.get("X-API-Key", ""),
                )
            )

            if state.delay:
                import time

                time.sleep(state.delay)

            code = state.status.get(parsed.path, 200)

            body = json.dumps(state.answers.get(parsed.path, {})).encode()

            self.send_response(code)
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
                # The provider gave up and closed the socket.
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


def test_the_folder_and_the_device_are_two_different_questions(daemon, url):
    """
    The defect this closes. `/rest/db/status` describes the folder
    on the server; `/rest/db/completion` describes what has
    reached the phone. On 2026-08-29 the first read `idle` with
    nothing pending while 159 selected artists had never been
    materialised — a true number under a false word, shown for
    seven weeks.
    """

    daemon.answers["/rest/db/status"] = {
        "state": "idle",
        "globalBytes": 3308034906,
        "needBytes": 0,
    }
    daemon.answers["/rest/db/completion"] = {
        "completion": 100,
        "needBytes": 0,
        "remoteState": "valid",
    }

    observed = SyncthingProvider(
        url, KEY, "music-android", "PNTJYZD"
    ).collect()["syncthing"]

    assert observed["reachable"]
    assert observed["folder"]["state"] == "idle"
    assert observed["device"]["completion"] == 100

    paths = [path for path, _, _ in daemon.seen]

    assert paths == ["/rest/db/status", "/rest/db/completion"]


def test_the_folder_and_the_device_are_named_in_the_query(daemon, url):

    SyncthingProvider(url, KEY, "music-android", "PNTJYZD").collect()

    status, completion = daemon.seen

    assert status[1] == {"folder": "music-android"}
    assert completion[1] == {
        "folder": "music-android",
        "device": "PNTJYZD",
    }


def test_the_key_travels_in_the_header_and_nowhere_else(daemon, url):
    """
    No secret reaches a governed artifact through this provider:
    it reads no environment and no file, and the key never enters
    the query string, where it would land in the daemon's access
    log.
    """

    SyncthingProvider(url, KEY, "music-android").collect()

    path, parameters, header = daemon.seen[0]

    assert header == KEY
    assert KEY not in json.dumps(parameters)
    assert KEY not in path


def test_an_unreachable_daemon_is_a_state_and_not_an_error():
    """
    The phone answers only through a tunnel and Android runs one
    VPN at a time; the daemon can be restarting. None of that is
    exceptional, and a screen that raised would say nothing at the
    moment it is most needed.
    """

    observed = SyncthingProvider(
        f"http://127.0.0.1:{closed_port()}", KEY, "music-android"
    ).collect()["syncthing"]

    assert observed["reachable"] is False
    assert "could not be reached" in observed["unreachable_reason"]
    assert observed["folder"] == {}


def test_a_rejected_key_says_so_rather_than_looking_like_a_network_fault(
    daemon, url
):
    """
    The failure that looks like the previous one and is not. A
    rotated key and an unplugged phone lead to different actions,
    so they read differently.
    """

    daemon.status["/rest/db/status"] = 403

    observed = SyncthingProvider(url, KEY, "music-android").collect()[
        "syncthing"
    ]

    assert observed["reachable"] is False
    assert "status 403" in observed["unreachable_reason"]


def test_a_missing_key_asks_nothing_and_says_why(daemon, url):

    observed = SyncthingProvider(url, "", "music-android").collect()[
        "syncthing"
    ]

    assert observed["reachable"] is False
    assert "no API key" in observed["unreachable_reason"]
    assert daemon.seen == []


def test_a_slow_daemon_is_given_up_on_rather_than_waited_for(daemon, url):
    """
    The screen is rendered on request. A daemon that hangs would
    hang the page, and a page that never renders says less than
    one saying the daemon did not answer.
    """

    daemon.delay = 0.5

    observed = SyncthingProvider(
        url, KEY, "music-android", timeout=0.05
    ).collect()["syncthing"]

    assert observed["reachable"] is False
    assert "did not answer within" in observed["unreachable_reason"]


def test_a_daemon_that_answers_once_keeps_what_it_answered(daemon, url):
    """
    Half an answer is not no answer. The folder was read; only the
    completion is missing, and it says why in its own place rather
    than discarding the half that arrived.
    """

    daemon.answers["/rest/db/status"] = {"state": "syncing"}
    daemon.status["/rest/db/completion"] = 500

    observed = SyncthingProvider(
        url, KEY, "music-android", "PNTJYZD"
    ).collect()["syncthing"]

    assert observed["reachable"] is True
    assert observed["folder"]["state"] == "syncing"
    assert "status 500" in observed["device"]["unavailable_reason"]


def test_no_device_means_no_second_question(daemon, url):

    SyncthingProvider(url, KEY, "music-android").collect()

    assert [path for path, _, _ in daemon.seen] == ["/rest/db/status"]


def test_what_the_daemon_did_not_return_is_not_invented(daemon, url):
    """
    A folder answering without `needBytes` and a folder with
    nothing left to transfer are different facts, and only one of
    them is good news.
    """

    daemon.answers["/rest/db/status"] = {"state": "idle"}

    observed = SyncthingProvider(url, KEY, "music-android").collect()[
        "syncthing"
    ]

    assert observed["folder"] == {"state": "idle"}
    assert "needBytes" not in observed["folder"]


def test_the_observation_names_what_it_looked_at(daemon, url):

    observed = SyncthingProvider(
        url, KEY, "music-android", "PNTJYZD"
    ).collect()

    assert observed["provider"]["id"] == "aistack.provider.syncthing"
    assert observed["syncthing"]["folder_id"] == "music-android"
    assert observed["syncthing"]["device_id"] == "PNTJYZD"
    assert observed["syncthing"]["url"] == url
