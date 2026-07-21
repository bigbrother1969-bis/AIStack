"""
Knowledge Transaction - Transport Operation Engine adapter.
"""

from __future__ import annotations

from aistack.transaction.interfaces.operation_engine import OperationEngine
from aistack.transport.contracts.transport_request import TransportRequest
from aistack.transport.interfaces.transport_engine import TransportEngine


class TransportOperationEngine(OperationEngine):
    """
    Adapts the Knowledge Transport Layer to the generic
    OperationEngine contract.
    """

    def __init__(
        self,
        transport_engine: TransportEngine,
    ) -> None:
        self._transport_engine = transport_engine

    def execute(
        self,
        payload: object,
    ) -> object:
        if not isinstance(payload, TransportRequest):
            raise TypeError(
                "TransportOperationEngine expects a TransportRequest payload."
            )

        return self._transport_engine.transport(payload)
