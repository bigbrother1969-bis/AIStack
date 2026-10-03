"""
`aistack.authentication.oidc` — every check the ID token must pass
(`ADR-0013` § 2), against a fake provider whose keys the test generates.
"""

from __future__ import annotations

import time
import urllib.parse

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from aistack.authentication.oidc import OidcClient, SignInError, pkce_challenge
from tests.unit.authentication_fake import (
    CLIENT_ID,
    CREDENTIALS,
    DEFINITION,
    ISSUER,
    FakeProvider,
    claims_for,
    jwk,
    sign,
)


def client(provider: FakeProvider) -> OidcClient:
    return OidcClient(DEFINITION, CREDENTIALS, provider)


def started(provider: FakeProvider, **claims):
    oidc = client(provider)
    url, state, pending = oidc.start("/health.html")
    provider.token_claims = claims
    provider.authorize(url)
    return oidc, url, state, pending


def test_the_authorization_request_carries_pkce_s256_state_nonce_and_the_fixed_redirect():
    provider = FakeProvider()
    url, state, pending = client(provider).start("/x")
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))

    assert url.startswith(f"{ISSUER}/authorize?")
    assert query["response_type"] == "code"
    assert query["client_id"] == CLIENT_ID
    assert query["redirect_uri"] == "https://aistack.persiaut-family.fr/auth/callback"
    assert query["scope"] == "openid profile email groups"
    assert query["state"] == state and query["nonce"] == pending.nonce
    assert query["code_challenge_method"] == "S256"
    assert query["code_challenge"] == pkce_challenge(pending.verifier)
    assert pending.verifier not in url


def test_a_good_sign_in_gives_the_person_and_their_groups():
    provider = FakeProvider()
    oidc, _, _, pending = started(provider)

    identity = oidc.finish("the-code", ISSUER, pending)

    assert identity.subject == "user-123"
    assert identity.name == "Fabrice Persiaut"
    assert identity.groups == ("aistack_admins",)


@pytest.mark.parametrize(
    ("claims", "case"),
    [
        ({"iss": "https://evil.example"}, "another issuer"),
        ({"aud": "another-client"}, "another audience"),
        ({"exp": int(time.time()) - 3600, "iat": int(time.time()) - 7200}, "expired"),
        ({"nonce": "replayed"}, "another nonce"),
    ],
)
def test_a_token_failing_a_check_is_refused(claims, case):
    provider = FakeProvider()
    oidc, _, _, pending = started(provider, **claims)

    with pytest.raises(SignInError) as refused:
        oidc.finish("the-code", ISSUER, pending)
    assert refused.value.reason == "auth.error.invalid_token", case


def test_a_token_signed_by_another_key_is_refused():
    provider = FakeProvider()
    oidc, _, _, pending = started(provider)
    provider.signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(SignInError, match="invalid_token"):
        oidc.finish("the-code", ISSUER, pending)


def test_a_token_with_another_algorithm_is_refused_before_any_key_is_looked_up():
    oidc = client(FakeProvider())
    token = sign(claims_for("n"), private_key="shared-secret-x" * 3, alg="HS256")

    with pytest.raises(SignInError, match="algorithm"):
        oidc.verify(token, "n")


def test_a_rotated_key_is_fetched_once_more_then_trusted():
    provider = FakeProvider()
    oidc, _, _, pending = started(provider)
    oidc._signing_keys()  # cached with k1 only
    new = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    provider.keys = [jwk(), jwk(new, "k2")]
    provider.signer, provider.kid = new, "k2"

    assert oidc.finish("the-code", ISSUER, pending).subject == "user-123"


def test_the_iss_response_parameter_must_name_the_issuer():
    provider = FakeProvider()
    oidc, _, _, pending = started(provider)

    for wrong in (None, "https://evil.example"):
        with pytest.raises(SignInError, match="wrong_issuer"):
            oidc.finish("the-code", wrong, pending)


def test_a_wrong_pkce_verifier_or_code_gets_no_token():
    provider = FakeProvider()
    oidc, _, _, pending = started(provider)

    with pytest.raises(SignInError, match="token_refused"):
        oidc.finish("another-code", ISSUER, pending)

    tampered = type(pending)(nonce=pending.nonce, verifier="x" * 64, next=pending.next)
    with pytest.raises(SignInError, match="token_refused"):
        oidc.finish("the-code", ISSUER, tampered)


def test_a_provider_naming_another_issuer_is_refused():
    provider = FakeProvider()
    provider.discovery["issuer"] = "https://evil.example"

    with pytest.raises(SignInError, match="provider_mismatch"):
        client(provider).start("/")


def test_an_unreachable_provider_is_said_so():
    provider = FakeProvider(down=True)

    with pytest.raises(SignInError, match="provider_unreachable"):
        client(provider).start("/")


def test_the_discovery_document_is_cached_for_an_hour():
    provider = FakeProvider()
    now = [0.0]
    oidc = OidcClient(DEFINITION, CREDENTIALS, provider, clock=lambda: now[0])

    oidc.start("/")
    oidc.start("/")
    now[0] = 3600.0
    oidc.start("/")

    assert provider.requests.count(f"{ISSUER}/.well-known/openid-configuration") == 2


def test_logout_goes_to_the_end_session_endpoint_with_the_hint():
    url = client(FakeProvider()).logout_url("the-id-token")
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url or "").query))

    assert url and url.startswith(f"{ISSUER}/api/oidc/end-session?")
    assert query["id_token_hint"] == "the-id-token"
    assert query["post_logout_redirect_uri"] == "https://aistack.persiaut-family.fr/console.html"


def test_every_refusal_reason_is_written_in_every_language():
    """`SignInError.reason` is shown through `t(...)` by key, so the
    catalog test cannot see it: every literal reason is checked here."""

    import re
    from pathlib import Path

    from aistack.authentication import oidc
    from aistack.i18n import load_catalogs, load_languages_yaml

    reasons = set(re.findall(r'"(auth\.error\.[a-z_]+)"', Path(oidc.__file__).read_text(encoding="utf-8")))
    catalogs = load_catalogs(load_languages_yaml())

    assert reasons
    for language, catalog in catalogs.items():
        assert reasons <= set(catalog), (language, reasons - set(catalog))


def test_the_real_client_names_itself_never_as_python_urllib(monkeypatch):
    """Cloudflare refuses `Python-urllib/3.x` as a robot (2026-10-03)."""

    import io
    import json as json_module
    import urllib.request

    from aistack.authentication.oidc import UrllibHttp

    sent = []

    def fake_urlopen(request, timeout):
        sent.append(request)
        return io.BytesIO(json_module.dumps({"ok": True}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    http = UrllibHttp()

    http.get_json("https://id.example/doc")
    http.post_form("https://id.example/token", {"a": "b"}, ("id", "secret"))

    for request in sent:
        agent = request.get_header("User-agent")
        assert agent.startswith("AIStack/") and "urllib" not in agent.lower()
