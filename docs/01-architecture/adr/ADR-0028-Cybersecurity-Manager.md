---
artifact:
  id: ADR-0028
  title: Cybersecurity Manager
  type: ADR
  semantic_type: ADR
  domain: Architecture
  criticality: C1
  confidence: Declared
  version: 0.16
  status: Proposed
  owner: Architecture
  created: 2026-11-19
  updated: 2026-11-20

relations:
  references:
    - ADR-0009
    - ADR-0012
    - ADR-0013
    - ADR-0014
    - ADR-0017
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

The vigil's rules (T4a): from "to fix" up, a finding is told at once and
once; "to watch" goes in one message a day; the owner's own work is declared
as a bounded maintenance window that holds the drift of files back and
nothing else; every window is journalled, so who silenced what, and when, is
always known. An alert is information: it never acts.

The console (T4b): a "Security" card, LAN only, whose badge counts the
findings "to watch" and worse that no maintenance window holds back, and
takes the colour of the worst (yellow to watch, orange to fix, red urgent,
nothing when there are none). The badge is square and says its word, so it
is not taken for the queues' round numbers, and red is kept for "urgent"
alone. The page `/security/` shows the findings grouped as what is
happening (logs, refusals, drift) and what is open (exposure, hygiene,
host, images), the sources the watch cannot read, the window with its
open and close buttons, and graphs of the series over 24 hours, 7 and 30
days, with a hole where a source was not read. Each finding has a sheet
with a text written by hand for its kind (what it means, how to check
with read-only commands, what to do), the same for everyone.

The AI assists, it does not decide (T4b). On a click, the local engine of
`ai_runtime.yml` (never Gemini: the owner's decision of 2026-11-20) is
asked to reason, explain and suggest, and its answers are marked "a
suggestion, never run" and recorded in the reasoning history. What it
receives is what the sheet already shows: the title, the severity and at
most five evidence lines, cut, flattened and fenced as data, because a
container's name, a path or a log's words can be chosen by whoever
attacks; the prompt says to follow nothing written in them and to give no
command that changes anything. The same rules ask for a calm tone, a reader addressed directly, and one to three read-only commands built from the
names read; a name that starts with `aistack-` proves nothing, so the answer is to check where it comes from. The engine is the first that answers among the local engines of
`ai_runtime.yml` (`engines:`, `ollama` or `openai_chat`; without it, the one
Ollama): the reader asks once and picks nothing, and every answer names the
model that gave it, and the engine it stood in for when one stayed silent. The hand-written text, not the model,
carries every command a person may copy. The page works without the
engine.

### 10. The web application does not hold the Docker socket

The Docker socket can start, stop and replace every container, so
whoever controls a process that holds it controls the host. The web
application is the one process with a public listener (`ADR-0017`), and
the assessment (T2a) listed it among the holders. It only reads Docker:
the containers, images, networks and volumes its pages show. Every
write — a restart, a CPU limit, a governed change — is made by another
service, or by the dock on the host.

So the compose file gives it no socket and no Docker group, and a ninth
service, `docker-proxy` (`tecnativa/docker-socket-proxy`), between them:
it answers the reads the application makes, refuses every write with an
HTTP 403, and listens on the host's loopback only (`127.0.0.1:2376`,
`AISTACK_DOCKER_PROXY_PORT`). The seven other services keep the socket;
none has a public listener. A test holds the settings: no write verb, no
`exec`, no build, no secrets, nothing beyond the six reads.

