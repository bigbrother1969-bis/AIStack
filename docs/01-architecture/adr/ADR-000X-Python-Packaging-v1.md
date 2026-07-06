# ADR-000X --- Python Packaging v1

-   **Status:** Accepted
-   **Date:** 2026-07-04

## Context

AIStack historically consisted of standalone Python scripts executed
individually:

``` bash
python3 script.py
```

Each script managed its own execution environment (`sys.path`, absolute
paths and local import logic).

The introduction of the first governed registry (`PathRegistry`) exposed
the architectural limitations of this approach. The issue was not Python
imports themselves, but the absence of a governed execution
architecture.

## Decision

AIStack progressively adopts a package-oriented Python architecture.

Key decisions:

1.  **Single Execution Environment**

    -   `bin/aistack_env.sh` is the single source of truth (SPOT) for
        the execution environment.
    -   Environment initialization is no longer duplicated across
        scripts.

2.  **Official Entry Points**

    -   Operational workflows are started through official launchers
        such as:
        -   `run_update_documentation.sh`
        -   `check_repository_integrity.sh`

3.  **Package-based Execution**

    -   Modules are executed using:

    ``` bash
    python3 -m package.module
    ```

    instead of direct script execution.

4.  **Progressive Packaging**

    -   Directories such as `architecture`, `runtime`, `knowledge`,
        `docker`, `reports` and `tools` become proper Python packages.

5.  **Progressive Removal of Local Environment Hacks**

    -   `sys.path.insert(...)` is no longer an acceptable architectural
        solution.
    -   Execution context belongs to the launcher, not to application
        modules.

## Consequences

### Positive

-   Consistent imports.
-   Centralized execution environment.
-   Easier testing.
-   Better portability.
-   Preparation for a future `pyproject.toml`.
-   Foundation for governed registries.

### Transitional

Migration is intentionally incremental. Existing workflows remain
operational throughout the transition.

## Architectural Discovery

This work revealed that packaging is not merely a technical concern.

Governed knowledge components (such as `PathRegistry`, `HealthPolicy`,
future registries and services) require a coherent namespace and
execution environment.

Packaging is therefore considered part of AIStack's knowledge governance
architecture.

## Future Evolution

Packaging v2 may introduce:

-   `pyproject.toml`
-   `aistack` command-line interface
-   Python entry points
-   Plugin architecture

## Codicil

> A knowledge governance system can only exist if the components
> carrying that knowledge belong to a coherent namespace. Packaging is
> therefore not a technical detail; it is part of the governance
> architecture itself.
