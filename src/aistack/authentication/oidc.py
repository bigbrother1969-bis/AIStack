"""
OpenID Connect against Pocket ID (`ADR-0013` § 2): Authorization Code
with PKCE (`S256`), a confidential client, and an ID token believed
only once its signature has been verified against the provider's
published keys.

The network is a collaborator (`Http`), so the suite runs every step
against a fake provider whose keys it generates.
"""

from __future__ import annotations

import base64
import importlib.metadata
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import jwt

from aistack.authentication.definition import AuthenticationDefinition, Credentials
from aistack.authentication.sessions import Pending

ALGORITHM = "RS256"
CACHE_SECONDS = 3600.0
LEEWAY_SECONDS = 60
TIMEOUT_SECONDS = 10.0


class SignInError(Exception):
    """A sign-in refused; `reason` is an i18n key the page shows."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


class Http(Protocol):
    def get_json(self, url: str) -> dict[str, Any]: ...

    def post_form(self, url: str, form: dict[str, str], basic_auth: tuple[str, str]) -> dict[str, Any]: ...


def user_agent() -> str:
    """How AIStack names itself to the provider.

    Never Python's default `Python-urllib/3.x`: Cloudflare, in front of
    Pocket ID, refuses that one as a robot — measured 2026-10-03, when
    `/login` failed on GIGABYTE while `curl` from the same host read
    the same document."""

    try:
        version = importlib.metadata.version("aistack")
    except importlib.metadata.PackageNotFoundError:
        version = "dev"
    return f"AIStack/{version} (sign-in; +https://github.com/bigbrother1969-bis/AIStack)"


class UrllibHttp:
    """The real network, with the standard library — no other HTTP
    client is a dependency of the heritage."""

    def get_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": user_agent()}
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return dict(json.loads(response.read()))

    def post_form(self, url: str, form: dict[str, str], basic_auth: tuple[str, str]) -> dict[str, Any]:
        user, password = (urllib.parse.quote(part, safe="") for part in basic_auth)
        token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(form).encode("ascii"),
            headers={
                "Accept": "application/json",
                "User-Agent": user_agent(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
                return dict(json.loads(response.read()))
        except urllib.error.HTTPError as error:
            # The provider's own error document, when it sent one.
            try:
                return dict(json.loads(error.read()))
            except ValueError:
                return {"error": f"http {error.code}"}


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def pkce_challenge(verifier: str) -> str:
    return _b64url(hashlib.sha256(verifier.encode("ascii")).digest())


@dataclass(frozen=True)
class Identity:
    subject: str
    name: str
    email: str
    groups: tuple[str, ...]
    id_token: str


@dataclass
class OidcClient:
    definition: AuthenticationDefinition
    credentials: Credentials
    http: Http = field(default_factory=UrllibHttp)
    clock: Callable[[], float] = time.monotonic
    _discovery: tuple[float, dict[str, Any]] | None = field(default=None, init=False, repr=False)
    _keys: tuple[float, dict[str, Any]] | None = field(default=None, init=False, repr=False)

    # -- the provider --------------------------------------------------

    def discovery(self) -> dict[str, Any]:
        """The discovery document, whose `issuer` must be the configured
        one exactly; cached for an hour."""

        if self._discovery is not None and self.clock() - self._discovery[0] < CACHE_SECONDS:
            return self._discovery[1]

        try:
            document = self.http.get_json(self.definition.issuer + "/.well-known/openid-configuration")
        except Exception as error:  # noqa: BLE001 — any network failure is the same answer
            raise SignInError("auth.error.provider_unreachable", str(error)) from error

        if document.get("issuer") != self.definition.issuer:
            raise SignInError("auth.error.provider_mismatch", str(document.get("issuer")))

        methods = document.get("code_challenge_methods_supported")
        if methods is not None and "S256" not in methods:
            raise SignInError("auth.error.provider_mismatch", "no S256 PKCE")

        self._discovery = (self.clock(), document)
        return document

    def _signing_keys(self, refresh: bool = False) -> dict[str, Any]:
        if not refresh and self._keys is not None and self.clock() - self._keys[0] < CACHE_SECONDS:
            return self._keys[1]

        try:
            document = self.http.get_json(str(self.discovery()["jwks_uri"]))
        except SignInError:
            raise
        except Exception as error:  # noqa: BLE001
            raise SignInError("auth.error.provider_unreachable", str(error)) from error

        keys: dict[str, Any] = {}
        for entry in document.get("keys", []):
            if entry.get("kty") != "RSA" or entry.get("use", "sig") != "sig":
                continue
            keys[str(entry.get("kid", ""))] = jwt.PyJWK(entry, algorithm=ALGORITHM)

        self._keys = (self.clock(), keys)
        return keys

    # -- the flow ------------------------------------------------------

    def start(self, next_path: str) -> tuple[str, str, Pending]:
        """The authorization URL, the `state` naming this attempt, and
        what must be kept server-side until the callback."""

        endpoint = str(self.discovery()["authorization_endpoint"])
        state = secrets.token_urlsafe(32)
        pending = Pending(
            nonce=secrets.token_urlsafe(32),
            verifier=secrets.token_urlsafe(64),
            next=next_path,
        )
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": self.credentials.client_id,
                "redirect_uri": self.definition.redirect_uri,
                "scope": " ".join(self.definition.scopes),
                "state": state,
                "nonce": pending.nonce,
                "code_challenge": pkce_challenge(pending.verifier),
                "code_challenge_method": "S256",
            }
        )
        return f"{endpoint}?{query}", state, pending

    def finish(self, code: str, issuer_parameter: str | None, pending: Pending) -> Identity:
        """The person the provider vouches for, once every check has
        passed — or `SignInError`."""

        document = self.discovery()

        # RFC 9207: a provider that announces the `iss` response
        # parameter must send it, and it must be this issuer.
        if document.get("authorization_response_iss_parameter_supported") or issuer_parameter:
            if issuer_parameter != self.definition.issuer:
                raise SignInError("auth.error.wrong_issuer", str(issuer_parameter))

        if not code:
            raise SignInError("auth.error.no_code")

        try:
            tokens = self.http.post_form(
                str(document["token_endpoint"]),
                {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.definition.redirect_uri,
                    "code_verifier": pending.verifier,
                },
                (self.credentials.client_id, self.credentials.client_secret),
            )
        except Exception as error:  # noqa: BLE001
            raise SignInError("auth.error.provider_unreachable", str(error)) from error

        id_token = tokens.get("id_token")
        if not isinstance(id_token, str) or not id_token:
            raise SignInError("auth.error.token_refused", str(tokens.get("error", "")))

        claims = self.verify(id_token, pending.nonce)

        groups = claims.get("groups") or ()
        if not isinstance(groups, list | tuple):
            groups = ()

        subject = str(claims["sub"])
        name = str(
            claims.get("name") or claims.get("preferred_username") or claims.get("email") or subject
        )
        return Identity(
            subject=subject,
            name=name,
            email=str(claims.get("email") or ""),
            groups=tuple(str(group) for group in groups),
            id_token=id_token,
        )

    def verify(self, id_token: str, nonce: str) -> dict[str, Any]:
        """The ID token's claims, believed only after its signature,
        issuer, audience, lifetime and nonce have been checked."""

        try:
            header = jwt.get_unverified_header(id_token)
        except jwt.PyJWTError as error:
            raise SignInError("auth.error.invalid_token", str(error)) from error

        if header.get("alg") != ALGORITHM:
            raise SignInError("auth.error.invalid_token", f"algorithm {header.get('alg')!r}")

        kid = str(header.get("kid", ""))
        keys = self._signing_keys()
        if kid not in keys:
            keys = self._signing_keys(refresh=True)
        if kid not in keys:
            raise SignInError("auth.error.invalid_token", f"unknown key {kid!r}")

        try:
            claims: dict[str, Any] = jwt.decode(
                id_token,
                keys[kid],
                algorithms=[ALGORITHM],
                audience=self.credentials.client_id,
                issuer=self.definition.issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as error:
            raise SignInError("auth.error.invalid_token", str(error)) from error

        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise SignInError("auth.error.invalid_token", "nonce")

        return claims

    def logout_url(self, id_token: str) -> str | None:
        """Where to send the browser to end the provider's session too;
        `None` when the provider cannot be reached or names no endpoint."""

        try:
            endpoint = self.discovery().get("end_session_endpoint")
        except SignInError:
            return None

        if not endpoint:
            return None

        query = {
            "client_id": self.credentials.client_id,
            "post_logout_redirect_uri": self.definition.after_logout_uri,
        }
        if id_token:
            query["id_token_hint"] = id_token
        return f"{endpoint}?{urllib.parse.urlencode(query)}"
