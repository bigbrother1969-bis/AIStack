
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
