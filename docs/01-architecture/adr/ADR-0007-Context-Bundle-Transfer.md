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
  version: 1.2
  created: 2026-07-24
  updated: 2026-08-28
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

## Implementation state

Measured 2026-08-27.

| Step | State |
|---|---|
| Transfer is an explicit component, not a shell command hidden inside an exporter | done — 2026-08-27 |
| `BundleTransferManager`, the component § *Decision* names | superseded — 2026-08-28 |
| transferring generated bundles | done — 2026-08-27 |
| transferring bootstrap documentation | done — 2026-08-27 |
| validating transfer success and reporting status | done — 2026-08-27 |
| configuration without hardcoded paths | done — 2026-08-27 |

What each was read against:

| Step | Evidence |
|---|---|
| explicit component | `context_bundle/transfer/` — a contract per role, `SshBundleTransfer` and `FileSystemBundleTransfer` as implementations. It still runs `scp`, and that is not what the decision forbade: what it forbade is a shell command *hidden inside an exporter*. |
| bundles | `DefaultContextBundleService.generate` calls the transfer service after the bundle is built, and records the failure rather than raising through the generation |
| bootstrap documentation | `scripts/export_project_sources.py` transfers `README_OUTPUT` explicitly, after the bundle |
| validation and status | `transfer_error` is captured, printed, and the script **exits 2** — *bundle generated and valid, delivery did not complete* is a third state, distinct from success and from failure |
| configuration | `load_transfer_configuration` reads a file and environment variables, and **the variables win**, so no deployment target has to enter the governed heritage |

**The transfer path is inert in this repository**, measured 2026-08-27:
`config/context_bundle_transfer.yml` does not exist — only
`context_bundle_transfer.yml.example` — so the script skips the whole block.
That is the configuration rule working, and it means this path has never run
in the governed tree.

### The second row, qualified `superseded` on 2026-08-28

`BundleTransferManager` **exists nowhere**: no class, no module, no other
artifact carries the name. Its four responsibilities are met, spread across
`SshBundleTransfer`, `DefaultContextBundleService.transfer_error` and the
entry-point script.

The obvious reading is that the name was superseded by another decomposition.
The owner declined it on 2026-08-27 — **unqualified, to investigate** — because
the correction made the same day sharpened the question rather than answering
it, and **accepted it on 2026-08-28** once the investigation was done.

What the investigation found, measured 2026-08-28 across the repository:

```text
ContextBundleTransferService
  SshBundleTransfer                     1 production caller — scripts/export_project_sources.py
  DefaultContextBundleTransferService   0 production callers, tests only
BundleTransferManager                   no class, no module, no artifact
```

Two implementations of the orchestration contract: `SshBundleTransfer`, which
holds a configuration and no policy, and `DefaultContextBundleTransferService`,
which holds a policy and delegates to a `BundleTransfer`. The second is the
decomposition this decision describes, and the first is the one that runs.

**`superseded` is what that supports and nothing more.** The role the decision
names is carried by a contract under another name; which class occupies it is a
question about consumers, not about whether this step was taken. Same shape as
ADR-0008's *Adapters* row, qualified the same day and for the same reason: the
substance exists, the name does not, and a decision that got its substance is
not unfinished.

*What `superseded` does not say: that the orchestration is settled.
`DefaultContextBundleTransferService` has no production caller, which is the
condition GOV-0002/OS-039 records for the Selection Engine and is not a row of
this table — this decision commits to the transfer being an explicit component,
not to which of two components the export script picks.*

## Principles Applied

- Knowledge is portable.
- Knowledge is transferable.
- Self-Onboarding.
- Architecture before implementation.
- Tests are mandatory at every layer.
- The code is a Knowledge Artifact.
