import base64
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import pytest

from aistack.providers.nextcloud import NextcloudProvider


USERNAME = "appolonie.persiaut"
APP_PASSWORD = "a-password-that-is-not-a-secret-here"
FOLDER = "Photos/iPhone-Appolonie"

_MULTISTATUS_HEADER = '<?xml version="1.0"?><d:multistatus xmlns:d="DAV:">'
_MULTISTATUS_FOOTER = "</d:multistatus>"


def _folder_response(href: str) -> str:
    return (
        f"<d:response><d:href>{href}</d:href>"
        "<d:propstat><d:prop><d:resourcetype><d:collection/>"
        "</d:resourcetype></d:prop>"
        "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
        "</d:response>"
    )


def _file_response(
    href: str,
    size: int = 1234,
    etag: str = '"abc123"',
    modified: str = "Fri, 18 Sep 2026 10:00:00 GMT",
) -> str:
    return (
        f"<d:response><d:href>{href}</d:href>"
        "<d:propstat><d:prop>"
        f"<d:getcontentlength>{size}</d:getcontentlength>"
        f"<d:getetag>{etag}</d:getetag>"
        f"<d:getlastmodified>{modified}</d:getlastmodified>"
        "<d:resourcetype/>"
        "</d:prop>"
        "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
        "</d:response>"
    )


def _multistatus(*responses: str) -> bytes:
    return (_MULTISTATUS_HEADER + "".join(responses) + _MULTISTATUS_FOOTER).encode()


class Daemon:
    """
    A Nextcloud that answers `PROPFIND` on a real socket.

    Same reasoning as `test_syncthing_provider.py`'s own `Daemon`: a
    stub passed in as a callable would test the code around the
    call, not the call. This exercises the method, the header, the
    body and the status codes — what actually breaks against a
    WebDAV server.
    """

    def __init__(self) -> None:
        self.bodies: dict[str, bytes] = {}
        self.status: dict[str, int] = {}
        self.seen: list[tuple[str, str, str, bytes]] = []
        self.delay = 0.0


@pytest.fixture
def daemon() -> Daemon:
    return Daemon()


