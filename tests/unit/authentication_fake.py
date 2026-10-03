"""
A fake Pocket ID for the suite (`ADR-0013` § Consequences): the same
discovery document as the real one measured on 2026-10-03, a signing key
the test generates, and a token endpoint that checks what the real one
checks — the code, the PKCE verifier, the client's credentials — then
signs an ID token.
"""

from __future__ import annotations

import json
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from aistack.authentication.definition import AuthenticationDefinition, Credentials
from aistack.authentication.oidc import pkce_challenge

ISSUER = "https://id.persiaut-family.fr"
CLIENT_ID = "aistack-client"
CLIENT_SECRET = "s3cret"

DEFINITION = AuthenticationDefinition(
    issuer=ISSUER,
    public_base_url="https://aistack.persiaut-family.fr",
    scopes=("openid", "profile", "email", "groups"),
    client_id_env="AISTACK_OIDC_CLIENT_ID",
    client_secret_env="AISTACK_OIDC_CLIENT_SECRET",
    local_admin_env="AISTACK_WEB_ADMIN_SCRYPT",
    admin_group="aistack_admins",
    session_idle_hours=8,
    session_absolute_days=7,
)
CREDENTIALS = Credentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, local_admin_hash="")

DISCOVERY = {
    "issuer": ISSUER,
    "authorization_endpoint": f"{ISSUER}/authorize",
    "token_endpoint": f"{ISSUER}/api/oidc/token",
    "end_session_endpoint": f"{ISSUER}/api/oidc/end-session",
    "jwks_uri": f"{ISSUER}/.well-known/jwks.json",
    "id_token_signing_alg_values_supported": ["RS256"],
    "code_challenge_methods_supported": ["plain", "S256"],
    "authorization_response_iss_parameter_supported": True,
}

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwk(private_key: Any = _KEY, kid: str = "k1") -> dict[str, Any]:
    entry = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    entry.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return dict(entry)


def sign(claims: dict[str, Any], private_key: Any = _KEY, kid: str = "k1", alg: str = "RS256") -> str:
    return jwt.encode(claims, private_key, algorithm=alg, headers={"kid": kid})


def claims_for(nonce: str, **overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "user-123",
        "name": "Fabrice Persiaut",
        "email": "fabrice@example.org",
        "groups": ["aistack_admins"],
        "iat": now,
        "exp": now + 300,
        "nonce": nonce,
    }
    claims.update(overrides)
    return claims


@dataclass
class FakeProvider:
    """Answers like Pocket ID; `token_claims` shapes every ID token."""

    discovery: dict[str, Any] = field(default_factory=lambda: dict(DISCOVERY))
    keys: list[dict[str, Any]] = field(default_factory=lambda: [jwk()])
    # What the test overrides in every ID token this provider signs.
    token_claims: dict[str, Any] = field(default_factory=dict)
    issued_claims: dict[str, Any] = field(default_factory=dict)
    signer: Any = _KEY
    kid: str = "k1"
    issued_code: str = "the-code"
    challenge: str = ""
    redirect_uri: str = ""
    requests: list[str] = field(default_factory=list)
    down: bool = False

    def get_json(self, url: str) -> dict[str, Any]:
        self.requests.append(url)
        if self.down:
            raise OSError("network unreachable")
        if url == f"{ISSUER}/.well-known/openid-configuration":
            return self.discovery
        if url == DISCOVERY["jwks_uri"]:
            return {"keys": self.keys}
        raise AssertionError(f"unexpected GET {url}")

    def post_form(self, url: str, form: dict[str, str], basic_auth: tuple[str, str]) -> dict[str, Any]:
        self.requests.append(url)
        assert url == DISCOVERY["token_endpoint"]
        if basic_auth != (CLIENT_ID, CLIENT_SECRET):
            return {"error": "invalid_client"}
        if form.get("code") != self.issued_code or form.get("grant_type") != "authorization_code":
            return {"error": "invalid_grant"}
        if pkce_challenge(form.get("code_verifier", "")) != self.challenge:
            return {"error": "invalid_grant"}
        # The code is exchanged with the redirect URI it was issued for.
        if form.get("redirect_uri") != self.redirect_uri:
            return {"error": "invalid_grant"}
        return {"id_token": sign(self.issued_claims, self.signer, self.kid), "token_type": "Bearer"}

    def authorize(self, url: str) -> dict[str, str]:
        """What a browser carries to Pocket ID; remembers the challenge."""

        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        self.challenge = query["code_challenge"]
        self.redirect_uri = query["redirect_uri"]
        self.issued_claims = {**claims_for(query["nonce"]), **self.token_claims}
        return query
