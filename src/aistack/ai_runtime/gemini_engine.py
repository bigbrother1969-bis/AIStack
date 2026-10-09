"""
Google Gemini as an `AIEngine` (the owner, 2026-10-09, UAT of 2.0:
"Gemini d'abord et Ollama en solution de secours").

On GIGABYTE (Phenom II, Quadro P400 of 2 GB) the local models took 25
to 34 minutes for one finding and answered in broken French; a model
of Gemini's size answers in seconds and can use the facts AIStack
sends with the question. What it costs: the question leaves the
house — the finding and the facts of step 2 (host names, paths,
service names, backup mechanisms; never a secret: no fact carries
one). The assistant says so before the owner's click.

One request, the API's documented generation endpoint
(`POST /v1beta/models/<model>:generateContent`), the key in the
`x-goog-api-key` header — never in the URL, so no error message, log
line or recorded reason can carry it. Tolerant like `OllamaEngine`:
every failure is a sentence, never an exception.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from urllib.parse import quote

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_USER_AGENT = "AIStack-AIRuntime/1.0"


class GeminiEngine:
    def __init__(self, model: str, api_key: str, timeout: float = 60.0, endpoint: str = ENDPOINT) -> None:
        self.model = model
        self._api_key = api_key
        self.timeout = timeout
        self._endpoint = endpoint

    def __repr__(self) -> str:  # never the key
        return f"GeminiEngine(model={self.model!r})"

    def complete(self, prompt: str) -> tuple[str, str]:
        if not self._api_key:
            return "", "Gemini: no API key in the environment"

        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint.format(model=quote(self.model, safe="")),
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
                "x-goog-api-key": self._api_key,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 — the declared endpoint
                answer = json.load(response)
        except TimeoutError:
            return "", f"Gemini did not answer within {self.timeout} seconds"
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                payload = json.loads(error.read().decode("utf-8", errors="replace"))
                detail = str(payload.get("error", {}).get("message", ""))
            except (OSError, ValueError, AttributeError):
                pass
            return "", f"Gemini refused the request with status {error.code}" + (f": {detail}" if detail else "")
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                return "", f"Gemini did not answer within {self.timeout} seconds"
            return "", f"Gemini could not be reached: {error.reason}"
        except (ValueError, OSError) as error:
            return "", f"Gemini answered with something unreadable: {error}"

        try:
            parts = answer["candidates"][0]["content"]["parts"]
            text = "".join(str(part.get("text", "")) for part in parts)
        except (KeyError, IndexError, TypeError, AttributeError):
            blocked = answer.get("promptFeedback", {}).get("blockReason") if isinstance(answer, dict) else None
            return "", f"Gemini gave no answer{f' (blocked: {blocked})' if blocked else ''}"

        if not text.strip():
            return "", "Gemini answered with no text"
        return text, ""
