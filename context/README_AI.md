# AI Bootstrap

Welcome to the AIStack project.

This document is the bootstrap protocol for any AI model working on AIStack.

It explains how to use the governed knowledge contained in the Context Bundle.

The Context Bundle is the shared knowledge heritage of the project.

Always read this document before using any other artifact.

---

# Governing Principles

- All governed knowledge artifacts shall be written in English.
- Human conversations may use any language.
- The Context Bundle is the reference context shared across AI sessions.
- The latest Context Bundle supersedes all previous versions.
- The Git repository hosted on Gitea is the Single Point Of Truth (SPOT).
- GitHub and Codeberg are publication mirrors.
- Never invent a new concept when an official one already exists in the project glossary.

---

# Working Protocol

When the user writes:

> "Gravé"

it means the proposal has been validated.

The AI shall then:

1. Identify the appropriate governed document.
2. Generate complete executable command sequences.
3. Preserve the official terminology.
4. Provide the required Git commands.
5. Never answer only with an acknowledgement.

---

# Command Generation Policy

The user shall never be expected to manually copy and paste text into project files.

Whenever a governed artifact must be created or modified, the AI shall generate complete executable command sequences.

This includes file creation, file updates, file appends, file replacements, directory creation, and Git operations.

Whenever possible, the AI shall generate complete shell commands rather than asking the user to manually edit files.

The objective is to eliminate typing errors, eliminate syntax errors, guarantee reproducibility, reduce cognitive load, and keep the workflow deterministic.

If a file already exists, the AI shall generate the appropriate update command rather than regenerating the entire file, unless a complete replacement has been explicitly requested.

Knowledge should be transmitted through deterministic executable commands rather than manual editing whenever possible.

---

# Engineering Principles

Always prioritize:

1. Understanding
2. Architecture
3. Governed Knowledge
4. Documentation
5. Implementation

Understanding is the cause.

Code is the consequence.

AIStack does not merely describe Governed Heritage Engineering.

It continuously proves it.

---

# Repository Context

Before generating any command sequence, the AI shall determine the project root.

Command sequences shall always be self-contained and begin by changing to the appropriate repository when required.

The AI shall never assume that the current working directory is correct.


---

# Command Completeness

Every generated command sequence shall be:

- complete;
- executable as-is;
- deterministic;
- self-contained.

The AI shall never generate partial command sequences requiring manual reconstruction.

Command sequences shall be verified for syntactic consistency before being proposed.

