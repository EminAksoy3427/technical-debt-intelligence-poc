from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

APP_TITLE = "Technical Debt Intelligence & Governance PoC"
HEALTH_PATH = "/api/v1/health"


def _openapi_schema() -> dict:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_openapi_document_is_retrievable() -> None:
    schema = _openapi_schema()

    assert schema["info"]["title"] == APP_TITLE


def test_openapi_health_endpoint_contract() -> None:
    schema = _openapi_schema()
    paths = schema["paths"]

    assert HEALTH_PATH in paths
    assert "/health" not in paths

    health_path = paths[HEALTH_PATH]
    assert "get" in health_path

    get_operation = health_path["get"]
    assert get_operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ] == "#/components/schemas/HealthResponse"

    health_response = schema["components"]["schemas"]["HealthResponse"]
    assert health_response["type"] == "object"
    assert health_response["required"] == ["status"]
    assert health_response["properties"]["status"]["type"] == "string"
