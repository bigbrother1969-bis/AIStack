---
artifact:
  id: ADR-0034
  title: Managing User Profiles
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
    - ADR-0013
    - ADR-0014
---

# ADR-0034 — Managing User Profiles

## Status

Proposed, 2026-11-28, by the owner.

## Context

*Measured on 2026-11-28, at commit `238e0e5`, against
`src/aistack/web/authentication.py` and `ADR-0014`.*

Today a profile is computed fresh on every request, never stored:
`profile_of(session, admin_group)` returns `admin` if `session.method
== LOCAL` (the local fallback account) or `admin_group in
session.groups`, `user` otherwise. `admin_group` is read from
`authentication.yml` (currently `aistack_admins`, a Pocket ID group).
No table of accounts or profiles exists anywhere in AIStack.

The owner wants AIStack to manage **roles only** for identities Pocket
ID already holds — never to create, disable or otherwise touch a
Pocket ID identity itself (cadrage
`CADRAGE-2026-11-28-gestion-profils-utilisateurs.md`):

- an admin can assign a profile to a Pocket ID identifier (an email)
  **before** that person's first sign-in;
- on conflict, the individual assignment wins over `admin_group`
  membership — the most recent, most specific decision prevails;
- revoking access cuts the live AIStack session **immediately**, not
  only a future sign-in; the Pocket ID account itself stays valid
  elsewhere;
- every profile change is logged — who assigned what, when, in the
  same spirit as the existing sign-in journal;
- the screen is an extension of the existing Settings page, admin-only.

Sessions already live in `generated_dir/web/sessions.sqlite3`
(`SessionStore`, a versioned schema, ADR-0014 § 6); `ADMIN_ACTION`
(`require_admin_action`) already gates an admin action behind a
session plus its CSRF token, with `/settings/sessions/close` as the
existing precedent for an admin action that closes a session.

## Decision

### 1. A list of known accounts, not a new identity store

A new store records every Pocket ID identifier AIStack has an opinion
about — its profile, and either a pre-assignment date or the date of
its first sign-in. This is distinct from the existing sign-in journal,
which records only sign-ins that actually happened: a pre-assigned
identifier that has never signed in still belongs in this store.

### 2. Priority order at resolution

`profile_of` (or its caller, `current_profile`) is extended to consult
this store first. Resolution order, most specific first:

1. an individual assignment in the new store;
2. `admin_group` membership (today's mechanism, unchanged);
3. the local fallback account (`session.method == LOCAL`, unchanged).

An identifier with no individual assignment falls through to the
existing group/fallback behaviour exactly as today.

### 3. Immediate session invalidation on revocation

A revocation invalidates or removes the live session row for that
account in `sessions.sqlite3`, not merely the new store's entry — the
same database `SessionStore` already uses, so the session in progress
ends at revocation rather than at its next natural expiry.

### 4. A profile-change log

Every assignment and revocation is recorded — who, what, when — in the
same spirit as the existing sign-in journal, as its own log rather
than folded into it (a pre-assignment with no sign-in has nothing to
attach to in the sign-in journal).

### 5. Screen and routing: later lots

The admin-only screen (list of known and pre-assigned accounts, change
profile, pre-assign, revoke, view the change log) and the
profile-based default landing screen at sign-in are separate lots
(GP2, GP3) — GP3 depends on the simplified console screen
(`PROPOSITION-2026-11-28-console-nuls-decoupage.md`, CN1) existing
first.

## Consequences

- A new persisted store joins `sessions.sqlite3`'s governed schema
  discipline; its own schema versioning follows the same precedent
  (ADR-0014 § 6).
- `profile_of`/`current_profile` gain a lookup against this store,
  evaluated before the existing `admin_group`/`LOCAL` checks — the
  existing checks are not removed, only deferred.
- A new admin action (assign, pre-assign, revoke) joins
  `/settings/sessions/close` behind `ADMIN_ACTION`, so it is gated by a
  session plus CSRF like every other admin action already is.
- Revocation now touches two stores in one action (the new store and
  `sessions.sqlite3`), not one.

## Open Points

None — ready for GP1.
