# Architecture consolidation — tracked debt

*Working note. Not governed knowledge: `docs/99-meta` is excluded from the
projection. This file exists so that a debt announced by three governed
documents does not disappear with the line that announced it.*

## What was removed, and why this file exists

Until 2026-08-21, `ARCH-0009`, `ARCH-0010` and `ARCH-0011` each carried a
prose `## Status` block declaring:

```
-   Status: Validated concept --- Pending architecture consolidation
```

while their frontmatter declared `status: Accepted`. Two statuses in one
document, contradicting each other, in three C1/C2 architecture documents.
The blocks also restated `criticality`, which the frontmatter already
carried — a second source for a fact that has one.

The owner decided on 2026-08-21 that the frontmatter is authoritative and
the prose blocks go. The three documents are `Accepted`: they are valid as
written.

What the removed line carried that the frontmatter does not is this note's
subject: **the three of them were written as concepts awaiting a
consolidation that has never been defined.**

## What "consolidation" is not known to mean

Nothing in the heritage says. The phrase appears in three documents and
nowhere else — not in an ADR, not in a roadmap, not in the registry.

That is the debt. It is not "these documents are wrong"; it is "three
documents announce a future act that nobody has specified, and they have
done so since they were written."

## What would close it

An ADR that answers three questions:

- what is being consolidated — the three concept documents into one, or the
  concepts into the ARCH series proper, or something else;
- what changes for a reader if it happens;
- whether it is still wanted at all. A pending act nobody has defined in a
  month may simply be a sentence that outlived its intention.

Until that ADR exists, the debt is here rather than in the governed
heritage, because a debt with no definition is not knowledge.

## Related

- `ARCH-0009` — Library Architecture Analogy (C1)
- `ARCH-0010` — Macro-Architecture (C2)
- `ARCH-0011` — Kernel Registry System (C2)
- `claude/SESSION-2026-08-21-continued.md` — how it surfaced
