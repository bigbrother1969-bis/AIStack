"""Profile resolution with an individual assignment (`ADR-0034`),
layered on top of `profile_of` (`ADR-0014`, `test_rights.py`)."""

from __future__ import annotations

from pathlib import Path

from aistack.authentication.oidc import OidcClient
from aistack.authentication.profiles import ADMIN as P_ADMIN
from aistack.authentication.profiles import USER as P_USER
from aistack.authentication.profiles import ProfileStore
from aistack.authentication.sessions import LOCAL, OIDC, Session, SessionStore
from aistack.web.authentication import (
    ADMIN,
    USER,
    Authentication,
    assign_account,
    resolved_profile,
    revoke_account,
)
from tests.unit.authentication_fake import CREDENTIALS, DEFINITION, FakeProvider

ADMIN_GROUP = "aistack_admins"


def session(email: str = "ada@example.com", groups: tuple[str, ...] = (), method: str = OIDC) -> Session:
    return Session(subject="s", name="Ada", email=email, groups=groups, method=method, id_token="", csrf="c")


def test_with_no_assignment_the_group_decides_exactly_as_before(tmp_path: Path):
    profiles = ProfileStore(tmp_path / "profiles.sqlite3")

    assert resolved_profile(session(groups=("family",)), ADMIN_GROUP, profiles) == USER
    assert resolved_profile(session(groups=(ADMIN_GROUP,)), ADMIN_GROUP, profiles) == ADMIN
    assert resolved_profile(None, ADMIN_GROUP, profiles) is None


def test_an_individual_assignment_wins_over_group_membership(tmp_path: Path):
    profiles = ProfileStore(tmp_path / "profiles.sqlite3")
    profiles.assign("ada@example.com", P_USER, by="owner")

    # In the group, but individually assigned to user: the individual wins.
    assert resolved_profile(session(groups=(ADMIN_GROUP,)), ADMIN_GROUP, profiles) == USER


def test_a_pre_assignment_resolves_before_any_sign_in_ever_happened(tmp_path: Path):
    profiles = ProfileStore(tmp_path / "profiles.sqlite3")
    profiles.assign("new-person@example.com", P_ADMIN, by="owner")

    assert resolved_profile(session(email="new-person@example.com", groups=()), ADMIN_GROUP, profiles) == ADMIN


def test_a_revoked_account_resolves_to_no_profile_even_in_the_admin_group(tmp_path: Path):
    profiles = ProfileStore(tmp_path / "profiles.sqlite3")
    profiles.assign("ada@example.com", P_ADMIN, by="owner")
    profiles.revoke("ada@example.com", by="owner")

    assert resolved_profile(session(groups=(ADMIN_GROUP,)), ADMIN_GROUP, profiles) is None


def test_the_local_fallback_account_is_untouched_it_has_no_email(tmp_path: Path):
    profiles = ProfileStore(tmp_path / "profiles.sqlite3")
    profiles.assign("ada@example.com", P_USER, by="owner")

    assert resolved_profile(session(email="", method=LOCAL), ADMIN_GROUP, profiles) == ADMIN


def _authentication(tmp_path: Path) -> Authentication:
    return Authentication(
        definition=DEFINITION,
        credentials=CREDENTIALS,
        sessions=SessionStore(tmp_path / "web" / "sessions.sqlite3", 8 * 3600, 7 * 86400),
        oidc=OidcClient(DEFINITION, CREDENTIALS, FakeProvider()),
        profiles=ProfileStore(tmp_path / "web" / "profiles.sqlite3"),
    )


def test_assigning_takes_effect_without_touching_any_session(tmp_path: Path):
    authentication = _authentication(tmp_path)
    identifier = authentication.sessions.open(
        subject="s", name="Ada", email="ada@example.com", method=OIDC
    )

    assign_account(authentication, "ada@example.com", P_ADMIN, by="owner")

    live_session = authentication.sessions.get(identifier)
    assert live_session is not None  # unaffected — only the profile changed
    assert resolved_profile(live_session, ADMIN_GROUP, authentication.profiles) == ADMIN


def test_revoking_cuts_the_live_session_immediately(tmp_path: Path):
    authentication = _authentication(tmp_path)
    identifier = authentication.sessions.open(
        subject="s", name="Ada", email="ada@example.com", groups=(ADMIN_GROUP,), method=OIDC
    )
    assert authentication.sessions.get(identifier) is not None

    revoke_account(authentication, "ada@example.com", by="owner")

    # Not merely profile-less: the session itself is gone, so
    # `require_signed_in` sees no session at all on the next request.
    assert authentication.sessions.get(identifier) is None


def test_revoking_an_account_with_no_live_session_still_logs_the_change(tmp_path: Path):
    authentication = _authentication(tmp_path)

    revoke_account(authentication, "never-signed-in@example.com", by="owner")

    assert authentication.profiles is not None
    assert authentication.profiles.profile_for("never-signed-in@example.com") == "revoked"
