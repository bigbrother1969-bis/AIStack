---
artifact:
  id: ADR-0020
  title: Host Traceability
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-10-08
  updated: 2026-10-08

relations:
  references:
    - ADR-0011
    - ADR-0016
    - ADR-0019
---

# ADR-0020 — Host Traceability

## Status

Accepted, 2026-10-08, by the owner — the day it was proposed, as
`ADR-0016` § 3 allows in the development phase.

## Context

*Measured on 2026-10-08, on both hosts.*

The Time Machine keeps what changes in the containers (`ADR-0011`, 1.5:
events, files, image digests, packages) and, since 1.10, the governed
changes of the dock (`ADR-0019`). What changes on the hosts themselves
is kept nowhere: a package upgraded by apt, a script edited in
`/usr/local/sbin`, a timer enabled, a line added to a crontab, a
compose file or an `.env` edited. Yet that is where most incidents of a
homelab begin.

Both hosts run Debian (LMDE 7 on GIGABYTE, Raspberry Pi OS / Debian 13
on the Raspberry), Python 3.13, and keep about eight months of
`dpkg.log` and `apt/history.log` (rotated monthly). `/etc` holds about
2 000 files (16 MB) on GIGABYTE and 960 (6.6 MB) on the Raspberry. The
Raspberry has no copy of AIStack; its disk `/media/BACKUP` is exported
over NFS to GIGABYTE, mounted there at the same path; the accounts that
own AIStack's files on both sides have uid 1000.

## Decision

Decided by the owner, 2026-10-08.

### 1. Observed on GIGABYTE and the Raspberry

Both hosts are traced. Others come once the mechanism has run.

### 2. A collector of its own on each host, run by systemd as root

One file, `aistack/host_collector.py`, written for the Python standard
library only, so the same file runs on a host with no copy of AIStack:
installed as `/usr/local/sbin/aistack-host-collector`, started by
`aistack-host-collector.timer` every 15 minutes. It runs as root because
part of what it watches only root can read (`/etc/shadow`,
`/etc/sudoers.d`, `/var/spool/cron/crontabs`) — read-only: the unit
mounts the whole system read-only but its output and its key
(`ProtectSystem=strict`), and gives it no network
(`PrivateNetwork=yes`).

### 3. What it records

- **Packages** — every install, upgrade, removal and purge from
  `dpkg.log`, every apt run from `apt/history.log` (its command line,
  who asked), dated by the logs themselves; at the first run, every
  rotation still on disk.
- **Files** — a change to a file of `/etc` (whole), of
  `/usr/local/bin` and `/usr/local/sbin`, of the user crontabs, of the
  compose files and `.env` files of the projects under `/srv` and
  `/opt`, and of any path the host's declaration adds: added, removed,
  modified (size, mode, owner, fingerprint). The first run records a
  baseline, not one event per existing file.
- **Units** — a systemd service, timer, socket or path unit enabled,
  disabled or masked.

### 4. Never the content

A file is known by a keyed fingerprint (HMAC-SHA-256), never by its
content: the key is drawn once per host, kept beside the collector,
readable by root only. A short secret in an `.env` file therefore cannot
be found again by trying values against its fingerprint. What the
Time Machine shows is that a file changed, when, and whether it went
back to an earlier fingerprint — never what it says.

### 5. Where the records go

Each host writes to its own directory, `hosts/<host>/`, owned by the
account AIStack runs as: under AIStack's data directory on GIGABYTE,
under `/media/BACKUP/AIStack/hosts/raspberry` on the Raspberry — the
disk GIGABYTE already mounts at the same path. AIStack only reads them.
A Raspberry not mounted is a gap in the record, said as such, not an
empty history.

### 6. Observation only

Nothing on a host changes through AIStack in this version: the dock
(`ADR-0019`) stays limited to image updates until it has governed a
real one; host packages may follow it.

### 7. Into the Time Machine

The records are read by AIStack into the history and projected into the
provenance graph like the container streams: per host, per kind,
dated by the event.

## Implementation state

| Part | State |
|---|---|
| § 2–5 the collector, its units, its key, its output | done — `aistack/host_collector.py` (standard library only), `deploy/host-collector/` (service, timer, configuration example) |
| § 7 reading the records, the graph, the Time Machine | to do |

## Consequences

- AIStack runs a process as root on each host for the first time:
  read-only, offline, its scope written in its unit file.
- The history of a host starts eight months back, from its own logs.
- A file's content never leaves the host; its fingerprint does, and
  is useless without the host's key.

## Open Points

- Files that change on their own (`/etc/adjtime`, generated caches)
  are ignored by a list the host's declaration can extend; the first
  weeks of records will say which others to add.
