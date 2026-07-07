
---

## Selection Strategies

### Decision

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

### Rationale

The Selection Engine is responsible only for orchestrating the selection process.

Selection policies are independent responsibilities and shall evolve by adding new strategies rather than modifying the engine.

This architecture follows the Open/Closed Principle: the engine remains closed for modification while remaining open for extension through new Selection Strategies.
