"""
What one application of AIStack is, declared in YAML rather than code.

The model names a technology (Syncthing), so it lives outside the
Kernel (ADR-0027 § 7); `aistack.application.yaml` loads it.
"""

from aistack.application.core import ApplicationDefinition, SyncthingDefinition

__all__ = [
    "ApplicationDefinition",
    "SyncthingDefinition",
]
