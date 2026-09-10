"""
GOV-0002/OS-056: a real `pip install .` silently dropped every non-
Python data file this heritage reads from disk at runtime —
`resource_priority.yml`, `service_categorization.yml`, and (before it
was vendored) the `mermaid.min.js` `architecture.html` embeds —
because `[tool.setuptools.packages.find]` discovers Python packages
only, and nothing declared `package-data` until this same patch.

`test_the_image_declares_what_it_ships.py` already guards two facts
about `Dockerfile`'s own text: that it installs the distribution
(`pip install .`) rather than copying a tree, and that the build
context and image stay bytecode-free. Neither reads what that
install actually produces. This is the one check that does — an
integration test, not a unit test, because it shells out to `pip`
and touches the filesystem for real, the same distinction this
repository already draws for `tests/integration/scripts/`.

**Why an editable install could never have shown this.** Every
developer, and this session's own patch-verification clones, run
`pip install -e .` — which points straight back at `src/`, where
every file already exists on disk regardless of what setuptools
declares as package data. Only a real, non-editable install — what
`Dockerfile` actually runs — can tell the difference, which is
exactly why nothing noticed for as long as it went unnoticed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_EXPECTED_DATA_FILES = (
    "aistack/priority/definitions/resource_priority.yml",
    "aistack/architecture/definitions/service_categorization.yml",
    "aistack/renderers/architecture/vendor/mermaid.min.js",
)


def test_a_real_non_editable_install_carries_every_file_read_from_disk(tmp_path):
    target = tmp_path / "site-packages"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            str(REPO_ROOT),
            "--no-deps",
            "--target",
            str(target),
            "--quiet",
        ],
        check=True,
        timeout=120,
    )

    for relative in _EXPECTED_DATA_FILES:
        installed = target / relative

        assert installed.is_file(), (
            f"{relative} is missing from a real, non-editable "
            f"`pip install .` — GOV-0002/OS-056"
        )
        assert installed.stat().st_size > 0
