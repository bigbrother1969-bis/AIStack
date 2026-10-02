---
artifact:
  id: OPS-0008
  title: Health Score Weights
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.3
  status: Draft
  owner: Operations
  created: 2026-09-11
  updated: 2026-10-03

relations:
  references:
    - OPS-0004
    - OPS-0005
    - OPS-0006
    - OPS-0007
---

# OPS-0008 — Health Score Weights

## Purpose

This register declares the weight, in points, that each instrumented
domain (Stockage, Services, Sauvegarde / PRA, GPU — `PLAN-J7` § 1's four,
plus Tests PRA, added 2026-09-23, plus État persistant and Écarts
d'inventaire, both added 2026-09-30 — see *Declared weights* below)
contributes to a health score of 100 for
every `RuntimeFinding` it carries — the numbers
`aistack.health.score.compute_health_score` reads rather than invents, the
same `GOV-P-001` discipline every prior threshold register in this family
(`OPS-0005`, `OPS-0006`, `OPS-0007`) already holds. `PLAN-J7` § 1 named
this decision at the plan's own start and left it undeclared until four
domains existed to weigh a score against — see
`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md` for that governance interview
in full; `claude/PLAN-TESTS-PRA-2026-09-23.md` covers the fifth domain's
own addition.

## Provenance

Declared directly by the owner, 2026-09-11, once Stockage, Services,
Sauvegarde/PRA and GPU were all instrumented and confirmed on GIGABYTE
(`PLAN-J7` §§ 6-10) — the same "wait until there is something real to
weigh" reasoning that kept this register empty through four domains' worth
of work rather than guessing at weights nothing yet exercised
(`aistack.renderers.health.html.render_html`'s own history: it rendered
findings with no score section at all until this register existed).

## Formula

Each instrumented domain first scores itself: `domain_score = max(0, 100 −
len(domain.findings) × weight)`. Findings within one domain are
cumulative, by the owner's own choice, unchanged since 2026-09-11: two
simultaneous GPU threshold breaches cost twice what one does, not a single
flat penalty per domain regardless of count.

The overall score is the **weighted average of those per-domain scores**,
weighted by each domain's own points from the table below:
`value = round(Σ(domain_score × weight) / Σ weight)`, summed over every
domain this run instrumented — never over a domain `PLAN-J7` § 5 /
`FDN-0003` Article 12 already marks not instrumented, which is excluded
from both the numerator and the denominator rather than treated as either
a penalty or a clean pass. When no domain is instrumented at all there is
nothing to average and the score is 100, matching what a zero-penalty
sum already produced under the prior formula in that same case.

This is the owner's 2026-09-26 correction to the formula declared
2026-09-11, which instead summed every domain's penalty into one global
subtraction (`value = max(0, 100 − Σ penalty)`). That formula let a single
saturated domain — one carrying enough findings to floor its own penalty
past 100 points — floor the *entire* score to 0 regardless of how clean
every other domain was, which stopped being representative once a fifth
domain (Tests PRA, weighted 25) existed to saturate on its own: five
untested or stale restore tests floored a cockpit to 0/100 even with all
four other domains perfectly clean. The weighted average keeps each
domain's own cumulative-findings behavior identical (see above) while
letting one domain's saturation cost only its own declared share of the
total, not everyone else's.

The result is bucketed into three bands, also the owner's own declared
values, unchanged by this correction:

- **excellent** — score ≥ 90
- **à surveiller** — 75 ≤ score < 90
- **action requise** — score < 75

A cockpit where fewer than all declared domains are instrumented reports
its score alongside how many it actually measured
(`measured_domains`/`total_domains`) — a 100 computed from one clean
domain out of five is not the same claim as a 100 computed from all five,
and this register does not let the display conflate them.

## Declared weights

| Domain | Points per finding |
|---|---|
| Stockage | 10 |
| Services | 15 |
| Sauvegarde / PRA | 25 |
| GPU | 8 |
| Tests PRA | 25 |
| État persistant | 25 |
| Écarts d'inventaire | 25 |

**This table had drifted from `src/aistack/health/definitions/
health_score_weights.yml` itself since 2026-09-30, and was caught and
corrected 2026-10-02** — État persistant (1.6 tranche 2, R9) and Écarts
d'inventaire (1.6 tranche 3, R9) had both been declared in the real
weights file for two days, each weighted 25 points on the owner's own
2026-09-30 choice ("même ordre de grandeur que le domaine le plus
proche en signification" — the same criterion Tests PRA's own weight
was set by), while this register's own table still named only the
original five. Nothing enforces agreement between a register and the
file it describes; this entry is the measured instance, not a general
claim that the two cannot drift again.

Sauvegarde / PRA carries the heaviest weight of the original four — a
missing or stale backup is the one failure among those four domains that
costs data outright if a real incident follows it, not merely degraded
service or comfort — the owner's own stated reasoning, 2026-09-11. GPU
carries the lightest — a hot or saturated GPU degrades performance
without putting anything at immediate risk. Stockage and Services sit
between the two, at values the owner confirmed directly rather than
derived from any formula.

Tests PRA, added 2026-09-23 once `PLAN-J11` § 11.9.1's third and last
named gap ("tests PRA") closed, is weighted the same 25 as Sauvegarde /
PRA — the owner's own choice, "même ordre de grandeur que le domaine le
plus proche en signification" (`src/aistack/health/definitions/
health_score_weights.yml`'s own header comment records this verbatim).

**No weight for a domain outside this closed set.** `compute_health_score`
raises rather than silently skipping a domain the cockpit names but this
register does not — the same `ARC-P-006` discipline that keeps every
threshold register in this family from being asked to cover a case the
owner has not yet named. Widening the domain vocabulary (`PLAN-J7` § 1,
reopened once already 2026-09-23 for Tests PRA) requires widening this
register in the same commit, never assumed to default to zero.

## Regenerating the cockpit — `console.html` and `health.html` must agree

**Measured 2026-10-02.** `console.html` (`aistack.cli.console_render`)
and `health.html` (`aistack.cli.health_render`) each build their own
`HealthCockpit` independently — a deliberate choice, "no CLI in this
package imports another" (both modules' own header comments) — and
each is a **static file, regenerated only when its own command is run**:
`console.html` at every `aistack-console` service start/restart
(`run_console.sh`; `aistack-web`/`run_web.sh` since 2026-10-03, `ADR-0012`), `health.html` only when someone runs
`python -m aistack.cli.health_render` by hand. Nothing ties the two
together, and two of the seven domains — Services and Écarts
d'inventaire — read live Docker state at the moment their own command
happens to run.

The owner caught the two pages disagreeing: `console.html` showed
61/100 (dette technique 0/100), `health.html` showed 81/100 (dette
technique 40/100), served from the same host seconds apart. Reconciled
against this register's own formula: Tests PRA's 4 findings (declared,
static — `OPS-0009`) were the only ones `health.html`'s render saw,
giving 81/100 and a 40/100 debt score. `console.html`'s render,
run at a different moment, additionally saw 1 live Services finding and
4 live Écarts d'inventaire findings that had cleared by the time
`health.html` was generated — giving 61/100 and a debt score clamped to
0. Both renders computed their own cockpit correctly; what they
disagreed on was the live Docker state at two different instants, not
the arithmetic above.

**The required procedure, until a shared snapshot exists (see below):
regenerate both pages in the same sitting, never one without the
other**, immediately before anyone reads either as a current figure —
publishing a release included:

```bash
python -m aistack.cli.console_render && python -m aistack.cli.health_render
```

`aistack.console.server` (`aistack.web.console` since 2026-10-03,
`ADR-0012`) reads `console.html` fresh off disk on every
request (`Cache-Control: no-cache`, no in-memory copy), so this takes
effect immediately — no service restart required for the console half.
A residual drift window remains between the two commands (Docker state
can still change in the few seconds between them); closing it fully
would mean the two renders sharing one `HealthCockpit` computed once,
which is a deliberate reversal of the "no CLI imports another"
convention above and is not built here, `ARC-P-006` — this section
exists so the two pages are at least never read as current without
having been regenerated together.

## Out of scope for this version

- **Per-finding severity within a domain** — a GPU reading 1°C over its
  threshold costs exactly as much as one 30°C over; this register does not
  yet grade how far past a threshold a finding is, only whether it exists.
  Revisit only against a real case, `ARC-P-006`.
- **A further domain's weight** — Tests PRA (2026-09-23), État persistant
  and Écarts d'inventaire (both 2026-09-30) each closed this bullet in
  turn; a new domain's weight is added only once the owner instruments
  it and states its weight, never guessed ahead of that domain existing.
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
