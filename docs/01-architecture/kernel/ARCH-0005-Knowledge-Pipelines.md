---
artifact:
  id: ARCH-0005
  title: Knowledge Pipelines
  type: Architecture Document
  semantic_type: Knowledge Artifact
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Architecture
  created: 2026-07-08
  updated: 2026-08-21
---

# ARCH-0005 — Knowledge Pipelines

## Purpose

This document describes the Knowledge Pipeline architecture.

## Definition

A Knowledge Pipeline is an executable governed chain that transforms observations into governed Knowledge Artifacts.

## Standard Flow

Provider
  -> Observation
  -> Runtime Catalog
  -> Artifact Generator
  -> Knowledge Artifact

## Current Pipelines

- Docker Runtime Pipeline
- Compose Runtime Pipeline

## Contract

A pipeline exposes a pipeline identifier, a pipeline name and a deterministic run operation.

## Principle

Pipelines make knowledge production executable, repeatable and governable.
