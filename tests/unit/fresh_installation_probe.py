"""
Run in a process of its own by `test_fresh_installation.py`: a new
installation's application — only the shipped declarations, copied by
`config_init` into an empty configuration directory, no reference
host — asked for every page an administrator can open on the local
network. Prints one line per page: the status, then the path.

Docker, Syncthing and the AI are replaced, as in every web test: what
is checked is that the neutral declarations hold up every screen.
"""

from __future__ import annotations

import os
import re
import socket
import sys
import tempfile
from pathlib import Path

assert not os.environ.get("AISTACK_REFERENCE_DIR"), "the reference host's declarations must not be read"

generated = Path(sys.argv[1])

# What the machine running the test shows of itself says nothing shipped:
# the test's own directory (pytest's, under whatever TMPDIR names — on
# GIGABYTE /media/TechData/duplicity-tmp/pytest-of-big-brother/…), its
# home, and its host name, which the pages rightly discover (GIGABYTE
# when the suite runs there). What AIStack ships is checked for these
# names by test_fresh_installation.py on every machine, from the files.
_OWN = sorted({str(generated.parents[2]), str(Path(tempfile.gettempdir())), str(Path.home()), socket.gethostname()}, key=len, reverse=True)
_OWN_PATHS = re.compile("|".join(re.escape(own) for own in _OWN if own))
_REFERENCE = re.compile(r"GIGABYTE|persiaut|TechData|[Rr]aspberry|PNTJYZD|big-brother|192\.168\.1\.10|sarfatti")


def reference_names(text: str) -> list[str]:
    return _REFERENCE.findall(_OWN_PATHS.sub("", text))


from aistack.cli import console_render, health_render  # noqa: E402

# Both write to reports/generated under the working directory.
os.chdir(generated.parent.parent)
console_render.main()
health_render.main()
for page in ("console.html", "health.html"):
    text = (generated / page).read_text(encoding="utf-8")
    found = reference_names(text)
    print("RENDERED", page, sorted(set(found)))

from tests.unit.web.test_rights import LAN_PORT, build, client  # noqa: E402
from tests.unit.web_signed_in import signed_in  # noqa: E402

from aistack.web.authentication import build_authentication  # noqa: E402

app = build(generated)
# The sign-in as the new installation's own declaration says, not the
# suite's fake provider.
app.state.authentication = build_authentication(generated, "http://localhost:8186")
web = signed_in(client(app, LAN_PORT))
for prefix, router, _guard in app.state.routers:
    for route in router.routes:
        if "GET" not in getattr(route, "methods", ()) or "{" in route.path:
            continue
        path = prefix + route.path
        reply = web.get(path + ("?lang=fr" if "?" not in path else ""))
        print(reply.status_code, path)
        text = reply.text if reply.headers.get("content-type", "").startswith("text/html") else ""
        found = reference_names(text)
        if found:
            print("REFERENCE", path, sorted(set(found)))
