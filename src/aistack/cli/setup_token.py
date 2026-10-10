"""
`python -m aistack.cli.setup_token` — the address that opens the
installation assistant, again (`ADR-0023` § 5), when the one install.sh
showed was lost. With Docker:

    docker compose exec web python -m aistack.cli.setup_token

Shows the token there is, or makes one when there is none; `--new`
replaces it (the old address stops working), `--reopen` opens a
finished assistant again.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aistack.config import PACKAGE_ROOT, configured
from aistack.instance import setup_wizard
from aistack.instance.yaml.store import load_instance_config_yaml

INSTANCE_CONFIG = PACKAGE_ROOT / "instance" / "definitions" / "instance_config.yml"


def address(generated: Path, token: str) -> str:
    config = load_instance_config_yaml(configured(INSTANCE_CONFIG))
    host = setup_wizard.install_answers(generated).get("HOST_ADDRESS") or config.lan_hostname
    port = config.service_ports.get("web_lan", 8186)
    return f"http://{host}:{port}/setup/open?token={token}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else None)
    parser.add_argument("--generated-dir", type=Path, default=Path("reports/generated"))
    parser.add_argument("--new", action="store_true", help="replace the token")
    parser.add_argument("--reopen", action="store_true", help="open a finished assistant again")
    arguments = parser.parse_args(argv)
    generated: Path = arguments.generated_dir

    if setup_wizard.finished(generated) and not arguments.reopen:
        print("The installation assistant is finished; --reopen opens it again.", file=sys.stderr)
        return 1
    token = setup_wizard.read_token(generated)
    if token is None or arguments.new or arguments.reopen:
        token = setup_wizard.new_token(generated, reopen=arguments.reopen)
    print(address(generated, token))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
