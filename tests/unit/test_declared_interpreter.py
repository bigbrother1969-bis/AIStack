from pathlib import Path
import re
import sys
import tomllib


ROOT = Path(__file__).parents[2]

IMAGES = ("Dockerfile", "Dockerfile.selection-ui")

BASE = re.compile(r"^FROM\s+python:(\d+\.\d+)", re.M)


def declared_range() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["requires-python"]


def declared_minimum() -> str:
    return declared_range().removeprefix(">=").strip()


def image_interpreter(name: str) -> str:
    """
    The Python version an image ships, read from its base image.

    Read rather than assumed: the failure message of the test
    below has said *"the result says nothing about what the images
    run"* since 2026-08-23, while nothing in the suite opened a
    Dockerfile.
    """

    found = BASE.search((ROOT / name).read_text())

    assert found, f"{name} declares no python base image"

    return found.group(1)


def declared_dependencies() -> list[str]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    return project.get("optional-dependencies", {}).get("dev", [])


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

    major, minor = (
        int(part) for part in declared_minimum().split(".")
    )

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


def test_the_images_ship_the_interpreter_the_heritage_declares():
    """
    The other half of the sentence above, and it was missing.

    That test asserts the *suite* runs on the declared
    interpreter, and its failure message says the result "says
    nothing about what the images run" — while nothing compared
    the two. `pyproject.toml` could be raised to 3.14 and both
    Dockerfiles left at `python:3.13-slim` with the whole suite
    green, which is exactly the drift STD-0100 warns about for the
    classification vocabulary: two projections of one decision
    that shall not drift apart.

    GOV-0002/OS-025.
    """

    for name in IMAGES:
        assert image_interpreter(name) == declared_minimum(), (
            f"{name} ships Python {image_interpreter(name)} while "
            f"pyproject.toml declares {declared_range()}"
        )


def test_both_images_ship_the_same_interpreter():
    """
    Stated separately because it fails differently. The two images
    could agree with each other and both disagree with the
    declaration, or agree with the declaration and — after a
    partial edit — no longer with each other.
    """

    assert len({image_interpreter(name) for name in IMAGES}) == 1


def test_the_suite_declares_the_tool_that_runs_it():
    """
    `pytest` was configured in `pyproject.toml` and declared as a
    dependency nowhere. It was installed by hand on both machines,
    and nothing said which version either held.

    ENG-TEST-0002 is C3 and promises reproducibility. A tool the
    heritage does not declare cannot deliver it: the same governed
    command on the same commit could run two pytest versions on
    two machines with nothing to report it — GOV-0002/OS-019
    without the warning that caught it.
    """

    declared = declared_dependencies()

    assert any(spec.startswith("pytest") for spec in declared), (
        "pyproject.toml configures pytest and does not declare it"
    )
