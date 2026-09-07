from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

APP_TITLE = "Technical Debt Intelligence & Governance PoC"
HEALTH_PATH = "/api/v1/health"
CANDIDATES_PATH = "/api/v1/candidates"
CANDIDATE_DETAIL_PATH = "/api/v1/candidates/{candidate_id}"
CANDIDATE_AGENT_RUNS_PATH = "/api/v1/candidates/{candidate_id}/agent-runs"
CANDIDATE_AGENT_RUN_PATH = (
    "/api/v1/candidates/{candidate_id}/agent-runs/{agent_run_id}"
)
CONNECTORS_PATH = "/api/v1/connectors"
CONNECTOR_DETAIL_PATH = "/api/v1/connectors/{connector_id}"
HUMAN_DECISIONS_PATH = "/api/v1/candidates/{candidate_id}/human-decisions"
TECHNICAL_DEBTS_PATH = "/api/v1/technical-debts"
TECHNICAL_DEBT_DETAIL_PATH = "/api/v1/technical-debts/{technical_debt_id}"
TECHNICAL_DEBT_ACTION_PROPOSALS_PATH = (
    "/api/v1/technical-debts/{technical_debt_id}/action-proposals"
)
HUMAN_VALIDATION_AUTHORITY_FIELDS = (
    "actor_reference",
    "role",
    "approval",
    "authorization",
    "is_authorized",
    "provider",
    "model",
    "tool",
    "technical_debt_id",
)


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

    detail_schema = schema["components"]["schemas"]["CandidateDetailResponse"]
    assert "governance" in detail_schema["properties"]

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


def test_openapi_candidate_agent_run_contract_is_server_composed() -> None:
    schema = _openapi_schema()
    paths = schema["paths"]

    assert set(paths[CANDIDATE_AGENT_RUNS_PATH]) == {"post"}
    assert set(paths[CANDIDATE_AGENT_RUN_PATH]) == {"get"}

    post_operation = paths[CANDIDATE_AGENT_RUNS_PATH]["post"]
    get_operation = paths[CANDIDATE_AGENT_RUN_PATH]["get"]
    assert "requestBody" not in post_operation
    assert post_operation["responses"]["201"]["content"]["application/json"][
        "schema"
    ]["$ref"] == "#/components/schemas/AgentRunResponse"
    assert get_operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"] == "#/components/schemas/AgentRunResponse"

    serialized_post = str(post_operation).lower()
    for forbidden in (
        "prompt",
        "tools",
        "scope",
        "approval",
        "provider",
        "model_name",
        "system_prompt",
        "reasoning",
        "scratchpad",
        "chain-of-thought",
        "credentials",
        "database_url",
    ):
        assert forbidden not in serialized_post

    agent_schemas = {
        name: component
        for name, component in schema["components"]["schemas"].items()
        if any(
            term in name
            for term in (
                "AgentRun",
                "Assessment",
                "GroundedClaim",
                "PolicyDecision",
                "ToolExecution",
            )
        )
    }
    exposed_properties = {
        property_name.lower()
        for component in agent_schemas.values()
        for property_name in component.get("properties", {})
    }
    for forbidden in (
        "prompt",
        "approval",
        "provider",
        "model_name",
        "system_prompt",
        "reasoning",
        "scratchpad",
        "chain-of-thought",
        "credentials",
        "database_url",
    ):
        assert forbidden not in exposed_properties


