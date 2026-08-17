from pathlib import Path

from fastapi.testclient import TestClient

from asep.ai_runtime import (
    AIRuntimeConnectionState,
    AIRuntimeConnectionStatus,
    CodexAIRuntimeConfig,
    CodexDiagnosticsConfig,
)
from asep.api.app import create_app
from asep.api import create_default_app
from asep.configuration import ApplicationSettings
from asep.application import AIRuntimeConnectionService, RunQueryService
from asep.metrics import MetricsService
from asep.runs import InMemoryRunRepository
from asep.timeline import InMemoryTimelineRepository


class Diagnostics:
    runtime_id = "codex"
    calls = 0

    def status(self) -> AIRuntimeConnectionStatus:
        self.calls += 1
        return AIRuntimeConnectionStatus(
            runtime_id="codex", installed=True, authenticated=True,
            ready=True, state=AIRuntimeConnectionState.READY,
            version="1.2.3", message="Codex is ready.",
        )


def client(diagnostics: Diagnostics) -> TestClient:
    query = RunQueryService(InMemoryRunRepository(), InMemoryTimelineRepository())
    return TestClient(create_app(
        query, MetricsService(query),
        ai_runtime_connection_service=AIRuntimeConnectionService((diagnostics,)),
    ))


def test_runtime_list_and_status_are_safe() -> None:
    diagnostics = Diagnostics()
    api = client(diagnostics)
    status = api.get("/api/v1/ai-runtimes/codex/status")
    listing = api.get("/api/v1/ai-runtimes")
    assert status.status_code == 200
    assert listing.json()["items"] == [status.json()]
    payload = status.text.casefold()
    for secret in ("access_token", "refresh_token", "cookie", "authorization", "api key", ".codex"):
        assert secret not in payload


def test_unknown_runtime_is_404_and_existing_endpoints_remain() -> None:
    api = client(Diagnostics())
    assert api.get("/api/v1/ai-runtimes/unknown/status").status_code == 404
    assert api.get("/api/v1/health").status_code == 200
    assert api.get("/api/v1/runs").status_code == 200
    assert api.get("/api/v1/metrics/summary").status_code == 200


def test_default_composition_exposes_runtime_endpoints_without_running_diagnostics() -> None:
    app = create_default_app(ApplicationSettings())
    paths = app.openapi()["paths"]
    assert "/api/v1/ai-runtimes" in paths
    assert "/api/v1/ai-runtimes/{runtime_id}/status" in paths


def test_composition_injects_same_configured_codex_executable(
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}
    diagnostics_config = CodexDiagnosticsConfig
    runtime_config = CodexAIRuntimeConfig

    def capture_diagnostics(**kwargs):
        config = diagnostics_config(**kwargs)
        captured["diagnostics"] = config.executable
        return config

    def capture_runtime(**kwargs):
        config = runtime_config(**kwargs)
        captured["runtime"] = config.executable
        return config

    monkeypatch.setattr(
        "asep.api.composition.CodexDiagnosticsConfig", capture_diagnostics
    )
    monkeypatch.setattr(
        "asep.api.composition.CodexAIRuntimeConfig", capture_runtime
    )

    create_default_app(
        ApplicationSettings(codex_executable=r"C:\short\codex.cmd")
    )

    assert captured == {
        "diagnostics": r"C:\short\codex.cmd",
        "runtime": r"C:\short\codex.cmd",
    }
