from __future__ import annotations

import json


def extract_dockerfile_command(document: str) -> str | None:
    """
    The command a Dockerfile's own `CMD` instruction declares, as a
    single space-joined string — or `None` if it declares none.

    `STD-0300` § VS-4 criterion 4.2's "deployment definition" side,
    for the two containers this repository actually builds. Takes
    the file's text, not a path — the same reason
    `read_signature_catalogue` takes `document: str` rather than
    reading a file itself: a path is an I/O detail the caller
    resolves, and this stays a pure function of what the file
    contains.

    **The last `CMD` wins, matching Docker's own semantics.** Only
    one is ever in effect at build time even if a Dockerfile declares
    several — extracting the first would report an instruction
    Docker itself does not use.

    **JSON-array form is parsed; shell form is returned verbatim.**
    `CMD ["python3", "-m", "uvicorn", ...]` is what both Dockerfiles
    in this repository use, and it is parsed and rejoined with plain
    spaces, so a comparison against a command Docker itself reports
    space-joined (`docker ps`'s `Command`, `docker top`'s `CMD`
    column) is comparing like with like. `CMD python3 -m uvicorn ...`
    — the shell form — is returned exactly as written instead: it is
    already a single string, and reformatting it would risk
    asserting an equivalence this function has not actually checked.
    """

    command: str | None = None

    for line in document.splitlines():
        stripped = line.strip()

        if not stripped.startswith("CMD"):
            continue

        rest = stripped[len("CMD"):].strip()

        if not rest:
            continue

        try:
            tokens = json.loads(rest)
        except json.JSONDecodeError:
            command = rest
            continue

        if isinstance(tokens, list):
            command = " ".join(str(token) for token in tokens)
        else:
            command = rest

    return command
