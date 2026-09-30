---
artifact:
  id: OPS-0011
  title: Inventory Reconciliation
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Operations
  created: 2026-09-30
  updated: 2026-09-30

relations:
  references:
    - OPS-0004
---

# OPS-0011 — Inventory Reconciliation

## Purpose

This register declares how AIStack reconciles what it declares
(`service_categorization.yml`) against what it actually finds running —
locally, and on other LAN hosts via the last network discovery. `STD-0300`
§ VS-4 criterion 4.5 requires each qualification a finding carries to be
traceable to a distinct policy; this is that policy for the roadmap's own
R9 constat's remaining bullet ("Écarts d'inventaire → quai → validation →
inventaire déclaré"), the same way `OPS-0006`/`OPS-0009`/`OPS-0010` are
the policies for backup freshness, restore-test freshness, and backup
strategy coverage.

**Unlike `OPS-0009`/`OPS-0010`, this register declares no new hand-written
file.** There is nothing here for the owner to declare that is not
already declared elsewhere — `service_categorization.yml` is the owner's
own inventory (`ARCH-0009`), and `network-docker-observation.json` is
`network_docker_discover`'s own last output. This register only says how
the two are read together, and what a mismatch between them means.

## Provenance

Declared 2026-09-30, 1.6 tranche 3 (R9's remaining bullet,
`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`): "Écarts d'inventaire → quai
→ validation → inventaire déclaré ; le CIDR reste une décision du
owner." Four cadrage decisions preceded any code, via `AskUserQuestion`,
all the recommended option:

- **Périmètre** — `service_categorization.yml` alone, not also
  `pra_tests.yml` (the roadmap's separate "liste des services de
  `pra_tests.yml` proposée depuis la découverte" bullet stays a distinct,
  not-yet-scoped tranche) — the only declared inventory with a `container`
  field alignable to what discovery actually observes.
- **Mécanisme du « quai »** — a new dedicated runtime module
  (`aistack.contracts.inventory_gap`, `aistack.runtime.inventory_gap`,
  `aistack.runtime.evaluate_inventory_gap`), not an extension of
  `aistack.package_manager` — `ARCH-0013`'s own four Open Points
  (exact `PackageManager` interfaces, validation policies, integration
  conflict resolution, package version lifecycle) stay untouched; this
  register never opens them.
- **Exposition** — a seventh cockpit domain, "Écarts d'inventaire".
- **Types d'écarts** — les deux sens : a container discovered but
  declared nowhere, and a declared container never found running,
  neither locally nor via the last network discovery.

## What "the quai" concretely is here

**A computed join, not a queue — and never written back.** Every render
recomputes the two directions fresh, from `service_categorization.yml`
and the last `network-docker-observation.json` (if any); nothing is
persisted to a new artifact (the owner's own choice at cadrage: "calcul
à la volée uniquement", no new file, no new CLI command). The roadmap's
own "validation" step is the owner reading a finding here and editing
`service_categorization.yml` by hand — the same discipline every prior
tranche has held (`GOV-P-001`: the agent never edits a declared file on
the owner's behalf, and never pushes).

## Two sources, joined

- **Locally** — `DockerRuntimeCatalogBuilder().build(DockerProvider()
  .collect())`, the same live local observation `services_domain` already
  makes, narrowed to `kind == "container"` items.
- **Remotely, best-effort** — the last `reports/generated/network-docker-
  observation.json` `network_docker_discover` wrote, if one exists. That
  command is never triggered automatically (`NetworkDockerDiscoveryProvider`'s
  own docstring, decided with the owner 2026-09-12); this register reads
  whatever it last found, never regenerating it. A missing or corrupt
  observation file narrows the reconciliation to local-only, silently —
  it is optional, supplementary data, not the primary declared source.

`service_categorization.yml` itself is the only source this register
treats as required: its absence or corruption is `instrumented=False`,
the same absence every other domain already holds for its own declared
file.

## Two kinds of gap, symmetric

- **`discovered_undeclared`** — a container found running, locally or
  remotely, that no declared service names.
- **`declared_undiscovered`** — a declared service naming a container
  that neither source ever found running.

A declared service naming no container at all
(`ServiceDefinition.container is None` — hardware AIStack has no
provider for, or a service reached without being a container of its
own) is excluded from both directions, the same exclusion
`build_architecture_graph`'s own `ServiceStatus.NO_CONTAINER` already
makes.

## Out of scope for this version

- **`pra_tests.yml`** — the roadmap's separate bullet ("liste des
  services de `pra_tests.yml` proposée depuis la découverte") stays
  unscoped, per the owner's own choice at cadrage.
- **`cmdb_probe_targets.yml`** — HTTP-probed URLs have no equivalent on
  the discovery side (`network_docker_discover` does no HTTP probing,
  only `docker ps` over SSH), so nothing here reconciles it.
- **Extending `aistack.package_manager`** — the owner's own choice at
  cadrage; `ARCH-0013`'s four Open Points stay untouched.
- **Widening the CIDR `network_discovery.yml` declares** — stays the
  owner's own decision, unchanged by this register (the roadmap's own
  words: "le CIDR reste une décision du owner").

Both are a named absence this register records (`FDN-0003` Article 12),
not a silent one.

## What this register does not do

It does not itself run a network discovery, and does not verify that a
discovered container is healthy or correctly configured — it only asks
one question per container identity: is it declared where it is found,
and found where it is declared. `find_inventory_gaps`
(`src/aistack/runtime/inventory_gap.py`) is the join; `evaluate_
inventory_gap` (`src/aistack/runtime/evaluate_inventory_gap.py`) is what
cites `OPS-0004` against a confirmed gap.

## Related Artifacts

- `OPS-0004` — Sustainability Qualifications, § *Seventh reference case*
- `OPS-0010` — Backup Strategy Declarations, the sibling register this
  one is confronted against without duplicating (a different bullet of
  the same R9 constat)
- `claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` — R9, the constat this
  register supports
- `claude/SESSION-2026-09-30-1.6-tranche3-inventory-reconciliation.md` —
  the session that declared this register
