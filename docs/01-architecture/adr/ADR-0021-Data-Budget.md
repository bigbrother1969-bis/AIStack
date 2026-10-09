---
artifact:
  id: ADR-0021
  title: Data Budget
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-10-09
  updated: 2026-10-09

relations:
  references:
    - ADR-0011
    - ADR-0016
    - ADR-0020
---

# ADR-0021 — Data Budget

## Status

Accepted, 2026-10-09, by the owner — the day it was proposed, as
`ADR-0016` § 3 allows in the development phase. It implements what
`ADR-0011` § 11 reserved as a principle: a disk budget declared per
host before the history grows unbounded, and a compaction that never
destroys a source.

## Context

*Measured on GIGABYTE, 2026-10-09.*

AIStack's data directory held 571 MB in 15 716 files: `docker-diff`
221 MB, `history` 179 MB, the graph (`timemachine`) 88 MB,
`docker-events` 64 MB, everything else under 5 MB each (the host
records: 1.1 MB). Over the last week, 12 to 23 MB were written a day
(61 MB on 2026-10-02, the history's import; 131 MB on 2026-10-08, the
day of the sandbox restores and the host baselines): 5 to 8 GB a year.
The data shares GIGABYTE's system disk (212 GB, 76 % used, 49 GB free)
with more than fifty containers — the disk that once reached 100 %.
Nothing bounded that growth.

## Decision

Decided by the owner, 2026-10-09.

### 1. A budget of 2 GB, declared

`data_budget.yml` (`./config`, shipped in
`aistack/data_budget/definitions/`): `budget_mb: 2048`,
`warn_percent: 80`. What the data directory takes is measured — every
file added up — never estimated; the pace is what was written over the
last seven days.

### 2. A health domain, "Données d'AIStack"

Past 80 % of the budget, a finding says how much is used, the share of
the budget, and in how many days the budget is reached at the recent
pace; past the budget, a finding of its own, which the vigil sends as
urgent. Weighted 10, as *Stockage*. Qualified sustainability anomaly
(`OPS-0004`).

### 3. Observations older than 90 days are compressed, in place

In `history`, `docker-diff` and `docker-events`, every observation file
under a `history/<stem>/` directory older than `compress_after_days: 90`
(by the instant in its name) becomes `<name>.gz` beside it. The
compressed copy is read back and compared byte for byte before the plain
file is removed; an interrupted run is finished by the next one.
`aistack.history` reads `.gz` and plain files alike, so the Time Machine
rebuilds the same graph: a source is compressed, never deleted, never
moved off the host (the owner chose in place over `/media/BACKUP`: the
old history must stay readable when the NFS mount is not).

The latest file of each stream, the graph itself (rebuilt from the
sources), the dock's proposals, the sandbox reports, the Explications,
the image digests (`docker-digest`, read directly by the rollback
rehearsal) and the host records are not compressed.

### 4. Daily, by the vigil

The vigil compresses at most once a day (`data-budget/last-compaction`);
`python -m aistack.cli.data_budget [--compress [--dry-run]]` measures,
and compresses on demand.

## Implementation state

| Part | State |
|---|---|
| § 1 declaration, measurement | done — `aistack.data_budget.budget`, `data_budget.yml`, `aistack.contracts.data_usage` |
| § 2 health domain | done — `aistack.data_budget.health`, `health_score_weights.yml`, catalogs |
| § 3 compaction, reading `.gz` | done — `compress_old`, `aistack.history.query` |
| § 4 daily run, command | done — `aistack.cli.vigil`, `python -m aistack.cli.data_budget` |

## Consequences

- AIStack watches its own footprint like any other disk it reports on.
- JSON compresses about tenfold: after 90 days, the history costs a
  fraction of its first size, and nothing of it is lost.
- `python -m aistack.cli.docker_events_refilter` (2026-10-02's one-off
  tool) only reads plain `.json` batches: it leaves compressed ones as
  they are.

## Open Points

- The first real compaction falls at the end of December 2026, 90
  days after the oldest observations (the 1.5 collectors started on
  2026-09-28): its gain is to be measured then.
