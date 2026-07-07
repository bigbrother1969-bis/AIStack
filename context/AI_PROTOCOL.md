# AI Collaboration Protocol

This document defines how an AI model shall collaborate with the user on AIStack.

It is a governed knowledge artifact and part of the AIStack Knowledge Operating System.

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

---

# File Update Strategy

The AI shall select the most appropriate update strategy.

- New file → create the file.
- Small addition → append.
- Targeted modification → modify only the required section.
- Complete rewrite → only when explicitly requested or when safer than incremental editing.

The AI shall preserve existing governed content whenever possible.

---

# Command Validation

Before proposing any command sequence that modifies governed project artifacts, the AI shall mentally validate the complete sequence.

The validation shall verify at least:

- repository context;
- execution order;
- syntax consistency;
- required dependencies;
- target files and directories;
- expected side effects.

The AI shall only propose command sequences that are complete, coherent, and executable without requiring manual reconstruction.

---

# Continuous Protocol Improvement

The AI Collaboration Protocol is a governed artifact.

Whenever a collaboration issue is identified and a better practice is validated, the protocol shall be updated accordingly.

The objective is to ensure that the same issue is not repeated in future sessions.

The protocol evolves through explicit validation and governed improvements.

---

# Protocol Governance

The AI Collaboration Protocol is itself a governed knowledge artifact.

It shall evolve according to the same engineering principles as the AIStack project.

The protocol is not a prompt.

It is a governed component of the Knowledge Operating System.

---

# Atomic Command Blocks

Executable command sequences shall be generated as independent atomic blocks.

No explanatory text, comments, or additional commands shall be embedded inside file generation blocks.

Every generated file shall be delimited by a single opening and closing EOF marker.

Git commands shall always appear after the file generation block.

The AI shall ensure that executable command sequences cannot accidentally corrupt generated artifacts through mixed content.

---

# AI Transactions

Every modification proposed by the AI shall be treated as a governed transaction.

A transaction shall follow this lifecycle:

1. Repository context
2. Artifact generation or modification
3. Validation
4. Git staging
5. Commit
6. Push

The AI shall generate complete transaction sequences whenever possible.

A transaction shall be atomic, reproducible, and executable without manual reconstruction.

---

# Transaction Validation

Before ending a transaction, the AI shall mentally verify that:

- the repository context is correct;
- every generated file is syntactically complete;
- every EOF block is correctly closed;
- Git commands are placed outside file generation blocks;
- the complete transaction can be executed from top to bottom without modification.

The AI shall never intentionally generate incomplete or interleaved transactions.

