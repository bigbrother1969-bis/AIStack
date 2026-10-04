---
artifact:
  id: ADR-0017
  title: Container Distribution
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.8
  status: Accepted
  owner: Architecture
  created: 2026-10-04
  updated: 2026-10-04

relations:
  references:
    - ADR-0012
    - ADR-0013
    - ADR-0016
    - OPS-0002
---

# ADR-0017 — Container Distribution

## Status

Accepted, 2026-10-04, by the owner — the day it was proposed, as
`ADR-0016` § 3 allows in the development phase.

Proposed 2026-10-04 as 1.8's framing.

## Context

*Measured on 2026-10-04, at commit `8ebe144`.*

The owner's goal, 2026-10-04: **someone who pulls the image from Docker
Hub gets a fully working AIStack.** Today `bigbrother1969/aistack-core`
carries the code but runs only the knowledge-integrity validator; the
reference host runs AIStack from a git clone, a virtual environment and
six systemd units (`aistack-web` and five collectors).

What stands between the two:

- **18 declarations ship inside the package**
  (`src/aistack/*/definitions/*.yml`), read through 51 path expressions
  in 20 modules, with the reference host's values; two of them are
  written by screens (CPU priorities, SSH user names) — inside an image,
  those writes would be lost.
- **AIStack observes its host**: the `docker` command (14 call sites),
  `sensors`, `nvidia-smi`, `ssh`, Syncthing, `/proc/self/mounts`, and the
  host paths its declarations name (backup disks, music library).
- Its data lives in `reports/generated/` (histories, explications,
  sessions, graph) and its secrets in `.env.web`.

## Decision

Decided by the owner, 2026-10-04.

### 1. The configuration lives outside the code, file by file

`AISTACK_CONFIG_DIR` (`/config` in the container) names a configuration
directory; a declaration of the same file name there replaces the
shipped one, and a file it does not hold keeps the shipped value
(`aistack.config.configured`). `python -m aistack.cli.config_init`
copies every shipped declaration into the directory, never overwriting
one — the container runs it at each start, so a screen that saves a
declaration writes into the directory. Without the variable, nothing
changes for a git installation.

### 2. One image, one service per process

The published image runs AIStack, not only the validator: a
`docker-compose.yml` starts the web application and the five collectors
as six services of the same image, restarted and logged by Docker as
systemd does today. The validator stays a command of the same image.

### 3. The host network, the host's paths at the same place

`network_mode: host` (the two ports and the LAN scan as they are), the
Docker socket, and every host directory a declaration names mounted at
the **same path** inside the container — read-only, except the data and
configuration volumes.

### 4. First start, guided

With a fresh configuration directory, AIStack starts and says what to
declare first (instance, identity provider) and where the manual is —
it never fails on the reference host's values.

Implemented 2026-10-04:

- **What is still the reference host's.** `config_init` keeps the
  fingerprint of every file it copies (`.shipped.json`, in the
  configuration directory). `instance_config.yml` and
  `authentication.yml` are still to declare while their file has that
  fingerprint — edited once, they are declared. A file the owner put
  in the directory himself was never copied and is never reported:
  comparing with the shipped values instead would report GIGABYTE —
  whose values are the shipped ones — as unconfigured at its move
  (§ 5).
- **What secret is missing.** The OpenID Connect client's ID and
  secret (required) and the fallback administrator's hash
  (recommended), read from the web process's environment. Checked
  with or without a configuration directory; the names only, never a
  value.
- **Where it is said.** `/setup`, public like the console — on a new
  installation nobody can sign in yet: each item, its file, the values
  in use, the restart command and the manual's *With Docker* section.
  While a required item is missing, every page's navigation carries a
  **⚠ To configure** link to it. Measured once, when the application
  starts: nothing it reads changes before a restart.

### 4 bis. Where the data lives, chosen from Settings

Asked by the owner, 2026-10-04; decided the same day: **one choice for
all of `reports/generated`** (histories, explications, graph, sessions,
generated pages), and **AIStack records it and shows the commands — it
never moves anything itself**.

- An administrator picks a **disk from a list** in Settings, under the
  disks and mounts (the owner's preference over a typed path, at the
  first trial, 2026-10-04): the local mounts the process can write to —
  in the container, the host directories it mounts — with their free
  space, except the disk the data is already on and any network share
  (the sessions are a SQLite file). The data goes to `AIStack/data` — a
  dedicated `AIStack` directory at the root of that disk (the owner's
  choice at the second trial, 2026-10-04). Refused: a disk not in the list, a disk with
  less free space than the data's size plus 10 % (measured within 5 s,
  else not checked). The choice — directory, who, when — is
  `data_location.yml`, in the configuration directory, else at the
  checkout's root, ignored by git.
- **A git installation** reads `reports/generated` relative to its
  working directory, in 22 places: the move makes that path a link to
  the chosen directory (stop the six units, mark the one tracked file
  under it `skip-worktree`, copy, link, start), the old directory kept
  as `reports/generated.avant-deplacement`. Done when the path resolves
  to the chosen directory.
