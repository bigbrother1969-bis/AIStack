"""
Any server that speaks `POST /v1/chat/completions` as an `AIEngine`.

The first user is the `llama-server` of OVHcloud's llama.cpp fork, which serves
Olala (Ollama cannot load that model); llama.cpp, vLLM and many others speak
the same request. One request, `stream: false`, the prompt as one user
message (after a system message when the caller gives one). Only the answer (`content`) is returned: a reasoning channel
(`reasoning_content`) is never shown. Every failure is returned as a sentence,
never raised, in the shapes `describe_unreachable` knows.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

_USER_AGENT = "AIStack-AIRuntime/1.0"
DEFAULT_TIMEOUT_SECONDS = 120.0
REASONING_EFFORTS = ("disabled", "low", "medium", "high")
# What the model's card advises for Olala; harmless defaults for another server.
# An engine with no reasoning answers in 100 to 400 tokens; one that loops would go on until the timeout
# (a call of 2940 tokens was seen, 20 Nov. 2026, at a low temperature). Past this it is stopped, and the
# caller hands over to the next engine.
DEFAULT_MAX_TOKENS = 800
DEFAULT_SAMPLING = {"temperature": 0.8, "top_p": 0.9, "top_k": 40, "repeat_penalty": 1.1}


class OpenAIChatEngine:
    def __init__(
        self,
        host: str,
        port: int,
        model: str,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        reasoning_effort: str | None = None,
        label: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        system: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.model = model
        self.timeout = timeout
        self.reasoning_effort = reasoning_effort
        self.label = label or model or "chat engine"
        self.temperature = temperature
        self.system = system.strip()
        self.max_tokens = max_tokens if max_tokens is not None else (
            DEFAULT_MAX_TOKENS if reasoning_effort in (None, "disabled") else None
        )

    def complete(self, prompt: str) -> tuple[str, str]:
        payload: dict[str, object] = {
            "model": self.model,
            "messages": ([{"role": "system", "content": self.system}] if self.system else [])
            + [{"role": "user", "content": prompt}],
            "stream": False,
            **{**DEFAULT_SAMPLING, **({"temperature": self.temperature} if self.temperature is not None else {})},
        }
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        request = urllib.request.Request(
            f"http://{self.host}:{self.port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": _USER_AGENT},
            method="POST",
        )
        where = f"{self.label} at {self.host}:{self.port}"

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310 — the declared engine
                answer = json.load(response)
        except TimeoutError:
            return "", f"{where} did not answer within {self.timeout} seconds"
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = error.read().decode("utf-8", errors="replace").strip()
            except OSError:
                pass
            return "", f"{self.label} refused the request with status {error.code} ({error.reason})" + (f": {detail[:200]}" if detail else "")
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                return "", f"{where} did not answer within {self.timeout} seconds"
            return "", f"{where} could not be reached: {error.reason}"
        except (ValueError, OSError) as error:
            return "", f"{self.label} answered with something unreadable: {error}"

        if not isinstance(answer, dict):
            return "", f"{self.label} answered with something unreadable"
        if "error" in answer:
            return "", f"{self.label} reported an error: {answer['error']}"

        choices = answer.get("choices")
        message = choices[0].get("message") if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
        text = message.get("content") if isinstance(message, dict) else None
        finish = choices[0].get("finish_reason") if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
        if finish == "length" and self.max_tokens is not None and isinstance(text, str) and text.strip():
            return "", f"{self.label} was stopped at {self.max_tokens} tokens without finishing, most likely repeating itself"
        if not isinstance(text, str) or not text.strip():
            if isinstance(message, dict) and str(message.get("reasoning_content") or "").strip():
                return "", f"{self.label} used its answer on reasoning and gave no final text (try a lower reasoning_effort)"
            return "", f"{self.label} answered with no response text"
        return text.strip(), ""
