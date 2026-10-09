"""
What the AI is working on for whom, and which answers are ready
(owner, 2026-10-09: "une notification cliquable apparaît quand les
moteurs d'IA ont terminé leur réponse, pour basculer directement
dessus sans avoir à attendre la réponse").

An assistant that hands work to the AI starts a job here, in the name
of the person who asked, and says each time an answer is ready, with
the page that shows it. Every page then asks `/notifications` what is
ready and not yet seen, and shows it as a clickable notice; opening the
answer's page marks it seen.

In memory, like the assistants' own sessions: a restart forgets what
was pending, never what was recorded.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class Ready:
    """One answer ready: what it is, where it is shown."""

    number: int
    label: str
    href: str
    at: float
    seen: bool = False


@dataclass
class AIJob:
    id: str
    owner: str
    subject: str
    started_at: float
    expected: int
    ready: list[Ready] = field(default_factory=list)

    @property
    def running(self) -> bool:
        return len(self.ready) < self.expected


class AIJobs:
    """Thread-safe: answers arrive on the AI worker thread."""

    def __init__(self, clock: object = time.time) -> None:
        self._jobs: dict[str, AIJob] = {}
        self._lock = threading.Lock()
        self._clock = clock

    def _now(self) -> float:
        return float(self._clock())  # type: ignore[operator]

    def start(self, job_id: str, owner: str, subject: str, expected: int) -> None:
        with self._lock:
            self._jobs[job_id] = AIJob(job_id, owner, subject, self._now(), expected)

    def answered(self, job_id: str, label: str, href: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job.ready.append(Ready(len(job.ready) + 1, label, href, self._now()))

    def seen(self, owner: str, href: str) -> None:
        """The answer shown at `href` has been opened by `owner`."""

        with self._lock:
            for job in self._jobs.values():
                if job.owner != owner:
                    continue
                for ready in job.ready:
                    if ready.href == href:
                        ready.seen = True

    def for_owner(self, owner: str) -> tuple[int, list[tuple[AIJob, Ready]]]:
        """How many of `owner`'s jobs are still running, and the answers
        ready for them not yet opened, newest first."""

        with self._lock:
            jobs = [job for job in self._jobs.values() if job.owner == owner]
            running = sum(1 for job in jobs if job.running)
            ready = [(job, item) for job in jobs for item in job.ready if not item.seen]
        return running, sorted(ready, key=lambda pair: pair[1].at, reverse=True)
