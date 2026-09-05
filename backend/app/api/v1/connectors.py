from fastapi import APIRouter

from app.api.v1.connector_schemas import ConnectorListResponse, connector_list_response
from app.connectors.registry import list_connectors

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("", response_model=ConnectorListResponse)
def get_connectors() -> ConnectorListResponse:
    return connector_list_response(list_connectors())
