
## Validation expérimentale — Reconstruction d'une interface perdue

Un incident survenu lors du développement d'AIStack a constitué une démonstration concrète de la valeur d'une approche Knowledge-Centric.

Une évolution importante de l'interface **Music Android Selection** avait disparu du dépôt. L'application fonctionnait toujours, mais une ancienne interface était exécutée.

Le diagnostic a nécessité de reconstituer progressivement la chaîne de connaissances :

- état des conteneurs Docker ;
- configuration du reverse proxy ;
- ports réellement exposés ;
- code effectivement exécuté ;
- comparaison avec l'architecture attendue ;
- reconstruction des fonctionnalités perdues.

Le problème n'était pas un dysfonctionnement technique du Runtime.

Le problème était la perte d'un patrimoine de connaissances concernant les fonctionnalités attendues de l'interface.

Cette expérience valide directement la vision d'AIStack :

> Transformer un incident technique en un problème de connaissance gouvernée.

Dans un Knowledge Operating System mature, AIStack aurait pu expliquer automatiquement :

- le service exécuté ;
- l'état du Runtime ;
- la version de l'artefact exécuté ;
- les fonctionnalités attendues mais absentes ;
- les observations ayant conduit au diagnostic ;
- la recommandation de reconstruction ;
- la validation par l'utilisateur.

Cette reconstruction démontre que la valeur principale ne réside pas dans le code, mais dans la connaissance gouvernée permettant de reconstruire fidèlement un artefact.

Elle constitue l'un des premiers cas de validation expérimentaux du Knowledge Operating System.


## Principle — Knowledge Begins with Evidence

AIStack distinguishes rigorously between reality, evidence, observations and knowledge.

Knowledge must never be derived directly from raw technical outputs.

A governed transformation pipeline is mandatory.

```text
Reality
    ↓
Evidence Collectors
    ↓
Evidence
    ↓
Normalizers
    ↓
Canonical Observations
    ↓
Correlation Engines
    ↓
Knowledge Assets
    ↓
Policies
    ↓
Inference Engines
    ↓
Recommendations
```

### Evidence

Evidence is the immutable record of what has been acquired from a source.

Typical examples include:

- command outputs;
- API responses;
- configuration files;
- JSON payloads;
- log excerpts;
- snapshots;
- measurements.

Evidence must remain as close as possible to the original source and be independently historized.

Evidence contains no business interpretation.

### Observation

An Observation is a canonical interpretation of one or more Evidence objects.

Its purpose is to normalize heterogeneous technologies into stable AIStack concepts.

Examples:

- Docker inspection;
- Compose project;
- filesystem inventory;
- running process;
- listening port.

Observations are technology-independent.

### Knowledge

Knowledge is produced only after observations have been correlated and evaluated according to explicit policies.

Knowledge may include:

- catalogs;
- technical debt;
- Sustainability Score;
- architecture evaluations;
- recommendations;
- documentation;
- governed artifacts.

### Separation of responsibilities

Each layer has a single responsibility.

- Collector → acquire Evidence.
- Normalizer → produce canonical Observations.
- Correlator → combine Observations.
- Builder → construct governed Knowledge Assets.
- Generator → generate Artifacts.
- Renderer → present knowledge.

No component should perform responsibilities belonging to another layer.

### Architectural consequences

The same Evidence may later be reinterpreted using:

- improved Normalizers;
- additional Correlation Engines;
- new Knowledge Policies;
- newer AI Engines.

This must not require a new acquisition from the infrastructure.

This separation enables explainability, reproducibility, auditability and long-term preservation of knowledge.

It also makes AIStack independent from acquisition technologies while preserving the complete Observation History.

## Principle — Modular Monolith First

AIStack shall be designed as a modular monolith before considering distributed deployment.

The primary objective is architectural decoupling rather than physical distribution.

Each responsibility must be isolated behind an explicit contract while remaining deployable within a single Runtime.

```text
Kernel Runtime
    │
    ├── Evidence Collectors
    ├── Evidence Normalizers
    ├── Correlation Engines
    ├── Catalog Builders
    ├── Knowledge Policies
    ├── Artifact Generators
    └── Renderers
```

Deployment boundaries must never dictate architectural boundaries.

Instead, deployment is derived from architecture.

Components may later evolve into independent services without modifying their contracts.

This evolution is justified only by demonstrated operational needs such as:

- distributed acquisition;
- security isolation;
- scalability;
- asynchronous processing;
- incompatible dependencies.

The default deployment model remains a single Runtime.

This principle minimizes complexity, reduces resource consumption, simplifies testing and deployment, and remains aligned with the Digital Sobriety principles of AIStack.

The objective is therefore:

