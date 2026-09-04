---
artifact:
  id: ADR-0004
  title: AIStack Kernel Architecture
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.5
  status: Accepted
  owner: Architecture
  created: 2026-07-07
  updated: 2026-09-04
---

# ADR-0004 - AIStack Kernel Architecture

## Status

Accepted

## Context

AIStack is evolving from a set of tools into a Knowledge Operating System.

Recent implementation work revealed a stable set of generic concepts: Catalog, Catalog View, Selection, Selection Strategy and Registry.

The more AIStack relies on generic Kernel concepts, the more portable and extensible it becomes.

Technology-specific concepts such as Docker, Syncthing, Linux, Kubernetes or Nextcloud shall remain outside the Kernel.

## Decision

AIStack introduces a technology-independent Kernel.

The Kernel contains only generic governed concepts, contracts, registries and engines.

Technology-specific implementations connect to the Kernel through governed contracts and registries.

The Kernel shall not depend directly on any specific infrastructure technology, provider, cloud, model or synchronization tool.

## Kernel Responsibilities

The Kernel is responsible for:

- defining stable contracts;
- managing registries;
- exposing generic engines;
- orchestrating governed concepts;
- preserving technology independence;
- enabling portability across environments.

## Kernel Structure

The target Kernel structure is:

    kernel/
    ├── contracts/
    ├── registry/
    ├── registries/
    ├── lifecycle/
    ├── discovery/
    ├── dependency/
    └── context/

## Generic Concepts

The Kernel manipulates concepts such as:

- Catalog;
- Catalog View;
- Selection;
- Selection Strategy;
- Registry;
- Policy;
- Renderer;
- Generator;
- Knowledge Artifact.

## External Implementations

External or domain-specific implementations include:

- Docker Providers;
- Filesystem Providers;
- Syncthing workflows;
- Nextcloud integrations;
- Kubernetes adapters;
- domain-specific Catalog Views;
- domain-specific Selection Strategies;
- rendering and generation implementations.

These implementations shall remain replaceable plugins around the Kernel.

## Rationale

The portability of AIStack comes from the genericity of its Kernel, not from Docker or any deployment technology.

Every technology-specific concept moved outside the Kernel increases portability, maintainability and extensibility.

The Kernel shall know contracts and registries, not concrete implementations.

## Implementation state

Measured 2026-08-28 at `1174078`. **The Kernel is built and its boundary holds;
what this decision names and what was built are two different sets.**

*The first version of this section read that the boundary was drawn in one place
the code contradicts. The owner qualified that place on 2026-08-28 — the
Composition Root may name technologies — and the sentence went with the row.*

| Step | State |
|---|---|
| A Kernel of generic governed concepts — `src/aistack/kernel/` | done — 2026-08-28 |
| The Kernel defines stable contracts — `kernel/contracts/` | done — 2026-08-28 |
| The Kernel manages registries — `Registry[T]` and `KernelRegistries` | done — 2026-08-28 |
| The Kernel exposes generic engines | done — 2026-08-28 |
| Technology-specific implementations connect through contracts and registries | done — 2026-08-28 |
| Those implementations remain replaceable — registered and resolved by name | done — 2026-08-28 |
| The Kernel depends on no specific infrastructure technology | done — 2026-08-28 |
| The target Kernel structure — `lifecycle/`, `discovery/`, `dependency/` | superseded — 2026-08-29 |
| The six registries § *Consequences* names follow the same pattern | superseded — 2026-08-29 |

What each was read against:

| Step | Evidence |
|---|---|
| the Kernel | `src/aistack/kernel/` holds **thirteen** packages (seventeen until 2026-08-29); `Catalog`, `CatalogView`, `Selection`, `SelectionStrategy`, `Registry` and `KnowledgeArtifact` are all declared inside it |
| contracts | `kernel/contracts/` — **seven** modules, all `Protocol` or base classes: base provider, catalog view, provider, registry, mutable registry, selection, task source. *`package_capability` was the eighth until 2026-08-29 and was abandoned with the nine classes that declared it — ADR-0008.* |
| registries | `kernel/registry/core.py` defines `Registry[T]`; five classes subclass it — provider, catalog view, selection strategy, task, contract — and `KernelRegistries` aggregates four of them, frozen |
| engines | `kernel/selection/engine/core.py`. It names no technology. **`kernel/engines/package_manager.py` was the second until 2026-08-29** — both its methods returned their argument unchanged, it had no caller, and it was removed with the Knowledge Package classes it orchestrated (ADR-0008, `GOV-0002/OS-041`). One engine still satisfies this row; the evidence is corrected rather than the row |
| the connection | `aistack/providers/`, `aistack/generators/`, `aistack/catalog/` sit outside `kernel/` and reach it through `KnowledgeProvider`, `CatalogViewEngine` and `SelectionStrategy` |
| replaceable | `kernel.registries.providers.register("docker", …)` and `ctx.registries.providers.get("docker")` — resolution is by identifier, and no consumer names a class. *This line read `ctx.providers.get(...)` until 2026-08-29, copied from four CLIs that had been raising `AttributeError` on that exact expression since 2026-07-20 — `GOV-0002/OS-044`. Evidence transcribed from code nobody had run.* |
| the boundary | ten imports inside `kernel/` leave the kernel package, two of them naming a technology — below |
| the target structure | `contracts/`, `registry/`, `registries/` and `context/` exist; `lifecycle/`, `discovery/` and `dependency/` do not |
| the six registries | measured across the repository, `archive/` excluded — below |

