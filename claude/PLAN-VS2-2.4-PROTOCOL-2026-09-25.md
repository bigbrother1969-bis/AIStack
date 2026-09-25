# VS-2.4 — Protocol for a Cross-Model Run

**Status: project working note, not governed heritage.** `STD-0300` § *Responsibilities*
states the specification does not own "how any scenario is implemented" — this
document is the how, kept in `claude/` for the same reason every other
session record is: no owner, no version, disposable under `ENG-P-003`.

**Supersedes**, for future runs, the procedure implied by
`claude/VS2-2.4-SYNTHESE-POINTS-2026-09-23.md`'s original point 13. That
synthesis compared two Boot Reports by reading them side by side — the
interactive judgement `STD-0300` § 8 excludes from a criterion. Criterion 2.4
was reworded 2026-09-25 (`GOV-0002/OS-071`) to a mechanically checkable form,
and this protocol is how to run it.

---

## 1. What 2.4 now asks

> Two agents of different models each cover the canonical set of declared
> unknowns (`FDN-0003` Article 12), add nothing `GOV-0002` already qualifies,
> and reach the same READY verdict.

Three things to check per run, not one:

1. **Coverage** — each agent's own Boot Report states, in its own words, the
   condition every line in the canonical set below points at. Paraphrase is
   fine; omission is not.
2. **No manufactured unknowns** — neither Boot Report flags as open a
   condition `GOV-0002`'s *Resolved* section already closes. An agent that
   re-opens a closed point fails this leg even if it also achieves coverage.
3. **Same verdict** — both Boot Reports reach the same READY / NOT READY
   conclusion.

## 2. The canonical set

Run the `declared-unknowns` integrity check (`GOV-0002/OS-071`,
`src/aistack/integrity/checks/declared_unknowns.py`) against a freshly
regenerated Context Bundle immediately before the run — not against the list
below, which is a snapshot taken 2026-09-25 for illustration and will drift
as the heritage changes:

```
python -m aistack.cli.knowledge_integrity
```

The check's own finding lists every line; read it once before scoring, the
same way `undated-assertions`' own docstring says a reader "scans twenty
lines and decides." Two kinds of line need to be told apart on that read,
by the same judgement `STD-0300` § 8 keeps out of the criterion and puts on
the person running it instead:

- **Substantive** — a condition about the world the receiving agent should
  itself be unable to resolve from the bundle alone (an unmeasured claim, an
  unresolved overlap, a `not verified` suite row).
- **Self-referential** — a line that names or explains the marker pattern
  itself (this document does that in section 1 above) rather than declaring
  an unknown. `undated-assertions` and `claude-note-references` already
  carry this same distinction; `declared-unknowns` inherits it rather than
  solving it, and its own docstring says so.

As of 2026-09-25 (source commit `ae23865`, 20 lines total), the substantive
subset an agent's Boot Report should be able to name is:

- `STD-0300` 2.4 itself: not verified (this run is what discharges it).
- `STD-0300` 4.1, 4.3, 4.6, 4.7: not verified (no idle-resource-consumption
  scenario has been run yet).
- `STD-0300` § 9 suite state: 5 of 22 criteria not verified.
- `OPS-0001` / `OPS-0003`: every container-log or lifecycle signature
  declares `grounding: unknown` — no fact yet speaks to which containers are
  who runs them.
- `GOV-0002` § *Numbering*: an early gap in the OS sequence, recorded as lost
  rather than reconstructed (`685bcc8`, 2026-08-01).
- `FDN-0009` § *Open Point*: read the artifact for current wording.
- `ARCH-0012` / `ARCH-0013` / `GOV-0001`: each carries an `Open Points`
  section — read it for current content, not this snapshot.

The remaining lines in a fresh run's output (design notes inside
`STD-0100`, `FDN-0010`, `FDN-0005`, `GOV-0002` that describe the pattern
rather than instantiate it) are not owed coverage; an agent is not penalised
for skipping them, and is not credited for reciting them either.

## 3. What "cannot decide" also covers — `OPS-0002`

One universal declared-unknown does not come from a bundle marker at all,
because it is a property of the transport, not the content: **a recipient
handed only the Context Bundle cannot reach anything outside it, and should
say so rather than assume** (`OPS-0002`, the freshness rule, itself an
application of `FDN-0003` Article 12 to the projection). Both Boot Reports
are expected to state this explicitly — that they are reasoning from a
projection of a given age and cannot independently confirm it against the
live repository — as part of coverage, alongside the bundle-text-derived
lines above. A Boot Report that states every marker line but never states
its own standing relative to the bundle has covered the letter of the
canonical set and missed what Article 12 is for.

## 4. Running it

1. Regenerate the bundle from current `main` (`scripts/export_project_sources.py`)
   and run `knowledge_integrity` to get the canonical set for that commit.
2. Start two fresh agents with no memory of this project or of each other:
   a new Claude conversation outside this session, and ChatGPT (or whichever
   second model is available). Give each **only** the Context Bundle — no
   chat history, no prior Boot Reports, no hints about what to look for.
   This is the same isolation `OPS-0002`'s freshness rule assumes; a run
   that leaks context between the two agents is not measuring what 2.4
   measures.
3. Each agent produces its own Boot Report independently.
4. Score each Boot Report against section 1's three legs, using the
   canonical set from step 1. Record which lines each report covers, which
   (if any) it manufactures, and its verdict.
5. Write the result as a dated session note (`claude/SESSION-<date>-vs2-2.4.md`
   or similar) — the run's outcome is provenance for whether `STD-0300` 2.4
   becomes `not verified` → verified, and belongs in `claude/` like every
   other run record, per `STD-0100`'s rule that a `claude/` citation is
   provenance and never the sole statement of the fact.
6. If 2.4 passes, update `STD-0300` § 9's suite-state count and `GOV-0002`
   accordingly — a governed-heritage change, so it goes through the owner
   like any other (`GOV-P-001`).

## 5. What this protocol does not decide

Whether a paraphrase counts as coverage on a borderline case is still a
human (or owner) reading — the same limit `claude-note-references` and
`undated-assertions` both state about their own output. This protocol turns
"compare two prose lists" into "check each report against a fixed,
mechanically produced list," which is what `STD-0300` § 8 requires of a
criterion; it does not make the individual line-by-line check itself
mechanical, and does not claim to.
