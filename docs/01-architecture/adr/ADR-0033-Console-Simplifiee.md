---
artifact:
  id: ADR-0033
  title: Simplified Console for the Non-Admin User
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Proposed
  owner: Architecture
  created: 2026-11-28
  updated: 2026-11-28

relations:
  references:
    - ADR-0012
    - ADR-0014
---

# ADR-0033 — Simplified Console for the Non-Admin User

## Status

Proposed, 2026-11-28, by the owner.

## Context

*Measured on 2026-11-28.*

AIStack's console (`aistack.web.console`, ADR-0012 § 1) answers on the
public port and reads like a systems console: architecture, health,
settings, a link to every screen. A non-admin member of the household
wants four things only — is it secure, are backups done, is there disk
space, is everything up to date — and nothing else (cadrage
`CADRAGE-2026-11-27-console-simplifiee-utilisateur-lambda.md`).

Every screen since 1.7 is a router of one FastAPI application
(`aistack.web.app.create_app`), each declaring exactly one exposure,
`PUBLIC` or `LAN_ONLY` (`aistack.web.exposure`, ADR-0012 § 1, § 3). A
screen added after ADR-0012 is a router in `aistack.web`, with its
declared scope and its own tests, from its first patch — this is that
screen.

## Decision

### 1. A new router, not a new process

The simplified console is `aistack.web.simple_console`, a router
mounted at its own prefix (`aistack.web.simple_console.PREFIX`,
`/simple`), included by `create_app` alongside the others. No new port,
no new systemd unit, no new `.venv` — the mini-app-per-port family
(`selection_ui`, `priority_ui`, …) that ADR-0012 folded into this
application is not revived.

### 2. Exposure: PUBLIC

Declared `PUBLIC` (`aistack.web.exposure.PUBLIC`), like the console: a
household member checking in from outside the LAN must reach it on the
public port, the one the console itself answers on.

### 3. A session is required

Declared `SIGNED_IN_ONLY` (`aistack.web.authentication.SIGNED_IN_ONLY`)
alongside `PUBLIC`, like Architecture and the Health cockpit
(`ADR-0014` § 5), not like the bare console: this screen shows the
same kind of infrastructure status those two gate behind a session —
security, backups, disk, updates — so it is gated the same way.
Confirmed against `tests/unit/web/test_rights.py`'s `ANYONE` allowlist
(the small, explicit set of pages that answer with no session): this
screen does not belong in it.

### 4. First lot: skeleton only

This lot (CN0,
`PROPOSITION-2026-11-28-console-nuls-decoupage.md`) adds this record,
the router and a minimal template — no maquette, no real data, no AI
button. CN1 brings the maquette (variant C, fixed values); CN2 wires
the four real sources; CN3 the admin-gated link to the full console.

## Consequences

- A fifth exposure-declared router joins the application; no change to
  `ADR-0012`'s two listeners.
- `tests/unit/web/test_every_route_declares_its_exposure.py` picks up
  the new router automatically — no route of this screen may be added
  without declaring `PUBLIC`.
- Signed out, `/simple` redirects to sign in, like `/architecture.html`
  and `/health.html` (`ADR-0014` § 2) — `tests/unit/web/test_rights.py`
  asks it of every route not in `ANYONE`.

## Open Points

None — ready for CN1.
