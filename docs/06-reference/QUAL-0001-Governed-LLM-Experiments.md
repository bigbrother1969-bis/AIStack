---
artifact:
  id: QUAL-0001
  title: Governed LLM Experiments — fast models and context levels
  type: Experiment Record
  semantic_type: Knowledge Artifact
  domain: Engineering
  criticality: C1
  confidence: Declared
  version: 1.0
  status: Published
  owner: Foundation
  created: 2026-11-15
  updated: 2026-11-15

relations:
  references:
    - ADR-0010
    - ADR-0011
    - STD-0102
    - GOV-0002
---

# QUAL-0001 — Governed LLM Experiments

## Purpose

This record states what the campaign `QUAL-0001` measured, what it did
not, and how it was closed. `ADR-0010` and `ADR-0011` cite it: the gate
`R8` of the automatic AI drafts depends on what it established.

## Provenance

**Written 2026-11-15.** Until then `QUAL-0001` was a session note,
`claude/QUAL-0001-GOVERNED-LLM-EXPERIMENTS-HANDOVER.md` — itself a
handover written outside this repository, by the owner with another
assistant, and reproduced unchanged on 2026-09-13. That note left `main`
on 2026-10-10 with the `claude/` directory; two Accepted ADRs kept citing
it. Found by `scripts/ghe_audit.py`, `GOV-0002/OS-092`; the owner decided
the same day that it becomes a document.

This record is a summary of that note and adds nothing to it. The note is
at `archive/heritage-2.0.0-rc1`, under `claude/`. **The primary evidence
is neither**: it is the 64 result files of the campaign, which were on
GIGABYTE under `/srv/aistack/ollama/governed-llm/experiments/` on
2026-09-25. Whether they are still there is not measured here.

## What was measured

A campaign run on 2026-08-02 on GIGABYTE (Quadro P400, 2 GB), with Ollama:

- 2 models — `qwen2.5:0.5b` and `deepseek-r1:1.5b`, the two found fast
  enough on that machine; the 3B models were set aside after calls
  exceeding 600 seconds;
- 4 levels of governed context, from the minimal foundation (G1, 2.5 KB)
  to the full operational context (G4, 11.8 KB);
- 8 prompts — a fact to restate, a closed question, a summary, a next
  step to derive, and two that test whether a missing piece of
  information is recognised as missing;
- `temperature` 0, `seed` 42.

64 runs, 64 completed, none failed technically.

## What it established

- **Speed and adequacy are different things.** `qwen2.5:0.5b` answered
  in about 16 seconds on average and `deepseek-r1:1.5b` in about 500. To
  the closed question whose governed answer is *no* — *is the AI the
  source of truth?* — the fast model answered *yes* at every level of
  context; the slow one answered correctly.
- **More context is not a better answer.** The fast model's time grew
  with the context (7.5 s at G1, 36.9 s at G4); the slow model's did not
  follow its size.
- **A model can recognise that knowledge is missing.** Asked for an
  acronym the context did not define, `deepseek-r1:1.5b` answered that
  the information was missing.

These are observations on one machine, not properties of the models.

## What it did not establish

**The human evaluation was never done.** A grid of seven criteria existed
(`EVAL-0001`); the 64 results were not scored against it, model by
model, context by context. Every statement above about quality rests on
individual results read during the campaign, not on that evaluation.

It measured nothing about the quality of an AI-written *Explication*: the
concept did not exist until 1.3.

## Closure

Closed on 2026-09-25 by decision of the owner, of three options: a real
test run that day against AIStack's own AI Runtime, with
`deepseek-r1:1.5b` declared in `ai_runtime.yml`, answered the practical
question the campaign had been opened for — which model to run. It
repeated the closed question, answered correctly in about 62 seconds, and
found what the campaign had not measured: a tendency of that model to
contradict itself on open prompts.

The human evaluation was not carried further, deliberately. Nothing was
deleted.

## What the citations mean

`ADR-0011` § 18 states the scope exactly: the closure addressed the
choice of a model, not the quality of an automatic draft, and `R8` stays
open for the owner to decide.

`ADR-0010` § *Open Points* reads *"`QUAL-0001`'s own human evaluation is
still open"*. Read against the closure: that evaluation is not open, it
was stopped. What is open is `R8`.