def test_openapi_connector_inventory_contract() -> None:
    schema = _openapi_schema()
    paths = schema["paths"]

    assert CONNECTORS_PATH in paths
    assert CONNECTOR_DETAIL_PATH not in paths
    assert set(paths[CONNECTORS_PATH]) == {"get"}
    assert (
        paths[CONNECTORS_PATH]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/ConnectorListResponse"
    )

    list_schema = schema["components"]["schemas"]["ConnectorListResponse"]
    assert set(list_schema["required"]) == {"items", "count"}
    assert "items" in list_schema["properties"]
    assert "count" in list_schema["properties"]

    connector_schema = schema["components"]["schemas"]["ConnectorResponse"]
    assert set(connector_schema["required"]) == {
        "connector_id",
        "display_name",
        "version",
        "source_system",
        "transport",
        "read_only",
        "status",
    }
    assert set(connector_schema["properties"]) == {
        "connector_id",
        "display_name",
        "version",
        "source_system",
        "transport",
        "read_only",
        "status",
    }

    status_schema = connector_schema["properties"]["status"]
    assert status_schema.get("const") == "registered" or status_schema.get("enum") == [
        "registered"
    ]

    serialized_connector_schemas = str(
        {
            name: component
            for name, component in schema["components"]["schemas"].items()
            if name.startswith("Connector")
        }
    ).lower()
    for forbidden in (
        "healthy",
        "last_run",
        "last_success",
        "last_error",
        "checkpoint",
        "enabled",
        "github_repository_owner",
        "github_repository_name",
        "github_request_timeout_seconds",
        "acquire",
    ):
        assert forbidden not in serialized_connector_schemas


def test_openapi_human_validation_request_exposes_only_untrusted_intent() -> None:
    schema = _openapi_schema()
    paths = schema["paths"]

    assert set(paths[HUMAN_DECISIONS_PATH]) == {"post"}
    post_operation = paths[HUMAN_DECISIONS_PATH]["post"]
    request_schema = post_operation["requestBody"]["content"]["application/json"][
        "schema"
    ]
    if "$ref" in request_schema:
        request_schema = schema["components"]["schemas"][
            request_schema["$ref"].rsplit("/", 1)[-1]
        ]

    assert set(request_schema["properties"]) == {
        "decision",
        "rationale",
        "requested_information",
        "expected_governance_revision",
    }
    assert request_schema.get("additionalProperties") is False
    for forbidden in HUMAN_VALIDATION_AUTHORITY_FIELDS:
        assert forbidden not in request_schema["properties"]

    assert post_operation["responses"]["201"]["content"]["application/json"][
        "schema"
    ]["$ref"] == "#/components/schemas/HumanValidationResponse"


def test_openapi_technical_debt_read_contract() -> None:
    schema = _openapi_schema()
    paths = schema["paths"]

    assert set(paths[TECHNICAL_DEBTS_PATH]) == {"get"}
    assert set(paths[TECHNICAL_DEBT_DETAIL_PATH]) == {"get"}
    assert (
        paths[TECHNICAL_DEBTS_PATH]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/TechnicalDebtListResponse"
    )
    assert (
        paths[TECHNICAL_DEBT_DETAIL_PATH]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/TechnicalDebtDetailResponse"
    )

    debt_schemas = {
        name: component
        for name, component in schema["components"]["schemas"].items()
        if "TechnicalDebt" in name or name == "ActionProposalResponse"
    }
    exposed_properties = {
        property_name.lower()
        for component in debt_schemas.values()
        for property_name in component.get("properties", {})
    }
    for forbidden in (
        "risk",
        "effort",
        "priority",
        "validated_owner",
        "target_date",
        "approval",
        "execution",
        "verification",
        "github_token",
    ):
        assert forbidden not in exposed_properties

    detail_schema = schema["components"]["schemas"]["TechnicalDebtDetailResponse"]
    assert "action_proposals" in detail_schema["properties"]
    assert set(paths[TECHNICAL_DEBT_ACTION_PROPOSALS_PATH]) == {"post"}
    post_operation = paths[TECHNICAL_DEBT_ACTION_PROPOSALS_PATH]["post"]
    assert "requestBody" not in post_operation
    assert post_operation["responses"]["201"]["content"]["application/json"][
        "schema"
    ]["$ref"] == "#/components/schemas/ActionProposalResponse"

    proposal_schema = schema["components"]["schemas"]["ActionProposalResponse"]
    assert set(proposal_schema["required"]) == {
        "action_proposal_id",
        "technical_debt_id",
        "action_type",
        "target_repository_owner",
        "target_repository_name",
        "title",
        "body",
        "payload_fingerprint",
        "reconciliation_marker",
        "prepared_by",
        "created_at",
    }
    serialized_post = str(post_operation).lower()
    for forbidden in (
        "github_token",
        "approval",
        "execution",
        "verification",
        "effect",
        "scope",
    ):
        assert forbidden not in serialized_post
