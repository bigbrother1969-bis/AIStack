---
artifact:
  id: ADR-0013
  title: Web Authentication
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Proposed
  owner: Architecture
  created: 2026-10-03
  updated: 2026-10-03

relations:
  references:
    - ADR-0012
    - GOV-0002
---

# ADR-0013 — Web Authentication

## Status

Proposed, 2026-10-03.

The decisions below were taken by the owner on 2026-10-03, at the start
of 1.7's second tranche, and are recorded here the same day; under the
rule adopted on 2026-08-21, this record is accepted the day after.

## Context

*Measured on 2026-10-03, from GIGABYTE, at commit `bf87515`.*

`ADR-0012` made AIStack one web application on two listeners — the
public port 8183, behind Nginx Proxy Manager and Cloudflare at
`https://aistack.persiaut-family.fr`, and the LAN port 8186 — and left
login, sessions and CSRF to tranche 2. The identity provider is the
owner's Pocket ID, `https://id.persiaut-family.fr` (declared by the
owner the same day). From GIGABYTE, `getent hosts` resolves it to two
Cloudflare IPv6 addresses, and its discovery document
(`/.well-known/openid-configuration`) states:

| Field | Value |
|---|---|
| `issuer` | `https://id.persiaut-family.fr` |
| `authorization_endpoint` | `https://id.persiaut-family.fr/authorize` |
| `token_endpoint` | `https://id.persiaut-family.fr/api/oidc/token` |
| `end_session_endpoint` | `https://id.persiaut-family.fr/api/oidc/end-session` |
| `jwks_uri` | `https://id.persiaut-family.fr/.well-known/jwks.json` (HTTP 200) |
| `id_token_signing_alg_values_supported` | `RS256` |
| `code_challenge_methods_supported` | `plain`, `S256` |
| `authorization_response_iss_parameter_supported` | `true` |
| `scopes_supported` | `openid`, `profile`, `email`, `groups` |
| `claims_supported` | includes `sub`, `name`, `email`, `preferred_username`, `groups` |

Nothing in the repository authenticates anyone yet.

## Decision

### 1. Tranche 2 authenticates; it refuses nothing

Decided by the owner, 2026-10-03: a visitor can sign in and out on the
public address, and every page shows who is signed in; **no page is
refused to an anonymous visitor in this tranche**. Refusals come with
profiles and rights in tranche 3. The LAN listener is unchanged.

### 2. OpenID Connect, Authorization Code with PKCE, a confidential client

- `GET /login` redirects to Pocket ID with `response_type=code`, the
  scopes `openid profile email groups`, a `state`, a `nonce` and a PKCE
  challenge (`S256` only — `plain` is never sent). The three secrets of
  the attempt are kept server-side, for ten minutes, keyed by `state`.
- `GET /auth/callback` refuses an unknown or expired `state`, an `iss`
  parameter other than the configured issuer (RFC 9207, which Pocket ID
  announces), then exchanges the code at the token endpoint with the
  PKCE verifier and the client secret.
- **The ID token is verified by its signature** against the provider's
  published keys (`PyJWT` with `cryptography`, decided 2026-10-02):
  `RS256` only, `iss` equal to the configured issuer, `aud` equal to the
  client ID, `exp`/`iat` with a minute of leeway, and `nonce` equal to
  the one sent. Nothing from the token response is trusted before that,
  and the userinfo endpoint is not used.
- The redirect URI is fixed, built from the public address in the
  configuration — `https://aistack.persiaut-family.fr/auth/callback` —
  never from a request header.
- The discovery document is read from the configured issuer and its
  `issuer` must equal it exactly; it and the keys are cached for an hour,
  and an unknown signing key forces one refresh.
- `POST /logout` ends the local session and sends the browser to the
  provider's `end_session_endpoint` with the ID token as hint.

The client ID and secret live in `.env.web`
(`AISTACK_OIDC_CLIENT_ID`, `AISTACK_OIDC_CLIENT_SECRET`); the issuer,
the public address and the session lifetimes are declared in
`aistack/authentication/definitions/authentication.yml`. Without a client ID and
secret, `/login` says, in the reader's language, that sign-in is not
configured — the application still serves every page.

### 3. Sessions on the server, on disk

Decided by the owner, 2026-10-03:

- the browser holds an opaque, random identifier (32 bytes) in the
  cookie `aistack_session` — `HttpOnly`, `SameSite=Lax`, `Path=/`, and
  `Secure` when the request arrived on the public port (served over
  HTTPS by the proxy); never `Secure` on the plain-HTTP LAN port, where
  it would not be sent back;
- the session lives in SQLite, `<generated_dir>/web/sessions.sqlite3`,
  keyed by the SHA-256 of the identifier — a copy of the file gives no
  usable cookie. It survives a restart, and deleting its row revokes it;
- a session ends after **8 hours without a request** or **7 days** in
  all, whichever comes first; expired rows are deleted when met;
- a new identifier is issued at every sign-in, never reused.

The public and LAN addresses are different origins, so a session opened
on one is not seen on the other.

### 4. Profiles come from Pocket ID's groups

Decided by the owner, 2026-10-03: tranche 3 reads the profile from the
ID token's `groups` claim (a Pocket ID group such as `aistack-admins`).
Tranche 2 already requests the `groups` scope and stores the groups with
the session; it decides nothing from them.

### 5. A local fallback administrator, on the LAN only

Decided by the owner, 2026-10-03: one local account, for when Pocket ID
or Cloudflare is down.

- Its form, `GET`/`POST /login/local`, is served **on the LAN port
  only**; it never exists on the public address.
- The password is stored only as an `scrypt` hash (`hashlib.scrypt`,
  `n=2**15, r=8, p=1`, 16-byte salt) in `.env.web`
  (`AISTACK_WEB_ADMIN_SCRYPT`), produced by
  `python -m aistack.cli.web_admin_password`; compared in constant time.
- Five failures within fifteen minutes refuse every attempt until the
  window has passed.
- Its session says it was opened locally (`method = local`); what that
  allows is tranche 3's.

### 6. CSRF

Every state-changing route of tranche 2 (`POST /logout`,
`POST /login/local`) requires a token bound to the session or to the
sign-in form, checked in constant time. The existing `POST` routes of
the LAN screens are protected the same way when tranche 3 gives a
session the right to call them.

### 7. Where the signed-in person is shown

The shared navigation (`aistack.renderers.nav.render_page_nav`) carries
a marker; the web layer fills it on every page it serves — generated
pages included — with the person's name and a sign-out button, or a
sign-in link.

## Consequences

- `PyJWT[crypto]` joins `pyproject.toml`'s `dependencies`; both governed
  environments install it before the code is applied.
- The owner creates the AIStack client in Pocket ID (callback
  `https://aistack.persiaut-family.fr/auth/callback`, logout callback
  `https://aistack.persiaut-family.fr/console.html`) and writes its ID
  and secret into `.env.web` on GIGABYTE.
- Every test of sign-in runs against a fake provider whose keys the test
  generates, so the suite never reaches Pocket ID.

## Open Points

- Profiles and rights, and refusing what a profile may not do, are
  tranche 3's.
- Lifting `R1` — serving the LAN screens on the public address, behind
  sign-in — is the owner's separate decision, after tranche 3.
