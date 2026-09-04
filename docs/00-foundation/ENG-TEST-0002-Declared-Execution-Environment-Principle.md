---
artifact:
  criticality: C3
  domain: Foundation
  id: ENG-TEST-0002
  owner: Engineering
  semantic_type: Principle
  status: Published
  title: Declared Execution Environment Principle
  type: Foundation Principle
  confidence: Declared
  created: 2026-07-24
  version: 2.4
  updated: 2026-09-03
---

# Declared Execution Environment Principle

## Principle

All AIStack Python tests shall be executed in the declared execution
environment.

The standard test execution command is:

``` bash
source scripts/dev-env.sh
pytest -q <test_path>
```

`bin/aistack_env.sh` is the single source of truth for that
environment, per ADR-0001. It **declares** the environment: the two
source roots and the interpreter the heritage is verified on.

`scripts/dev-env.sh` **provides** it. It sources
`bin/aistack_env.sh` — so the declaration is never bypassed — then
puts the project virtual environment ahead of the system
interpreter and reports which `python` and which `pytest` are
actually in use.

Declaring and providing are two responsibilities and stay two
files. A sourced file that is the source of truth for a
configuration should not also be the thing that mutates the
caller's shell to satisfy it.

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

## Host-touching UI screens declare their own dependencies, outside this environment

This principle's environment is the one AIStack's governed test suite runs
in. `selection_ui` and `priority_ui` are not part of that suite — decision
#9, 2026-08-29 (`claude/PLAN-UI-SELECTION-2026-08-29.md`): each is a
host-touching screen (`docker`, a real HTTP server) verified live rather
than by `pytest`, and nothing under `src/aistack` imports `fastapi`,
`uvicorn`, `jinja2` or `python-multipart`.

**The pattern, stated once rather than reasoned twice.** A screen of this
kind declares its own dependencies in its own `<screen>/requirements.txt`,
installed by its own `scripts/setup_<screen>_env.sh` into a dedicated
virtual environment, never into `.venv`. This environment —
`bin/aistack_env.sh` declared, `scripts/dev-env.sh` provided — stays exactly
what this principle already requires: the environment the governed suite
runs in, and nothing a screen needs only to serve HTTP.

**Why not `pyproject.toml [project.optional-dependencies]` instead.**
That would gain this principle's own reproducibility floor, at a cost
disproportionate to what it buys: nothing installs from it, verified
2026-09-03 (each screen's setup script reads its own `requirements.txt`, not
`pyproject.toml`), so the gain is available only if those scripts are
rewritten to install from `pip install .[<screen>]` instead — a change to
how installation actually works, not to where a list of names lives — and
declaring host-touching, untested packages beside the governed suite's own
dependency blurs the one line this principle exists to keep bright: what
`pytest` depends on, and what a screen depends on to run, are not the same
question.

**Recorded 2026-09-03**, `GOV-0002/OS-046`: found repeated identically
twice (`selection_ui`, then `priority_ui`) rather than reasoned once and
declared. This section is that declaration — the same shape decision #9
already used, made a stated pattern rather than a precedent each new
screen has to rediscover.

## What Changed In v2.4

`status` moves from `Draft` to `Published`, `GOV-0002/OS-050`. This is a
C3 principle, created 2026-07-24, that had stayed `Draft` while every
other artifact treated it as governing — including `bin/aistack_env.sh`'s
own designation as SPOT, and the Deployment host section `ADR-0001`
carries as of the same day. Measured 2026-09-03: `Accepted` is this
repository's status for decisions; `Published` is what a Foundation
Principle reaches. Nothing about the principle's content changes with
this entry.

## What Changed In v2.2

The command named `bin/aistack_env.sh`, which declares the environment
without providing it.

`pyproject.toml` requires Python 3.13 since 2026-08-23 and both images
ship `python:3.13-slim`. A developer's `python3` is whatever the
distribution installs — 3.12 on Linux Mint 22.3. The conforming
interpreter lives in the project virtual environment, and
`scripts/dev-env.sh` is what puts it on the PATH.

So the governed command was **the half that does not finish the job**,
and on 2026-08-23 the owner ran it exactly as written, on a bare shell:
514 passed and the interpreter test failed. The environment was declared
correctly and the principle pointed at the wrong file.

Version 2.1 had already established that a value retyped on the command
line is not more explicit than one declared in the repository. This
version applies the same reading one step further: a file that is correct
and incomplete is not a safer instruction than one that is complete.
`source .venv/bin/activate` typed by hand would have been version 1.0's
mistake again — a configuration reproduced from memory.

GOV-0002/OS-025, and the entry records that it was first opened on the
claim that no artifact named the virtual environment at all. That claim
was false: `scripts/dev-env.sh` had named it since 2026-08-21.

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
asked for `src` alone. FDN-P-005 requires one SPOT per knowledge item; the
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
declared by `bin/aistack_env.sh` and provided by `scripts/dev-env.sh`.

Any alternative execution mode must be considered an
environment-specific diagnostic and not the reference validation method.

This applies to the AI as much as to a human. A result reported from an
undeclared environment states nothing about AIStack; it states something
about the machine that produced it.

## Criticality

C3 --- Core Engineering Principle

AIStack must never rely on implicit runtime configuration for software
validation.
