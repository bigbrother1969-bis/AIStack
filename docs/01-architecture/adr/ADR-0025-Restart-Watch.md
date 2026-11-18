---
artifact:
  id: ADR-0025
  title: Restart Watch
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Accepted
  owner: Architecture
  created: 2026-11-15
  updated: 2026-11-18

relations:
  references:
    - ADR-0009
    - ADR-0012
    - ADR-0017
    - ADR-0021
---

# ADR-0025 — Restart Watch

## Status

Accepted, 2026-11-15, by the owner, the day of the proposal
(`ADR-0016` § 3). Decided with the owner the same day, after a cold boot of the reference host left four
containers stuck.

## Context

*Measured on the reference host (MSI), 2026-11-15, after a cold boot.*

Seventy-four containers came back; five of them were running and
useless, and nothing in Docker said so except Kuma's red probes:

- **Scrutiny** and **Firefly**: s6-supervised images that hung at init
  (`s6-rc: fatal: timed out`, no web server). Scrutiny declares no
  healthcheck; Firefly's has a 300 s start period, after which it said
  `unhealthy`.
- **qBittorrent** and **Mularr**: `network_mode: container:<gluetun id>`.
  gluetun restarted after them, so they held a network namespace that no
  longer existed — running, healthy-looking, reaching nothing.

None had exited, so the restart policy did nothing. Each was brought back
by hand with `docker restart`, gluetun's dependents after gluetun. The
maintenance page (`scripts/maintenance_page.sh`) already restarts what
was running before it stopped Docker, but only for its own stop; a boot
is not covered. `ADR-0009 § 6` already says an undeclared healthcheck is
not a verdict, and `aistack.runtime.restart_loop` /
`container_distress` already read *state* and *health* — neither acts.

## Decision

Decided by the owner, 2026-11-15.

### 1. It acts, with guardrails

The watch restarts the containers it finds stuck; it does not only
report. The guardrails are the decision: a window, a confirmation, a
limit per hour, an order, and a stop at the first failure (§ 3–§ 5).

### 2. Three signs of "stuck"

Only a **running** container is judged (a stopped one is the owner's
wish or the restart policy's business).

1. its healthcheck says `unhealthy` (Docker says it only after the start
   period, so a container still starting is never named);
2. it shares another container's network and that provider was started
   *more than two seconds after it* — a stale namespace;
3. it declares no healthcheck, the owner declared a **probe** for it in
   `restart_watch.yml` (an HTTP address asked from the host's network),
   and the probe got no answer (any HTTP answer under 500 counts as
   alive: the probe asks whether the program answers, never whether it
   is right).

Nothing is guessed for a container without a healthcheck and without a
declared probe: it is not judged.

### 3. The order is read from Docker, the owner states exceptions

A provider is restarted before whoever depends on it: from
`network_mode: container:…`, from the Compose `depends_on` label, from
`after:` in the declaration. Restarting a network provider also restarts
every running container sharing its network (their namespace is replaced
by the restart). Ties break by name; a loop in the declared order is
noted and ordered by name. Containers are restarted one at a time, each
only once the previous one answers (healthy, or its probe replies, or —
with neither — running for ten seconds); the plan stops at the first
that does not come back within `wait_seconds`.

### 4. When: the window after a start

The watch acts for `window_minutes` (30) after **its own start**. It is
a service with `restart: unless-stopped`, so it starts with Docker, at a
boot or when the daemon restarts; a deployment of the watch itself opens
the window too (accepted: bounded by § 5). Outside the window it only
writes down, once per container and episode, what it sees stuck.
`--ignore-window` lets the owner act on a host that has been up for a
while.

### 5. Limits

A container must be seen stuck `confirm_cycles` (2) polls in a row
(30 s apart). At most `max_attempts_per_hour` (2) attempts per container
per hour, kept across restarts of the watch. The watch never restarts
itself, nor a container listed under `never`.

### 6. What is recorded, and who is told

Every decision is a line of `restart-watch.jsonl` (restarted, failed,
planned, outside the window, refused by the limit, order loop), trimmed
to its newest 500; the state of the last pass is
`restart-watch-state.json`. The console's card *Relance au démarrage*
(LAN only, reading only) shows the window, who is stuck now, what is
declared, and the journal. A container that does not come back is sent
to Gotify (the vigil's address and token), urgent. A successful restart
is not notified.

A plain journal rather than the Observation History of
`resource_priority`: a decision here is an event, not a state to compare,
and the screen reads the newest lines.

## Consequences

- One more service (`restart-watch`, container `aistack-restart-watch`),
  declared in `service_categorization.yml`, and a systemd unit for a git
  installation.
- The declaration `restart_watch.yml` ships neutral: no exception, no
  probe. A container like Scrutiny, which declares no healthcheck, is
  covered only once the owner declares its probe.
- Out of scope: a container that exits (the restart policy), a restart
  loop (`restart_loop`), a container that is healthy and wrong.
- `docker restart` is the only action; the watch never recreates,
  removes or updates anything.

## Implementation state

Measured 2026-11-18, in `main`: `aistack.restart_watch` (`detect`, `order`, `act`,
`guard`, `journal`, `load`), the command `aistack.cli.restart_watch`, the
service `restart-watch` of `docker-compose.yml`, the systemd unit
`deploy/systemd/aistack-restart-watch.service`, the declaration
`restart_watch.yml` (neutral: no exception, no probe), and
`tests/unit/restart_watch/`.

| Step | State |
|---|---|
| § 1 It acts, with guardrails | done — 2026-11-18 |
| § 2 Three signs of "stuck" (`unhealthy`, stale network namespace, declared probe) | done — 2026-11-18 |
| § 3 The order is read from Docker, the owner states exceptions (`after:`, `never:`) | done — 2026-11-18 |
| § 4 When: the window after a start (30 minutes, `--ignore-window`) | done — 2026-11-18 |
| § 5 Limits (two polls in a row, two attempts per hour, never itself) | done — 2026-11-18 |
| § 6 What is recorded and who is told (journal trimmed to 500 lines, the console card *Relance au démarrage*, Gotify urgent on failure) | done — 2026-11-18 |

**What a real run has shown.** On 2026-11-16, on throwaway containers on the
reference host: detection, order, restart and wait for the return, for
`unhealthy` and for a stale network. **Not tried for real**: a declared probe
(Scrutiny), the window after a real cold boot, and the Gotify message when a
restart fails. *Done* above says the code does what the decision asks, not that
every path has met the host.

## Open points

- The window opens at the watch's start, not at the boot itself; a
  measure on a second boot would say whether Docker's own start time
  should replace it.
- Containers that depend on one another only through the application
  (no `depends_on`, no shared network) need an `after:` line.
