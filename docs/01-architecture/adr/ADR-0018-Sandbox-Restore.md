---
artifact:
  id: ADR-0018
  title: Sandbox Restore
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.10
  status: Accepted
  owner: Architecture
  created: 2026-10-08
  updated: 2026-10-09

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
database. It reads the live containers to know which image they run
(by digest) — the restore uses the same image as the live service —
and, when a comparison is asked (§ 7), to count rows and files.

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

### 6. Going back to the image before an upgrade

Decided by the owner, 2026-10-08. A rollback is rehearsed before it is
done: the latest backup restored in the sandbox with the image the
service ran before its last upgrade — the newest digest the digest
collector recorded that differs from the running one — and checked
like any restore. The command then prints the line to pin in the
service's compose file (`image: <repository>@sha256:…`) and the command
to apply it. Going back for real stays the owner's act.

An earlier image no longer on the host is fetched again by its registry
digest, which the digest collector looks up once per image since 1.9 and
remembers beside the history (`registry-digests.json`, the history
itself untouched) — the images running today included, so their next
upgrade can be rehearsed. An image that was already gone before has
none: the rehearsal says it cannot be fetched and goes on with the
other containers of the recipe (GIGABYTE, 2026-10-08: WordPress's
previous MariaDB image had been removed). A pulled image stays on the host: it is the one the
real rollback needs.

### 7. Comparing the sandbox with the live service

Decided by the owner, 2026-10-08. On demand (`--compare`), before the
sandbox is removed, the restored backup is set next to the live service
as numbers: rows per table, files and bytes per first-level folder,
biggest gaps first, tables found on one side only. No verdict and no
check: a backup taken last night is always a little behind, the report
shows by how much and the owner judges. It never changes the measured
time to recovery.

The live side is read only: files are walked on the host; a database is
asked `SELECT COUNT(*)` from inside its own live container, with that
container's own environment — its password stays there, never on a
command line AIStack builds, never in a report. A part that cannot be
compared is said so; the others still are.

### 8. Scheduled, and recorded by AIStack

Added 2026-10-09 (2.0; the owner: "tests PRA planifiés", and, asked
whether a successful scheduled test proposes its entry or records it,
"enregistrée seule"). Every week a timer on the host runs § 1 for each
service with a recipe not tested in the last six days. Its outcome —
success with the measured recovery time, or failure with its reason —
is recorded by AIStack in the data directory (`pra/scheduled.jsonl`,
appended), not in `pra_tests.yml`: the owner's file, comments
included, is never rewritten. The Tests PRA domain keeps, per service,
the more recent of the two. A test run by hand (§ 5) still only
proposes its entry. A scheduled test waits for the dock executor's
lock (`ADR-0019`) and holds it while it runs.

## Implementation state

| Part | State |
|---|---|
| § 1 command | done — `aistack.sandbox`, `aistack.cli.sandbox`; run on GIGABYTE 2026-10-08 |
| § 2 isolation | done — `aistack.sandbox`, `aistack.cli.sandbox`; run on GIGABYTE 2026-10-08 |
| § 3 local disk, cleanup | done — `aistack.sandbox`, `aistack.cli.sandbox`; run on GIGABYTE 2026-10-08 |
| § 4 WordPress recipe | done — first real run on GIGABYTE 2026-10-08, success, 55.8 s, recorded in `pra_tests.yml` |
| § 4 AIStack recipe | done — first real run on GIGABYTE 2026-10-08, success, 77.8 s, recorded in `pra_tests.yml` |
| § 4 Nextcloud, Immich recipes | done — first real runs on GIGABYTE 2026-10-08, success (84.8 s, 262.8 s), recorded in `pra_tests.yml` |
| § 5 report and proposed entry | done — `aistack.sandbox`, `aistack.cli.sandbox`; run on GIGABYTE 2026-10-08 |
| Rollback before an upgrade, by digest | done — `python -m aistack.cli.sandbox rollback <service>`: rehearsal in the sandbox with the earlier image, pin printed; first real run 2026-10-08: the earlier MariaDB image was gone, said so |
| § 8 scheduled tests | done — `aistack.pra.scheduled`, `python -m aistack.cli.pra_schedule`, `run_pra_schedule.sh`, `deploy/systemd/aistack-pra.{service,timer}` (Sunday 05:00) |
| Diff between the sandbox and the live service | done — `restore <service> --compare` (§ 7); first real run by the owner to come |

## Consequences

- A PRA test becomes something the owner can run in minutes, as often
  as wanted, without touching the live service.
- A backup that cannot be restored shows up as a failed run with the
  step that failed, not as a surprise on the day of a real disaster.
- The host needs free local disk for the size of the largest backup
  restored; the command refuses to start otherwise.

## Open Points

- Measured 2026-10-08 while writing the Nextcloud and Immich recipes:
  Nextcloud's files and Immich's uploads live on the backup disk
  itself (`/media/BACKUP`, the Raspberry's NFS share) and no backup
  copies them. `backup_strategy.yml` states it (`nextcloud-files`,
  `immich-uploads`, no engine); the recipes restore the databases,
  check the files that are really backed up (Immich's external
  library, from Deja Dup) and say what is not. The owner, the same
  day: no disk is available for a copy of this size; the risk is known,
  kept and to be fixed later — the two uncovered-state findings stay
  on the Health page until then.

- Where the run directory lives on hosts other than the reference
  host: declared per instance, not decided here.
