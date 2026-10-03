---
artifact:
  id: ADR-0012
  title: Single Web Application
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.2
  status: Proposed
  owner: Architecture
  created: 2026-10-02
  updated: 2026-10-03

relations:
  references:
    - ADR-0010
    - ADR-0011
    - ENG-TEST-0001
    - ENG-TEST-0002
    - GOV-0002
---

# ADR-0012 — Single Web Application

## Status

Proposed, 2026-10-02.

The decisions below were taken by the owner on 2026-10-02, at the framing
of 1.7, and are recorded here the same day. Under the rule adopted on
2026-08-21 (an act binding the heritage is proposed one day and accepted
the next), what awaits acceptance is this record, not the decisions.

## Context

*Measured on 2026-10-02, at commit `3f2f4b6`.*

AIStack serves six web processes on GIGABYTE, each with its own systemd
unit, run as `big-brother`:

| Process | Port | Server | Scope | Environment |
|---|---|---|---|---|
| console (`aistack.console.server`) | 8183 | standard library | public (Nginx Proxy Manager, `aistack.persiaut-family.fr`) | governed `.venv` |
| `selection_ui` | 8181 | FastAPI/uvicorn | LAN | `.venv-selection-ui` |
| `priority_ui` | 8182 | FastAPI/uvicorn | LAN | `.venv-priority-ui` |
| `network_discovery_ui` | 8184 | FastAPI/uvicorn | LAN | `.venv-network-discovery-ui` |
| `troubleshooting_assistant_ui` | 8185 | FastAPI/uvicorn | LAN | `.venv-troubleshooting-assistant-ui` |
| `timemachine_ui` | 8186 | FastAPI/uvicorn | LAN | `.venv-timemachine-ui` |

Ports from `aistack/instance/definitions/instance_config.yml`; scope from
each card's `scope` in `console_links.yml`. A screen is LAN-only **because
no Proxy Host in Nginx Proxy Manager points at its port** — nothing in
the code refuses a request.

The five screens live at the repository root, 3246 lines of `app.py` in
all, and none is imported by the governed suite: decision #9 (2026-08-29)
kept their web dependencies out of `.venv`. `timemachine_ui/app.py` alone
carries 27 private helpers. Decision #9 was revoked for tests on
2026-10-02 (`GOV-0002/OS-084`, `ENG-TEST-0001` v1.4) because 1.7 puts
login, sessions and admin/user rights behind these screens.

`aistack.conformance.inventory` imports every module of the `aistack`
package (`importlib.import_module` over `pkgutil.walk_packages`). Any
module placed under `src/aistack/` that imports a web framework therefore
needs that framework wherever the inventory runs — the governed `.venv`
on both hosts and the published image, whose `Dockerfile` installs
`pyproject.toml`'s `dependencies` and nothing else.

## Decision

### 1. One application, under `src/aistack/web`

The console and the five screens become **one FastAPI application**,
built by a factory (`aistack.web.app.create_app`) that receives its
configuration as arguments — generated directory, languages, instance
configuration, and the host-touching collaborators each screen needs —
so the suite can build it with fakes.

Each screen is an `APIRouter` mounted under its own prefix:

| Screen | Prefix |
|---|---|
| console, Architecture, Health, Settings | `/` (unchanged paths: `/console.html`, `/architecture.html`, `/health.html`, `/settings`) |
| `selection_ui` | `/selection` |
| `priority_ui` | `/priority` |
| `network_discovery_ui` | `/network-discovery` |
| `troubleshooting_assistant_ui` | `/troubleshooting` |
| `timemachine_ui` | `/timemachine` |

The console keeps its paths so the Nginx Proxy Manager entry and existing
bookmarks need no change. A screen's templates stop writing absolute
paths (`href="/node"`) and build them from the router's prefix.

Decided against keeping six processes sharing a signed session cookie
behind the proxy: one address and one session is what the roadmap asks of
1.7, and six processes would each have to verify the same session.

### 2. The web layer's dependencies are the heritage's own

