from pathlib import Path
import sys
import tomllib


ROOT = Path(__file__).parents[2]


def declared_range() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["requires-python"]


def test_the_suite_runs_on_the_interpreter_the_heritage_declares():
    """
    ENG-TEST-0002 is C3 and promises *reproducibility,
    deterministic execution, portability across environments*.
    Until 2026-08-23 the declared environment named its source
    roots and not its interpreter, and `pyproject.toml` declared
    three supported versions of which one was ever run —
    whichever the machine happened to have.

    That was not free. The contract inventory reported 20 orphan
    contracts on 3.11 and 22 on 3.12 and 3.13 at the same commit,
    because the tool mistook a CPython 3.12 internal for a
    contract requirement. It was found because two people ran the
    same command on two machines, not because anything checked.

    This is the check. A suite that passes on an interpreter the
    heritage does not claim proves something about a system
    nobody ships.
    """

    minimum = declared_range().removeprefix(">=").strip()

    major, minor = (int(part) for part in minimum.split("."))

    assert sys.version_info[:2] >= (major, minor), (
        f"this suite is running on Python "
        f"{sys.version_info.major}.{sys.version_info.minor} while "
        f"pyproject.toml declares {declared_range()}; the result "
        f"says nothing about what the images run"
    )


def test_the_declared_range_names_a_single_supported_version():
    """
    The owner narrowed the range on 2026-08-23 rather than build
    a matrix. A range wider than what is executed is a claim
    nobody verifies, and this asserts the decision so that
    widening it again is deliberate — and comes with the matrix
    that would make it true.
    """

    assert declared_range() == ">=3.13"
