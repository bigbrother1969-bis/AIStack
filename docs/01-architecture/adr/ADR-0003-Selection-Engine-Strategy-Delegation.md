---
artifact:
  id: ADR-0003
  title: Selection Engine Strategy Delegation
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.4
  status: Accepted
  owner: Architecture
  created: 2026-07-07
  updated: 2026-08-29
---

# ADR-0003 - Selection Engine Strategy Delegation

## Status

Accepted.

A status records whether the decision was taken, not whether the code has
caught up. This ADR was `Proposed` until 2026-08-21 because its decision was
unimplemented — which conflated two different facts, and conflicted with
ADR-0001, `Accepted` on the same day while one of its own decisions had never
held. The gap belongs in *Implementation state*, below, where it can be read
without casting doubt on the decision itself.

## Context

The Selection Engine turns a Catalog View into a Selection.

Selection criteria differ from one use case to the next — by identity, by label,
by tag, by policy, by rule — and there is no reason to believe the list is
closed. Implementing them inside the engine would make every new criterion a
modification of the engine itself, and every such modification a risk to the
criteria that already work.

## Decision

The Selection Engine shall remain generic and stable.

Selection criteria shall not be implemented directly inside the engine.

Instead, the engine delegates the selection logic to interchangeable Selection Strategies.

The generic workflow becomes:

    Catalog View
          │
          ▼
    Selection Engine
          │
          ├── ByIdsStrategy
          ├── ByLabelsStrategy
          ├── ByTagsStrategy
          ├── ByPolicyStrategy
          ├── ByRuleStrategy
          └── ...
          │
          ▼
      Selection

## Rationale

The Selection Engine is responsible only for orchestrating the selection process.

Selection policies are independent responsibilities and shall evolve by adding new strategies rather than modifying the engine.

This architecture follows the Open/Closed Principle: the engine remains closed for modification while remaining open for extension through new Selection Strategies.

## Implementation state

Observed on 2026-08-21, at `90313d6`:

- One strategy exists — `ByIdsSelectionStrategy` — in
  `src/aistack/kernel/selection/strategies/by_ids.py`. The engine exists
  beside it, in `src/aistack/kernel/selection/engine/core.py`.
- `ByLabelsStrategy`, `ByTagsStrategy`, `ByPolicyStrategy` and
  `ByRuleStrategy` have no implementation.
- The delegation this ADR decides **is** how the one existing strategy is
  wired: the engine holds a `SelectionStrategy`, not a branch per criterion.

A previous version of this section reported that
`src/aistack/selection/engine/` and `src/aistack/selection/strategies/`
existed but were empty, and read that as the decision not being carried out.
Both were re-export façades that nothing imported, and they were removed on
2026-08-21. The engine and the strategy were in the kernel package all along;
the observation had been looking at the wrong tree.

What remains open is coverage, not structure: four of the five criteria this
ADR anticipates have no strategy yet.

### Re-measured 2026-08-27

| Step | State |
|---|---|
| `SelectionStrategy` — the contract the engine delegates to | done — 2026-08-27 |
| `SelectionEngine` — generic, no criterion inside | done — 2026-08-27 |
| `ByIdsSelectionStrategy` | done — 2026-08-27 |

The table exists because STD-0100 v2.6 requires it: the paragraphs above were
true and precise, and **nothing in this heritage could read them**. *Yet* and
*have no implementation* are not among `undated-assertions`' four markers, so
the knowledge sat in the right artifact and no report could carry it to anyone
who had not opened the file.

**The re-measurement said more than the paragraphs did**, and that is why it
was taken rather than converted. The prose above describes a coverage gap —
four criteria of five. Measured across the whole repository on 2026-08-27:

```text
SelectionEngine        → 0 callers, 0 tests
ByIdsSelectionStrategy → 1 instantiation, in bootstrap, with an empty list,
                         registered as `by-ids` and never retrieved
```

`selection_ui/app.py` imports `Selection`, the model, not the engine.
`docker_selection_catalog` builds a `SelectionCatalog` and writes JSON without
passing through the engine or `CatalogView`. `kernel/selection/__init__.py`
does not export the engine at all.

**So the delegation is complete for one criterion and consumed by nothing**,
and no instrument sees it: `contract-debt` does not count `SelectionStrategy`,
because `ByIdsSelectionStrategy` satisfies it, and `SelectionEngine` is not a
contract. That is GOV-0002/OS-039, and it is not a row of this table — this
decision commits to the engine delegating, not to anything calling it.