`fastapi`, `uvicorn`, `jinja2` and `python-multipart` join `PyYAML` and
`pyoxigraph` in `pyproject.toml`'s `dependencies` — not an optional
extra, because the inventory imports `aistack.web` wherever it runs, the
published image included, and the owner's requirement of 2026-09-27 is
that the image be self-sufficient once pulled. An HTTP client, needed
only by the test client, joins the `dev` extra — `httpx2` (revised
2026-10-03: Starlette 1.7 deprecates its test client's use of `httpx`).
Every `<screen>/requirements.txt`,
`scripts/setup_<screen>_env.sh`, `run_<screen>.sh`, `.venv-<screen>/` and
`.env.<screen>` pattern is removed when its screen has moved.

### 3. One process, two listeners, until login exists

Moving the five LAN screens onto the public port would publish them
before 1.7's login exists — the exposure roadmap `R1` forbids. Decided by
the owner, 2026-10-02:

- **one process and one systemd unit** (`aistack-web.service`) serve the
  application on **two ports**;
- **8183, the public port**, answers only the console pages, Settings and
  — from tranche 2 — the login routes; any other path is a 404 there;
- **the LAN port**, never a Proxy Host, answers everything. It is
  `instance_config.yml`'s `service_ports.web_lan`: **8186** — 8187
  while `timemachine_ui` still held 8186, moved on 2026-10-03 by the
  patch that brought the Time Machine into the application, so that
  bookmark keeps answering;
- the refusal is decided by **the port the request arrived on**
  (`request.scope["server"]`), never by a header the proxy sets or a
  client could forge;
- exposure is declared **once per router**, as a dependency
  (`PUBLIC` or `LAN_ONLY`, `aistack.web.exposure`); `include`, the only
  way the factory adds routes, refuses a router that declares none or
  two, and a test asks every registered route, with every method it
  accepts, on an undeclared port and on the public port, proving the
  guard runs. A refused route answers exactly like a missing one.

The LAN listener is removed only when the owner lifts `R1`, after
tranche 2. Decided against filtering on the `Host` header (a protection
that depends on how the proxy forwards it) and against path rules in Nginx
Proxy Manager (a protection outside this repository, invisible to the
suite).

### 4. Every route is tested, in process

The suite exercises every route through FastAPI's test client — no
socket, no host. A route is a thin adapter: it parses the request, calls
a function under `src/aistack/` that the suite already tests on its own,
and renders a template. What a screen's `app.py` still computes moves into
the package it belongs to (`aistack.timemachine`,
`aistack.troubleshooting`, …) with its tests, before or with its route.
Host-touching collaborators (Docker, Syncthing, the AI Runtime, writes
under `reports/generated/`) reach a route by FastAPI dependency
injection, so a test replaces them; a route never builds one itself.

### 5. Migration, one screen at a time

Tranche 1 of 1.7 moves the console first, then `network_discovery_ui`,
`priority_ui`, `selection_ui`, `troubleshooting_assistant_ui` and
`timemachine_ui`, one patch each. Each patch removes its screen's
directory at the repository root, its launcher, setup script and
requirements file, and its own systemd unit file from `deploy/systemd/`;
the owner stops and disables the running unit on GIGABYTE when applying
it. `instance_config.yml`'s `service_ports` and the console's links
follow each move. `GOV-0002/OS-084` closes with the last one.

## Consequences

- Six systemd units and six ports become one unit and two ports. The
  owner's bookmarks to `GIGABYTE:8181`, `:8182`, `:8184` and `:8185`
  stop answering; `GIGABYTE:8186` keeps answering, with the Time Machine
  under `/timemachine` instead of `/`.
- The governed `.venv` on both hosts must install the four web packages
  and `httpx2` before the first patch of tranche 1 is applied, or the
  suite cannot import `aistack.web`.
- The published image grows by the web packages it now declares.
- The console loses its standard-library server: `ADR-0010` § 5 described
  it as such, and is revised when the console moves.
- A screen added after this record is a router in `aistack.web`, with a
  declared scope and its tests, from its first patch.

## Open Points

- **Login, sessions and CSRF** belong to tranche 2 and are recorded then:
  OIDC Authorization Code with PKCE against Pocket ID, ID tokens verified
  by signature against the provider's published keys (`PyJWT` with
  `cryptography`, decided 2026-10-02), the local fallback admin
  (`hashlib.scrypt`), and protection of every `POST` route once a session
  can authorise it.
- **Pocket ID's address and transport** (HTTPS or not) are not measured
  yet; tranche 2 cannot start without them.
