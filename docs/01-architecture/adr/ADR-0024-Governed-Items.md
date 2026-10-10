---
artifact:
  id: ADR-0024
  title: Governed Items
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 0.1
  status: Proposed
  owner: Architecture
  created: 2026-10-10
  updated: 2026-10-10

relations:
  references:
    - ADR-0011
    - ADR-0015
    - ADR-0019
    - ADR-0023
---

# ADR-0024 — Governed Items

## Status

Proposed, 2026-10-10, for 2.1 or 3.0 — not before 2.0.0. Asked by the
owner the same day, on reading what 2.0.0-rc2 removed: *"Il va falloir
revoir le fonctionnement global pour utiliser ces composants."* Nothing
here is decided yet; § *Decision* is a proposal to contest.

## Context

From July to September the heritage wrote six packages to govern
knowledge: `item` (*"everything AIStack manages is a Governed Item"*: an
identifier, a type, an owner, a provenance, a lifecycle), `policies`
(rules read from governed documents), `package_manager` (a proposed change
received, inspected, validated, then integrated), `knowledge` (a knowledge
artifact and where it is found), `location` (where a resource lives) and
`context_bundle` (the knowledge handed to an AI). They governed **the
project's own documents**, not the server AIStack watches, and nothing in
the product ever called them. 2.0.0-rc2 removed them; they are at the tag
`archive/heritage-2.0.0-rc1`.

Meanwhile the product built the same ideas **one domain at a time, for the
server**, without a common model:

| Concept of the heritage | What the product does today, and where |
|---|---|
| Governed Item, with an owner and a type | A service is a name repeated in several declarations: `service_categorization.yml` (category, `on_demand`), `backup_strategy.yml`, `pra_tests.yml`, `dock.yml`, `resource_priority.yml`, the thresholds per host. A host is in `hosts.yml`, a disk in the thresholds. Nothing says these names are one thing. |
| Lifecycle | `on_demand` for a stopped service; an Explication's status (`KnowledgeLifecycle`, still in `contracts`); the Dock's proposal states. Three lifecycles, none for the service itself. |
| Policy | The thresholds (OPS-0005 to 0007), the backup strategies (OPS-0010), the CPU priorities, the health weights (OPS-0008): declared per file, each with its own reader. |
| Proposal, validated before integration | The Dock (`ADR-0019`): proposed with a reason, validated by a second person, rehearsed, applied, rolled back on failure. The Explications (`ADR-0015`): written, validated or discarded. The shipped declarations a new version brings (Settings). |
| Knowledge artifact | Explications are `KnowledgeArtifact`s (`contracts/artifact.py`); the Time Machine keeps every observation as a dated PROV-O fact (`ADR-0011`). |
| Location | Where AIStack keeps its data (Settings, 1.8), the folders it reads (`config/volumes.yml`, `ADR-0023`). |
| Context bundle | The facts the troubleshooting assistant gives Gemini or Ollama about a finding. |
| Reconciliation | The inventory gaps (OPS-0011): declared services against containers discovered. |

What this costs: a service renamed or added is edited in up to six files,
by hand; a finding cannot say *whose* service it is or how critical; the
Time Machine knows a container by its name, the health cockpit by another
key, and nothing ties the two; the Dock is the only change that goes
through a proposal, though a new threshold or a backup strategy changes the
server's governance as much.

## Decision (proposed)

### 1. One registry of Governed Items

Every thing AIStack governs on the server is an item with one identifier:
a host, a service (a compose project or a container), an image, a volume or
folder, a backup, a device. Discovery proposes items; an administrator
confirms them. The registry is the one place that says what exists, by
which identifier every screen, finding and fact refers to it.

### 2. Each item carries its governance

An owner, a criticality, a lifecycle (proposed, active, on demand, retired),
and its provenance — discovered by which collector, confirmed by whom,
when. The declarations of today (backup strategy, restore test, priority,
thresholds, Dock) become attributes or policies **attached to an item**,
not separate files keyed by a repeated name.

### 3. Every change to governance is a proposal

The Dock's path — a reason in writing, a second person, a rehearsal where
one is possible, a trace in the Time Machine — becomes the general path for
changing an item or its policies, not only an image. The phase rule of
`ADR-0016` applies: lighter in development, two people in production.

### 4. Policies are evaluated against items

The health cockpit's domains read the items and their policies instead of
each reading its own file; a finding names the item it is about, and so
inherits its owner and its criticality — the technical-debt and health
scores can then weigh by criticality rather than by domain only.

### 5. What is handed to an AI is a declared projection of items

The facts given to Gemini or Ollama about a finding become a projection of
the item, its policies, its recent facts and its Explications — declared
once, the same for every finding, and recorded with the answer.

## Consequences, if accepted

- The YAML declarations of 2.0 are migrated once into the registry, the
  files kept readable as an import path; `config_init` and the installation
  assistant write items rather than files.
- The Time Machine's subjects become item identifiers, so a renamed
  container stays the same subject.
- What the heritage wrote is reused as concepts and contracts (`Item`,
  `ItemMetadata`, `ItemLifecycle`, `GovernanceProposal`), not as code: it
  held its state in memory and had no persistence.
- A larger change than any since 1.7: every domain is touched. It is
  planned as its own version, after the test of 2.0 on a second server.

## Open points

- Where the registry lives: the Time Machine's graph (already PROV-O, one
  store), or a store of its own the graph projects.
- Whether an item may be declared without being discovered (a service
  planned, a remote backup).
- What the owner of an item is on a homelab with one administrator: a
  person, a role, a group of the identity provider.
