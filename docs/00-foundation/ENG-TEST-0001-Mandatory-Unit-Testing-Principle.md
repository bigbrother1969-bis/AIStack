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
  version: 1.3
  updated: 2026-09-23
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

## Principle

Every AIStack software component, contract, engine, service, and
architectural layer shall include unit tests.

## Scope

The obligation binds what the governed test suite covers: the `aistack`
package under `src/`, and everything `pytest` imports in the environment
`ENG-TEST-0002` declares.

**A host-touching screen is outside that scope.** It is an application at
the repository root that serves HTTP (`fastapi`, `uvicorn`, `jinja2`,
`python-multipart`) and acts on a real host. Its web dependencies are kept
out of the governed environment on purpose, so the suite cannot import it.
It is verified by live execution against the host it serves, under
`ENG-TEST-0002` § *Host-touching UI screens*. Decided 2026-08-29 by the
owner (decision #9) and stated here on 2026-09-23, `GOV-0002/OS-069`.
Four screens fall under it on 2026-09-23: `selection_ui`, `priority_ui`,
`network_discovery_ui` and `troubleshooting_assistant_ui`.

What such a screen imports from `aistack` stays under this principle,
because the suite covers it. Logic written in the screen itself does not.

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
