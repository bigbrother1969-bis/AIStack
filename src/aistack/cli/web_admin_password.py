"""
`python -m aistack.cli.web_admin_password` — the fallback
administrator's line for `.env.web` (`ADR-0013` § 5).

Asks the password twice, without echo, and prints the scrypt hash as a
shell assignment, single-quoted: `run_web.sh` loads `.env.web` with
`source`, and an unquoted `$` would be read as a variable. The password
itself is never printed nor written anywhere. Typical use, appending
the line without showing it:

    python -m aistack.cli.web_admin_password >> .env.web
"""

from __future__ import annotations

import getpass
import sys
from collections.abc import Callable

from aistack.authentication.definition import load_authentication_yaml
from aistack.authentication.local_admin import hash_password

MINIMUM_LENGTH = 12


def main(ask: Callable[[str], str] = getpass.getpass) -> int:
    variable = load_authentication_yaml().local_admin_env
    first = ask("Fallback administrator password: ")
    if len(first) < MINIMUM_LENGTH:
        print(f"Refused: at least {MINIMUM_LENGTH} characters.", file=sys.stderr)
        return 1
    if ask("Again: ") != first:
        print("Refused: the two passwords differ.", file=sys.stderr)
        return 1

    print(f"{variable}='{hash_password(first)}'")
    print(f"Hash written to standard output as {variable}.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
