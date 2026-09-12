---
artifact:
  id: README-AISTACK
  owner: Foundation
  status: Draft
  title: AIStack Main README
  type: Entry Point Documentation
  semantic_type: Knowledge Artifact
  domain: Foundation
  criticality: C2
  confidence: Declared
  version: 5
  created: 2026-07-04
  updated: 2026-09-12
---

# AIStack

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE.txt)

**AIStack** is an open-source **Infrastructure Knowledge Platform (IKP)** designed to transform digital infrastructures into governed, explainable, portable, and sustainable knowledge.

*IKP is the category this project presents itself in. What AIStack **is** is
defined once, in `FDN-0002` § *AIStack*: a semantic system for building,
governing and exploiting the Governed Heritage of Digital Ecosystems. The
architecture it is built toward is named a Knowledge Operating System —
`ARCH-0010`.*

AIStack does not aim to build the most powerful infrastructure.

**Its ambition is to build the best understood and most sustainable one.**

---

# Human Guide

## Why AIStack?

Modern information systems have become increasingly complex.

Their knowledge is often:

- scattered across multiple tools;
- partially undocumented;
- dependent on individuals;
- difficult to maintain;
- difficult to transmit.

AIStack addresses this challenge by transforming infrastructure knowledge into a governed and sustainable heritage.

The objective is not merely to operate infrastructures.

The objective is to **understand**, **preserve**, and **transmit** them.

---

## What AIStack Does

AIStack helps organizations to:

- Observe infrastructures.
- Collect operational evidence.
- Build governed knowledge.
- Explain architectures and decisions.
- Maintain operational understanding.
- Preserve knowledge over time.
- Assist administrators with explainable recommendations.
- Facilitate infrastructure evolution and migration.

AIStack transforms observations into sustainable knowledge assets.

### Concrete capabilities, as of 0.7.0

- **Docker infrastructure discovery** — a governed catalog of a live
  Docker host: identity, image, state, ports, mounts, and the real
  `depends_on:` relationships between containers, regenerated from the
  host itself every time.
- **Architecture, visualized** — `architecture.html` renders that same
  discovery as a self-contained topology graph, plus a Docker dependency
  view, a section naming the external network topology and each
  machine's hardware, and a live Beszel health-metrics section.
- **Network-wide Docker discovery** — an explicitly-triggered LAN scan,
  over SSH, that reports Docker containers running on machines other
  than the one AIStack itself runs on, with a LAN-only screen to manage
  the candidate SSH usernames it tries.
- **Health Cockpit** — a scored dashboard across four domains (Storage,
  Services, Backup/DR, GPU), each instrumented against a real incident
  or a real declared threshold.
- **Console** — one entry point linking Selection UI, Priority CPU,
  Architecture, Health Cockpit and the network discovery screen, all
  reachable from the same page.
- **Context Bundle self-onboarding** — a portable, integrity-checked
  archive of the whole governed knowledge base, so a new AI session or
  contributor can get up to speed without reading the repository's
  entire history.
- **Knowledge integrity validation** — sixteen checks run against the
  governed documentation on every test suite and before every
  publication.
- **CPU resource priority scheduling** — declared priority applications
  get more CPU while active and give it back once idle, background
  containers throttle down for the duration, and every decision is
  recorded.
- **Music sync selection** — choosing, under a real capacity limit, what
  part of a media library syncs to a device.

**Full history of what changed release by release: `docs/03-handbook/RELEASE-NOTES.md`.**

---

## Quality Approach

Nothing ships on the strength of one look. Three governed gates run before
any change is published, and each exists because something specific once
got past its absence.

- **Tests, "cave au grenier."** Every generator has its own test, asserted
  through its own `generate()` — not only through the shared utility it
  calls or the CLI command that drives it at the front door. The project's
  own phrase for this, from the test suite itself: *"cave au grenier" per
  generator, not just at the shared utility and at the CLI's front door* —
  written after four provider CLIs raised on their second line for forty
  days, unnoticed, because nothing had ever imported them end to end.
