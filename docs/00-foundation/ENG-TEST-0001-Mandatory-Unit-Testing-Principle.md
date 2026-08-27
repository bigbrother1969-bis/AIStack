---
artifact:
  criticality: C3
  domain: Foundation
  id: ENG-TEST-0001
  owner: Engineering
  semantic_type: Principle
  status: Draft
  title: Mandatory Unit Testing Principle
  type: Foundation Principle
  confidence: Declared
  created: 2026-07-24
  version: 1.1
  updated: 2026-08-21
---

# Mandatory Unit Testing Principle

## Principle

Every AIStack software component, contract, engine, service, and
architectural layer shall include unit tests.

A feature, refactoring, or new capability cannot be considered complete
without automated verification of its expected behavior.

## Rationale

Unit tests are not only code validation tools.

They are executable documentation of software contracts.

They ensure that:

-   architectural intentions remain valid;
-   contracts are preserved over time;
-   regressions are detected early;
-   refactoring remains safe;
-   knowledge embedded in software remains reproducible.

## Engineering Rule

Any new implementation must be delivered with its corresponding unit
tests.

Any modification of an existing component must update or extend its
tests when the behavior or contract changes.

## Criticality

C3 --- Core Engineering Principle

AIStack must never consider untested software as a completed engineering
artifact.
