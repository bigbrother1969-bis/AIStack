---
artifact:
  criticality: C3
  domain: Engineering
  id: ENG-TEST-0002
  owner: Engineering
  semantic_type: Principle
  status: Draft
  title: Declared Execution Environment Principle
  type: Foundation Principle
  confidence: Declared
  created: 2026-07-24
  version: 2.0
  updated: 2026-08-21
---

# Declared Execution Environment Principle

## Principle

All AIStack Python tests shall be executed in the declared execution
environment.

The standard test execution command is:

``` bash
source bin/aistack_env.sh
pytest -q <test_path>
```

`bin/aistack_env.sh` is the single source of truth for that
environment, per ADR-0001.

## Rationale

Tests must execute against the source tree explicitly targeted by the
development environment.

Implicit Python path resolution may hide:

-   missing package configuration;
-   incorrect environment setup;
-   accidental dependency on globally installed packages;
-   differences between development and deployment environments.

Explicit configuration ensures:

-   reproducibility;
-   deterministic execution;
-   portability across environments;
-   early detection of packaging issues.

## What Changed In v2.0

Version 1.0 stated the command as:

``` bash
PYTHONPATH=src pytest -q <test_path>
```

That command was explicit and it was incomplete. AIStack has two source
roots: `src/` holds the `aistack` package, and the repository root holds
`selection_ui`, `examples` and `tools`. A developer typing `src` by hand
configured half the tree, and had no way to know it.

Worse, the value being typed was already declared elsewhere — three
times, differently. `bin/aistack_env.sh`, designated by ADR-0001 as the
SPOT for the execution environment, exported the repository root and not
`src`, so sourcing the governed file did not make `aistack` importable.
`scripts/dev-env.sh` exported `src` and not the root. This principle
asked for `src` alone. FDN-005 requires one SPOT per knowledge item; the
execution environment had three, and none of them was complete.

The principle is unchanged: the environment is stated, never inferred.
What changed is where it is stated. A value retyped on every command line
is not more explicit than a value declared once in the repository — it is
the same value, unversioned, unreviewed and impossible to correct in one
place. Version 1.0 made every developer responsible for reproducing a
configuration by memory, and the configuration they were reproducing was
wrong.

## Engineering Rule

A test result is considered valid only when executed in the environment
declared by `bin/aistack_env.sh`.

Any alternative execution mode must be considered an
environment-specific diagnostic and not the reference validation method.

This applies to the AI as much as to a human. A result reported from an
undeclared environment states nothing about AIStack; it states something
about the machine that produced it.

## Criticality

C3 --- Core Engineering Principle

AIStack must never rely on implicit runtime configuration for software
validation.
