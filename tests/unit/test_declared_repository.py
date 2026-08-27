from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[2]

PROCEDURE = (
    ROOT / "docs" / "04-development" / "OPS-0002-Heritage-Publication.md"
)

CANONICAL = "AIStack"


def declared_repository() -> str:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["urls"]["Repository"]


def test_the_declared_repository_carries_the_canonical_name():
    """
    The repository is `AIStack`, and `pyproject.toml` is where that
    is declared — a project fact, identical on every machine, which
    is why the Context Bundle publishes `repository_url` from here
    rather than from any clone's remote.

    It is addressed as `AISTack` on Codeberg and in the publisher's
    `origin`, and as `AIStack` on GitHub and here — measured
    2026-08-23 and still true on 2026-08-27. Gitea tolerates case in
    repository names, so nothing ever failed and nobody saw it for
    weeks. GOV-0002/OS-028.
    """

    assert declared_repository().endswith(f"/{CANONICAL}.git")


def test_the_procedure_states_the_same_name():
    """
    OPS-0002 states the canonical name; `pyproject.toml` declares
    it. Two projections of one decision, and the heritage has been
    bitten by that shape often enough to compare them — the
    classification vocabulary, the test command, the interpreter
    and the images.
    """

    body = PROCEDURE.read_text()

    assert f"**`{CANONICAL}`**" in body
