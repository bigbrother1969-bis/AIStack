---
artifact:
  id: ARCH-0006
  title: Knowledge Providers
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.1
  status: Draft
  owner: Architecture
  created: 2026-07-08
  updated: 2026-09-23
---

# ARCH-0006 — Knowledge Providers

## Purpose

This document describes the Knowledge Provider model.

## Responsibility

A Knowledge Provider collects governed raw observations from an external source.

Providers do not decide, interpret or recommend.

## Current Providers

Measured 2026-09-23 from the Context Bundle's `contract-inventory.json` and
`registry-inventory.json` (projection of `71c1588`): thirteen classes satisfy
the `Provider` contract. Two are registered in the Kernel's
`ProviderRegistry` by `kernel/bootstrap/providers.py`. The other eleven are
instantiated directly by the commands that use them.

| Provider | Package | Registered in the Kernel |
|---|---|---|
| `DockerProvider` — observes the local Docker runtime | `providers.docker` | yes (`docker`) |
| `ComposeProvider` — derives Docker Compose project observations from Docker runtime labels | `providers.compose` | yes (`compose`) |
| `BeszelProvider` | `providers.beszel` | no |
| `BackupProvider` | `providers.filesystem` | no |
| `MediaLibraryProvider` | `providers.filesystem` | no |
| `StorageProvider` | `providers.filesystem` | no |
| `NvidiaGpuProvider` | `providers.gpu` | no |
| `HostProvider` | `providers.host` | no |
| `HttpProbeProvider` | `providers.http_probe` | no |
| `JellyfinProvider` | `providers.jellyfin` | no |
| `NetworkDockerDiscoveryProvider` | `providers.network_docker` | no |
| `NextcloudProvider` | `providers.nextcloud` | no |
| `SyncthingProvider` | `providers.syncthing` | no |

Whether the eleven should be registered, as `ARCH-0007` § *Discovery Model*
describes, is an open decision: `GOV-0002/OS-068`.

## Future Providers

- GitRepositoryProvider
- DocumentationProvider
- RuntimeProvider
- OllamaProvider

*Corrected 2026-09-23, `GOV-0002/OS-067`. § Current Providers listed
`DockerProvider` and `ComposeProvider` only, and § Future Providers listed
`FilesystemProvider`. Filesystem observation exists as three providers under
`aistack.providers.filesystem`, so the name left that list.*

## Principle

Providers produce evidence.

The Runtime and governed rules transform evidence into knowledge.
