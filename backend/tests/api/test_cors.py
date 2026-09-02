from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

from app.core.config import Settings
from app.main import app, apply_cors

CONFIGURED_ORIGIN = "http://localhost:3000"
UNTRUSTED_ORIGIN = "https://cors-probe.invalid"


def _application_with_cors(origins: list[str]) -> FastAPI:
    application = FastAPI()
    apply_cors(
        application,
        Settings(_env_file=None, cors_allowed_origins=origins),
    )

    @application.get("/probe")
    def probe() -> dict[str, str]:
        return {"status": "ok"}

    return application


def test_application_uses_cors_middleware() -> None:
    assert any(item.cls is CORSMiddleware for item in app.user_middleware)


def test_untrusted_origin_does_not_receive_wildcard_or_reflected_allow_origin() -> None:
    response = TestClient(app).get(
        "/api/v1/health",
        headers={"Origin": UNTRUSTED_ORIGIN},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("access-control-allow-origin") not in {
        "*",
        UNTRUSTED_ORIGIN,
    }


def test_configured_origin_receives_cors_allow_origin_on_get() -> None:
    client = TestClient(_application_with_cors([CONFIGURED_ORIGIN]))

    response = client.get("/probe", headers={"Origin": CONFIGURED_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == CONFIGURED_ORIGIN
    assert "access-control-allow-credentials" not in response.headers


def test_unconfigured_origin_does_not_receive_allow_origin() -> None:
    client = TestClient(_application_with_cors([CONFIGURED_ORIGIN]))

    response = client.get("/probe", headers={"Origin": UNTRUSTED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") not in {
        "*",
        UNTRUSTED_ORIGIN,
    }


def test_configured_origin_preflight_allows_get() -> None:
    client = TestClient(_application_with_cors([CONFIGURED_ORIGIN]))

    response = client.options(
        "/probe",
        headers={
            "Origin": CONFIGURED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Accept",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == CONFIGURED_ORIGIN
    allowed_methods = {
        method.strip()
        for method in response.headers["access-control-allow-methods"].split(",")
    }
    assert "GET" in allowed_methods
    assert "POST" not in allowed_methods
    assert "PUT" not in allowed_methods
    assert "DELETE" not in allowed_methods
    assert "PATCH" not in allowed_methods
