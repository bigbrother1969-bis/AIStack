---
artifact:
  criticality: C3
  domain: Engineering
  id: ENG-TEST-0002
  owner: Engineering
  semantic_type: Principle
  status: Draft
  title: Explicit Python Path Test Execution Principle
  type: Foundation Principle
lifecycle:
  created: 2026-07-24
---

# Explicit Python Path Test Execution Principle

## Principle

All AIStack Python tests shall be executed with an explicit source path
declaration.

The standard test execution command is:

``` bash
PYTHONPATH=src pytest -q <test_path>
```

## Rationale

Tests must execute against the source tree explicitly targeted by the
development environment.

Implicit Python path resolution may hide:

-   missing package configuration;
-   incorrect environment setup;
-   accidental dependency on globally installed packages;
-   differences between development and deployment environments.

Explicit source path configuration ensures:

-   reproducibility;
-   deterministic execution;
-   portability across environments;
-   early detection of packaging issues.

## Engineering Rule

A test result is considered valid only when executed using the official
AIStack test command convention.

Any alternative execution mode must be considered an
environment-specific diagnostic and not the reference validation method.

## Criticality

C3 --- Core Engineering Principle

AIStack must never rely on implicit runtime configuration for software
validation.
