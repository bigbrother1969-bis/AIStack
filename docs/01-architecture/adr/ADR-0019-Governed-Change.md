---
artifact:
  id: ADR-0019
  title: Governed Change
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C1
  confidence: Declared
  version: 1.2
  status: Accepted
  owner: Architecture
  created: 2026-10-08
  updated: 2026-10-08

relations:
  references:
    - ADR-0014
    - ADR-0016
    - ADR-0018
    - ARCH-0009
    - ARCH-0013
---

# ADR-0019 — Governed Change

## Status

Accepted, 2026-10-08, by the owner — the day it was proposed, as
`ADR-0016` § 3 allows in the development phase.

## Context

*Measured on 2026-10-08, at commit `83ec1ed`.*

Until now AIStack observes, explains and proposes; it never changes a
service. Images on the reference host change on their own: Watchtower
updates every container that carries its label, at night, with no
record of why, no test before and no way back once the old image is
cleaned up (the sandbox's first rollback rehearsal found both earlier
WordPress images already removed).

1.9 brought what a governed change needs: a restore test in a sandbox
(`ADR-0018`), a rehearsal with another image than the running one, a
comparison with the live service, the registry digests to fetch an image
again. The pieces of the "receiving dock" exist but are not wired: the
transaction contracts and executor (`aistack.transaction`), an operation
registry, and `KernelServices` without the transaction service.

## Decision

Decided by the owner, 2026-10-08.

### 1. The first governed change: a service's image update

A service declared in `dock.yml` is updated only through the dock: a
newer image published for the tag it runs is detected, proposed,
validated, tested, applied — and can be undone.

A governed service no longer carries the Watchtower label: the owner
removes it, and AIStack reports any governed container that still has
it. Only services whose sandbox recipe can rehearse them are declared;
the first one is WordPress (`wp_app`, `wordpress_db`).

### 2. Nothing changes without its why

A proposal carries a written reason, mandatory. It is recorded as the
change's explication, beside the observations it changes, in the Time
Machine.

### 3. Proposed and validated in the application, executed on the host

The web application lists the updates available and records proposals
and validations: administrators only, on the local network only, each
action bound to its session. In production a proposal is validated by
another administrator than the one who wrote it; in the development
phase one may do both (`ADR-0016`).

A validated proposal is executed by **the dock**, an executor on the host
(a systemd unit running as the account AIStack runs as), not by the web
container: the sandbox needs the host's local disk and tools, and the
container exposed to the network keeps the rights it has.

### 4. What must pass before the change

Before the live service is touched, in this order, each step recorded:

1. a sandbox restore of the service's latest backup has succeeded
   within the last 24 hours — run now if none has;
2. the same restore with the **new** image succeeds (rehearsal);
3. the new image is the one validated: fetched by its registry digest,
   never by a tag that could have moved since.

Any failure stops the change; nothing live has been touched.

### 5. The change, and the way back

The service's containers are recreated on the new image with their own
compose project. Then the recipe's checks run against the live service.
If they fail, the previous image — kept by its digest — is put back the
same way and the change is recorded as rolled back.

### 6. One transaction, one trace

A change is one transaction of operations (gates, fetch, apply, check,
rollback), executed by `aistack.transaction`'s executor through engines
registered by operation kind — the transaction service joins
`KernelServices`. Every operation's status, timing and output is kept
with the proposal; the change, its why and its outcome enter the
provenance graph.

## Implementation state

| Part | State |
|---|---|
| § 1 `dock.yml`, update detection, Watchtower label check | done — `aistack.dock` (registry `HEAD` with an anonymous token), page `/dock` |
| § 2 mandatory why, recorded as an explication | done — `aistack.dock.explication`: once executed, per container, under its digest subject (`<project>/<service>`), by its author, `Declared`/`Validated`, outcome in the text |
| § 3 proposals and validations in the application | done — `/dock`, administrators, LAN, two people in production |
| § 3 the dock executor on the host | done — `aistack.dock.executor`, `python -m aistack.cli.dock`, `aistack-dock.timer` (every two minutes, one executor at a time) |
| § 4 gates (sandbox restore, rehearsal, digest) | done — the newest restore with the live images decides; the rehearsal starts `repository@digest` |
| § 5 apply, check, rollback | done — previous image kept as `aistack-dock/<container>:<proposal>`; checks: image, running, health, no restart after 30 s, WordPress database and pages |
| § 6 transaction service in `KernelServices`, provenance trace | done — `TransactionServices` (registry + executor: statuses, stop at the first failure, a listener); the dock registers nine kinds; `project_dock_changes`: one `prov:Activity` per change, its people, images and why |

## Consequences

- The first time AIStack acts on a service. What it may do is bounded:
  only declared services, only an image update, only after validation
  and the gates, always with the way back prepared.
- A governed service updates when someone decides it, not at night on
  its own; an update not proposed waits.
- The dock runs with the account's Docker rights on the host: what it
  executes is only what a validated proposal names.

## Open Points

- The operations run as `aistack.transaction` operations and are
  still kept in the proposal (name, kind, status, start, seconds,
  detail), which the page and the graph read; a transaction is not
  persisted on its own.
- The live checks of a recipe are written for WordPress, the only
  governed service; another recipe gets the generic checks (image,
  running, health, restarts) until its own are written.

- Other change kinds (host packages, declared scripts) come after this
  one has run for real.