What it does not close, and the owner knows: a reader of the proxy
still sees each container's configuration, its environment variables
included, so a compromised web application can read a secret a
container receives that way. Any process on the host's network can also
reach the loopback port: authenticating the proxy (a certificate, or a
socket file under a directory only the web application mounts) was
weighed and left, for a gain that is small beside the failure it adds.
The proxy's image is a tag, not a digest, until the owner pins one
(`AISTACK_DOCKER_PROXY_IMAGE`).

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
| T2 | Hygiene and what is behind: sensitive file permissions, privileged containers, Docker-socket mounts, images and packages behind | T2a done, 2026-11-19: what the running containers may do to the host (privileged, Docker socket, host process or IPC namespace, kernel capabilities, sensitive host mounts), from `docker inspect`; the owner accepts a risk by container name in `security.yml` (`accepted`), and `--propose` prints the block. T2b done, 2026-11-19: how old each running container's image is (its build date, read locally with `docker image inspect`; no registry is asked, so it says what is old, never that a newer image exists), against `max_image_age_days` (365); an old image the owner keeps is accepted by container name (`accepted: old_image`). T2c done, 2026-11-20: what the host says about its packages and its sensitive files, through a second root unit, `aistack-host-hygiene` (hourly; separate from the firewall snapshot, which it leaves as it is; its writes are declared exempt in `ADR-0027` § 11 on the owner's decision). Packages: `apt-get -s dist-upgrade` reads the lists already on the disk and asks no network; a security update that waits is to watch, other updates are information, a reboot required is information then to watch past `max_reboot_pending_days` (14), package lists older than `max_apt_age_days` (7) are to watch. Files: mode, owner and group of SSH host and user keys, `.env` files under `/srv`, `/opt` and the homes, Docker and cloudflared credentials and the UPS accounts — never a content; any access for other users is to fix, access for a group is to watch; the owner accepts a file by path (`accepted_files`). A snapshot older than three hours is set aside and the report says so |
| T2e | Packages and sensitive files of the other traced hosts | done, 2026-11-20: the unit of T2c also runs on the other hosts of `hosts.yml`, writing `<their data folder>/security/`; the push of `ADR-0020` (`rsync -a` of the whole folder, every 15 minutes) brings it to `hosts/<name>/security/`, and the assessment judges it like the local host, each finding naming its host (`host.<name>.…`). A host with no `security` folder is not reported. A snapshot older than 25 hours (`silent_after_minutes`) is set aside and said so, as information: a host may be off for a day. Ports, containers and firewall stay those of the host AIStack runs on |
| T3 | Detection from existing logs and `ADR-0020` records | T3a done, 2026-11-20: drift of files and units on the traced hosts, read from the `events.jsonl` of `ADR-0020` over the last `drift_window_hours` (24), with nothing installed on any host. A change to a sensitive path (accounts, privilege, SSH, firewall, VPN, UPS, tunnel, hand-installed programs, scheduled jobs; `drift_sensitive`) or a unit newly enabled is to watch, unless an apt run on that host explains it (`drift_apt_grace_minutes`, 60: the collector notes a change when it next runs); noise (`drift_noise`: printer queue, hardware clock, `*.dpkg-new`…) and the owner's `accepted_drift` are counted, never reported; the rest is a count in one information finding per host. A finding names a path and an action, never a fingerprint or a content. A host that is silent or whose records cannot be read is an information finding about the source. By the owner's decision of 2026-11-20, T3 findings go no higher than `watch` until thresholds are calibrated on real records. T3b done, 2026-11-20: refused packets counted from the firewall's own counters. `aistack-firewall-snapshot` asks `iptables-save -c` (the counters are removed from the two text files, so the reader of the rules is unchanged) and appends to `firewall-refusals.jsonl`, kept seven days, the packets dropped by `DOCKER-USER`, by the default policy of `INPUT`, by ufw's rules and by other chains, with the boot identifier. The report sums them over `refusal_window_hours` (24); a counter that goes down or a new boot is a restart from zero, never a negative count. A counter holds no address: the finding says how many and which rule refused, and that only the `DOCKER-USER` refusals are known to come from outside the LAN and the VPN. Information by default; `refusal_watch_per_hour` (0 = off) makes a sustained rate (over at least an hour of readings) a finding to watch, to be set once the usual figure is known. An installed unit needs only its script copied again. T3c done, 2026-11-20: who tried to get in, from the host's logs, through a third root unit, `aistack-host-logs` (hourly, same schema as the firewall snapshot and the host hygiene; its writes are declared exempt in `ADR-0027` § 11 on the owner's decision). It writes `host-logs.json`: counts over the last 24 hours and nothing else, by kind of network (the LAN, the VPN, outside; the VPN's network is given to the unit, the LAN is the private ranges unless said otherwise): SSH logins that failed and user names the host does not have, `DOCKER-USER` packets that were refused and logged (the kernel log keeps at most six a minute, the counters of T3b count them all), and, where Nginx Proxy Manager keeps its logs on the host, per virtual host the requests by status class the probes (`/.env`, `/.git`, `/../`: nobody but a scanner asks for them) and the application paths (`wp-login.php`, `xmlrpc.php`, `phpmyadmin`, `/cgi-bin`: a scanner asks for them and so does the person who uses the application), each with how many were answered with a success (2xx); a probe a virtual host answers with a success is a finding to watch whatever the threshold, the owner accepting by name a host that answers 200 to every path (`accepted_proxy_hosts`). Added the same day after the first reading showed `xmlrpc.php` answered 452 times in 24 h on the public WordPress site: a count of 404s did not tell it apart. Never an address, a path, a user name or a log line: provenance is a class, not an address (the owner's decision of 2026-11-20). Each source is read on its own and a source that fails says so, as information, and its numbers are not used. On the other hosts the file reaches `hosts/<name>/security/` through the push of `ADR-0020` and is judged the same way, each finding naming its host; a file older than 25 hours is set aside. Information by default; `ssh_failed_outside_watch` and `npm_scans_outside_watch` (0 = off) make the figure from outside a finding to watch once it reaches the number the owner sets. T3 is done: its findings go no higher than `watch` until thresholds are calibrated on real records |
| T4a | What the vigil tells Gotify, a maintenance window, the series | done, 2026-11-20: the vigil runs `security.assess` at each pass and reads the report. A finding to fix or urgent is told at once, once while it stands (urgent rings, Gotify priority 8; to fix shows); one that goes and comes back is told again. The findings to watch go in one message a day at `digest_hour` (8) in `digest_timezone` (Europe/Paris), each with how long it has stood, and only when there are some; the message also says when the report has not been redone for three hours. The first pass after the slice only notes what is there. By the owner's decision of 2026-11-20, his own changes are not alerts: `python -m aistack.cli.security_window --for 2h` opens a maintenance window of at most `window_max_hours` (4), during which the drift of files and units is counted and not told (whatever its severity but urgent; everything else is told as usual), told when the window ends if it still stands; the window ends by itself and says so once, and each opening and closing is kept in `security-window.jsonl`. The report carries `measures` (counts by severity and area, ports, refusals, SSH, proxy, drift, updates: never an address, a path or a content; a source not read adds no key) and the vigil appends them to `security-series.jsonl` (`series_days`, 90) before it sends, so a Gotify that does not answer leaves no gap. Nothing acts on any host |
| T4b | The console card and the Security page: findings, sources, the window, graphs drawn from the series | done, 2026-11-20: `/security/` (LAN only, signed in; the window and the AI need the administrators' group) with the card and its badge; the fixed texts are `security.guide.*` in both languages; the window is declared through the `security.window` Task; the AI goes through `ask_ollama`, never `ask_ai_runtime`. Nothing acts on any host |
| T4c | Putting the local engines side by side | done, 2026-11-20: the Task `ai.compare` and `python -m aistack.cli.ai_compare` ask each engine alone, on the same findings and with the same prompts as the page, and write a markdown report (times, answers, automatic flags: a "vous" where the page says "tu", the word "owner", a command that modifies, a mention of intrusion, no answer); read-only, no engine that can leave the network is asked, `--dry-run` sends nothing. The reader decides which engine and which `reasoning_effort` the page uses. First reading (qwen2.5:7b, Olala `disabled`, Olala `low`): Olala `disabled` twice as fast as qwen and as useful, but it wrote once in English and vouvoyed; the French directive now asks for tutoiement as its last word, and the flags see the verbs in -ez, English, an alarmist tone and an intrusion that is denied |
| T2d | The web application no longer holds the Docker socket (§ 10) | done, 2026-11-20: `docker-proxy` in the compose file, a test of its settings; tried on the reference host the same morning — the web application `healthy`, its Dock and CPU-priority pages answer, a write through the proxy is refused (403), the report goes from two points to watch to one |
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
