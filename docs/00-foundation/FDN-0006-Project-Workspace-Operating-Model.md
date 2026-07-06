---
artifact:
  id: FDN-0006
  title: Project Workspace Operating Model
  type: Foundation Document
  version: 1.0
  status: Published
  owner: Foundation

lifecycle:
  created: 2026-07-06
  updated: 2026-07-06

relations:
  references:
    - FDN-0005
    - STD-0100
    - CMP-0001
---

# FDN-0006 — Project Workspace Operating Model

## Purpose

This document defines how AIStack Project Workspaces collaborate.

Its objective is to organize engineering work into specialized workspaces while preserving a single governed knowledge heritage.

---

# Principles

Project Workspaces are collaborative engineering spaces.

They are not the Single Point Of Truth.

The Git repository remains the unique canonical source of knowledge.

---

# Workspace Responsibilities

Each workspace owns a responsibility.

A workspace never owns the knowledge itself.

Validated knowledge is always published into the Governed Heritage.

---

# Official Workspaces

## 00 — Foundation

Responsibilities:

- vision;
- principles;
- constitution;
- governance;
- standards;
- project operating model.

Produces:

Foundation Knowledge Artifacts.

---

## 01 — Documentation

Responsibilities:

- Knowledge Artifacts;
- documentation standards;
- changelog;
- release notes;
- Context Bundles.

Produces:

Governed documentation.

---

## 02 — Governed Heritage Engineering

Responsibilities:

- methodology;
- engineering principles;
- reusable patterns;
- validation of the approach.

Produces:

Methodological knowledge.

---

## 03 — Design

Responsibilities:

- architecture;
- conceptual models;
- user experience;
- interaction design.

Produces:

Architectural artifacts.

---

## 04 — Development

Responsibilities:

- implementation;
- generators;
- APIs;
- Docker;
- automation;
- testing.

Produces:

Software components.

---

## 05 — Bugs

Responsibilities:

- investigations;
- regressions;
- fixes;
- incident analysis.

Produces:

Corrective knowledge.

---

## 06 — Ideas

Responsibilities:

- exploration;
- innovation;
- brainstorming.

Ideas remain provisional until validated.

Produces:

Candidate Knowledge Artifacts.

---

## 07 — Roadmap

Responsibilities:

- planning;
- priorities;
- Open Work Items;
- releases;
- engineering sprints.

Produces:

Project planning artifacts.

---

## 08 — Literature

Responsibilities:

- books;
- articles;
- conferences;
- public communication.

Produces:

Editorial knowledge.

---

## XX — Roast Me

Responsibilities:

- challenge assumptions;
- identify blind spots;
- simplify architecture;
- detect inconsistencies.

Produces:

Critical review.

---

# Knowledge Flow

```text
Ideas
    │
    ▼
Foundation
    │
    ▼
Design
    │
    ▼
Development
    │
    ▼
Documentation
    │
    ▼
Roadmap
    │
    ▼
Release
```

Bug investigations feed Development.

Roast Me may challenge any workspace.

---

# Governed Heritage

Validated knowledge follows the same lifecycle.

```text
Discussion

↓

Validation

↓

Publication in Git

↓

Context Bundle Generation

↓

ChatGPT Project Sources

↓

Workspace Synchronization
```

Git remains the Single Point Of Truth.

Context Bundles distribute governed knowledge.

---

# Workspace Rules

A workspace owns a responsibility, not a topic.

Topics may span several workspaces.

Knowledge moves between workspaces through validated Knowledge Artifacts.

---

# Project Synchronization

Every workspace receives the same governed knowledge through Context Bundles.

No workspace should maintain its own private version of canonical knowledge.

---

# Related Artifacts

- FDN-0005 — Project Operating Model
- STD-0100 — Documentation Standard
- CMP-0001 — Context Bundle Generator
