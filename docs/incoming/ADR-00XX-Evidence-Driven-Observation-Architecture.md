# ADR-00XX — Evidence-Driven Observation Architecture

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
