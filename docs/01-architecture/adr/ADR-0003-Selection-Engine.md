---
artifact:
  id: ADR-0003
  title: Selection Engine Strategy Delegation
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Accepted
  owner: Architecture
  created: 2026-07-07
  updated: 2026-08-21
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
