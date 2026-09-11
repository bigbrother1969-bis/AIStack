---
artifact:
  id: OPS-0008
  title: Health Score Weights
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
    - OPS-0005
    - OPS-0006
    - OPS-0007
---

# OPS-0008 — Health Score Weights

## Purpose

This register declares the weight, in points, that each of `PLAN-J7`'s four
instrumented domains (Stockage, Services, Sauvegarde / PRA, GPU) subtracts
from a health score of 100 for every `RuntimeFinding` it carries — the
number `aistack.health.score.compute_health_score` reads rather than
invents, the same `GOV-P-001` discipline every prior threshold register in
this family (`OPS-0005`, `OPS-0006`, `OPS-0007`) already holds. `PLAN-J7` §
1 named this decision at the plan's own start and left it undeclared until
four domains existed to weigh a score against — see
`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` for that governance interview
in full.

## Provenance

Declared directly by the owner, 2026-09-11, once Stockage, Services,
Sauvegarde/PRA and GPU were all instrumented and confirmed on GIGABYTE
(`PLAN-J7` §§ 6-10) — the same "wait until there is something real to
weigh" reasoning that kept this register empty through four domains' worth
of work rather than guessing at weights nothing yet exercised
(`aistack.renderers.health.html.render_html`'s own history: it rendered
findings with no score section at all until this register existed).

## Formula

`value = max(0, 100 − Σ penalty)`, where a domain's own penalty is
`len(domain.findings) × weight` for every domain this run instrumented —
never for a domain `PLAN-J7` § 5 / `FDN-0003` Article 12 already marks not
instrumented; an absence is excluded from the score entirely rather than
treated as either a penalty or a clean pass. Findings within one domain
are cumulative, by the owner's own choice: two simultaneous GPU threshold
breaches cost twice what one does, not a single flat penalty per domain
regardless of count.

The result is bucketed into three bands, also the owner's own declared
values:

- **excellent** — score ≥ 90
- **à surveiller** — 75 ≤ score < 90
- **action requise** — score < 75

A cockpit where fewer than all four domains are instrumented reports its
score alongside how many of the four it actually measured
(`measured_domains`/`total_domains`) — a 100 computed from one clean
domain out of four is not the same claim as a 100 computed from all four,
and this register does not let the display conflate them.

## Declared weights

| Domain | Points per finding |
|---|---|
| Stockage | 10 |
| Services | 15 |
| Sauvegarde / PRA | 25 |
| GPU | 8 |

Sauvegarde / PRA carries the heaviest weight of the four — a missing or
stale backup is the one failure among these four domains that costs data
outright if a real incident follows it, not merely degraded service or
comfort — the owner's own stated reasoning, 2026-09-11. GPU carries the
lightest — a hot or saturated GPU degrades performance without putting
anything at immediate risk. Stockage and Services sit between the two, at
values the owner confirmed directly rather than derived from any formula.

**No weight for a domain outside this closed set.** `compute_health_score`
raises rather than silently skipping a domain the cockpit names but this
register does not — the same `ARC-P-006` discipline that keeps every
threshold register in this family from being asked to cover a case the
owner has not yet named. Widening the domain vocabulary (`PLAN-J7` § 1)
requires widening this register in the same commit, never assumed to
default to zero.

## Out of scope for this version

- **Per-finding severity within a domain** — a GPU reading 1°C over its
  threshold costs exactly as much as one 30°C over; this register does not
  yet grade how far past a threshold a finding is, only whether it exists.
  Revisit only against a real case, `ARC-P-006`.
- **A fifth domain's weight** — added only once the owner instruments a
  fifth domain and states its weight, never guessed ahead of that domain
  existing.
- **Time decay or trend weighting** — a finding present for a week costs
  the same as one present for a minute; this register scores one snapshot,
  not a history.

Each is a named absence this register records (`FDN-0003` Article 12), not
a silent one — mirroring `OPS-0005`'s, `OPS-0006`'s and `OPS-0007`'s own
"out of scope for this version" sections, and revisited later against a
real case rather than built speculatively now.

## What this register does not do

It does not itself decide whether a domain is instrumented, nor what
qualifies as a finding — those are `HealthDomain.__post_init__` and each
domain's own `evaluate_*` function respectively, unchanged by this
register's existence. `aistack.health.score.compute_health_score` is the
pure function that reads this register's weights against an
already-built `HealthCockpit` and produces a `HealthScore`;
`aistack.health.score_weights.health_score_weights` is what loads this
file without ever raising, mirroring `storage_thresholds_for_host`/
`backup_thresholds_for_host`/`gpu_thresholds_for_host`.

## Related Artifacts

- `OPS-0004` — Sustainability Qualifications, whose qualified
  `RuntimeFinding`s are what this register counts, not requalifies
- `OPS-0005` — Storage Capacity Thresholds, the Stockage domain this
  register weighs
- `OPS-0006` — Backup Freshness Thresholds, the Sauvegarde / PRA domain
  this register weighs
- `OPS-0007` — GPU Consumption Thresholds, the GPU domain this register
  weighs
- `claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` — the health cockpit this
  register scores
