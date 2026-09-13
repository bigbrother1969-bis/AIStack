from __future__ import annotations

import json
import urllib.error
import urllib.request

_USER_AGENT = "AIStack-AIRuntime/1.0"

# Ollama generation is not a sub-second HTTP call — GIGABYTE's own
# GPU (`Quadro P400`, 2 GB VRAM, confirmed real hardware,
# `claude/PLAN-J11-CONSOLE-2026-09-11.md` § 10.1) is small enough
# that a real model may run partly or wholly on CPU. 5 seconds
# (`BeszelProvider`'s own default, a plain read against an already-
# computed API) would time out a real generation before it produced
# anything. Chosen as a first, generous number to revise once a real
# call has been timed against the real instance, the same way the
# 50 %/15 s CPU-threshold numbers were chosen as a starting guess
# (`CpuThresholdDetectorDefinition`'s own docstring).
DEFAULT_TIMEOUT_SECONDS = 120.0


class OllamaEngine:
    """
    Ask a real Ollama instance to complete a prompt —
    `aistack.ai_runtime.engine.AIEngine`'s only implementation today
    (J6, `claude/PLAN-TRAJECTOIRE-2026-09-04.md`).

    One request, Ollama's own documented generation endpoint
    (`POST /api/generate`, `stream: false` so the whole answer comes
    back as one JSON object rather than a stream of partial ones —
    this class has no caller yet that would consume a stream, and
    consuming one only to concatenate it here would be the same
    shape as `stream: false` with extra steps).

    **Unreachable is a state, not an error — the same reasoning
    `BeszelProvider`/`NetworkDockerDiscoveryProvider` already hold.**
    No Ollama at this host/port, a model not pulled
    (`aistack.ai_runtime.definition.AIRuntimeDefinition.model` naming
    one Ollama has never heard of), a generation that outlives
    `timeout` are all ordinary, not exceptional — `complete` reports
    each into the same kind of sentence those two providers already
    use, never raises.

    **No `User-Agent` lesson assumed away.** `BeszelProvider` found,
    2026-09-12, that a fronting proxy can reject `urllib`'s own
    default string outright; nothing here is known to front Ollama on
    a bare LAN host, but declaring one explicitly costs nothing and
    keeps this class consistent with every other network client this
    heritage writes, rather than relying on today's absence of a
    proxy to stay true.
    """

    def __init__(
        self,
        host: str,
        port: int,
        model: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.host = host
        self.port = port
        self.model = model
        self.timeout = timeout

    def complete(self, prompt: str) -> tuple[str, str]:
        body = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False}
        ).encode("utf-8")

        request = urllib.request.Request(
            f"http://{self.host}:{self.port}/api/generate",
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout
            ) as response:
                answer = json.load(response)

        except TimeoutError:
            return "", (
                f"Ollama at {self.host}:{self.port} did not answer "
                f"within {self.timeout} seconds"
            )

        except urllib.error.HTTPError as error:
            body_text = ""

            try:
                body_text = error.read().decode("utf-8", errors="replace")
            except OSError:
                pass

            return "", (
                f"Ollama refused the request with status {error.code} "
                f"({error.reason})"
                + (f": {body_text.strip()}" if body_text.strip() else "")
            )

        except urllib.error.URLError as error:

            if isinstance(error.reason, TimeoutError):
                return "", (
                    f"Ollama at {self.host}:{self.port} did not answer "
                    f"within {self.timeout} seconds"
                )

            return "", (
                f"Ollama at {self.host}:{self.port} could not be "
                f"reached: {error.reason}"
            )

        except (ValueError, OSError) as error:
            return "", f"Ollama answered with something unreadable: {error}"

        if not isinstance(answer, dict):
            return "", "Ollama answered with something unreadable"

        if "error" in answer:
            return "", f"Ollama reported an error: {answer['error']}"

        text = answer.get("response", "")

        if not text:
            return "", "Ollama answered with no response text"

        return text, ""