- **Static checks — ruff and mypy.** `ruff check src tests` and `mypy src`
  run on every patch, alongside the test suite. Adopted 2026-09-10, after
  evaluating both against this codebase: on their very first run, before
  either had a configuration file to tune them, mypy found two real defects
  (an incompatible method override, two builders passing the wrong
  container type) and ruff found a genuine `zip()` truncation risk and
  four regex-escaping ambiguities in test assertions — not hypothetical
  findings, real ones, still in the commit history.
- **Publication — governed, and never automated.** `docs/04-development/
  OPS-0002-Heritage-Publication.md` states the procedure command by
  command. Before an image is built: a clean tree, on `main`, `HEAD` equal
  to `origin/main`, and `ruff`, `mypy`, `pytest` and the knowledge-integrity
  validator all clean — four preconditions, each refusing a different way
  of publishing something nobody could check. Every previous "current"
  image is re-pulled and its digest re-verified before a new one is built,
  so a published tag cannot quietly drift from what it once meant
  (`GOV-0002/OS-047`). Published images are pinned by digest in
  `docker-compose.yml`, one comment block per version, and a retracted or
  superseded entry is kept and explained, never deleted. The agent that
  helps write this heritage never builds or pushes an image itself — by
  design, not caution: the owner authenticates to the registry personally,
  for this step as for every other.

**As of 0.7.0**: `pytest -q` — **1751 passed**; `ruff check src tests` —
all checks passed; `mypy src` — no issues found in **447 source files**;
`python3 -m aistack.cli.knowledge_integrity` — **73 knowledge artifacts**,
`blocking: 0 warnings: 0 clean: True`.

The metrics quoted above and in `docs/03-handbook/RELEASE-NOTES.md` — test
counts, artifact counts, `clean: True` — are recorded by hand at each
publication, read off that publication's own `pytest`/knowledge-integrity
run. There is no CI pipeline in this repository yet to record them
automatically on every push; today's discipline is manual, applied
consistently rather than enforced by a hook.

---

## Core Principles

AIStack is built upon a small set of fundamental principles:

- Knowledge before Artificial Intelligence.
- Observation before Understanding.
- Governance before Automation.
- Architecture before Implementation.
- Documentation First.
- Generated artifacts are disposable.
- Sustainability over complexity.
- Explainability before optimization.
- Open standards before vendor lock-in.

---

## High-Level Architecture

```text
Applications
        │
        ▼
Interfaces
        │
        ▼
Kernel Services
        │
        ▼
Kernel
├── Engines
├── Registries
├── Repositories
└── Capabilities
```

The Kernel orchestrates the platform.

Capabilities implement technical operations.

Providers observe infrastructures.

Knowledge Artifacts preserve governed knowledge.

---

## Getting Started

Clone the repository:

```bash
git clone <repository-url>
cd AIStack
```

Generate the AI Context Bundle:

```bash
python3 scripts/export_project_sources.py
```

Run the validation suite:

```bash
source scripts/dev-env.sh
python3 -m compileall src/aistack && pytest -q
```

`bin/aistack_env.sh` declares the execution environment (ADR-0001,
ENG-TEST-0002) and `scripts/dev-env.sh` provides it — it sources the
first, then puts the project virtual environment ahead of the system
interpreter, which on most distributions is not the 3.13 this heritage
is verified on. `pytest` with no argument runs the AIStack suite and
only it: the paths are declared in `pyproject.toml`, per STD-0002.

---

## Project Documentation

The repository contains:

- Foundation documents
- Architecture documentation
- ADRs (Architecture Decision Records)
- Development standards
- Governance rules
- Knowledge artifacts
- Context Bundle
- Roadmap

---

# AI Bootstrap Guide

## Purpose

This section is intended for AI assistants collaborating on AIStack.

Before answering any question related to the project, an AI assistant must first understand the project's governance model.

---

## Acquisition SPOT

