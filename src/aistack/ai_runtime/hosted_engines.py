"""
ChatGPT (OpenAI) and Claude (Anthropic) as `AIEngine`s, beside Google Gemini.

All three are *external* engines (ADR-0029 § 3): using one sends the finding and
the collected facts (host names, paths, service names, backup mechanisms; never a
secret) outside the house, and only a caller declared `external_allowed` in
`ai_policy.yml` may reach them.

One request each, `stream: false`. The key goes in a header, never in the URL, so
no error message or log line can carry it, and `repr()` never shows it. Every
failure is returned as a sentence, never raised, as the `AIEngine` contract says.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MAX_TOKENS = 1024
_USER_AGENT = "AIStack-AIRuntime/1.0"


def post_json(name: str, url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float) -> tuple[Any, str]:
    """
    POST `payload` as JSON; return `(answer, "")`, or `(None, reason)` when the request did not
    give a readable answer. `name` opens every sentence ("ChatGPT", "Claude").
    """

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT, **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 — the declared endpoint
            return json.load(response), ""
    except TimeoutError:
        return None, f"{name} did not answer within {timeout} seconds"
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            body = json.loads(error.read().decode("utf-8", errors="replace"))
            raw = body.get("error", {}) if isinstance(body, dict) else {}
            detail = str(raw.get("message", "") if isinstance(raw, dict) else raw)
        except (OSError, ValueError, AttributeError):
            pass
        return None, f"{name} refused the request with status {error.code}" + (f": {detail[:200]}" if detail else "")
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            return None, f"{name} did not answer within {timeout} seconds"
        return None, f"{name} could not be reached: {error.reason}"
    except (ValueError, OSError) as error:
        return None, f"{name} answered with something unreadable: {error}"


class OpenAIEngine:
    """ChatGPT: `POST /v1/chat/completions`, the prompt as one user message."""

    name = "ChatGPT"

    def __init__(self, model: str, api_key: str, timeout: float = 60.0, endpoint: str = OPENAI_ENDPOINT) -> None:
        self.model = model
        self._api_key = api_key
        self.timeout = timeout
        self._endpoint = endpoint

    def __repr__(self) -> str:  # never the key
        return f"OpenAIEngine(model={self.model!r})"

    def complete(self, prompt: str) -> tuple[str, str]:
        if not self._api_key:
            return "", f"{self.name}: no API key in the environment"

        answer, reason = post_json(
            self.name,
            self._endpoint,
            {"Authorization": f"Bearer {self._api_key}"},
            {"model": self.model, "messages": [{"role": "user", "content": prompt}], "stream": False},
            self.timeout,
        )
        if answer is None:
            return "", reason

        try:
            message = answer["choices"][0]["message"]
            text = message.get("content")
        except (KeyError, IndexError, TypeError, AttributeError):
            return "", f"{self.name} gave no answer"
        if not isinstance(text, str) or not text.strip():
            refusal = message.get("refusal") if isinstance(message, dict) else None
            return "", f"{self.name} answered with no text" + (f" (refused: {str(refusal)[:120]})" if refusal else "")
        return text.strip(), ""


class AnthropicEngine:
    """Claude: `POST /v1/messages`, the prompt as one user message; `max_tokens` is required by the API."""

    name = "Claude"

    def __init__(
        self,
        model: str,
        api_key: str,
        timeout: float = 60.0,
        max_tokens: int = DEFAULT_ANTHROPIC_MAX_TOKENS,
        endpoint: str = ANTHROPIC_ENDPOINT,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens
        self._endpoint = endpoint

    def __repr__(self) -> str:  # never the key
        return f"AnthropicEngine(model={self.model!r})"

    def complete(self, prompt: str) -> tuple[str, str]:
        if not self._api_key:
            return "", f"{self.name}: no API key in the environment"

        answer, reason = post_json(
            self.name,
            self._endpoint,
            {"x-api-key": self._api_key, "anthropic-version": ANTHROPIC_VERSION},
            {"model": self.model, "max_tokens": self.max_tokens, "messages": [{"role": "user", "content": prompt}]},
            self.timeout,
        )
        if answer is None:
            return "", reason

        try:
            blocks = answer["content"]
            text = "".join(str(block.get("text", "")) for block in blocks if block.get("type") == "text")
        except (KeyError, TypeError, AttributeError):
            return "", f"{self.name} gave no answer"
        if not text.strip():
            stop = answer.get("stop_reason") if isinstance(answer, dict) else None
            return "", f"{self.name} answered with no text" + (f" (stopped: {stop})" if stop else "")
        return text.strip(), ""
