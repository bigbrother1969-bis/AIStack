---
artifact:
  id: ADR-0018
  title: Sandbox Restore
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.3
  status: Accepted
  owner: Architecture
  created: 2026-10-08
  updated: 2026-10-08

relations:
  references:
    - ADR-0016
    - ADR-0017
    - OPS-0006
    - OPS-0010
---

# ADR-0018 — Sandbox Restore

## Status

Accepted, 2026-10-08, by the owner — the day it was proposed, as
`ADR-0016` § 3 allows in the development phase.

## Context

*Measured on 2026-10-08.*

A restore test proves a backup: the declared PRA tests
(`pra_tests.yml`) are real only when someone restored the backup and
looked at the result. On the reference host, four of them have never
been run or are late — `gigabyte`, `wordpress`, `nextcloud`, `immich`.
Each test done by hand so far (arrstack, Raspberry, AIStack itself)
followed the same steps: pick the latest backup, restore it somewhere
that is not the live service, check it, time it, write down the result,
clean up.

The per-engine backup strategies (`backup_strategy.yml`, `OPS-0010`)
already say how each service is backed up. What is missing is the
place to restore into, and the steps run the same way each time.

## Decision

Decided by the owner, 2026-10-08.

### 1. A command first

A sandbox restore is started by a command on the host, run by the
owner. A button in Settings comes later, with the governed path, which
is where actions started from the web belong.

### 2. Isolated: an internal network, no port

Every sandbox runs on its own Docker network created `internal`: no
route to the Internet, no route to the live services, no port
published on the host. Its containers have their own names
(`aistack-sandbox-…`) and a label (`aistack.sandbox`). Checks run from
inside the sandbox network.

A sandbox never writes to a live container, a live volume or a live
database. It reads the live containers only to know which image they
run (by digest) — the restore uses the same image as the live service.

The sandbox gets its own throwaway credentials, generated for the run
and never written to a report. It never reads the live service's
secrets.

### 3. Local disk, removed after the test

Restored files go under one directory on the host's local disk, one
sub-directory per run. Before restoring, the command checks there is
enough free space for the backup unpacked, with a margin; if not, it
stops before writing anything.

At the end — success, failure or interruption — the sandbox's
containers, network and files are removed. Only the report stays.
A cleanup command removes what an interrupted run may have left, found
by its label and directory.

### 4. Each service has a recipe

How to restore one service is declared, not guessed: which backup files
to take, which images, how to load them, what to check. The first
recipe is **WordPress** (database dump + `wp-content` archive).
AIStack itself, Nextcloud and Immich follow, one recipe each.

### 5. What a run produces

A report per run, in `reports/generated/sandbox/`: which backup, which
images, each step and its duration, each check and its result, and the
measured time to recovery (from the start of the restore to the last
check passed).

The report proposes an entry for `pra_tests.yml` (date, result, time to
recovery, why). It does not write it: the entry enters only once the
owner has read the report and copied it.

## Implementation state

| Part | State |
|---|---|
| § 1 command | done — `aistack.sandbox`, `aistack.cli.sandbox`; run on GIGABYTE 2026-10-08 |
| § 2 isolation | done — `aistack.sandbox`, `aistack.cli.sandbox`; run on GIGABYTE 2026-10-08 |
| § 3 local disk, cleanup | done — `aistack.sandbox`, `aistack.cli.sandbox`; run on GIGABYTE 2026-10-08 |
| § 4 WordPress recipe | done — first real run on GIGABYTE 2026-10-08, success, 55.8 s, recorded in `pra_tests.yml` |
| § 4 AIStack recipe | done — first real run on GIGABYTE 2026-10-08, success, 77.8 s, recorded in `pra_tests.yml` |
| § 4 Nextcloud, Immich recipes | to do |
| § 5 report and proposed entry | done — `aistack.sandbox`, `aistack.cli.sandbox`; run on GIGABYTE 2026-10-08 |
| Rollback before an upgrade, by digest | to do |
| Diff between the sandbox and the live service | to do |

## Consequences

- A PRA test becomes something the owner can run in minutes, as often
  as wanted, without touching the live service.
- A backup that cannot be restored shows up as a failed run with the
  step that failed, not as a surprise on the day of a real disaster.
- The host needs free local disk for the size of the largest backup
  restored; the command refuses to start otherwise.

## Open Points

- Where the run directory lives on hosts other than the reference
  host: declared per instance, not decided here.
