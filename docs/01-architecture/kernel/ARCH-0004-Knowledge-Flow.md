---
artifact:
  id: ARCH-0004
  title: Knowledge Flow
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

# ARCH-0004 — Knowledge Flow

## Purpose

This document describes the deterministic knowledge flow of the AIStack Kernel.

## Flow

Observation
  -> Catalog
  -> Catalog View
  -> Selection
  -> Policy Evaluation
  -> Knowledge Artifact
  -> Human Validation
  -> Assisted Action

## Source Of Truth

Generated artifacts are derived from governed sources.

Git remains the Single Point Of Truth for the governed project heritage.

## AI Integration

AI engines reason on governed knowledge produced by the deterministic Runtime.

AI engines never replace governed knowledge.

## Principle

Knowledge is produced before AI reasoning.
