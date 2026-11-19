---
artifact:
  id: ADR-0028
  title: Cybersecurity Manager
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C1
  confidence: Declared
  version: 0.4
  status: Proposed
  owner: Architecture
  created: 2026-11-19
  updated: 2026-11-19

relations:
  references:
    - ADR-0009
    - ADR-0012
    - ADR-0013
    - ADR-0014
    - ADR-0018
    - ADR-0019
    - ADR-0020
    - ADR-0025
    - ADR-0027
---

# ADR-0028 — Cybersecurity Manager

## Status

Proposed, 2026-11-19. Scope and four choices decided with the owner the
same day (§ 1, § 2, § 5); the rest is proposed and waits for the owner.
No code exists yet.

## Context

*Measured on the reference hosts, 2026-11-08 and 2026-11-19.*

AIStack already reads most of what a security assessment needs, and
acts on none of it:

- **Exposure.** About sixty Docker ports are published on `0.0.0.0` on
  the MSI; `DOCKER-USER` refuses new inbound traffic from outside the
  LAN and the VPN subnet since 2026-11-08 (service
  `docker-user-regles`); UFW denies inbound by default for host
  services. The Freebox forwards one port (51820/UDP to the second
  Pi-hole), no DMZ. The public entrance is Cloudflare's tunnel and
  NPM; AIStack's web application listens on 8183 (public) and 8186
  (LAN), and `ia-bascule` on 8190.
- **What changes on the hosts.** `ADR-0020` records packages, files
  (by keyed fingerprint, never content) and units on both hosts, and
  raises a silent host as a health finding.
- **The network and Docker.** `network_docker.discover` (`ADR-0027`
  § 10) finds hosts of the LAN and their containers.
- **Telling the owner.** The vigil sends to Gotify; `ADR-0025` is the
  precedent for a service that acts with guardrails.

Two facts frame the risk:

- **Monitoring is not independent.** Uptime Kuma and Gotify run on the
  Raspberry; a host that fails blanks both.
- **A false alarm can be a self-inflicted outage.** On 2026-11-19 a
  script forced the shutdown of both hosts because the UPS raised a
  "battery low" flag while on mains. The same shape applies here, more
  sharply: a component allowed to close access and purge is the most
  dangerous one of the stack when it is wrong.

## Decision

### 1. It starts read-only

Decided by the owner, 2026-11-19. The first slices assess and tell;
they change nothing on any host. Responses (§ 5 onward) come later,
each behind its own decision.

### 2. It reads what AIStack already collects

Decided by the owner, 2026-11-19. Sources, in this order: the exposure
(published ports, tunnel, proxy, firewall rules), host hygiene
(permissions of sensitive files, privileged containers, mounts of the
Docker socket, images and packages behind), the host records of
`ADR-0020` (drift of fingerprints, new units, new cron lines), and the
logs already on the hosts (firewall refusals, SSH failures, proxy
access). An external tool or a vulnerability feed (CVE) is added only
when a real need appears, and by a decision of its own.

### 3. A finding is evidence, never a secret

A finding carries: what, where, since when, how severe, the evidence
(a path, a port, a count) and what is not known. Never a secret, a
token, a file's content or a person's data (the rule of `ADR-0011`
§ 6 and `ADR-0020` § 4). Severity is a small closed scale
(information, to watch, to fix, urgent); a finding that stays is not
repeated (the vigil's rule). A missing source (a log not readable, a
host silent) is a finding about the assessment itself, never an
absence of finding.

### 4. Where it runs

The assessment is a Task of the Runtime (`ADR-0027` § 10), run on
demand and by the vigil, on the MSI. It names no technology in the
Kernel (`ADR-0027` § 7): each source is a provider read through the
registry. A second, much smaller watcher runs on the Raspberry — the
independent witness: it checks that the MSI answers and that the
entrance is in the expected state, and tells Gotify without depending
on the MSI. Its design is a later slice.

### 5. The response ladder

Decided by the owner, 2026-11-19: automatic only for what is
reversible; purge and restore always confirmed by the owner.

| Level | What | Who triggers |
|---|---|---|
| 0 | Assess and alert | automatic |
| 1 | Reversible isolation: close the Internet entrance (stop the tunnel, or refuse at the proxy). The LAN, the VPN and the owner's way in stay open | automatic, under § 6 |
| 2 | Cut a service or a host from the network | the owner |
| 3 | Purge and restore a clean configuration | the owner, after § 7 |

Nothing on this ladder shuts a host down, deletes data or touches the
UPS chain.

### 6. The one automatic action, and its conditions

Level 1 is an exception to the rule that a recommendation is never
carried out on its own (`ADR-0019`, the reasoning assistants). It is
the only one, because it is reversible and because waiting costs more
than a closed door. It requires all of:

