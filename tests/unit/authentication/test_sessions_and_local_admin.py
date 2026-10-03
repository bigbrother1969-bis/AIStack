"""
`aistack.authentication.sessions`, `.local_admin` and `.definition`
(`ADR-0013` § 3, § 5).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from aistack.authentication.definition import (
    credentials_from,
    load_authentication_yaml,
)
from aistack.authentication.local_admin import (
    MAX_FAILURES,
    WINDOW_SECONDS,
    FailureWindow,
    hash_password,
    verify_password,
)
from aistack.authentication.sessions import OIDC, PENDING_SECONDS, Pending, SessionStore
from aistack.cli import web_admin_password


def store(tmp_path: Path, now: list[float]) -> SessionStore:
    return SessionStore(tmp_path / "web" / "sessions.sqlite3", 8 * 3600, 7 * 86400, clock=lambda: now[0])


def test_a_session_is_found_by_its_cookie_and_the_file_holds_no_cookie(tmp_path: Path):
    now = [1000.0]
    sessions = store(tmp_path, now)

    identifier = sessions.open(subject="u", name="Ann", groups=("g",), method=OIDC, id_token="t")
    session = sessions.get(identifier)

    assert session is not None and session.name == "Ann" and session.groups == ("g",)
    assert sessions.get("forged") is None
    raw = (tmp_path / "web" / "sessions.sqlite3").read_bytes()
    assert identifier.encode() not in raw


def test_each_sign_in_gets_a_new_identifier(tmp_path: Path):
    sessions = store(tmp_path, [0.0])

    assert sessions.open(subject="u", name="a", method=OIDC) != sessions.open(subject="u", name="a", method=OIDC)


def test_a_session_ends_after_eight_idle_hours_and_the_row_goes(tmp_path: Path):
    now = [0.0]
    sessions = store(tmp_path, now)
    identifier = sessions.open(subject="u", name="a", method=OIDC)

    now[0] = 8 * 3600 - 1
    assert sessions.get(identifier) is not None  # and the idle clock restarts
    now[0] = 2 * 8 * 3600 - 2
    assert sessions.get(identifier) is not None
    now[0] = 3 * 8 * 3600
    assert sessions.get(identifier) is None
    assert sessions.count() == 0


def test_a_session_ends_after_seven_days_however_active(tmp_path: Path):
    now = [0.0]
    sessions = store(tmp_path, now)
    identifier = sessions.open(subject="u", name="a", method=OIDC)

    while now[0] < 7 * 86400 - 3600:
        now[0] += 3600
        assert sessions.get(identifier) is not None
    now[0] = 7 * 86400
    assert sessions.get(identifier) is None


def test_closing_a_session_revokes_it(tmp_path: Path):
    sessions = store(tmp_path, [0.0])
    identifier = sessions.open(subject="u", name="a", method=OIDC)

    sessions.close(identifier)

    assert sessions.get(identifier) is None


def test_a_pending_sign_in_is_taken_once_and_expires(tmp_path: Path):
    now = [0.0]
    sessions = store(tmp_path, now)
    sessions.remember("s1", Pending(nonce="n", verifier="v", next="/x"))
    sessions.remember("s2", Pending(nonce="n", verifier="v", next="/x"))

    assert sessions.take("s1") == Pending(nonce="n", verifier="v", next="/x")
    assert sessions.take("s1") is None
    now[0] = PENDING_SECONDS
    assert sessions.take("s2") is None


def test_the_sessions_survive_a_restart(tmp_path: Path):
    identifier = store(tmp_path, [0.0]).open(subject="u", name="a", method=OIDC)

    assert store(tmp_path, [10.0]).get(identifier) is not None
    assert sqlite3.connect(tmp_path / "web" / "sessions.sqlite3").execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1


def test_a_password_hash_verifies_only_its_password():
    stored = hash_password("correct horse battery")

    assert stored.startswith("scrypt$32768$8$1$")
    assert verify_password("correct horse battery", stored)
    assert not verify_password("correct horse batterz", stored)
    assert not verify_password("x", "not-a-hash")
    assert hash_password("same") != hash_password("same")  # salted


def test_five_failures_lock_the_form_for_fifteen_minutes():
    now = [0.0]
    window = FailureWindow(clock=lambda: now[0])

    for _ in range(MAX_FAILURES):
        assert not window.locked()
        window.failed()
    assert window.locked()
    now[0] = WINDOW_SECONDS
    assert not window.locked()


def test_the_declared_definition_and_the_environment(tmp_path: Path):
    definition = load_authentication_yaml()

    assert definition.issuer == "https://id.persiaut-family.fr"
    assert definition.redirect_uri == "https://aistack.persiaut-family.fr/auth/callback"
    assert "groups" in definition.scopes

    configured = credentials_from(
        {"AISTACK_OIDC_CLIENT_ID": " id ", "AISTACK_OIDC_CLIENT_SECRET": "s"}, definition
    )
    assert configured.oidc_configured and configured.client_id == "id"
    assert not credentials_from({}, definition).oidc_configured

    bad = tmp_path / "authentication.yml"
    bad.write_text("issuer: http://id.example\npublic_base_url: https://a\nscopes: [openid]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="https://"):
        load_authentication_yaml(bad)


def test_the_cli_prints_a_quoted_line_and_never_the_password(capsys):
    answers = iter(["a long enough password", "a long enough password"])

    assert web_admin_password.main(lambda prompt: next(answers)) == 0
    line = capsys.readouterr().out.strip()

    name, value = line.split("=", 1)
    assert name == "AISTACK_WEB_ADMIN_SCRYPT"
    assert value.startswith("'scrypt$") and value.endswith("'")
    assert "long enough" not in line
    assert verify_password("a long enough password", value.strip("'"))


@pytest.mark.parametrize("answers", [["short", "short"], ["a long enough password", "another one, longer"]])
def test_the_cli_refuses_a_short_or_mistyped_password(answers, capsys):
    replies = iter(answers)

    assert web_admin_password.main(lambda prompt: next(replies)) == 1
    assert capsys.readouterr().out == ""
