---
artifact:
  id: OPS-0006
  title: Backup Freshness Thresholds
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Operations
  created: 2026-09-11
  updated: 2026-09-11

relations:
  references:
    - OPS-0004
---

# OPS-0006 — Backup Freshness Thresholds

## Purpose

This register declares the backup-existence and backup-age thresholds a
`BackupReading` is compared against before a `RuntimeFinding` cites
`OPS-0004`'s `technical debt` and `deployment misconfiguration`
qualifications for a backup location that is missing its file entirely, or
whose newest file is older than declared. `STD-0300` § VS-4 criterion 4.5
requires each qualification a finding carries to be traceable to a distinct
policy; this is that policy for backup freshness, the same way `OPS-0005`
is the policy for storage capacity. No threshold here was chosen by
AIStack — it is the owner's own declared value, the same discipline
`GOV-P-001` requires.

## Provenance

Declared directly by the owner, 2026-09-11, in answer to what `PLAN-J7`'s
fourth domain (Sauvegarde/PRA) needed a threshold for. Unlike `OPS-0005`,
which was declared against live `df -h` output describing volumes already
mounted, this register's own case is a stated requirement rather than an
observed incident — see `OPS-0004` § *Fourth reference case* for that
distinction, recorded there rather than smoothed over.
`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` records the exchange that
produced each value.

## Why one kind of threshold

`OPS-0005` declares two kinds — free bytes and percent occupied — because
storage capacity has two different questions worth asking depending on the
volume. A backup location asks only one question: is there a file, and how
old is it. There is no second kind here, and `BackupThreshold` carries no
`kind` field the way `StorageThreshold` does.

## Declared thresholds

### GIGABYTE — WordPress backup

- **Path**: `/media/BACKUP/persiaut-consulting/wordpress/`, written by
  `/srv/scripts/backup-wordpress.sh`.
- **Threshold**: alert if no backup file is found at all, or if the newest
  one found is older than **7 jours** (7 days = 168 hours).

This is the only backup location declared so far — the one mechanism
already running and already observable, the owner's own choice for the v1
scope of this domain (`OPS-0004` § *Fourth reference case*).

### Out of scope for this version

- **Periodic restore tests** — demonstrating that a backup can actually be
  restored, not merely that a file exists. Named directly in the owner's
  own stated requirement, and explicitly deferred: "effectuer des tests à
  intervalles réguliers qui démontrent que les systèmes de backup
  fonctionnent" is not checked by this register or by anything reading it.
- **Documentation currency** — verifying that backup/restore procedures
  exist and are kept up to date. Also named directly in the owner's stated
  requirement, and also explicitly deferred: "démontrer que les procédures
  existent et sont à jour" is not checked here.
- **Any backup location other than the WordPress backup on GIGABYTE** —
  the homelab's other backup mechanisms (Déjà Dup/duplicity for laptop
  backups, for instance) are not declared in this register; adding one
  happens when the owner names a real case for it, per `ARC-P-006`, not by
  extrapolating from this one.

Both scope reductions are a named absence this register records
(`FDN-0003` Article 12), not a silent one — mirroring `OPS-0005`'s own
"out of scope for this version" section, and revisited later against a
real case rather than built speculatively now.

## What this register does not do

It does not itself detect a restore failure, a corrupted archive, or a
backup that runs but writes nothing useful — only whether a file exists at
the declared path and how recently its newest entry was modified.
`BackupProvider.collect_freshness` (`src/aistack/providers/filesystem/backup.py`)
is the provider that reads this; `aistack.runtime.backup_gap
.find_backup_gaps` is the correlation that compares a reading against this
register's declared thresholds; `aistack.runtime.evaluate_backup` is what
cites `OPS-0004` against a confirmed gap.

## Related Artifacts

- `OPS-0004` — Sustainability Qualifications, § *What each qualification
  means* (`technical debt`, `deployment misconfiguration`), § *Fourth
  reference case*
- `OPS-0005` — Storage Capacity Thresholds, the sibling register this one
  mirrors in shape
- `claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` — the health cockpit this
  register supports
