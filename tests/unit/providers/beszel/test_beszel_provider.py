import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest

from aistack.providers.beszel import BeszelProvider


EMAIL = "aistack-readonly@persiaut-family.fr"
PASSWORD = "a-password-that-is-not-a-secret-here"
TOKEN = "a-token-that-is-not-a-secret-here"


class Hub:
    """
    A Beszel hub that answers on a real socket — same reasoning as
    `JellyfinProvider`'s own test daemon: a stub passed in as a
    callable would have tested the code around the call and not the
    call itself. Two routes, matching the two real requests
    `BeszelProvider` makes.
    """

    def __init__(self):
        self.auth_status = 200
        self.auth_answer: object = {
            "token": TOKEN,
            "record": {"id": "q6bpa5zceh2mrpx", "email": EMAIL},
        }
        self.systems_status = 200
        self.systems_answer: object = {"items": [], "page": 1}
        self.seen: list[tuple[str, str, str]] = []
        self.delay = 0.0


@pytest.fixture
def hub():
    return Hub()


@pytest.fixture
def url(hub):
    state = hub

    class Handler(BaseHTTPRequestHandler):

        def do_POST(self):
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")

            state.seen.append((parsed.path, "POST", body))

            if state.delay:
                import time

                time.sleep(state.delay)

            payload = json.dumps(state.auth_answer).encode()
            self.send_response(state.auth_status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            parsed = urlparse(self.path)

            state.seen.append(
                (parsed.path, "GET", self.headers.get("Authorization", ""))
            )

            payload = json.dumps(state.systems_answer).encode()
            self.send_response(state.systems_status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

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


# --------------------------------------------------------------------
# The happy path
# --------------------------------------------------------------------


def test_systems_are_returned_exactly_as_the_hub_answered_them(hub, url):
    hub.systems_answer = {
        "items": [
            {"id": "s1", "name": "Gigabyte", "host": "192.168.1.10", "status": "up"}
        ]
    }

    observed = BeszelProvider(url, EMAIL, PASSWORD).collect()["beszel"]

    assert observed["reachable"] is True
    assert observed["systems"] == hub.systems_answer["items"]


def test_authentication_happens_before_the_systems_request(hub, url):
    BeszelProvider(url, EMAIL, PASSWORD).collect()

    paths = [path for path, _method, _extra in hub.seen]
    assert paths == [
        "/api/collections/users/auth-with-password",
        "/api/collections/systems/records",
    ]


def test_the_credentials_travel_in_the_auth_body_and_the_token_in_the_header(
    hub, url
):
    """
    No secret reaches a governed artifact through this provider: the
    email/password are sent once, to authenticate, and never again;
    the token from that step travels as the literal `Authorization`
    header value on the systems request — no `Bearer ` prefix, which
    is what the owner's own real hub proved it wants, 2026-09-12.
    """

    BeszelProvider(url, EMAIL, PASSWORD).collect()

    auth_path, _method, auth_body = hub.seen[0]
    systems_path, _method2, auth_header = hub.seen[1]

    assert json.loads(auth_body) == {"identity": EMAIL, "password": PASSWORD}
    assert auth_header == TOKEN
    assert not auth_header.startswith("Bearer ")


def test_the_observation_names_what_it_looked_at(hub, url):
    observed = BeszelProvider(url, EMAIL, PASSWORD).collect()

    assert observed["provider"]["id"] == "aistack.provider.beszel"
    assert observed["beszel"]["url"] == url


# --------------------------------------------------------------------
# Missing credentials
# --------------------------------------------------------------------


def test_missing_credentials_ask_nothing_and_say_why(hub, url):
    observed = BeszelProvider(url, "", "").collect()["beszel"]

    assert observed["reachable"] is False
    assert "no credentials" in observed["unreachable_reason"]
    assert hub.seen == []


def test_a_missing_password_alone_also_asks_nothing(hub, url):
    observed = BeszelProvider(url, EMAIL, "").collect()["beszel"]

    assert observed["reachable"] is False
    assert hub.seen == []


# --------------------------------------------------------------------
# Authentication failures
# --------------------------------------------------------------------


def test_a_rejected_login_says_so_rather_than_looking_like_a_network_fault(
    hub, url
):
    hub.auth_status = 403
    hub.auth_answer = {
        "data": {},
        "message": "The request doesn't satisfy the collection requirements to authenticate.",
        "status": 403,
    }

    observed = BeszelProvider(url, EMAIL, PASSWORD).collect()["beszel"]

    assert observed["reachable"] is False
    assert "authentication" in observed["unreachable_reason"]
    assert "403" in observed["unreachable_reason"]
    # The systems endpoint was never reached — authentication failed first.
    assert len(hub.seen) == 1


def test_a_response_with_no_token_is_named_as_such(hub, url):
    hub.auth_answer = {"record": {"id": "x"}}

    observed = BeszelProvider(url, EMAIL, PASSWORD).collect()["beszel"]

    assert observed["reachable"] is False
    assert "no token" in observed["unreachable_reason"]


# --------------------------------------------------------------------
# Systems-request failures, after a successful login
# --------------------------------------------------------------------


def test_a_rejected_systems_request_says_so(hub, url):
    hub.systems_status = 401
    hub.systems_answer = {"message": "unauthorized"}

    observed = BeszelProvider(url, EMAIL, PASSWORD).collect()["beszel"]

    assert observed["reachable"] is False
    assert "status 401" in observed["unreachable_reason"]


def test_an_empty_systems_list_is_reachable_not_an_error(hub, url):
    hub.systems_answer = {"items": []}

    observed = BeszelProvider(url, EMAIL, PASSWORD).collect()["beszel"]

    assert observed["reachable"] is True
    assert observed["systems"] == []


# --------------------------------------------------------------------
# Unreachable hub
# --------------------------------------------------------------------


def test_an_unreachable_hub_is_a_state_and_not_an_error():
    observed = BeszelProvider(
        f"http://127.0.0.1:{closed_port()}", EMAIL, PASSWORD
    ).collect()["beszel"]

    assert observed["reachable"] is False
    assert "could not be reached" in observed["unreachable_reason"]
    assert observed["systems"] == []


def test_a_slow_hub_is_given_up_on_rather_than_waited_for(hub, url):
    hub.delay = 0.5

    observed = BeszelProvider(
        url, EMAIL, PASSWORD, timeout=0.05
    ).collect()["beszel"]

    assert observed["reachable"] is False
    assert "did not answer within" in observed["unreachable_reason"]
