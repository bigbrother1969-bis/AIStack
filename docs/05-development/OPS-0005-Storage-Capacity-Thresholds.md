---
artifact:
  id: OPS-0005
  title: Storage Capacity Thresholds
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

# OPS-0005 — Storage Capacity Thresholds

## Purpose

This register declares the disk-capacity thresholds a storage reading is compared
against before a `RuntimeFinding` cites `OPS-0004`'s `deployment misconfiguration`
qualification for a volume running low on space. `STD-0300` § VS-4 criterion 4.5
requires each qualification a finding carries to be traceable to a distinct policy;
this is that policy for storage capacity, the same way `OPS-0004` is the policy for
the vocabulary itself. No threshold here was chosen by AIStack — each is the owner's
own declared value, the same discipline `GOV-P-001` requires.

## Provenance

Declared directly by the owner, 2026-09-11, against `df -h` output taken live from
GIGABYTE and the Raspberry — the same hosts as `OPS-0004`'s second reference incident
(GIGABYTE disk exhaustion). `claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` records the
exchange that produced each value.

## Why two kinds of threshold

An OS volume is small, and a stated percentage can hide how little is actually left:
the Raspberry's root partition, 72% occupied, has only 3.9G free on a 15G card — the
same 72% on GIGABYTE's 212G root leaves 56G. A percentage threshold would need a
different number per volume to mean the same thing; a **free-space** threshold
(absolute, in GB) says it directly. A media volume is the opposite case: large, slow
to fill, predictable growth, plenty of headroom — exactly what makes a **percentage**
threshold, identical across volumes of very different sizes, the natural fit there.

## Declared thresholds

### OS volumes — free-space threshold (GB)

- **GIGABYTE `/` (`/dev/sdc1`, 212G)** — alert below **20 GB free**. At declaration
  time: 73% occupied, 56G free.
- **Raspberry `/` (`/dev/mmcblk0p2`, 15G)** — alert below **2 GB free**. At
  declaration time: 72% occupied, 3.9G free — already close, and the volume the
  reference incident's own reasoning named as already tight.

### Media / storage volumes — percentage threshold

Applies identically to:

- GIGABYTE `/media/Films` (1.8T)
- GIGABYTE `/media/TechData` (1.8T)
- GIGABYTE `/media/Multimedia` (870G)
- GIGABYTE `/media/Documents` (47G)
- GIGABYTE `/media/Comics` (916G)
- GIGABYTE `/media/BD` (1.8T)
- Raspberry `/media/BACKUP` (9.1T)

Alert at **90% occupied**.

### Out of scope for this version

- Raspberry `/boot/firmware` (510M) — left unmonitored; small, changes rarely, and no
  case names a reason to cover it yet (`ARC-P-006`).
- Virtual filesystems (`tmpfs`, `udev`, `/dev/shm`, `/run/*`) and read-only snap
  loopback mounts (`/snap/*`, always at or near 100% by construction) — excluded, not
  real capacity to track.

## What this register does not do

It does not collect a reading. No provider exists yet that reads volume occupancy —
`providers/filesystem/` holds only `media_library.py`. This register says what a
reading would be compared against once one exists; `PLAN-J7` tracks writing the
provider and the correlation function that would cite `OPS-0004`'s `deployment
misconfiguration` against these thresholds.

It does not cover growth-rate ("remplissage sauvage") detection — only a static
threshold. The owner's original need named both; `PLAN-J7` §9 scoped the first
version to the threshold alone, deferring rate-of-fill detection to a later pass.

## Related Artifacts

- `OPS-0004` — Sustainability Qualifications, § *What each qualification means*
  (`deployment misconfiguration`), § *Second reference incident*
- `claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` — the health cockpit this register
  supports
