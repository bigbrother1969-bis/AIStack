---
artifact:
  id: ADR-0007
  title: Context Bundle Transfer Capability
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  status: Accepted
  owner: Architecture
---

# ADR-0007 - Context Bundle Transfer Capability

## Status

Accepted

## Context

AIStack generates Context Bundles containing governed knowledge artifacts.

The bundle is the portable representation of the AIStack knowledge heritage.

A generated bundle must not remain limited to the machine that produced it.
Knowledge portability and Self-Onboarding require the ability to automatically
transfer the generated context to another trusted environment.

Historically, file transfer was considered an operational task performed
manually by an operator.

This approach does not satisfy AIStack principles:

- Knowledge is portable.
- Knowledge is transferable.
- Self-Onboarding is a core capability.
- Generated artifacts must be usable by another environment.

## Decision

Introduce a dedicated Context Bundle Transfer capability.

The generation pipeline becomes:

```
ContextBundleService
        |
        v
ContextBundleEngine
        |
        v
BundleExportManager
        |
        v
Context Bundle Artifact
        |
        v
BundleTransferManager
        |
        v
Target Environment
```

The transfer operation is an explicit architecture component.

It is not implemented as a hidden shell command inside exporters.

## Responsibilities

### BundleTransferManager

Responsible for:

- transferring generated bundles;
- transferring bootstrap documentation;
- validating transfer success;
- reporting transfer status.

It does not:

- generate knowledge;
- classify artifacts;
- modify the bundle content.

## Configuration

Transfer targets must be configurable.

No environment-specific path must be hardcoded.

Configuration may be provided through:

- configuration files;
- environment variables;
- runtime configuration.

## Rationale

This decision enables:

- automated knowledge propagation;
- reproducible onboarding;
- portable AIStack environments;
- explicit and testable transfer workflows.

## Principles Applied

- Knowledge is portable.
- Knowledge is transferable.
- Self-Onboarding.
- Architecture before implementation.
- Tests are mandatory at every layer.
- The code is a Knowledge Artifact.
