---
artifact:
  id: ADR-0008
  title: Evidence-Driven Observation Architecture
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Accepted
  owner: Architecture
  created: 2026-07-31
  updated: 2026-08-21

relations:
  references:
    - STD-0300
---

# ADR-0008 — Evidence-Driven Observation Architecture

This file supersedes the previous draft and freezes the architectural decision.

## Decision
AIStack separates the **Execution Dimension** from the **Knowledge Acquisition Dimension**.

Execution:
```
Request -> Task -> Kernel Runtime -> Observation Service -> Capability -> Action
```

Knowledge:
```
Reality -> Evidence -> Evidence Normalization -> Canonical Observations -> Item Qualification -> Knowledge Assets -> Governed Heritage
```

Key decisions:
- Discovery produces Evidence, never Knowledge.
- Qualification is independent from acquisition.
- Location abstracts where reality is observed.
- Technical access is implemented through interchangeable Adapters.
- Migration remains incremental.
