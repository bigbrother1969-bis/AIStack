---
artifact:
  criticality: C3
  domain: Foundation
  id: ENG-TEST-0001
  owner: Engineering
  semantic_type: Principle
  status: Published
  title: Mandatory Unit Testing Principle
  type: Foundation Principle
  confidence: Declared
  created: 2026-07-24
  version: 1.5
  updated: 2026-10-03
---

# Mandatory Unit Testing Principle

## Status

`status` moves from `Draft` to `Published`, `GOV-0002/OS-050`,
2026-09-04. This is a C3 principle, created 2026-07-24 and unchanged in
substance since, already enforced across the governed suite — 936 tests
passing, `ENG-TEST-0002` § *Engineering Rule* holding every result to it.
Nothing about the principle's content changes with this entry.

v1.3, 2026-09-23, `GOV-0002/OS-069`: § *Scope* added. The principle is
unchanged for everything the governed suite covers; the section states what
it covers, and the one exception the owner decided on 2026-08-29.

v1.4, 2026-10-02, `GOV-0002/OS-084`: the exception is **revoked** by the
owner, ahead of 1.7 (roadmap `R5`). § *Scope* states the revocation, the
date it takes effect, and the five screens it brings into the suite.

v1.5, 2026-10-03, `GOV-0002/OS-084`: the dated paragraph of § *Scope* is
discharged — the five screens are in the suite; the section says by what.

## Principle

Every AIStack software component, contract, engine, service, and
architectural layer shall include unit tests.

## Scope

The obligation binds what the governed test suite covers: the `aistack`
package under `src/`, and everything `pytest` imports in the environment
`ENG-TEST-0002` declares.

**A host-touching screen was outside that scope from 2026-08-29 to
2026-10-02.** It is an application at the repository root that serves
HTTP (`fastapi`, `uvicorn`, `jinja2`, `python-multipart`) and acts on a
real host. Its web dependencies were kept out of the governed environment
on purpose, so the suite could not import it, and it was verified by live
execution against the host it serves. Decided 2026-08-29 by the owner
(decision #9), stated here on 2026-09-23, `GOV-0002/OS-069`. Measured
2026-10-02, five screens fell under it, not the four this section named:
`selection_ui`, `priority_ui`, `network_discovery_ui`,
`troubleshooting_assistant_ui` and `timemachine_ui` (added 2026-09-27,
never listed here) — 3246 lines of `app.py`, none of it imported by the
suite.

**Decision #9 is revoked for tests, 2026-10-02, by the owner**
(`GOV-0002/OS-084`, roadmap `R5`). The 1.7 version brings login, sessions
and admin/user rights: code that decides who may act on a host cannot be
verified by hand. From 1.7's first tranche onwards:

- the web layer's dependencies are declared in `pyproject.toml` and
  installed into the governed environment (`ENG-TEST-0002`);
- the console and the five screens become **one application** under
  `src/aistack/`, and every route is exercised by the suite through an
  in-process test client — no socket, no host;
- the logic a screen still holds in its own `app.py` moves into `src/`
  with its tests; a route stays a thin adapter.

**Discharged 2026-10-03.** The five screens no longer exist at the
repository root: each is a router of the single web application
`aistack.web` (`ADR-0012`), its logic in the package it belongs to —
`aistack.network_discovery`, `aistack.priority`, `aistack.selection`,
`aistack.troubleshooting`, `aistack.timemachine` — and every route is
exercised by `tests/unit/web/`, on both listeners. No `<screen>/
requirements.txt` or `scripts/setup_<screen>_env.sh` remains;
`GOV-0002/OS-084` is resolved. No screen is verified only by live
execution any more.

What a screen imports from `aistack` stays under this principle, because
the suite covers it.

A feature, refactoring, or new capability cannot be considered complete
without automated verification of its expected behavior.

## Rationale

Unit tests are not only code validation tools.

They are executable documentation of software contracts.

They ensure that:

-   architectural intentions remain valid;
-   contracts are preserved over time;
-   regressions are detected early;
-   refactoring remains safe;
-   knowledge embedded in software remains reproducible.

## Engineering Rule

Any new implementation must be delivered with its corresponding unit
tests.

Any modification of an existing component must update or extend its
tests when the behavior or contract changes.

## Criticality

C3 --- Core Engineering Principle

AIStack must never consider untested software as a completed engineering
artifact.
