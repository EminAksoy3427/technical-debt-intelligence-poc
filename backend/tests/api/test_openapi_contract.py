from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

APP_TITLE = "Technical Debt Intelligence & Governance PoC"
HEALTH_PATH = "/api/v1/health"
CANDIDATES_PATH = "/api/v1/candidates"
CANDIDATE_DETAIL_PATH = "/api/v1/candidates/{candidate_id}"


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
    assert (
        get_operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ]
        == "#/components/schemas/HealthResponse"
    )

    health_response = schema["components"]["schemas"]["HealthResponse"]
    assert health_response["type"] == "object"
    assert health_response["required"] == ["status"]
    assert health_response["properties"]["status"]["type"] == "string"


def test_openapi_candidate_read_contract_has_no_governance_fields() -> None:
    schema = _openapi_schema()
    paths = schema["paths"]

    assert CANDIDATES_PATH in paths
    assert CANDIDATE_DETAIL_PATH in paths
    assert set(paths[CANDIDATES_PATH]) == {"get"}
    assert set(paths[CANDIDATE_DETAIL_PATH]) == {"get"}
    assert (
        paths[CANDIDATES_PATH]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/CandidateListResponse"
    )
    assert (
        paths[CANDIDATE_DETAIL_PATH]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/CandidateDetailResponse"
    )

    candidate_schemas = {
        name: component
        for name, component in schema["components"]["schemas"].items()
        if "Candidate" in name
    }
    serialized_schemas = str(candidate_schemas).lower()
    for forbidden in (
        "review_status",
        "validation_status",
        "decision_status",
        "technical_debt_status",
        "risk_score",
        "effort",
        "priority",
        "suggested_team",
        "recommended_owner",
        "confidence",
    ):
        assert forbidden not in serialized_schemas

    dependency_schema = candidate_schemas["CandidateDependencyContextResponse"]
    reachability_description = dependency_schema["properties"]["reachable_dependents"][
        "description"
    ]
    assert "dependency graph" in reachability_description
    assert "not guaranteed outage or causal impact" in reachability_description
