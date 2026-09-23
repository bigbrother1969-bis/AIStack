import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aistack.providers.http_probe import HttpProbeProvider


class Server:
    """
    A real socket, same reasoning as `BeszelProvider`'s own test
    `Hub` — a stubbed callable would test the code around the request,
    not the request itself. `status_by_path` lets a single server
    answer several targets with different codes, so one fixture
    covers the whole fleet a real render probes.
    """

    def __init__(self):
        self.status_by_path: dict[str, int] = {}
        self.default_status = 200
        self.delay = 0.0
        self.seen_paths: list[str] = []
        self.user_agents_seen: list[str] = []


@pytest.fixture
def server():
    return Server()


@pytest.fixture
def base_url(server):
    state = server

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):
            state.seen_paths.append(self.path)
            state.user_agents_seen.append(self.headers.get("User-Agent", ""))

            if state.delay:
                time.sleep(state.delay)

            status = state.status_by_path.get(self.path, state.default_status)
            body = b""
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

        def handle_one_request(self):
            try:
                super().handle_one_request()
            except OSError:
                self.close_connection = True

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{httpd.server_port}"

    httpd.shutdown()
    httpd.server_close()


def closed_port() -> int:
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


# --------------------------------------------------------------------
# The happy path
# --------------------------------------------------------------------


def test_a_2xx_response_is_reachable_with_its_status_code(server, base_url):
    server.default_status = 200

    targets = (("Gitea", base_url + "/gitea"),)
    observed = HttpProbeProvider(targets).collect()

    target = observed["http_probe"]["targets"][0]
    assert target["name"] == "Gitea"
    assert target["url"] == base_url + "/gitea"
    assert target["reachable"] is True
    assert target["status_code"] == 200
    assert target["unreachable_reason"] == ""


def test_every_target_is_probed_and_travels_in_order(server, base_url):
    server.status_by_path = {"/a": 200, "/b": 200, "/c": 200}

    observed = HttpProbeProvider(
        (
            ("Alpha", base_url + "/a"),
            ("Bravo", base_url + "/b"),
            ("Charlie", base_url + "/c"),
        )
    ).collect()

    names = [t["name"] for t in observed["http_probe"]["targets"]]
    assert names == ["Alpha", "Bravo", "Charlie"]
    assert sorted(server.seen_paths) == ["/a", "/b", "/c"]


def test_the_observation_names_the_provider(server, base_url):
    observed = HttpProbeProvider((("Gitea", base_url),)).collect()

    assert observed["provider"]["id"] == "aistack.provider.http_probe"
    assert observed["provider"]["name"] == "HTTP Probe Provider"
    assert "collected_at" in observed


def test_an_empty_target_list_probes_nothing(server, base_url):
    observed = HttpProbeProvider(()).collect()

    assert observed["http_probe"]["targets"] == []


def test_every_request_carries_an_explicit_user_agent(server, base_url):
    """
    Same fix `BeszelProvider` needed 2026-09-12 for the identical
    reason: Cloudflare, fronting these same `*.persiaut-family.fr`
    names, refuses `urllib.request`'s own default signature.
    """

    HttpProbeProvider((("Gitea", base_url),)).collect()

    assert len(server.user_agents_seen) == 1
    assert server.user_agents_seen[0]
    assert not server.user_agents_seen[0].lower().startswith("python-urllib")


# --------------------------------------------------------------------
# The server answered — with an error status
# --------------------------------------------------------------------


@pytest.mark.parametrize("status", [301, 404, 500, 503])
def test_an_error_status_is_still_reachable(server, base_url, status):
    server.default_status = status

    observed = HttpProbeProvider((("Svc", base_url),)).collect()

    target = observed["http_probe"]["targets"][0]
    assert target["reachable"] is True
    assert target["status_code"] == status
    assert target["unreachable_reason"] == ""


# --------------------------------------------------------------------
# Injoignable — a state, not an error
# --------------------------------------------------------------------


def test_an_unreachable_target_is_a_state_and_not_an_error():
    url = f"http://127.0.0.1:{closed_port()}"

    observed = HttpProbeProvider((("Svc", url),)).collect()

    target = observed["http_probe"]["targets"][0]
    assert target["reachable"] is False
    assert target["status_code"] is None
    assert "could not be reached" in target["unreachable_reason"]


def test_a_slow_target_is_given_up_on_rather_than_waited_for(server, base_url):
    server.delay = 0.5

    observed = HttpProbeProvider(
        (("Svc", base_url),), timeout=0.05
    ).collect()

    target = observed["http_probe"]["targets"][0]
    assert target["reachable"] is False
    assert target["status_code"] is None
    assert "did not answer within" in target["unreachable_reason"]


def test_one_unreachable_target_does_not_stop_the_others(server, base_url):
    unreachable_url = f"http://127.0.0.1:{closed_port()}"

    observed = HttpProbeProvider(
        (
            ("Down", unreachable_url),
            ("Up", base_url),
        )
    ).collect()

    targets = {t["name"]: t for t in observed["http_probe"]["targets"]}
    assert targets["Down"]["reachable"] is False
    assert targets["Up"]["reachable"] is True
    assert targets["Up"]["status_code"] == 200
