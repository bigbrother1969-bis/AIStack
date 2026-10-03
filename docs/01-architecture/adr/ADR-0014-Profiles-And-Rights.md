---
artifact:
  id: ADR-0014
  title: Profiles and Rights
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
    - ADR-0013
---

# ADR-0014 — Profiles and Rights

## Status

Proposed, 2026-10-03. The decisions below were taken by the owner on
2026-10-03, at the start of 1.7's third tranche; under the rule adopted
on 2026-08-21, this record is accepted the day after.

## Context

*Measured on 2026-10-03, at commit `de19351`.*

Tranche 2 (`ADR-0013`) signs people in and refuses nothing. Signing in
with Pocket ID was verified for real on the public address the same
evening; the group the owner created in Pocket ID for administrators is
displayed `aistack-admins` and **named `aistack_admins`** — the name the
`groups` claim carries, and the one this record uses.

The application answers 39 routes. Nine are `POST`, and seven of those
change something on the host — SSH user names, CPU priorities, the music
selection, a troubleshooting run and its fix — all on the LAN port, open
to anyone who reaches it. Every page is readable without signing in.
On the LAN port the only way to sign in is the fallback administrator:
Pocket ID's session belongs to the public address.

The Health cockpit's "Diagnostiquer" buttons are forms that post from
the cockpit's page to the LAN port — another site: the browser sends no
session with them, and they could carry no token the LAN port issued.

## Decision

### 1. Two profiles, from the session

Decided by the owner, 2026-10-03:

| Profile | Who | May |
|---|---|---|
| **admin** | a Pocket ID session whose `groups` holds `aistack_admins`, or the fallback administrator | read everything, and act — every state-changing route |
| **user** | any other Pocket ID session | read everything; act on nothing |
| *anonymous* | no session | the console, Help, Legal notice, Licence, Settings' language, signing in |

The administrators' group is declared in `authentication.yml`
(`admin_group`), not written in code. The profile is computed from the
session at each request, never stored: removing someone from the group
in Pocket ID takes effect at their next sign-in.

### 2. What is refused, and how

- A page that needs a session (Architecture, the Health cockpit, every
  LAN screen), asked without one: a `303` to `/login?next=<the page>`.
- An action asked without the admin profile: `403`, with a page saying
  so in the reader's language. An action asked without a session: the
  same `303` to sign in.
- The rule is the same on both listeners; the port still decides only
  where a route answers (`ADR-0012` § 3).
- Every route declares what it needs — `ANYONE`, `SIGNED_IN` or `ADMIN`
  — next to its exposure; a test asks every route, anonymously and as a
  user, and checks the answer.

### 3. Every action carries the session's CSRF token

Every state-changing route requires the session's token in a `csrf`
form field, compared in constant time. Forms do not hand-write it: a
marker inside each form is filled with the token by the same middleware
that shows who is signed in (`ADR-0013` § 7).

The cockpit's "Diagnostiquer" buttons become **links** to the
Troubleshooting screen, where starting a diagnosis is a protected
action of that screen's own page.

### 4. Pocket ID on the LAN too

Decided by the owner, 2026-10-03: signing in on the LAN port uses
Pocket ID as on the public address. The redirect URI is the one of the
listener the sign-in started on — `https://aistack.persiaut-family.fr/
auth/callback` or `http://GIGABYTE:8186/auth/callback`, the second built
from `instance_config.yml`'s `lan_hostname` and `web_lan` — kept with
the pending attempt, so the callback exchanges the code with the same
one. Both, and both after-logout addresses, are declared in Pocket ID.
The fallback administrator stays, for when Pocket ID cannot be reached.

### 5. The public address, signed out

Decided by the owner, 2026-10-03: the console, Help, Legal notice and
Licence stay public; Architecture and the Health cockpit, which describe
the infrastructure, need a session. The console's summary of the
cockpit keeps its counts; the detail is behind the link.

### 6. Settings

Decided by the owner, 2026-10-03:

- **My profile**, for everyone signed in: name, e-mail, profile, groups,
  how and on which listener the session was opened, when it ends.
- **Open sessions**, for an administrator: who, how, which listener,
  since when, last seen — and closing any of them.
- **Sign-in journal**, for an administrator: sign-ins, refusals,
  sign-outs and fallback failures, newest first; kept 30 days.

Both lists are read from the sessions database (`ADR-0013` § 3), whose
schema is versioned; a database of an earlier version is rebuilt empty,
which signs everyone out once.

## Consequences

- The owner adds `http://GIGABYTE:8186/auth/callback` and
  `http://GIGABYTE:8186/console.html` to the AIStack client in Pocket ID.
- Reading a LAN screen needs a session from this tranche on.
- `ADR-0013` § 4 named the group `aistack-admins`; it is `aistack_admins`.

## Open Points

- Lifting `R1` — the LAN screens on the public address, behind these
  rights — stays the owner's separate decision.
