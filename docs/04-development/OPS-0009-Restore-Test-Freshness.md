---
artifact:
  id: OPS-0009
  title: Restore Test Freshness
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Operations
  created: 2026-11-15
  updated: 2026-11-15

relations:
  references:
    - OPS-0004
    - OPS-0006
    - OPS-0010
    - ADR-0018
    - GOV-0002
---

# OPS-0009 — Restore Test Freshness

## Purpose

A backup that has never been restored is a hope. This register states when
a service's restore test is due, what counts as a test, and what AIStack
reports when one is missing, failed or too old. It is the policy the
*Tests PRA* domain of the Cockpit cites, the way `OPS-0006` is the policy
of backup freshness and `OPS-0010` that of persistent state.

## Provenance

**Written 2026-11-15, after the code it governs.** The identifier has been
cited since 1.1 — by `OPS-0004`, `OPS-0008`, `OPS-0010`, `OPS-0011`, the
release notes and eleven files under `src/aistack` — and no document ever
bore it, in `main` or at `archive/heritage-2.0.0-rc1`. Found by
`scripts/ghe_audit.py`, `GOV-0002/OS-092`; the owner decided the same day
that the document is written rather than the citations corrected.

It therefore describes what `main` does on `f2cf0dd`, read from the code,
and decides nothing new. Where the code and a comment disagree, it says
so (§ *What this register does not do*).

## What is declared

One file, `pra_tests.yml`, the owner's, hand-written and never rewritten
by AIStack:

```yaml
max_age_days: 90
services:
  - name: nextcloud
    last_test:
      status: success
      date: "2026-10-08"
      rto_minutes: 5
```

- `max_age_days` — one threshold for every service. A successful test
  older than this is due again. The shipped value is 90.
- `services` — the services whose restore is tested. A new installation
  declares none.
- `last_test` — `null` for a service never tested; otherwise a `status`,
  `success` or `failed`, its `date`, and optionally the time the restore
  took (`rto_minutes`).

`max_age_days` and `services` are both required: a file without one is
refused with the name of the missing key, not read as empty.

## What counts as a test

Two sources, and the more recent outcome of the two stands for each
service:

- **a test done by hand**, recorded by the owner in `pra_tests.yml`.
  `python -m aistack.cli.sandbox restore <service>` performs one in a
  sandbox (`ADR-0018`) and prints the entry it proposes; the owner copies
  it if he accepts it;
- **a scheduled test**, run every week by `aistack-pra.timer` for each
  service that has a sandbox recipe. Its outcome is appended to
  `pra/scheduled.jsonl` in the data directory. A scheduled success
  refreshes the date; a scheduled failure stands until a later run
  succeeds.

Neither touches a live service.

## What is reported

A finding per service, for one of four reasons — a closed set:

| Reason | Condition |
|---|---|
| `untested` | the service is declared and `last_test` is `null` |
| `failed` | the last test failed; reported at once, whatever its age |
| `stale` | the last success is older than `max_age_days` |
| `not_declared` | `OPS-0010` declares the service stateful and this file does not name it |

Every finding cites three qualifications of `OPS-0004`: technical debt,
sustainability anomaly and deployment misconfiguration. Energy
inefficiency does not apply.

The remediation is always a real test and its real outcome. For a service
that is not declared, it is to add it with `last_test: null` — never a
guessed date or status — and then to test it.

## What this register does not do

- **It sets no threshold per service.** The loader copies the one value
  into one entry per service, which leaves room for it; nothing declares
  a second value today.
- **It does not say which services must be tested.** `OPS-0010` does, by
  declaring which hold state.
- **It does not judge the quality of a restore** beyond `success` or
  `failed`. `rto_minutes` is recorded and compared with nothing.
- **A comment disagrees with the code.** The header of the shipped
  `pra_tests.yml` says the file is recorded *"from the troubleshooting
  assistant, or by the scheduled restore tests"*. Measured 2026-11-15:
  the scheduled tests never write it (`aistack.pra.scheduled`,
  `aistack.cli.pra_schedule`: *"`pra_tests.yml` is never rewritten"*), and
  nothing under `src/aistack/troubleshooting` writes it either — it reads
  it. The file is written by the owner. The comment is left as it is by
  this document and is to be corrected with the code.

## Related Artifacts

- `OPS-0004` — the qualifications a finding cites
- `OPS-0006` — backup freshness, the sibling threshold
- `OPS-0010` — the stateful services this register is confronted against
- `ADR-0018` — the sandbox a test runs in
