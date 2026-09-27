"""
`aistack.console.server` — ADR-0010 § 5.

The console's server replaced the standard library's `http.server`,
and stays standard library itself so the governed suite can test it
(roadmap R5, 2026-09-27: logic in `src/`, tested; web layers thin).
Every route is exercised through `respond`, a pure function of the
request line, the cookie and the generated directory; one test at the
end opens a real socket, so the handler that wraps `respond` is proven
wired too.
"""

from __future__ import annotations

import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from aistack.console.server import PAGES, make_handler, respond
from aistack.i18n.pages import page_file
from aistack.i18n import LANGUAGE_COOKIE, Language, Languages

LANGUAGES = Languages(
    reference="fr",
    available=(Language("fr", "Français"), Language("en", "English")),
)


@pytest.fixture
def generated(tmp_path: Path) -> Path:
    for page in PAGES:
        stem = page.removesuffix(".html")
        (tmp_path / page).write_text(f"<p>{stem} fr</p>", encoding="utf-8")
        (tmp_path / f"{stem}.en.html").write_text(f"<p>{stem} en</p>", encoding="utf-8")

    (tmp_path / "docker-observation.json").write_text("{}", encoding="utf-8")
    (tmp_path / "history").mkdir()

    return tmp_path


def header(response, name: str) -> str | None:
    for key, value in response.headers:
        if key == name:
            return value
    return None


# --------------------------------------------------------------------
# page_file — the reference keeps each page's historical name
# --------------------------------------------------------------------


def test_the_reference_language_keeps_the_historical_file_name(tmp_path: Path):
    assert page_file(tmp_path, "console.html", "fr", "fr") == tmp_path / "console.html"


def test_another_language_sits_beside_it(tmp_path: Path):
    assert page_file(tmp_path, "health.html", "en", "fr") == tmp_path / "health.en.html"


# --------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------


def test_a_page_is_served_in_the_reference_language_by_default(generated: Path):
    response = respond("GET", "/console.html", None, generated, LANGUAGES)

    assert response.status == 200
    assert response.body == b"<p>console fr</p>"
    assert header(response, "Content-Type") == "text/html; charset=utf-8"
    assert header(response, "Set-Cookie") is None


def test_a_requested_language_is_served_and_remembered(generated: Path):
    response = respond("GET", "/architecture.html?lang=en", None, generated, LANGUAGES)

    assert response.body == b"<p>architecture en</p>"
    assert header(response, "Set-Cookie").startswith(f"{LANGUAGE_COOKIE}=en;")


def test_the_remembered_language_is_served_without_rewriting_the_cookie(generated: Path):
    response = respond("GET", "/health.html", "aistack_lang=en", generated, LANGUAGES)

    assert response.body == b"<p>health en</p>"
    assert header(response, "Set-Cookie") is None


def test_a_page_missing_in_the_chosen_language_falls_back_to_the_reference(
    generated: Path,
):
    (generated / "health.en.html").unlink()

    response = respond("GET", "/health.html?lang=en", None, generated, LANGUAGES)

    assert response.status == 200
    assert response.body == b"<p>health fr</p>"


def test_a_page_never_generated_is_a_404_that_names_it(tmp_path: Path):
    response = respond("GET", "/health.html?lang=en", None, tmp_path, LANGUAGES)

    assert response.status == 404
    assert b"health.html" in response.body
    assert b"has not been generated" in response.body


def test_a_page_varies_with_the_cookie_and_is_never_cached(generated: Path):
    response = respond("GET", "/console.html", None, generated, LANGUAGES)

    assert header(response, "Vary") == "Cookie"
    assert header(response, "Cache-Control") == "no-cache"


def test_head_sends_headers_without_a_body(generated: Path):
    response = respond("HEAD", "/console.html", None, generated, LANGUAGES)

    assert response.status == 200
    assert response.body == b""
    assert header(response, "Content-Length") == str(len(b"<p>console fr</p>"))


# --------------------------------------------------------------------
# Only the closed list is ever served
# --------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    [
        "/docker-observation.json",
        "/history/",
        "/../console.html",
        "/%2e%2e/etc/passwd",
        "/console.en.html",
        "/public/console.html",
    ],
)
def test_nothing_outside_the_closed_list_is_served(generated: Path, target: str):
    response = respond("GET", target, None, generated, LANGUAGES)

    assert response.status == 404


# --------------------------------------------------------------------
# Root and Settings
# --------------------------------------------------------------------


def test_the_root_redirects_to_the_console(generated: Path):
    response = respond("GET", "/", None, generated, LANGUAGES)

    assert response.status == 302
    assert header(response, "Location") == "/console.html"


def test_the_root_keeps_a_requested_language(generated: Path):
    response = respond("GET", "/?lang=en", None, generated, LANGUAGES)

    assert header(response, "Location") == "/console.html?lang=en"
    assert header(response, "Set-Cookie").startswith(f"{LANGUAGE_COOKIE}=en;")


def test_settings_is_rendered_in_the_current_language(generated: Path):
    response = respond("GET", "/settings", "aistack_lang=en", generated, LANGUAGES)

    assert response.status == 200
    assert b'<html lang="en">' in response.body
    assert b"Interface language" in response.body
    assert b"Language saved" not in response.body


def test_choosing_a_language_in_settings_remembers_it_and_confirms(generated: Path):
    response = respond("GET", "/settings?lang=en", "aistack_lang=fr", generated, LANGUAGES)

    assert header(response, "Set-Cookie").startswith(f"{LANGUAGE_COOKIE}=en;")
    assert b"Language saved for this browser." in response.body
    assert b'value="en" checked' in response.body


def test_an_unknown_route_is_a_localized_404(generated: Path):
    response = respond("GET", "/nowhere", "aistack_lang=en", generated, LANGUAGES)

    assert response.status == 404
    assert b"Page not found" in response.body


# --------------------------------------------------------------------
# The real handler, over a real socket
# --------------------------------------------------------------------


def test_the_handler_serves_respond_over_http(generated: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(generated, LANGUAGES))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        port = server.server_address[1]

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/console.html?lang=en") as reply:
            assert reply.status == 200
            assert reply.read() == b"<p>console en</p>"
            assert reply.headers["Set-Cookie"].startswith(f"{LANGUAGE_COOKIE}=en;")

        with pytest.raises(urllib.error.HTTPError) as refused:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/docker-observation.json")

        assert refused.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
