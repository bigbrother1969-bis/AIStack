from __future__ import annotations

import json
import urllib.error
import urllib.request

_USER_AGENT = "AIStack-AIRuntime/1.0"

# Generation on a small GPU or on CPU can take minutes; this is a generous
# first estimate, not a measured value.
DEFAULT_TIMEOUT_SECONDS = 120.0


class OllamaEngine:
    """
    Ask an Ollama instance to complete a prompt via `POST /api/generate`
    (`stream: false`, so the answer comes back as one JSON object).

    An unreachable host, an unknown model or a timeout are reported as a
    reason, never raised. An explicit `User-Agent` is sent because some
    proxies reject `urllib`'s default.
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