*The search covered the whole repository and not only `src/`, which is the
mistake GOV-0002/OS-001 recorded: a contract's position is what implements it,
what consumes it, and what governs it, and any one alone gives a confident
wrong answer.*

*One divergence noted while measuring and left as an observation rather than
repaired here: the Protocol declares `select(view) -> tuple[str, ...]` and the
one implementation returns `list[str]`.*

### The delegation became live on 2026-08-29

Every statement in the measurement above changed that day, and the entry is
dated rather than rewritten:

```text
2026-08-27                                  2026-08-29
SelectionEngine  → 0 callers, 0 tests       → called by aistack.selection.workflow, 6 tests
ByIdsSelectionStrategy → registered as      → registration removed; constructed per
  `by-ids` with an empty list, never          selection by the workflow
  retrieved
selection_ui imports Selection, not the     → imports the workflow, which holds
  engine                                      engine and strategy
docker_selection_catalog builds a           → builds a CatalogView through a
  SelectionCatalog                            registered engine
```

**The `by-ids` registration was removed rather than fixed.** `ByIdsSelectionStrategy`
carries its identifiers in its **constructor**, so the registered instance held
an empty list and selected nothing; a registry of instances can only hold
pre-configured strategies, and a strategy configured per use is not a registry
entry. Decided by the owner on 2026-08-29. *The registry itself stays — it is
the mechanism this decision names — and `unused-registrations` now reports
`selection_strategies` as empty after bootstrap, which is the true statement to
publish.*

**The return type was repaired the same day**, because the divergence stopped
being harmless the moment something consumed the chain. It had been correct to
leave it: nothing called the engine, so nothing could observe the difference.
*Neither `contract-debt` nor `false-declarations` sees a return type — both
compare call shapes — so the only instrument on it is a test.*

**What this decision commits to is now exercised rather than asserted.** The
engine holds a `SelectionStrategy` and no criterion; the criterion is the
strategy; and a stale identifier is dropped by the strategy rather than carried
into governed knowledge, which the Selection UI's hand-built `Selection` did
not do. **Coverage is unchanged** — one criterion of the five named — and that
is not a row, for the reason below.

### The four named strategies are not a row

`ByLabelsStrategy`, `ByTagsStrategy`, `ByPolicyStrategy` and `ByRuleStrategy`
sat in this table as one row, `not implemented`, from 2026-08-27 until
2026-08-29. **They are illustrations of an open list, and the decision says so
in its own words.**

§ *Context*: *by identity, by label, by tag, by policy, by rule — **and there is
no reason to believe the list is closed***. § *Decision*'s diagram ends on
`└── ...`. A row built from an open list can never reach a terminal state:
writing the four would not close it, because the sentence that produced them
anticipates a sixth.

**Removed 2026-08-29 by the owner**, on the rule this heritage had already
applied twice and not to itself here: `ADR-0001` § *Implementation state* leaves
out its decisions 2 and 4, `ADR-0004` § *What is not a row* leaves out
seventeen, and `ADR-0008` leaves out *migration remains incremental* — each
because *such as*, *includes* and a policy about how work arrives are not steps.
**This one was missed for two days while the rule was being cited in three other
files.**

*What the row was carrying that is true stays written, in the prose above and
below: one criterion of the five named has a strategy. That is coverage, it is
governed knowledge, and it never needed a row that reports it as unfinished work
for ever.*

*Measured 2026-08-29, so the alternative is on the record rather than implied:
the four are implementable. `ByLabelsStrategy` would read `CatalogViewItem.label`
and `ByTagsStrategy` its `metadata`. They were not written because four
strategies with no caller is `GOV-0002/OS-039` four times over — and
`ByPolicyStrategy` would name a family `OS-043` had declared non-existent hours
earlier.*

## Consequences

These follow from the decision, not from the current code:

- adding a selection criterion means adding a strategy, never modifying the
  engine;
- the engine's contract has to be stable enough for strategies to be genuinely
  interchangeable, which makes that contract the real design work;
- each strategy becomes independently testable, since it has no dependency on
  the orchestration around it;
- the set of available strategies becomes governed knowledge in its own right —
  a consumer cannot know what selection is possible without it.

## Related Artifacts

- ADR-0002 — Catalog View Engine, which produces the Catalog View this engine consumes
