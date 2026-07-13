
# P2 — Knowledge Time Machine

Concevoir l’historisation multi-orthogonale d’AIStack.

AIStack ne doit pas conserver un seul historique, mais quatre historiques orthogonaux :

1. Knowledge Heritage History
2. Observation History
3. Runtime Operation History
4. AI Reasoning History

Objectif final : reconstruire fidèlement l’état complet du patrimoine gouverné, du système observé, des traitements exécutés et des raisonnements IA à n’importe quel instant du passé.


## Validation Use Case — Development Mode Energy Waste

### Question

How can AIStack detect and eliminate unnecessary resource consumption?

### Observed incident

The permanent `aistack-selection-ui` service consumed approximately 50% of one CPU core while idle.

Evidence:
- no incoming HTTP requests;
- no active browser session;
- continuous filesystem traversal;
- Uvicorn started with `--reload`;
- the complete Git repository mounted into `/app`.

System-call observation showed repeated `newfstatat`, `getdents64`, `openat` and `fstat` calls.

### Root cause

The development-only Uvicorn reload mechanism continuously monitored the mounted repository.

### Remediation

Remove `--reload` from the permanent container command and rebuild the image.

Observed result:
- before: approximately 48–58% of one CPU core;
- after: approximately 0.2% CPU while idle.

### AIStack validation objective

AIStack shall be able to:
1. detect abnormal idle resource consumption;
2. correlate the process, container and deployment definition;
3. identify development options enabled in a permanent service;
4. collect technical evidence;
5. classify the issue as technical debt, deployment misconfiguration, energy inefficiency and sustainability anomaly;
6. explain the root cause;
7. recommend a safe remediation;
8. verify the improvement after remediation.

### Expected workflow

```text
Runtime Observation
        ↓
Process and Container Correlation
        ↓
Deployment Configuration Analysis
        ↓
Knowledge Policies
        ↓
Technical Debt Evaluation
        ↓
Sustainability Score
        ↓
Explainable Recommendation
        ↓
Human Validation
        ↓
Remediation
        ↓
Before / After Verification
```

This use case validates that technical debt is derived knowledge produced from observations, evidence and explicit policies rather than a subjective opinion.

## Validation Use Case — Official Validation Suite

The following scenarios constitute the first official validation suite of AIStack.

### 1. Docker Runtime Discovery

Objective:

Demonstrate that AIStack can automatically discover, model and document a Docker infrastructure.

Validated capabilities:

- Runtime observation
- Knowledge Catalog generation
- Artifact generation
- Infrastructure explanation

---

### 2. Context Bundle / Self-Onboarding

Objective:

Demonstrate that AIStack can transmit its governed knowledge to another AI instance.

Validated capabilities:

- Context Bundle generation
- PROJECT-CONTEXT
- NEXT-SESSION-TODO
- Knowledge transfer
- Self-Onboarding

---

### 3. Music Sync Selection Pipeline

Objective:

Demonstrate that the same Runtime architecture can orchestrate a business process rather than infrastructure only.

Validated capabilities:

- Selection Pipeline
- Catalog
- Artifact generation
- User interaction
- Regeneration

---

### 4. Sustainability & Technical Debt Analysis

Objective:

Demonstrate that AIStack can derive technical debt and sustainability issues from runtime observations.

Reference incident:

The Selection UI permanently consumed approximately 50% of one CPU core because Uvicorn was started with the development option `--reload`.

AIStack must be able to:

- observe the anomaly;
- correlate process, container and deployment;
- identify the root cause;
- explain the reasoning;
- recommend the correction;
- verify the effectiveness of the remediation.

Measured result:

- before: approximately 48–58% CPU;
- after: approximately 0.2% CPU.

This validation demonstrates one of the core principles of Governed Heritage Engineering:

> Technical debt is not an opinion.
> It is derived knowledge produced from observations, evidence and explicit policies.


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

