from fastapi.testclient import TestClient

from asep.api import create_app
from asep.application import RunQueryService
from asep.configuration import Configuration
from asep.metrics import MetricsService
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository


def _client(*origins: str) -> TestClient:
    query = RunQueryService(
        InMemoryRunRepository(),
        InMemoryTimelineRepository(),
    )
    return TestClient(
        create_app(
            query,
            MetricsService(query),
            cors_origins=origins,
        )
    )


def test_allowed_local_origin_receives_cors_headers() -> None:
    client = _client("http://localhost:3000")

    response = client.get(
        "/api/v1/metrics/summary",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:3000"
    )


def test_disallowed_origin_does_not_receive_cors_permission() -> None:
    client = _client("http://localhost:3000")

    response = client.get(
        "/api/v1/runs",
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_preflight_is_supported_for_allowed_origin() -> None:
    client = _client("http://127.0.0.1:3000")

    response = client.options(
        "/api/v1/runs",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://127.0.0.1:3000"
    )


def test_cors_origins_are_loaded_from_explicit_environment_setting() -> None:
    settings = Configuration.load(
        {
            "ASEP_CORS_ORIGINS": (
                "http://localhost:3000, http://192.0.2.10:3000/"
            )
        }
    )

    assert settings.cors_origins == (
        "http://localhost:3000",
        "http://192.0.2.10:3000",
    )
