"""
What the vigil tells the owner, and how (2.0, tranche 2; the owner,
2026-10-09).

Since 2.0's tranche 3, also AIStack's own data nearing (or past) its
disk budget (ADR-0021), urgent past it.

Four kinds of event, chosen by the owner: the health going down, the
dock (a proposal waiting, a change applied, rolled back or failed), a
silent host, a failed restore test. "1 par événement, regroupé": each
event is said once — a finding that stays is not said again until it
has gone and come back — and the events of one pass go out as one
message. The first pass of a fresh install only takes note of what is
already there: no burst of old news.

Sent to Gotify (`AISTACK_GOTIFY_URL`, `AISTACK_GOTIFY_TOKEN` in
`.env.web`, never shown). Without them the vigil still keeps its state,
and says that notifications are off.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from aistack.dock import proposals as store
from aistack.i18n import Translator
from aistack.vigil.snapshot import Snapshot, SnapshotFinding

STATE = Path("notify") / "state.json"
URL_VARIABLE = "AISTACK_GOTIFY_URL"
TOKEN_VARIABLE = "AISTACK_GOTIFY_TOKEN"
# Gotify's own scale: 5 shows a notification, 8 also rings on Android.
NORMAL = 5
URGENT = 8
HOSTS_DOMAIN = "Hôtes"
PRA_DOMAIN = "Tests PRA"
PRA_FAILED = "findings.pra_tests.failed.interpretation"
DATA_DOMAIN = "Données d'AIStack"
DATA_OVER = "findings.data_budget.over.interpretation"
DOCK_ENDED = {store.APPLIED: "applied", store.ROLLED_BACK: "rolled_back", store.FAILED: "failed"}


@dataclass(frozen=True)
class Event:
    kind: str
    line: str
    urgent: bool = False


@dataclass
class State:
    known: bool = False
    score: int | None = None
    findings: tuple[str, ...] = ()
    proposals: dict[str, str] | None = None


def read_state(generated_dir: Path) -> State:
    try:
        data = json.loads((generated_dir / STATE).read_text(encoding="utf-8"))
        return State(
            known=True,
            score=data.get("score"),
            findings=tuple(str(key) for key in data.get("findings") or []),
            proposals={str(k): str(v) for k, v in (data.get("proposals") or {}).items()},
        )
    except (OSError, ValueError, TypeError, AttributeError):
        return State()


def write_state(generated_dir: Path, state: State) -> None:
    path = generated_dir / STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {"score": state.score, "findings": list(state.findings), "proposals": state.proposals or {}},
            ensure_ascii=False,
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _said(t: Translator, finding: SnapshotFinding) -> str:
    if finding.message:
        return " ".join(t(key, **dict(params)) for key, params in finding.message)
    return finding.text


def events(
    t: Translator,
    previous: State,
    snapshot: Snapshot | None,
    proposals: Sequence[store.Proposal],
) -> tuple[list[Event], State]:
    """The events between `previous` and now, and the state to keep."""

    found: list[Event] = []
    current = State(
        known=True,
        score=previous.score,
        findings=previous.findings,
        proposals={p.id: p.status for p in proposals},
    )

    if snapshot is not None:
        current.score = snapshot.score
        current.findings = tuple(sorted(f.key for f in snapshot.findings))
        if previous.known:
            before = set(previous.findings)
            new = [f for f in snapshot.findings if f.key not in before]
            for finding in new:
                if finding.domain == HOSTS_DOMAIN:
                    found.append(Event("host", t("notify.event.host", text=_said(t, finding)), urgent=True))
                elif finding.domain == PRA_DOMAIN and finding.message and finding.message[0][0] == PRA_FAILED:
                    found.append(Event("pra", t("notify.event.pra", text=_said(t, finding)), urgent=True))
                elif finding.domain == DATA_DOMAIN:
                    over = bool(finding.message) and finding.message[0][0] == DATA_OVER
                    found.append(Event("data", t("notify.event.data", text=_said(t, finding)), urgent=over))
            if (
                snapshot.score is not None
                and previous.score is not None
                and snapshot.score < previous.score
            ):
                found.append(
                    Event("health", t("notify.event.health", before=previous.score, after=snapshot.score))
                )
                for finding in new:
                    if finding.domain not in (HOSTS_DOMAIN, DATA_DOMAIN) and not (
                        finding.domain == PRA_DOMAIN and finding.message and finding.message[0][0] == PRA_FAILED
                    ):
                        found.append(Event("health", "· " + _said(t, finding)))

    if previous.known:
        seen = previous.proposals or {}
        for proposal in proposals:
            before_status = seen.get(proposal.id)
            if before_status == proposal.status:
                continue
            if proposal.status == store.PROPOSED and before_status is None:
                found.append(Event("dock", t("notify.event.dock_proposed", service=proposal.service, by=proposal.proposed_by)))
            elif proposal.status in DOCK_ENDED:
                outcome = DOCK_ENDED[proposal.status]
                found.append(
                    Event(
                        "dock",
                        t(f"notify.event.dock_{outcome}", service=proposal.service),
                        urgent=proposal.status != store.APPLIED,
                    )
                )
    return found, current


@dataclass(frozen=True)
class Message:
    title: str
    body: str
    priority: int


def compose(t: Translator, found: Sequence[Event]) -> Message | None:
    if not found:
        return None
    return Message(
        title=t("notify.title", count=sum(1 for e in found if not e.line.startswith("· "))),
        body="\n".join(e.line for e in found),
        priority=URGENT if any(e.urgent for e in found) else NORMAL,
    )


Post = Callable[[str, bytes, dict[str, str]], Any]


# Python's own "Python-urllib/3.x" is refused by Cloudflare's bot
# protection in front of a self-hosted Gotify (HTTP 403, GIGABYTE,
# 2026-10-09): AIStack says who it is.
USER_AGENT = "AIStack-vigil (+https://codeberg.org/bigbrother1969/AIStack)"


class GotifyRefused(OSError):
    """Gotify, or what stands in front of it, answered with an error."""


def _post(url: str, data: bytes, headers: dict[str, str]) -> Any:
    request = urllib.request.Request(url, data=data, headers={**headers, "User-Agent": USER_AGENT}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as answer:  # noqa: S310 — the owner's own server
            return answer.status
    except urllib.error.HTTPError as error:
        body = error.read(300).decode("utf-8", errors="replace").strip()
        served_by = error.headers.get("Server", "") if error.headers else ""
        raise GotifyRefused(
            f"HTTP {error.code} from {url}"
            + (f" (server: {served_by})" if served_by else "")
            + (f": {body}" if body else "")
        ) from None


@dataclass(frozen=True)
class Gotify:
    url: str
    token: str

    @staticmethod
    def from_environment(environ: dict[str, str] | None = None) -> "Gotify | None":
        env = os.environ if environ is None else environ
        url = (env.get(URL_VARIABLE) or "").strip().rstrip("/")
        token = (env.get(TOKEN_VARIABLE) or "").strip()
        return Gotify(url, token) if url and token else None

    def send(self, message: Message, click: str = "", post: Post = _post) -> None:
        payload: dict[str, Any] = {"title": message.title, "message": message.body, "priority": message.priority}
        if click:
            payload["extras"] = {"client::notification": {"click": {"url": click}}}
        post(
            f"{self.url}/message",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            {"Content-Type": "application/json", "X-Gotify-Key": self.token},
        )
