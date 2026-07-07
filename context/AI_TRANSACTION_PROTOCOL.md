# AI Transaction Protocol

This document defines how an AI model shall generate executable engineering transactions for AIStack.

It is a governed knowledge artifact and part of the AIStack Knowledge Operating System.

---

# Transaction Principle

Every modification proposed by the AI shall be treated as a governed transaction.

A transaction shall be:

- atomic;
- complete;
- reproducible;
- executable as-is;
- self-contained;
- deterministic.

---

# Transaction Lifecycle

A transaction shall follow this lifecycle:

1. Repository context
2. Artifact generation or modification
3. Validation
4. Git staging
5. Commit
6. Push

---

# Repository Context

Before generating any command sequence, the AI shall determine the project root.

Command sequences shall always be self-contained and begin by changing to the appropriate repository when required.

The AI shall never assume that the current working directory is correct.

---

# File Update Strategy

The AI shall select the most appropriate update strategy.

- New file → create the file.
- Small addition → append.
- Targeted modification → modify only the required section.
- Complete rewrite → only when explicitly requested or when safer than incremental editing.

The AI shall preserve existing governed content whenever possible.

---

# Atomic Command Blocks

Executable command sequences shall be generated as independent atomic blocks.

No explanatory text, comments, or additional commands shall be embedded inside file generation blocks.

Every generated file shall be delimited by a single opening and closing EOF marker.

Git commands shall always appear after file generation blocks.

The AI shall ensure that executable command sequences cannot accidentally corrupt generated artifacts through mixed content.

---

# Command Validation

Before proposing any command sequence that modifies governed project artifacts, the AI shall mentally validate the complete sequence.

The validation shall verify at least:

- repository context;
- execution order;
- syntax consistency;
- required dependencies;
- target files and directories;
- expected side effects;
- correct EOF block closure;
- Git commands placed outside file generation blocks.

The AI shall only propose command sequences that are complete, coherent, and executable without requiring manual reconstruction.
