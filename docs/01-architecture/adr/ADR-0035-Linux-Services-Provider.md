---
artifact:
  id: ADR-0035
  title: Linux Services Provider (Self-Discovery Outside Docker)
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Proposed
  owner: Architecture
  created: 2026-11-28
  updated: 2026-11-28

relations:
  references:
    - ADR-0004
    - ADR-0027
---

# ADR-0035 — Linux Services Provider (Self-Discovery Outside Docker)

## Status

Proposed, 2026-11-28, by the owner.

## Correction against the cadrage (2026-11-28, read of the real repo)

The cadrage (`CADRAGE-2026-11-27-self-discovery-linux-services.md`) and
its découpage (`PROPOSITION-2026-11-28-self-discovery-linux-decoupage.md`)
recorded LS0's trace-of-decision as "extend `PROVIDERS.md`, no separate
ADR — `LinuxProvider` is already announced there as a Future Provider."
Read against a fresh clone of the real repository: **no `PROVIDERS.md`
exists anywhere in it, and no file announces a `LinuxProvider` as a
future addition.** The premise behind that decision was false. This
ADR replaces it as LS0's actual deliverable.

## Context

*Measured on 2026-11-28, at commit `238e0e5`, against
`src/aistack/registrations.yml` and
`src/aistack/kernel/bootstrap/registrations.py`.*

A provider joins AIStack by a line in `src/aistack/registrations.yml`
(ADR-0027 § 8) — not by a narrative announcement anywhere, and not by
a change to the Kernel. `kernel/bootstrap/registrations.py` reads that
file once, at boot, and registers what it declares; `ADR-0004`'s own
"External Implementations" list (Docker Providers, Filesystem
Providers, …) is illustrative, not a governed registry — it already
omits `host`, `gpu`, `storage` and `backup`, all four registered today.

Not every provider is listed under `providers:`, though. One precedent
already matches the shape this one needs: `network_docker.discover`
(`aistack.tasks:NetworkDockerDiscoverTask`) reads per-host SSH
configuration (`hosts.yml`) and builds its own provider internally,
with no separate `provider:` entry — because its provider is
configured per host rather than built once with no argument, the shape
every `providers:` entry assumes (`factory()`, no arguments).

The cadrage (`CADRAGE-2026-11-27-self-discovery-linux-services.md`)
confirmed: four signals (`systemd`, installed packages, listening
ports, config files), four target services (MariaDB/MySQL, PostgreSQL,
Apache, PHP), every host already known to `hosts.yml`, observation
only — no gap qualification in this chantier, same sequencing as
Docker (observation first, a screen later, in its own cadrage).

## Decision

### 1. `LinuxServicesProvider` follows the `network_docker` shape, not the `providers:` shape

Built and owned by its own Task (`aistack.tasks:LinuxServicesDiscoverTask`
or similar, named at LS1), reading `hosts.yml` for the hosts to reach
over SSH — the same multi-host SSH mechanism `network_docker.discover`
already uses. No `providers:` entry in `registrations.yml`; a `tasks:`
entry instead, the same family as `network_docker.discover`.

### 2. Observation schema (confirmed at cadrage)

Per service, per host: `host`, `service`, `package_version`,
`unit_state`, `listening_ports`, `config_path`, `observed_at`. A host
missing a signal (no `dpkg`/`rpm`, say) is observed partially — the
unavailable field is absent, the host is kept for the other three
signals, never excluded.

### 3. Catalog: alongside Docker, not a separate one

The observation feeds the existing Infrastructure Data Catalog, next
to Docker's — a symmetrical pipeline (Provider → Observation → Runtime
Catalog → Artifact Generator → Knowledge Artifact), landing in the
same catalog rather than a new one.

### 4. On-demand collection only

Triggered manually, like `network_docker.discover` — no new scheduled
task in this chantier.

## Consequences

- `registrations.yml` gains a `tasks:` entry once LS1 names its class;
  no `providers:` entry, so `ProviderRegistry` gains nothing from this
  chantier alone — a reader checking "what providers exist" by that
  registry's contents alone will not find this one, same as
  `network_docker`'s provider today.
- `ADR-0004`'s "External Implementations" list stays what it already
  is — illustrative, already incomplete against the real registry —
  and this ADR does not attempt to make it exhaustive.
- LS1 contracts and tests follow the `network_docker` precedent:
  fixture SSH outputs, no real network access in the test suite.

## Open Points

None — ready for LS1.