1. **Two independent signals** of different kinds (for example a
   fingerprint drift on a host *and* refused connections from outside),
   never one, and never a flag a device raises by itself.
2. **A fresh reading** of both, within a short window, after one
   re-check.
3. **A bounded effect**: the entrance only; a maximum duration after
   which it reopens by itself unless the owner confirms it stays
   closed; a limit of one closure per hour.
4. **The owner is told first**, urgent, with the evidence and the one
   command that reopens.
5. **A simulation mode** that writes what it would have done, kept on
   for a stated period before the action is enabled (the lesson of
   2026-11-19).

### 7. Purge and restore: a snapshot first, a clean point verified

Level 3 never starts without (a) a **snapshot** of the current state
kept off the affected host — the evidence, and the way back if the
restore was wrong; (b) a **clean point** — a configuration whose
fingerprints were verified when it was saved, kept where an intruder on
the MSI cannot rewrite it (the append-only restic repository on the
vault host is the candidate, `ADR-0018`); (c) the owner's confirmation,
word by word, in the manner of the homelab scripts. A clean point
newer than the first sign of compromise is refused: it might already
carry it.

### 8. The power to act lives outside the web application

The public web application never holds the power to close or purge.
A small privileged actuator, with a closed list of actions (the model
of `ia-bascule`: one purpose, refuses a call without its header),
reached from the LAN only, executes level 1 and level 3. The web
application asks; the actuator checks the conditions of § 6 itself.

### 9. What is told, and where

Through the vigil's Gotify channel, plus the Raspberry watcher's own
for the case where the MSI is the problem. The message says what, how
sure, what was done, and how to undo it. No secret, no content.

## Consequences

- A first slice delivers value with no action at all: an exposure
  assessment and an alert, on data already collected.
- The Raspberry becomes a second pillar of the answer, as it already
  is for monitoring: its availability matters more.
- A false positive costs an alert at level 0 and a reversible, bounded
  closure at level 1, and never data.
- `ADR-0019`'s rule gets a written, single exception.

## Implementation state

Nothing is built. Planned slices (each its own patch, tested before
delivery):

| Slice | Content | State |
|---|---|---|
| T1 | Exposure and inventory of the host AIStack runs on: listening sockets and the ports Docker publishes, judged against `security.yml`; the Task `security.assess` and `python -m aistack.cli.security_assess` | done, in part — 2026-11-19: sockets, published ports and the firewall rules (a host snapshot). **Not read yet**: the tunnel and the proxy (see Open points); only the host AIStack runs on |
| T2 | Hygiene and what is behind: sensitive file permissions, privileged containers, Docker-socket mounts, images and packages behind | T2a done, 2026-11-19: what the running containers may do to the host (privileged, Docker socket, host process or IPC namespace, kernel capabilities, sensitive host mounts), from `docker inspect`; the owner accepts a risk by container name in `security.yml` (`accepted`), and `--propose` prints the block. **Not started**: images behind, host packages, sensitive file permissions |
| T3 | Detection from existing logs and `ADR-0020` records | not started |
| T4 | Alerts (severity, deduplication) and the console card | not started |
| later | Raspberry witness; actuator; level 1; snapshot, clean point, level 3 | not started, each to be decided |

## Open points

- **Reading the firewall: done, 2026-11-19 (T1b).** The container cannot
  read it (no `iptables`; `ADR-0020`'s collector has no network), so a
  small root unit, `aistack-firewall-snapshot`, runs `iptables-save` and
  `ip6tables-save` in the host's namespace every ten minutes and writes
  their answer, dated, under the data directory. The assessment reads
  those files and says, per port, from where it can be reached: the
  `INPUT` chain and the chains ufw jumps to for host ports, `DOCKER-USER`
  for published ones. It is an approximation: a rule it cannot classify
  (connection state, destination address, source port) is set aside,
  never counted as an opening; a snapshot older than two hours is not
  used. What stays unknown, and is said: whether a router in front of
  the host forwards ports to it. Still to read: the tunnel and the proxy.
- **What a real run has shown**: the first run on the reference host
  (2026-11-19) listed 82 ports on every interface, none to fix. T1b is
  verified by the suite against a ufw-shaped snapshot; its first run on
  the host is still to come.
- A vulnerability feed (CVE) for images and packages: which source,
  and whether any data leaves the LAN.
- How level 1 closes the entrance: stop the tunnel, or refuse at the
  proxy; and what keeps the owner's own way in open.
- Where the clean point lives, and who verifies its fingerprints.
- What a second signal means for the first real detections: the
  rules are written once the first weeks of readings exist.
