
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
