"""
Knowledge Transport Layer - Transport Endpoint contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class TransportEndpoint:
    """
    Technology-neutral transport endpoint.
    """

    endpoint_id: str

    endpoint_type: str

    uri: str

    metadata: Mapping[str, Any] = field(default_factory=dict)
