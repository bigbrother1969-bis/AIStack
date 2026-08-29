from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def declared_version() -> str:
    """
    The version the installed distribution declares.

    **Read rather than repeated.** This module printed a literal
    `version 0.1.0` until 2026-08-29, three months after
    `pyproject.toml` started declaring the same number: two
    declarations of one fact, which drift. The literal was still
    right, and it was right by luck — nothing compared them, and
    the bump to 0.2.0 would have left it saying 0.1.0.

    A source tree that is not installed has no metadata to read,
    and that is reported as `unknown` rather than guessed. FDN-0003
    Article 12: the absence of a fact is a state, not a default.
    """

    try:
        return version("aistack")
    except PackageNotFoundError:
        return "unknown"


def main() -> None:
    print("AIStack Knowledge Operating System")
    print(f"version {declared_version()}")


if __name__ == "__main__":
    main()
