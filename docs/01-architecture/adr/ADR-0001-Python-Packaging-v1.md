---
artifact:
  id: ADR-0001
  title: Python Packaging v1
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.3
  status: Accepted
  owner: Architecture
  created: 2026-07-04
  updated: 2026-09-04
---

# ADR-0001 --- Python Packaging v1

## Status

Accepted.

Observed on 2026-08-21: `pyproject.toml` declares the setuptools backend and
`where = ["src"]`, so the decision below is in force.

Also observed on 2026-08-21: decision 1 was declared and not held. This ADR
named `bin/aistack_env.sh` the SPOT for the execution environment; that file
exported the repository root alone, so sourcing it did not make `aistack`
importable. Environment initialization was therefore never de-duplicated —
`scripts/dev-env.sh` exported a second value and ENG-TEST-0002 asked
developers to type a third. All three were incomplete, because AIStack has
two source roots and each declaration named one. Corrected the same day:
`bin/aistack_env.sh` now exports both, `scripts/dev-env.sh` sources it, and
ENG-TEST-0002 v2.0 refers to it. The decision below is unchanged; it is now
implemented.

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

## Implementation state

Measured 2026-08-27. **All five key decisions are in force.**

| Step | State |
|---|---|
| 1 — Single Execution Environment, `bin/aistack_env.sh` as SPOT | done — 2026-08-27 |
| 2 — Official Entry Points | done — 2026-08-27 |
| 3 — Package-based Execution, `python3 -m package.module` | done — 2026-08-27 |
| 4 — Progressive Packaging | done — 2026-08-27 |
| 5 — Removal of Local Environment Hacks | done — 2026-08-27 |

What each was read against:

| Step | Evidence |
|---|---|
| 1 | `bin/aistack_env.sh` exports both source roots, idempotently, and forbids compiled bytecode; `scripts/dev-env.sh` sources it rather than restating it; ENG-TEST-0002 v2.2 names it. The § *Status* paragraph above records the day this stopped being a declaration and became true. |
| 2 | four launchers: `scripts/dev-env.sh`, `scripts/sync_mirrors.sh`, `scripts/maintenance/sync_context_bundle.sh`, `scripts/repository_inventory.sh` |
| 3 | `python3 -m aistack.cli.knowledge_integrity` is the command OPS-0002 § 1 prescribes. The one script invoked as a script is `scripts/export_project_sources.py`, which ADR-0006 § *Decision* declares the official Context Bundle entry point. |
| 4 | `pyproject.toml` declares `where = ["src"]`, and **every directory tracked under `src/aistack` carries an `__init__.py`** |
| 5 | one occurrence of `sys.path.insert` in the whole repository, in the launcher named above. **No application module inserts a path.** |

### Three readings the measurement corrected

**Two of the five decisions list examples, not requirements**, and reading them
as requirements produced two wrong answers before the words were read
properly.

Decision 2 names `run_update_documentation.sh` and
`check_repository_integrity.sh` *such as*. Neither has ever existed: measured
across the whole history on 2026-08-27, and the first commit of this repository
is `69485b7`, dated 2026-07-04 — the day this decision was accepted. They are
illustrations of a kind of launcher, and four launchers of that kind exist.

Decision 4 names six directories the same way. `runtime` and `knowledge` are
packages under `src/aistack`; Docker lives as `providers/docker` and
`catalog/docker`; `reports/` is an output directory rather than code; `tools/`
is a package at the root. The decision is that directories become proper
Python packages, and they have.

*A defect was nearly reported here that does not exist.* A `find` over the
working tree returned `src/aistack/funnel` without an `__init__.py` — an
**empty, untracked** directory git left on disk when `7b706ed` removed its
files on 2026-08-23 (GOV-0002/OS-018). `git ls-files` does not see it. The
packaging measurement is taken against the repository and not against a working
tree, and the two disagree.

### Where decision 5 touches decision 1

The single `sys.path.insert` sits in a launcher, which is where decision 5 says
execution context belongs — *not to application modules* — so decision 5 is
satisfied rather than excused.

**It is decision 1 that carries the tension.** `bin/aistack_env.sh` is the SPOT
for the execution environment, and here a launcher establishes its own import
path instead of relying on the sourced one. There is a measured reason:
`tests/integration/context_bundle/legacy/test_legacy_export_compatibility.py`
runs that script through `sys.executable` **without** sourcing the environment,
and without the insert it fails.

Recorded as prose rather than as a row state, because the row is not the thing
that is unfinished: **two places establish the same knowledge**, which is what
FDN-P-005 forbids, and the artifact that would have to change is this decision
rather than that script.

## Deployment host, 2026-09-04

Decision 1 names `bin/aistack_env.sh` the SPOT for the execution
environment, and every measurement above is taken against a development
workstation — the machine that edits and tests this repository.
`GOV-0002/OS-048`, decided 2026-09-04, names the gap that left open: the
reference deployment host (GIGABYTE) is neither a development workstation
nor a container built from `Dockerfile`, and had no pattern of its own,
so the four provider CLIs were run there with `PYTHONPATH=src` supplied
by hand on every invocation.

**The pattern already exists — it is what `Dockerfile` does.**
`aistack` is a real installable package (`pyproject.toml`, the
`setuptools` backend, `where = ["src"]`), and `Dockerfile` already runs
`pip install .` rather than setting `PYTHONPATH`. A deployment host is
closer to the image than to a development workstation — it runs the
package, it does not edit it — so it follows the same pattern: an
editable install into its own dedicated virtual environment.

```bash
python3 -m venv .venv-deploy
.venv-deploy/bin/pip install -e .
.venv-deploy/bin/python -m aistack.cli.docker_discover
```

`-e` rather than a plain install, because a deployment host tracks
`git pull`, not a rebuilt artifact — the same reasoning
`scripts/dev-env.sh` already applies to a development workstation's own
venv.
This is additive to decision 1, not a change to it: `bin/aistack_env.sh`
stays the SPOT for a development workstation; a deployment host now has
its own named pattern rather than an ad hoc workaround.

**Measured live on GIGABYTE 2026-09-04.** The three commands above were
run there: `aistack==0.4.0` installed editable, and
`.venv-deploy/bin/python -m aistack.cli.docker_discover` wrote
`reports/generated/docker-provider-observation.json` with no
`PYTHONPATH` set. `GOV-0002/OS-048` closes on that measurement, per
§ *What a closure must carry* — a condition about a host outside this
repository closes only against its own measurement, and this one now has
it.

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