> Modular Monolith First.

> Service-Oriented Evolution Only When Justified.

## Architecture Evolution — Knowledge Acquisition Pipeline

The former Provider abstraction has reached its architectural limits.

AIStack shall progressively replace technology-oriented Providers with a governed Knowledge Acquisition Pipeline.

The pipeline becomes:

```text
Reality
    ↓
Evidence Collectors
    ↓
Evidence
    ↓
Normalizers
    ↓
Canonical Observations
    ↓
Correlation Engines
    ↓
Knowledge Assets
    ↓
Policies
    ↓
Inference Engines
    ↓
Recommendations
```

This architecture separates acquisition, normalization, correlation and reasoning into explicit responsibilities.

The existing Provider implementations become transitional compatibility components and shall be progressively replaced by:

- Evidence Collectors;
- Evidence Normalizers;
- Correlation Engines.

The migration shall remain incremental and preserve a working Runtime after every commit.

## Distinguish Interfaces from Contracts

AIStack distinguishes two complementary architectural concepts.

### Interfaces

Interfaces define the internal programming contracts between AIStack components.

Examples:

- EvidenceCollector
- EvidenceNormalizer
- CorrelationEngine
- KnowledgeGenerator

Interfaces specify responsibilities and behavioral expectations inside the Knowledge Operating System.

### Knowledge Contracts

Knowledge Contracts define governed exchange agreements with external systems.

Examples:

- Docker Engine Contract
- Docker Compose Contract
- Filesystem Contract
- Git Contract
- REST Contract
- GraphQL Contract
- SQL Contract
- LDAP Contract
- SNMP Contract

A Knowledge Contract specifies:

- supported capabilities;
- exchanged information;
- semantics;
- version compatibility;
- limitations;
- trust assumptions;
- evidence provenance.

Knowledge Contracts describe **what an external system exposes**.

Interfaces describe **how AIStack components consume those capabilities**.

This separation allows AIStack to remain independent from technologies while depending only on explicit governed contracts.


## Everything AIStack Manages Is a Governed Item

Everything AIStack manages is a Governed Item.

AIStack does not define in advance the nature of managed entities.

Instead, it defines the governance model they must satisfy.

Any entity that complies with this governance model becomes a Governed Item and can participate in the Knowledge Operating System.

A Governed Item is therefore the fundamental abstraction of AIStack.

Examples include, but are not limited to:

- Evidence
- Observation
- Knowledge Asset
- Policy
- Recommendation
- ADR
- Documentation
- Runtime Event
- Technical Debt Item
- Catalog Entry

These are not independent concepts.

They are specialized Governed Items.

The architecture is therefore open by construction.

New categories of entities can appear over time without requiring any architectural redesign.

Specialization is a consequence of governance, not the opposite.

Governance precedes specialization.

This recursive definition deliberately avoids defining in advance what AIStack governs.

Instead, AIStack governs every entity that satisfies its governance model.


## Separate Domains from Capabilities

The Knowledge Operating System distinguishes two complementary architectural concepts.

### Domains

Domains represent the stable concepts of the knowledge model.

They define what AIStack fundamentally understands.

Examples include:

- Governed Item
- Evidence
- Observation
- Knowledge
- Governance
- Contracts
- Kernel

Domains evolve slowly because they represent the ontology of the Knowledge Operating System.

### Capabilities

Capabilities are the services provided by the Knowledge Operating System.

They manipulate Governed Items but do not define them.

Examples include:

- Acquisition
- Normalization
- Correlation
- Selection
- Generation
- Rendering
- Search
- Export
- Inference

Capabilities can evolve, be replaced, optimized or specialized independently from the knowledge model.

### Architectural Principle

Domains define the semantics.

Capabilities define the behavior.

A capability never owns the knowledge model.

Instead, it operates on Governed Items defined by the domains.

This separation preserves long-term architectural stability while allowing continuous evolution of the system capabilities.


## Architecture Is Built from Domains and Capabilities

The architecture of the Knowledge Operating System is built from two complementary dimensions:

- Domains
- Capabilities

### Domains

Domains define what the system fundamentally understands.

They represent the stable ontology of the Knowledge Operating System.

Domains should evolve slowly.

### Capabilities

Capabilities define what the system knows how to do.

They operate on Governed Items exposed by the Domains.

Capabilities are expected to evolve continuously.

### Architectural Matrix

Every architectural component belongs to one Domain and may participate in one or more Capabilities.

This separation guarantees that:

- the knowledge model remains stable;
- system behavior can evolve independently;
- new capabilities can appear without redesigning the knowledge model;
- new domains can be introduced without rewriting existing capabilities.

This principle maximizes long-term maintainability, extensibility and portability.

