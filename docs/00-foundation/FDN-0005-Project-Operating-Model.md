---
artifact:
  id: FDN-0005
  title: Project Operating Model
  type: Foundation Document
  semantic_type: Knowledge Artifact
  domain: Foundation
  confidence: Declared
  criticality: C3
  version: 1.2
  status: Published
  owner: Foundation
  created: 2026-07-06
  updated: 2026-08-27

relations:
  references:
    - FDN-0002
    - FDN-0003
    - FDN-0004
    - STD-0001
---

# AIStack Project Operating Model

## Purpose

This document defines how the AIStack project is organized and operated.

It is the reference onboarding guide for every contributor.

It describes the project organization, the knowledge lifecycle and the collaboration model.

The objective is to ensure that every contributor works consistently with the Governed Heritage.

See also:

- Constitution
- Foundation Glossary
- Governed Heritage

---

# Vision

AIStack is developed according to the principles of Governed Heritage Engineering.

The primary objective is not to produce software.

The primary objective is to build, govern, distribute and exploit the Governed Heritage of Digital Ecosystems.

Software is one of the artifacts produced by this process.

---

# Project Organization

The project is organized into specialized Workspaces.

Each Workspace has a clearly defined responsibility.

Knowledge flows between Workspaces through governed publication.

The Git repository is the Single Point of Truth.

---

# Workspaces

## Foundation

Mission

Govern the long-term principles of AIStack.

Responsibilities

- Constitution
- Glossary
- Principles
- Governed Heritage
- Engineering philosophy

---

## Documentation

Mission

Transform validated knowledge into canonical Knowledge Artifacts.

Responsibilities

- official documentation
- reference documents
- publication quality
- consistency

---

## Governed Heritage Engineering

Mission

Develop the methodology independently from AIStack.

Responsibilities

- concepts
- philosophy
- terminology
- research
- validation of emerging concepts

---

## Design

Mission

Design the architecture of AIStack components.

Responsibilities

- architecture
- interfaces
- responsibilities
- ADR preparation

---

## Development

Mission

Implement validated architecture.

Responsibilities

- implementation
- configuration
- testing
- packaging

Development never redefines Foundation concepts.

---

## Bugs

Mission

Analyze incidents and improve the Governed Heritage.

A bug is considered an opportunity to improve understanding.

---

## Ideas

Mission

Explore new concepts before governance.

Ideas are not official knowledge.

---

## Roadmap

Mission

Plan the evolution of AIStack.

---

## Literature

Mission

Make Governed Heritage Engineering understandable and transmissible.

---

## Roast Me

Mission

Challenge assumptions and reveal weaknesses.

Its purpose is to improve the quality of the Governed Heritage.

---

## Experimentation

Mission

Run proofs of concept outside the projection, and integrate them
when they are ready.

**The practice is deliberate.** Work that is not yet knowledge is
carried out in a space of its own, and enters the heritage by
being written as a Knowledge Artifact — never by being found
there. `docs/99-meta/roadmap/` holds intentions and is not this:
an experiment produces measurements, an intention produces none.

Two campaigns have been run this way. Both produced a governed
decision **after** the fact rather than under a rule, which is
what this section corrects (GOV-0002/OS-022).

### How a proof of concept is referred to

An experiment carries an identifier and a state, and both may be
cited by the heritage before it is complete. A campaign that is
technically finished and awaiting human evaluation is a fact about
the project; citing it as *pending* states more than silence does,
and FDN-0003 Article 12 makes an undeclared state a governed one.

**QUAL-0001** — a 64-test qualification of local language models
against four levels of governed context — is complete in execution
and pending in evaluation as of 2026-08-27. It is cited here so
that it can be cited anywhere.

### What this section does not decide

The states a proof of concept passes through, the criteria that
make one integrable, and who decides. Two observed cases justify
declaring that the practice exists; they do not justify fixing its
procedure in advance. When a third case shows what the rule should
be, it will be written — and this paragraph is the record that it
was deliberately left open on 2026-08-27.

---

# Knowledge Lifecycle

Knowledge follows an explicit lifecycle.

Idea

↓

Discussion

↓

Validated

↓

Emerging Concept

↓

Real-world Usage

↓

Foundation Review

↓

Gravé

↓

Published

↓

Distributed

↓

Consumed

↓

Improved

Every stage is governed.

---

# Publication Workflow

Conversations are working environments.

They are not the official source of knowledge.

The publication workflow is:

Discussion

↓

Validation

↓

Publication into Git

↓

Context Bundle Generation

↓

Project Sources

↓

Workspace Consumption

---

# Git Repository

The Git repository is the official Single Point of Truth.

Every canonical Knowledge Artifact is stored and versioned there.

Knowledge is never published directly into conversations.

## The ancestor

AIStack has a predecessor repository, backed up on 2026-08-22 as
`aistack-origin`. It holds the source of the experimenter that
preceded this project, built three days before this repository's
first commit, and it contains this repository as a subdirectory —
which is why the question of which one is the product was open,
and defensible either way.

**This repository is the product. The ancestor is an archive.**
Decided by the owner on 2026-08-23 (GOV-0002/OS-013).

The consequence is that whatever still lives in the ancestor
migrates here or ends there, and that `aistack-origin` is a
permanent backup rather than a second line of development. The
migration of its function is decided separately, in ADR-0009.

*Named by its repository rather than by its path on any machine.
A filesystem location is a route, and this document describes a
product rather than a host — the same boundary ADR-0009 § 7.2
draws for the expected state of a deployment.*

---

# Heritage Views

Different consumers require different views of the Governed Heritage.

Examples:

- ChatGPT
- Claude
- Developer Workspace
- Public Documentation

A Heritage View contains only the knowledge required by its consumer.

---

# Context Bundles

A Context Bundle is a generated representation of a Heritage View.

Bundles are generated artifacts.

Bundles are never edited manually.

If a bundle is incorrect, the canonical Knowledge Artifacts or the generation process must be corrected.

---

# Contribution Rules

Every contribution shall follow this sequence:

Understand

↓

Discuss

↓

Validate

↓

Document

↓

Publish

↓

Implement

Implementation never precedes understanding.

---

# Vocabulary

Validated

The idea has been accepted.

Gravé

The idea shall become part of the official Governed Heritage.

Published

The canonical Knowledge Artifact has been updated in the Git repository.

Distributed

Updated Heritage Views have been generated.

---

# Daily Workflow

The daily workflow is intentionally simple.

1. Discuss within the appropriate Workspace.
2. Validate ideas.
3. Publish canonical knowledge into Git.
4. Generate updated Context Bundles.
5. Update Project Sources.
6. Continue working from the updated shared knowledge.

---

# Long-Term Vision

The long-term objective is Self-Onboarding.

Any human or AI contributor should be able to join the project by reading the Governed Heritage without requiring prior knowledge.

This capability is one of the defining characteristics of Governed Heritage Engineering.
