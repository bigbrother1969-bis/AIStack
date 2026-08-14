
# P2 — Knowledge Time Machine

Concevoir l’historisation multi-orthogonale d’AIStack.

AIStack ne doit pas conserver un seul historique, mais quatre historiques orthogonaux :

1. Knowledge Heritage History
2. Observation History
3. Runtime Operation History
4. AI Reasoning History

Objectif final : reconstruire fidèlement l’état complet du patrimoine gouverné, du système observé, des traitements exécutés et des raisonnements IA à n’importe quel instant du passé.


## Validation Use Cases

Moved out of this note.

The official validation suite is now a governed specification:
**STD-0300 — Official Validation Suite**
(`docs/02-standards/validation/STD-0300-Official-Validation-Suite.md`).

It is the single point of truth for what AIStack must demonstrate.

---

## P2 — Adaptive Resource Scheduler

### Objectif

Concevoir un moteur de gouvernance des ressources capable d'adapter dynamiquement les ressources CPU allouées aux conteneurs en fonction de la charge observée et des politiques définies.

### Fonctionnalités

- Observation continue de la charge CPU des conteneurs.
- Détection des traitements exceptionnels (indexation, OCR, IA, sauvegardes, migrations…).
- Réallocation dynamique des CPU (cpuset, quotas Docker ou équivalent).
- Priorisation des services critiques.
- Garantie d'un minimum de ressources par service.
- Retour automatique à une allocation nominale après le pic de charge.
- Historisation de toutes les décisions.

### Contraintes

- Éviter les oscillations.
- Éviter toute famine de ressources.
- Respecter les politiques de gouvernance.
- Garantir la stabilité de l'infrastructure pendant les réallocations.
- Toutes les décisions doivent être explicables.

### Cas de validation

Lors d'une reconstruction d'index Immich (OCR, reconnaissance faciale, embeddings…), AIStack détecte le besoin temporaire de puissance, augmente automatiquement les ressources CPU du conteneur concerné, puis restitue ces ressources une fois le traitement terminé.

### Évolution

À terme, généraliser ce moteur en **Resource Governance Engine** afin de gouverner également :

- CPU
- Mémoire
- GPU
- I/O disque
- Bande passante réseau
- Consommation énergétique


## Next Architecture Migration

Priority P0

- create Evidence contracts;
- create Collector contracts;
- create Normalizer contracts;
- create Correlation contracts;
- create Collector Registry;
- create Normalizer Registry;
- create Correlation Registry;
- migrate Docker Provider incrementally.

# P0 — Knowledge Operating System Bootstrap

The theoretical foundations are now considered stable enough to start the first implementation of the Knowledge Operating System.

Implementation shall follow the validated engineering methodology:

Architecture
→ Domains
→ Capabilities
→ Contracts
→ Implementation
→ Packaging

Packaging must remain a consequence of validated concepts, never the starting point.

## Phase 1 — Governed Item

- [ ] feat(item): introduce Governed Item domain
- [ ] define core interfaces
- [ ] define metadata model
- [ ] define lifecycle model
- [ ] introduce registry

## Phase 2 — Evidence

- [ ] feat(evidence): introduce Evidence domain
- [ ] define Evidence specialization
- [ ] define EvidenceCollector interfaces

## Phase 3 — Knowledge Acquisition

- [ ] feat(capability): introduce Acquisition capability
- [ ] create first acquisition pipeline
- [ ] migrate first Docker collector

## Phase 4 — Validation

- [ ] validate Domain / Capability architecture
- [ ] evaluate package organization
- [ ] migrate package layout only if the architecture naturally confirms it