### The Kernel imports Docker

Measured 2026-08-28 across `src/aistack/kernel/`:

```text
kernel/bootstrap/providers.py     → aistack.providers.docker, aistack.providers.compose
kernel/bootstrap/catalog_views.py → aistack.catalog.views.music
kernel/bootstrap/default.py       → aistack.transport (three modules)
kernel/runtime/core.py            → aistack.transport
kernel/services/core.py           → aistack.transport (three modules)
```

**Two readings fit the same bytes**, and no artifact chooses between them:

- **`bootstrap/` is the Composition Root**, which is where technology is
  supposed to appear. The code says so itself — `bootstrap/default.py` names
  itself *the Runtime Composition Root*. Under this reading the boundary holds,
  and what is wrong is that the composition root is packaged inside the thing it
  composes;
- **the Kernel is the package `aistack.kernel`**, in which case
  `from aistack.providers.docker import DockerProvider` is the dependency
  § *Decision* forbids in the words it forbids it, and the repair is to move
  `bootstrap/` out.

Which one is right is not derivable from the code, and it is not a measurement:
it is a decision about where the boundary is drawn. ARCH-0002 § *Boundary*
restates the rule without saying which package carries it.

**Decided 2026-08-28 by the owner: the first.** The Kernel is the architectural
layer, `bootstrap/` is its Composition Root, and naming technologies is what a
composition root is for — a root that could not name `DockerProvider` could not
compose anything. The row is `done`: the boundary this decision draws is
honoured, and the four CLIs reach Docker through `providers.get("docker")`
rather than through a class.

**What that decision leaves open is narrower and is not a row.** The Composition
Root is packaged inside the thing it composes, so `git grep docker
src/aistack/kernel` answers *yes* on a Kernel that depends on no technology, and
every future reader will measure it the same way and reach the same wrong
conclusion the first reading reached here. Whether `bootstrap/` moves out of
`src/aistack/kernel/` is a question about packaging, not about this decision's
boundary, and it is recorded rather than answered.

**Answered 2026-09-04, `GOV-0002/OS-054`: it stays.** Both readings are
defensible — composition as a facet of the thing composed, or composition
as a separate concern assembling a `Kernel` from outside — and nothing
depends on which: the five import sites (`kernel/runtime/core.py`, three
CLIs, `aistack/conformance/registries.py`) all reach `create_kernel`
through `aistack.kernel.bootstrap` and would import identically either
way. The owner chose not to move it: a mechanical rename touching five
imports, for a question this ADR already named as stylistic rather than
architectural, is exactly the unearned motion `ARC-P-006` exists to
refuse. Recorded rather than left implicit, so a future reader measures
the same bytes and does not reopen a question already asked and
answered.

*The `aistack.transport` imports are a different question and are not what that
row is about*: nothing under `aistack/transport/` names an infrastructure
technology. They are concrete implementations imported by name where
§ *Rationale* says the Kernel shall know contracts and registries — a coupling
recorded here, not the boundary.

### Five of the six registries exist nowhere

§ *Consequences* names six, by name and not as examples:

| Registry | Where |
|---|---|
| `ProviderRegistry` | `kernel/registries/provider_registry.py` |
| `GeneratorRegistry` | exists nowhere |
| `RendererRegistry` | exists nowhere |
| `PolicyRegistry` | exists nowhere |
| `PortRegistry` | exists nowhere |
| `PathRegistry` | exists nowhere |

**The pattern is not the gap.** `Registry[T]` exists and five registries follow
it — provider, catalog view, selection strategy, task, contract. What this
decision named and what was built are two sets that overlap in one place.

**Qualified `superseded` on 2026-08-29 by the owner**, and the measurement that
decided it is per registry rather than per count:

| Registry | What it would hold, measured 2026-08-29 |
|---|---|
| `GeneratorRegistry` | **four real classes** — `DockerCatalogArtifactGenerator`, `DockerObservationArtifactGenerator`, the Compose generator, the filesystem copy generator. The only one of the five with members |
| `RendererRegistry` | **nothing.** `src/aistack/renderers/` holds one empty `__init__.py` and declares no class |
| `PolicyRegistry` | **a family `GOV-0002/OS-043` resolved as non-existent** the same day: `KnowledgePolicy` is a predicate, `BundleTransferPolicy` a configuration, and they share no member |
| `PortRegistry` | no class named `Port` exists anywhere |
| `PathRegistry` | no class named `Path` exists anywhere |

