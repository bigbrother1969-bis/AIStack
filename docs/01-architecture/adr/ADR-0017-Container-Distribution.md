---
artifact:
  id: ADR-0017
  title: Container Distribution
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C2
  confidence: Declared
  version: 1.0
  status: Proposed
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

Proposed, 2026-10-04 — 1.8's framing. Under `ADR-0016` § 3 (development
phase), accepted the day the owner accepts it.

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

### 5. GIGABYTE moves to it at the end of 1.8

The last tranche replaces GIGABYTE's six systemd units by the compose
file, with a documented way back. The git + systemd installation stays
supported.

## Implementation state

| Step | State |
|---|---|
| § 1 — `aistack.config`, `config_init`, every declaration path through `configured()` | done — 2026-10-04 |
| § 2 — the image runs AIStack; `docker-compose.yml` with six services, `.env.example` | done — 2026-10-04, not yet run on a host |
| § 3 — host network, socket, same-path mounts | done — 2026-10-04, not yet run on a host |
| § 4 — guided first start | not started |
| Choosing where each component lives, from Settings (asked 2026-10-04) | not started |
| § 5 — GIGABYTE on the compose file | not started |

## Consequences

- An upgrade of the image never touches the owner's declarations; a new
  declaration a version brings is added at the next start.
- The validator image's default command changes; `OPS-0002` § *Publishing
  an image* is revised with § 2.

## Open Points

- The Selection screen's `selection_file`, a relative path, resolves
  against the configuration directory when there is one (decided in
  § 2's implementation, 2026-10-04): the owner's selection file goes to
  `./config/examples/selections/` at the move.
- `web_admin_password` asks the password interactively: in a container
  it needs `docker compose exec` with a terminal.
