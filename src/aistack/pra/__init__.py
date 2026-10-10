"""
PRA (restore) tests, as declared in `pra_tests.yml` (OPS-0009).

Not a live observation: each record is the owner's declaration of a
restore test performed by hand, plus the scheduled tests' outcomes
(`aistack.pra.scheduled`).
"""

from aistack.pra.yaml.store import load_pra_tests_yaml

__all__ = ["load_pra_tests_yaml"]
