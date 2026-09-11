---
artifact:
  id: OPS-0004
  title: Sustainability Qualifications
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.2
  status: Draft
  owner: Operations
  created: 2026-09-04
  updated: 2026-09-11

relations:
  references:
    - STD-0300
    - FDN-0012
    - FDN-0002
---

# OPS-0004 — Sustainability Qualifications

## Purpose

This register declares what each of VS-4's four qualifications — technical
debt, deployment misconfiguration, energy inefficiency, sustainability
anomaly — means, in the owner's own words, so a runtime finding can cite
one or more of them instead of inventing a severity label. `STD-0300` §
VS-4 criterion 4.5 requires each qualification a finding carries to be
traceable to a distinct policy; this is that policy for the vocabulary as
a whole.

## Provenance

Every definition below is the owner's own statement, given directly,
2026-09-04, in answer to a question asking why the reference incident
(`aistack-selection-ui`'s permanent `--reload`, documented in `STD-0300` §
VS-4) deserved each qualification. `GOV-P-001` governs this register the
same way it governs `OPS-0001` and `OPS-0003`: the owner states the
knowledge, the system records what was said, and invents nothing beyond
it.

## The vocabulary is closed

Four qualifications, and no more may be added without the owner naming a
fifth: technical debt, deployment misconfiguration, energy inefficiency,
sustainability anomaly. A finding does not need to carry all four —
`STD-0300` § VS-4 criterion 4.5 was reworded on 2026-09-04 for exactly
this reason: the reference incident, examined against all four, was
found by the owner to carry three of them, not four (below). What makes
a finding derived knowledge rather than an opinion about severity is that
whichever qualifications it does carry are each cited to this register —
not that a fixed count of them is always reached.

## What each qualification means

- **Technical debt** — applies while the issue is known and pending
  correction; it is a standing entry on a backlog of fixes still to make.
  The qualification is not permanent: once the correction lands, the
  label no longer applies going forward — the record of it having
  applied stays in history (a validation suite entry, a commit, a
  document), but nothing continues to hold the corrected system as
  carrying that debt today.
- **Energy inefficiency** — resource (CPU, in the reference incident)
  consumed for no functional benefit — no work is being done that the
  consumption produces.
- **Sustainability anomaly** — excessive resource consumption with a
  physical consequence: heat generated, and a risk to the hardware
  components running it. Distinct from energy inefficiency, which is
  about the waste itself; this is about what the waste does to the
  machine.
- **Deployment misconfiguration** — named 2026-09-11, by the second
  reference incident below, filling the slot this entry left open since
  2026-09-04: a service deployed without the operational safeguards its
  own kind of workload requires — no log rotation, no size cap declared
  anywhere — such that ordinary operation degrades the host over time.
  Distinct from energy inefficiency and sustainability anomaly, which are
  about resource consumed *while running*; this one is about what was
  missing when the thing was set up.

## First reference incident — `aistack-selection-ui`'s `--reload`, qualified

Examined against the vocabulary above, 2026-09-04, the owner found
`aistack-selection-ui`'s permanent `--reload` (`STD-0300` § VS-4's
reference incident) to carry:

- **technical debt** — yes, while it was outstanding on the corrections
  backlog; not anymore, since it was fixed;
- **energy inefficiency** — yes, 48–58 % of one CPU core consumed for no
  functional benefit;
- **sustainability anomaly** — yes, excessive CPU consumption, excessive
  heat, a risk to the hardware;
- **deployment misconfiguration** — no, not pertinent to this case.

Three qualifications, one explicitly excluded by the owner rather than
left unconsidered — the exclusion is itself the fact this register
records, not a gap.

## Second reference incident — GIGABYTE disk exhaustion, 2026-09-11, qualified

A second case, given directly by the owner 2026-09-11 in answer to what J7
(`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`, the health cockpit) needed a
storage domain for: on GIGABYTE, a service producing logs with no rotation
and no size cap filled the host's disk — *"des logs en folie qui ont
rempli le disque / je n'avais plus de place disponible"*.

- **deployment misconfiguration** — yes: this is the case the first
  incident's entry above left the definition open for. No rotation, no
  cap, declared nowhere — the gap is in how the service was set up, not
  in one bad run.

**Draft, pending the owner's own examination of the other three
qualifications against this case** — the same four-way review the first
incident received above, not yet carried out for this one.

One qualification named for the first time by a real case —
`deployment misconfiguration` is no longer an open slot.

## What this register does not do

**Updated 2026-09-11** — the paragraph below described the state as of
2026-09-04, when it was still true of all four qualifications. It no
longer is: `0.6.0` (`claude/PLAN-J5-EVALUATE-QUALIFIED-FINDING-2026-09-11.md`)
wired two of the four. Kept, corrected in place, so the record shows what
changed rather than reading as if it had always been current.

As of `0.6.0`, `energy inefficiency` and `sustainability anomaly` are wired
into a runtime finding: `aistack.runtime.evaluate` correlates
`UnexplainedConsumption` against `TemperatureReading` into a
`RuntimeFinding` citing one or both. `RuntimeFinding` now carries a
`qualifications` field (`src/aistack/contracts/runtime_finding.py`)
enforcing this register's closed vocabulary — the gap this section
originally named for those two is closed.

`technical debt` and `deployment misconfiguration` are not wired yet —
one still undefined in practice, the other defined above (2026-09-11) but
with no provider yet to feed it:

- **technical debt** — needs a backlog register this heritage does not
  have yet, something a corrected issue can be removed from. Not built:
  the owner declined to build one ahead of a real pending correction to
  seed it with, 2026-09-04.
- **deployment misconfiguration** — needs a storage-capacity provider;
  none exists yet. `providers/filesystem/` holds only `media_library.py`
  (the music-sync selection feature) — nothing that reads disk usage.
  Named by a real case (above, 2026-09-11) before the provider that would
  detect it is written — the case comes first, per `ARC-P-006`; the code
  comes after (`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`).

It no longer says it does not define "deployment misconfiguration" — the
second reference incident above names it, the same way `frigate`'s
`intermittent` lifecycle got recorded in `OPS-0003`: stated once, by the
owner, about a real case, not guessed at in general.