The Git repository hosted on Gitea is the **Single Point Of Truth (SPOT)**.

GitHub and Codeberg are publication mirrors. They are not authoritative and shall
never be used as the origin of governed knowledge.

**OPS-0002 states the publication procedure** — which role pushes where, in what
order, and what must hold before each step. Until 2026-08-27 this section
declared the principle and no artifact declared the procedure.

The **Context Bundle** is the official portable projection of the governed
heritage. It is not the SPOT. The most recent Context Bundle supersedes all
previous versions.

A bundle carries its own integrity information in `manifest.json`:

- `source_commit` — the commit the projection was taken from;
- `repository_url` — the canonical location of the SPOT;
- `content_hash` — a fingerprint of the governed knowledge carried, derived from
  artifact identities only, and therefore independent of generation time, machine
  and path.

Two bundles sharing a `content_hash` carry exactly the same knowledge. An agent
shall read these fields before reasoning, and shall state which bundle it is
operating from.

---

## AI Bootstrap Protocol

Always follow this sequence:

```text
README
    │
    ▼
Knowledge Classification
    │
    ▼
Criticality Evaluation
    │
    ▼
Relevant Context Acquisition
    │
    ▼
Reasoning
    │
    ▼
Response
```

The objective is **not** to load the entire repository.

The objective is to acquire only the governed knowledge required for the current task.

---

## AI Operating Principles

An AI assistant must always:

- Understand before modifying.
- Respect the Single Point Of Truth (SPOT).
- Never invent unknown knowledge.
- Clearly distinguish observations from assumptions.
- Produce explainable reasoning.
- Preserve governance.
- Prefer architectural improvements over implementation shortcuts.

Artificial Intelligence is considered a reasoning assistant, never an autonomous source of truth.

---

## Development Workflow

Every significant modification follows the same governed workflow:

```text
Proposal
      │
      ▼
Validation
      │
      ▼
SPOT Update
      │
      ▼
Git Commit
      │
      ▼
Context Bundle Regeneration
```

Knowledge is always validated before becoming part of the project's heritage.

*This is `FDN-0007`'s Governed Engineering Cycle at the scope of a repository
change. `FDN-0007` is the SPOT of the lifecycle; `FDN-0001` § *Working Workflow*
is its other instance, for Foundation contributions. The last two steps are
carried out by the procedure `OPS-0002` § 1 states command by command.*

---

## AIStack Architectural Model

AI assistants should understand the following responsibilities:

- Applications expose user-oriented functionality.
- Interfaces connect external systems.
- Kernel Services coordinate business operations.
- The Kernel composes platform capabilities.
- Engines perform core reasoning and orchestration.
- Registries maintain governed references.
- Repositories manage persistent knowledge.
- Capabilities implement technical mechanisms.
- Providers observe infrastructures.
- Knowledge Artifacts preserve and transmit knowledge.

Understanding the architecture always takes precedence over writing code.

---

## Engineering Philosophy

AIStack follows a Knowledge-Centric Engineering approach.

Engineering begins with understanding.

Implementation is only one consequence of sufficient understanding.

The platform therefore prioritizes:

- Architecture
- Documentation
- Governance
- Knowledge
- Implementation

rather than the opposite.

---

## Contributing

Contributions are welcome.

Before contributing, please ensure that:

- architectural consistency is preserved;
- documentation is updated when necessary;
- governance principles are respected;
- validation tests pass successfully;
- knowledge remains traceable and explainable.

---

## License

AIStack is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

The AGPL v3 guarantees that AIStack and any derivative work remain free and open, including when the software is provided as a network service. Any modifications distributed or made available through a server must also be released under the same license.

For the complete license terms, please refer to the **LICENSE.txt** file included in this repository.

---

## Vision

AIStack is not simply another infrastructure management platform.

Its mission is to transform digital infrastructures into governed, explainable, portable, and sustainable knowledge.

**Knowledge is the primary asset.**

Everything else exists to serve it.
