from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def declared_version() -> str:
    """
    The version the installed distribution declares, read from package
    metadata so it cannot drift from `pyproject.toml`; `unknown` when
    the source tree is not installed.
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
