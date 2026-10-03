"""
A test client signed in (`ADR-0014`): a session opened in the
application's own store, its cookie set, and every `POST` carrying the
session's CSRF token, as a page served to that session would.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from aistack.authentication.sessions import OIDC
from aistack.web.authentication import SESSION_COOKIE

ADMINS = ("aistack_admins",)


def signed_in(client: TestClient, groups: tuple[str, ...] = ADMINS, name: str = "Tester") -> TestClient:
    """`client`, signed in — as an administrator unless `groups` says otherwise."""

    sessions = client.app.state.authentication.sessions  # type: ignore[attr-defined]
    identifier = sessions.open(subject=f"sub-{name}", name=name, groups=groups, method=OIDC)
    session = sessions.get(identifier)
    client.cookies.set(SESSION_COOKIE, identifier)

    original = client.post

    def post(url: Any, *args: Any, data: Any = None, **kwargs: Any) -> Any:
        if isinstance(data, list):
            data = [*data, ("csrf", session.csrf)]
        else:
            data = {"csrf": session.csrf, **(data or {})}
        return original(url, *args, data=data, **kwargs)

    client.post = post  # type: ignore[method-assign]
    return client


def as_user(client: TestClient) -> TestClient:
    """`client`, signed in without the administrators' group."""

    return signed_in(client, groups=(), name="Reader")
