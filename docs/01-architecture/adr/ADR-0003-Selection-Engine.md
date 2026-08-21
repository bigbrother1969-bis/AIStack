---
artifact:
  id: ADR-0003
  title: Selection Engine Strategy Delegation
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Proposed
  owner: Architecture
  created: 2026-07-07
  updated: 2026-08-21
---

# ADR-0003 - Selection Engine Strategy Delegation

## Status

Proposed.

The decision below is stated; it is not carried out. See *Implementation state*.

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

Observed on 2026-08-21, at `588ca0f`:

- `src/aistack/selection/engine/` and `src/aistack/selection/strategies/`
  contain nothing but `__init__.py`. The packages exist; the engine and the
  strategies do not.
- One strategy exists — `ByIdsSelectionStrategy` — and it lives in
  `src/aistack/kernel/selection/strategies/by_ids.py`, a different package from
  the one this ADR implies.
- `ByLabelsStrategy`, `ByTagsStrategy`, `ByPolicyStrategy` and `ByRuleStrategy`
  have no implementation.

This section records an observation, not a verdict. The decision may well be the
right one; it has simply not been carried out, which is why the status above is
`Proposed` rather than `Accepted`. An ADR that claimed otherwise would make the
heritage describe a system that does not exist.

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