- **The container** sees `/app/reports/generated` whatever the host
  directory behind it: `docker-compose.yml` mounts
  `${AISTACK_DATA_DIR:-./data}` there and passes the same value in, so
  the move is declaring `AISTACK_DATA_DIR` in `.env` after the copy.
  Done when the value names the chosen directory.

### 5. GIGABYTE moves to it at the end of 1.8

The last tranche replaces GIGABYTE's six systemd units by the compose
file, with a documented way back. The git + systemd installation stays
supported.

Prepared 2026-10-04; decided by the owner the same day: **the data
stays where it is** (`reports/generated` on `/`), moved later from
Settings if wanted (§ 4 bis).

- **The checkout stays** — it builds the image (`AISTACK_VERSION=dev`
  until 1.8.0 is published) and holds `docker-compose.yml`, `.env.web`
  and `.env.resource-priority`, which compose reads from the same
  place.
- **The declarations are placed, not copied**: GIGABYTE's own files
  (`src/aistack/*/definitions/*.yml`) and its selections
  (`examples/selections/`) go into `./config` before the first start,
  so `config_init` keeps them and the first-start page reports none of
  them (§ 4).
- **The data is mounted where it is**: `AISTACK_DATA_DIR` in `.env`
  names `reports/generated`.
- **What only this host needs** is `docker-compose.override.yml`, never
  committed, from `docker-compose.override.example.yml`: the one host
  directory the application writes to (the Selection screen's
  `target_root`), and the GPU for the troubleshooting assistant
  (NVIDIA container runtime).
- `scripts/compose_preflight.sh` reads, without changing anything,
  what the move depends on: account and socket group, NVIDIA runtime,
  units, ports, secrets files, an existing `.env` or `./config`, a
  planned data move, host crontab entries and timers that run AIStack.
- **The way back**: `docker compose down`, then
  `systemctl enable --now` the six units. What a screen saved meanwhile
  is in `./config`; the files that differ from the checkout's are
  listed and copied back by hand.
- **Done 2026-10-04, 14:49.** The preflight found an earlier trial's
  `.env` and an existing `./config` (both set aside in
  `~/aistack-avant-compose/`, not deleted) and, in the crontab, only
  the nightly mirror publication. That `./config` held only
  `context_bundle_transfer.yml.example`, which the checkout tracks
  (`ADR-0007`): set aside, it left the working tree unclean and
  `sync_mirrors.sh` refused to publish, the same evening. It stays in
  `./config`, beside the declarations — neither `configured()` nor
  `config_init` reads a file that is not `.yml` — and the preflight now
  looks only for declarations there.
  Three declarations live one level deeper
  (`src/aistack/providers/*/definitions/`): the copy is a `find`, not a
  one-level glob. From the first minute the collectors observed
  AIStack's own containers — the Compose project `aistack` — like any
  other project.
- After the move, one-off commands run in the image
  (`docker compose exec web python -m aistack.cli.…`), which reads
  `./config`; the checkout's virtual environment reads the shipped
  declarations and stays for development only.

## Implementation state

| Step | State |
|---|---|
| § 1 — `aistack.config`, `config_init`, every declaration path through `configured()` | done — 2026-10-04 |
| § 2 — the image runs AIStack; `docker-compose.yml` with six services, `.env.example` | done — 2026-10-04; tried on GIGABYTE the same day (`dev` image, ports 9183/9186): console and manual answer 200, ready ≈ 12 s after start |
| § 3 — host network, socket, same-path mounts | done — 2026-10-04; tried on GIGABYTE the same day: both ports listening on the host, `docker ps` answers inside the container |
| § 4 — guided first start | done — 2026-10-04 |
| § 4 bis — where the data lives, chosen from Settings | done — 2026-10-04 |
| § 5 — GIGABYTE on the compose file | done — 2026-10-04, 14:49: six containers of the `dev` image, console 200 after 21 s, no first-start notice; sign-in, Settings, CPU priority, Selection and the Time Machine checked by the owner |

## Consequences

- An upgrade of the image never touches the owner's declarations; a new
  declaration a version brings is added at the next start.
- The validator image's default command changes; `OPS-0002` § *Publishing
  an image* is revised with § 2.

## Open Points

- A declaration changed in the repository no longer reaches a host
  whose `./config` already holds that file (measured 2026-10-04, the
  evening of the move: AIStack's six containers declared in
  `service_categorization.yml` had to be copied into GIGABYTE's
  `./config` by hand). `config_init` never overwrites, by design; a way
  to see, per file, how the shipped one differs from the one in use is
  still to decide.

- The Selection screen's `selection_file`, a relative path, resolves
  against the configuration directory when there is one (decided in
  § 2's implementation, 2026-10-04): the owner's selection file goes to
  `./config/examples/selections/` at the move.
- `web_admin_password` asks the password interactively: in a container
  it needs `docker compose exec` with a terminal.
