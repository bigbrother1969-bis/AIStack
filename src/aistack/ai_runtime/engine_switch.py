"""
The client of the actuator that starts an engine when a question comes (ADR-0028, slice T4d).

An engine that costs memory (Olala: up to 10 GB of RAM) is not left running: the actuator on the host
(`aistack-engine-switch`) starts it on the first question and stops it after a quiet delay, each time
freeing what Ollama holds on the GPU. The web application and the watch only *ask* it; they hold no
power over Docker. When the actuator cannot be reached or the engine does not become ready, the
engine counts as silent and the next declared engine answers, as for any other silence.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

from aistack.ai_runtime.definition import SwitchDefinition
from aistack.ai_runtime.engine import AIEngine

TOKEN_HEADER = "X-Engine-Switch-Token"
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_of(url: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(url, threading.Lock())


class EngineSwitch:
    """Ask the actuator for the engine; one start at a time, whoever asks."""

    def __init__(self, definition: SwitchDefinition, label: str) -> None:
        self.definition = definition
        self.label = label

    def ready(self) -> str:
        """Empty when the engine is ready; otherwise the reason, as a sentence."""

        with _lock_of(self.definition.url):
            try:
                answer = self._call("start", self.definition.start_timeout + 10)
            except _Unreachable as error:
                return f"{self.label} could not be started: {error}"
        if answer.get("state") == "ready":
            return ""
        return f"{self.label} could not be started: {answer.get('reason') or answer.get('state') or 'no answer'}"

    def used(self) -> None:
        """The engine was used just now (the actuator's `touch` action); a failure here costs nothing, the actuator stops it on its own."""

        try:
            self._call("touch", 5.0)
        except _Unreachable:
            pass

    def _call(self, action: str, timeout: float) -> dict[str, object]:
        try:
            token = Path(self.definition.token_file).read_text(encoding="utf-8").strip()
        except OSError:
            raise _Unreachable("the secret of the switch cannot be read") from None
        request = urllib.request.Request(
            f"{self.definition.url}/{action}",
            data=b"{}",
            headers={TOKEN_HEADER: token, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise _Unreachable(f"the switch refused ({error.code})") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise _Unreachable("the switch cannot be reached") from None
        except ValueError:
            raise _Unreachable("the switch answered something unreadable") from None
        return body if isinstance(body, dict) else {}


class _Unreachable(Exception):
    pass


class SwitchedEngine:
    """An engine that is started on demand: no answer unless the switch says it is ready."""

    def __init__(self, inner: AIEngine, switch: EngineSwitch) -> None:
        self.inner = inner
        self.switch = switch

    def complete(self, prompt: str) -> tuple[str, str]:
        reason = self.switch.ready()
        if reason:
            return "", reason
        try:
            return self.inner.complete(prompt)
        finally:
            self.switch.used()