@pytest.fixture
def url(daemon: Daemon):
    state = daemon

    class Handler(BaseHTTPRequestHandler):

        def do_PROPFIND(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""

            state.seen.append(
                (
                    unquote(parsed.path),
                    self.headers.get("Authorization", ""),
                    self.headers.get("Depth", ""),
                    body,
                )
            )

            if state.delay:
                import time

                time.sleep(state.delay)

            code = state.status.get(unquote(parsed.path), 207)
            reply = state.bodies.get(unquote(parsed.path), _multistatus())

            self.send_response(code)
            self.send_header("Content-Type", "application/xml; charset=utf-8")
            self.send_header("Content-Length", str(len(reply)))
            self.end_headers()

            if code < 300:
                self.wfile.write(reply)

        def log_message(self, *_args) -> None:
            pass

        def handle_one_request(self) -> None:
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


def _path() -> str:
    return f"/remote.php/dav/files/{USERNAME}/{FOLDER}"


def test_the_observation_names_what_it_looked_at(daemon, url):
    observed = NextcloudProvider(
        url, USERNAME, APP_PASSWORD, FOLDER
    ).collect()

    assert observed["provider"]["id"] == "aistack.provider.nextcloud"
    assert observed["nextcloud"]["url"] == url
    assert observed["nextcloud"]["username"] == USERNAME
    assert observed["nextcloud"]["folder"] == FOLDER


def test_the_app_password_travels_in_the_header_and_nowhere_else(daemon, url):
    """
    Same discipline as `SyncthingProvider`'s API key: the password
    never enters the query string or the path, where a reverse
    proxy's access log would keep it.
    """

    NextcloudProvider(url, USERNAME, APP_PASSWORD, FOLDER).collect()

    path, authorization, _depth, _body = daemon.seen[0]

    expected = "Basic " + base64.b64encode(
        f"{USERNAME}:{APP_PASSWORD}".encode()
    ).decode()

    assert authorization == expected
    assert APP_PASSWORD not in path


def test_an_unreachable_server_is_a_state_and_not_an_error():
    observed = NextcloudProvider(
        f"http://127.0.0.1:{closed_port()}", USERNAME, APP_PASSWORD, FOLDER
    ).collect()["nextcloud"]

    assert observed["reachable"] is False
    assert "could not be reached" in observed["unreachable_reason"]
    assert observed["files"] == []


def test_a_missing_app_password_asks_nothing_and_says_why(daemon, url):
    observed = NextcloudProvider(url, USERNAME, "", FOLDER).collect()[
        "nextcloud"
    ]

    assert observed["reachable"] is False
    assert "no app password" in observed["unreachable_reason"]
    assert daemon.seen == []


def test_a_slow_server_is_given_up_on_rather_than_waited_for(daemon, url):
    daemon.delay = 0.5

    observed = NextcloudProvider(
        url, USERNAME, APP_PASSWORD, FOLDER, timeout=0.05
    ).collect()["nextcloud"]

    assert observed["reachable"] is False
    assert "did not answer within" in observed["unreachable_reason"]


def test_a_rejected_password_says_so_rather_than_looking_like_a_network_fault(
    daemon, url
):
    daemon.status[_path()] = 401

    observed = NextcloudProvider(
        url, USERNAME, APP_PASSWORD, FOLDER
    ).collect()["nextcloud"]

    assert observed["reachable"] is False
    assert "status 401" in observed["unreachable_reason"]


def test_a_folder_that_has_never_received_anything_is_not_an_error(
    daemon, url
):
    """
    `PLAN-PHOTOS-IPHONE-NEXTCLOUD-IMMICH-2026-09-18.md` names the
    target as a brand-new subfolder — a `404` there, on a fresh
    account, is the ordinary first state, not a fault.
    """

    daemon.status[_path()] = 404

    observed = NextcloudProvider(
        url, USERNAME, APP_PASSWORD, FOLDER
    ).collect()["nextcloud"]

    assert observed["reachable"] is True
    assert observed["unreachable_reason"] == ""
    assert observed["folder_exists"] is False
    assert observed["files"] == []


def test_files_are_reported_with_size_etag_and_modified_date(daemon, url):
    href = _path() + "/IMG_0001.HEIC"

    daemon.bodies[_path()] = _multistatus(
        _folder_response(_path() + "/"),
        _file_response(href, size=2048576, etag='"9f8e7d"'),
    )

    observed = NextcloudProvider(
        url, USERNAME, APP_PASSWORD, FOLDER
    ).collect()["nextcloud"]

    assert observed["reachable"] is True
    assert observed["folder_exists"] is True
    assert observed["files"] == [
        {
            "name": "IMG_0001.HEIC",
            "size": 2048576,
            "etag": "9f8e7d",
            "last_modified": "Fri, 18 Sep 2026 10:00:00 GMT",
        }
    ]


def test_the_folder_itself_is_not_reported_as_one_of_its_files(daemon, url):
    """
    `Depth: 1` answers about the queried collection first, in the
    same list as its children — that entry is not a file.
    """

    daemon.bodies[_path()] = _multistatus(
        _folder_response(_path() + "/"),
    )

    observed = NextcloudProvider(
        url, USERNAME, APP_PASSWORD, FOLDER
    ).collect()["nextcloud"]

    assert observed["files"] == []


def test_subfolders_are_not_reported_as_files(daemon, url):
    daemon.bodies[_path()] = _multistatus(
        _folder_response(_path() + "/"),
        _folder_response(_path() + "/2026-09/"),
    )

    observed = NextcloudProvider(
        url, USERNAME, APP_PASSWORD, FOLDER
    ).collect()["nextcloud"]

    assert observed["files"] == []


def test_a_property_the_server_declined_is_not_invented(daemon, url):
    """
    A server that answers `404` for one property inside its own
    `propstat` group is declining it, not reporting an empty etag —
    the two are different facts.
    """

    href = _path() + "/IMG_0002.HEIC"

    body = (
        _MULTISTATUS_HEADER
        + f"<d:response><d:href>{href}</d:href>"
        + "<d:propstat><d:prop><d:getcontentlength>512</d:getcontentlength>"
        + "<d:resourcetype/></d:prop>"
        + "<d:status>HTTP/1.1 200 OK</d:status></d:propstat>"
        + "<d:propstat><d:prop><d:getetag/></d:prop>"
        + "<d:status>HTTP/1.1 404 Not Found</d:status></d:propstat>"
        + "</d:response>"
        + _MULTISTATUS_FOOTER
    ).encode()

    daemon.bodies[_path()] = body

    observed = NextcloudProvider(
        url, USERNAME, APP_PASSWORD, FOLDER
    ).collect()["nextcloud"]

    assert observed["files"] == [
        {
            "name": "IMG_0002.HEIC",
            "size": 512,
            "etag": None,
            "last_modified": None,
        }
    ]


def test_depth_one_is_asked_so_subfolders_are_not_recursed(daemon, url):
    NextcloudProvider(url, USERNAME, APP_PASSWORD, FOLDER).collect()

    _path_seen, _authorization, depth, _body = daemon.seen[0]

    assert depth == "1"
