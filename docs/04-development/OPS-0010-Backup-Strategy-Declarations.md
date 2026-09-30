---
artifact:
  id: OPS-0010
  title: Backup Strategy Declarations
  type: Operations Policy Register
  semantic_type: Policy
  domain: Operations
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Draft
  owner: Operations
  created: 2026-09-30
  updated: 2026-09-30

relations:
  references:
    - OPS-0004
---

# OPS-0010 — Backup Strategy Declarations

## Purpose

This register declares, for every stateful service in its scope, whether a
real backup mechanism is confirmed to cover its persistent state, and if
so, which engine(s) it actually uses. `STD-0300` § VS-4 criterion 4.5
requires each qualification a finding carries to be traceable to a
distinct policy; this is that policy for the roadmap's own R9 constat
("état persistant non couvert"), the same way `OPS-0006`/`OPS-0009` are
the policies for backup freshness and restore-test freshness. No
declaration here was chosen by AIStack — it is the owner's own declared
record, or an explicit "not confirmed" where this session could not
ground one (`GOV-P-001`).

## Provenance

Declared 2026-09-30, 1.6 tranche 2 (R9,
`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md`): "Services avec état confrontés
aux sauvegardes connues ; constat « état persistant non couvert » avec
stratégie par moteur (dump SQL pour une base vivante, arrêt + archive pour
une configuration), qui sert aussi au bac à sable (R9). Pas de
généralisation au-delà (`ARC-P-006`)." Three cadrage decisions preceded any
code, via `AskUserQuestion`, all the recommended option:

- **Scope** — "le stock déjà réel": the services already named in this
  session's own real PRA history (`OPS-0009`'s `pra_tests.yml`), not the
  ~60 services `service_categorization.yml` lists.
- **Mechanism** — a new dedicated file, `backup_strategy.yml`, the same
  "declared, never guessed" convention `pra_tests.yml`/
  `backup_thresholds.yml` already hold.
- **Exposure** — a sixth cockpit domain, "État persistant", the same
  deliberate reopening `Tests PRA` already went through 2026-09-23.

Where this session's own grounding ran out — the exact mechanism behind
"des timers systemd pour les bases Nextcloud/Immich" (mentioned in
passing 2026-09-11), and GIGABYTE's own host-level backup status — the
owner was asked directly, 2026-09-30, and did not know either by heart.
Declared here as a real, confirmed gap (`nextcloud`, `immich`, `gigabyte`:
`has_state: true`, `engines: []`) rather than guessed.

## Three real engines, not an abstract taxonomy

`ARC-P-006` — never generalize a mechanism beyond a real, cited case.
Three engines are declared, each grounded in a script this session found
and read, none invented ahead of a real case:

- **`dump_sql`** — a live database dumped without stopping the service.
  `backup-wordpress.sh`'s `mysqldump`; `backup_raspberry.sh`'s
  `mariadb-dump --single-transaction` for Vikunja.
- **`stop_and_archive`** — the service is stopped, its configuration
  archived, then restarted. `backup-arrstack.sh`.
- **`live_file_backup`** — plain files backed up while the service keeps
  running, no stop and no database dump. `backup_raspberry.sh`'s restic
  snapshot of six SQLite-backed Raspberry stacks.

R9's own text names only the first two as examples; `live_file_backup` is
added because it is a third real mechanism already running, not a
hypothetical fourth case invented ahead of one.

## Declared services

Twelve, all on the "stock déjà réel" scope: `wordpress`, `arrstack`,
`nextcloud`, `immich`, `gigabyte` (GIGABYTE), and `changedetection`,
`homepage`, `npm`, `pocketid`, `uptime-kuma`, `vaultwarden`, `vikunja`
(Raspberry). Full detail — mechanism, script path, real restore-test
history where one exists — is in `backup_strategy.yml`'s own header
comment, not duplicated here.

Three real, confirmed gaps: `nextcloud`, `immich` (mechanism mentioned in
passing but never grounded to a script), `gigabyte` (the host's own
system-level state, distinct from the app-level backups that run on it —
`pra_tests.yml` already declares `gigabyte.last_test: null` for the same
reason).

### Out of scope for this version

- **The ~50 remaining `service_categorization.yml` services** — no backup
  mechanism has been cited for them; adding one happens when the owner
  names a real case for it, per `ARC-P-006`, not by extrapolating from
  this file's own twelve.
- **A general, pluggable "backup engine" taxonomy** — only the three
  engines above are declared, each tied to a real script this session
  read; a fourth is added only against a fourth real case.

Both are a named absence this register records (`FDN-0003` Article 12),
not a silent one.

## What this register does not do

It does not itself verify that a declared engine still runs, or that it
still produces a usable backup — `OPS-0006`/`OPS-0009` already cover
freshness and restore-test verification for the services that overlap
with this file. This register only asks one question per stateful
service: is a real backup mechanism known at all.
`load_backup_strategy_yaml` (`src/aistack/backup_strategy/yaml/store.py`)
is the loader; `aistack.runtime.uncovered_state_gap.find_uncovered_state`
is the correlation that decides which declared services have no known
engine; `aistack.runtime.evaluate_uncovered_state` is what cites
`OPS-0004` against a confirmed gap.

## Related Artifacts

- `OPS-0004` — Sustainability Qualifications, § *Sixth reference case*
- `OPS-0009` — the sibling register this one is confronted against
  (declared restore-test history) without duplicating
- `claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` — R9, the constat this
  register supports
- `claude/SESSION-2026-09-30-1.6-tranche2-backup-strategy.md` — the
  session that declared this register
