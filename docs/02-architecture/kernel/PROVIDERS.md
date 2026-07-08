# Knowledge Providers

## Purpose

This document describes the Knowledge Provider model.

## Responsibility

A Knowledge Provider collects governed raw observations from an external source.

Providers do not decide, interpret or recommend.

## Current Providers

- DockerProvider: observes the local Docker runtime.
- ComposeProvider: derives Docker Compose project observations from Docker runtime labels.

## Future Providers

- FilesystemProvider
- GitRepositoryProvider
- DocumentationProvider
- RuntimeProvider
- OllamaProvider

## Principle

Providers produce evidence.

The Runtime and governed rules transform evidence into knowledge.