**Five of the six have no subject, and building them would manufacture exactly
what ARC-P-006 refuses** — four empty registries, one of them for a family this
heritage decided that morning does not exist. What the decision was reaching for
is delivered: `Registry[T]` and resolution by identifier, followed by five
registries the decision did not name. **The row is superseded by the pattern
rather than left unfinished by the list.**

*`GeneratorRegistry` is the one that could be built, and was not. Nothing would
retrieve a generator by identifier: the CLIs instantiate them directly. A sixth
registration nobody retrieves is what `unused-registrations` was written to
report, and building it to close a row would be writing the finding into the
code on purpose. Recorded here so that a future reader knows it was considered.*

**What still asserts otherwise.** ARCH-0007 § *Current Registries* lists
`PipelineRegistry: registered Knowledge Pipelines`, and no class of that name
exists in the repository; the same section omits `TaskRegistry` and
`ContractRegistry`, which do. It is wrong in both directions, and it is not
corrected in this commit — one commit, one concept. Named here per GOV-0002
§ *What a closure must carry*, rule 2.

### The target structure diverged in both directions

Of the seven directories § *Kernel Structure* names, four exist. `lifecycle/`,
`discovery/` and `dependency/` do not, and that is what the row records, because
those are what the decision names. The kernel also holds packages the target
does not name — measured 2026-08-29: `bootstrap`, `catalog`, `execution`,
`knowledge`, `resolution`, `runtime`, `selection`, `services`, `tracing`.

*That list held four more on 2026-08-28 — `capabilities`, `engines`, `models`
and `repositories`. **All four were removed on 2026-08-29 because they were
empty or held only classes that could not run**: nine capabilities that could
not be instantiated, two `KnowledgePackage` declarations, and a facade
returning its argument. The divergence from the target narrowed by four
directories, and not one line of behaviour changed.*

Whether a structure declared on 2026-07-07 is still the target is a question for
the owner and not a measurement, so it was recorded and not answered.

**Answered 2026-08-29: `superseded`.** The Kernel diverged in both directions
and works — four of the seven named directories exist, and thirteen the target
never named carry the concepts this decision is about. A structure the code has
outgrown in both directions is not a target that remains unreached; it is a
target that was replaced by what was built.

*The alternative was to create `lifecycle/`, `discovery/` and `dependency/`.
Declined because nothing in this heritage says what they would contain, so the
work is not three packages — it is deciding three responsibilities, which is a
new decision and not this one's unfinished step. Two empty re-export façades
were removed on 2026-08-21 for the same reason (`ADR-0003`).*

*§ *Kernel Structure* is left standing above rather than rewritten. An
intention declared on 2026-07-07 is what this ADR is a record of, and a decision
that edited its own § *Decision* to match the code would stop being one.*

### What is not a row

§ *Generic Concepts* lists nine **such as**, and § *External Implementations*
lists eight it says it **includes**. Both are illustrations, as ADR-0001
§ *Implementation state* records for its own decisions 2 and 4; rows built from
them would be seventeen commitments this decision never made.

Measured anyway, because the list is a useful reading of the boundary:
`Catalog`, `Catalog View`, `Selection`, `Selection Strategy`, `Registry` and
`Knowledge Artifact` are declared in the Kernel. **`Policy`, `Renderer` and
`Generator` are not concepts anywhere** — `aistack/renderers/` declares no class
at all, `aistack/policies/` declares one exception type, and
`aistack/generators/` holds three technology-specific generators, which is
exactly where this decision puts implementations. The concept is absent, not
misplaced.

*Future components shall first be evaluated against the Kernel boundary* is a
policy about how the rest of the work arrives, not a step that can reach a
terminal state. It is left out of the table for the reason ADR-0008 records for
its own fifth key decision: a row that can never be closed is reported as
unfinished at every projection for ever.

*`KnowledgeArtifact` is declared four times* — `kernel/knowledge/artifact/model.py`
and three classes outside the Kernel, in `contracts/`, `knowledge/contracts/`
and `transport/contracts/`. The concept is in the Kernel, which is what this
decision requires; that it is also in three other places is FDN-P-005's subject
and not a row here.

---

## Consequences

Future components shall first be evaluated against the Kernel boundary.

If a concept is generic, it may belong to the Kernel.

If a concept is technology-specific, it shall remain an implementation registered through a Kernel registry.

ProviderRegistry, GeneratorRegistry, RendererRegistry, PolicyRegistry, PortRegistry and PathRegistry shall follow the same registry pattern.

AIStack development shall continue to favor generic Kernel concepts before technology-specific implementation.
