from typing import Literal

from pydantic import BaseModel

from app.connectors.contracts import ConnectorDescriptor
from app.connectors.registry import RegisteredConnector

ConnectorInventoryStatus = Literal["registered"]


class ConnectorResponse(BaseModel):
    connector_id: str
    display_name: str
    version: str
    source_system: str
    transport: str
    read_only: bool
    status: ConnectorInventoryStatus


class ConnectorListResponse(BaseModel):
    items: list[ConnectorResponse]
    count: int


def connector_response(descriptor: ConnectorDescriptor) -> ConnectorResponse:
    return ConnectorResponse(
        connector_id=descriptor.connector_id,
        display_name=descriptor.display_name,
        version=descriptor.version,
        source_system=descriptor.source_system,
        transport=descriptor.transport,
        read_only=descriptor.read_only,
        status="registered",
    )


def connector_list_response(
    registrations: tuple[RegisteredConnector, ...],
) -> ConnectorListResponse:
    items = [
        connector_response(registration.descriptor) for registration in registrations
    ]
    return ConnectorListResponse(items=items, count=len(items))
