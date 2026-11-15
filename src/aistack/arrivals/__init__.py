"""
Arrivals (ADR-0026): notice a container or a machine that appeared, and
propose it, instead of waiting for the owner to find the gap.

AIStack already compares the declared services with the containers it
finds (`aistack.runtime.inventory_gap`) and the vigil already runs every
15 minutes. This package adds what was missing between the two: it
remembers what it has seen, says a new container *once*, after it was
seen on `confirm_passes` passes in a row (a short-lived container never
is), and prepares the declaration for the owner to accept or ignore. The
same goes for a machine that answers SSH and runs Docker, read from the
network discovery.

Nothing is declared by itself: `declare` writes only on the owner's click,
in the screen *Nouveautés*, and keeps a dated copy of what it changed.

Pure parts: `detect`, `propose`, `declare` (text in, text out). The disk
stays in `state` and `run`, Docker in `facts`.
"""

from aistack.arrivals.detect import Arrival
from aistack.arrivals.load import load_arrivals_yaml
from aistack.arrivals.run import remember, run

__all__ = ["Arrival", "load_arrivals_yaml", "remember", "run"]
