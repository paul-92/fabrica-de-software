from __future__ import annotations

from pathlib import Path
import sys

from deployment.preflight import MINIMUM_NODE, MINIMUM_NPM, check
from asep.providers.process import ProcessRunner


ROOT = Path(__file__).parents[3]
SYSTEMD = ROOT / "deployment" / "systemd"


def unit(name: str) -> str:
    return (SYSTEMD / name).read_text(encoding="utf-8")


def valid_environment(tmp_path: Path) -> dict[str, str]:
    database = tmp_path / "data" / "asep.db"
    database.parent.mkdir()
    hosted = tmp_path / "workspaces"
    hosted.mkdir()
    release = tmp_path / "release"
    (release / "frontend" / ".next").mkdir(parents=True)
    (release / "frontend" / ".next" / "BUILD_ID").write_text("build", encoding="utf-8")
    return {
        "ASEP_ENVIRONMENT": "production", "ASEP_STORAGE_BACKEND": "sqlite",
        "ASEP_SQLITE_DATABASE": str(database.resolve()),
        "ASEP_HOSTED_ROOT": str(hosted.resolve()),
        "ASEP_CORS_ORIGINS": "https://beta.example",
        "ASEP_ACCESS_COOKIE_SECURE": "true",
        "ASEP_LEGACY_ADMIN_EMAIL": "admin@example.test",
        "ASEP_LEGACY_ADMIN_PASSWORD": "strong-private-beta-password",
        "ASEP_RELEASE_ROOT": str(release.resolve()),
    }


def test_units_enforce_private_production_processes():
    backend = unit("asep-backend.service")
    frontend = unit("asep-frontend.service")
    assert "User=asep" in backend and "User=asep" in frontend
    assert "EnvironmentFile=/etc/asep/asep.env" in backend
    assert "EnvironmentFile=/etc/asep/asep.env" in frontend
    assert "--host 127.0.0.1 --port 8000" in backend
    assert "--hostname 127.0.0.1 --port 3000" in frontend
    combined = (backend + frontend).casefold()
    assert "--reload" not in combined and "next dev" not in combined
    assert "next build" not in combined and "0.0.0.0" not in combined


def test_preflight_accepts_complete_runtime(tmp_path):
    versions = {"/bin/node": MINIMUM_NODE, "/bin/npm": MINIMUM_NPM, "/bin/codex": (1, 0)}
    assert check(valid_environment(tmp_path), which=lambda name: f"/bin/{name}", command_version=versions.get) == ()


def test_preflight_fails_without_node_and_npm(tmp_path):
    failures = check(valid_environment(tmp_path), which=lambda name: "/bin/codex" if name == "codex" else None, command_version=lambda _: (1, 0))
    assert any("node" in item for item in failures)
    assert any("npm" in item for item in failures)


def test_preflight_handles_codex_as_required_observable_runtime(tmp_path):
    failures = check(valid_environment(tmp_path), which=lambda name: None if name == "codex" else f"/bin/{name}", command_version=lambda path: MINIMUM_NODE if path.endswith("node") else MINIMUM_NPM)
    assert any("Codex CLI" in item for item in failures)


def test_preflight_rejects_inadequate_python(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "version_info", (3, 11, 0))
    versions = {"/bin/node": MINIMUM_NODE, "/bin/npm": MINIMUM_NPM, "/bin/codex": (1, 0)}
    assert any("Python 3.12" in item for item in check(valid_environment(tmp_path), which=lambda name: f"/bin/{name}", command_version=versions.get))


def test_preflight_validates_persistence_and_does_not_echo_secrets(tmp_path):
    environment = valid_environment(tmp_path)
    secret = environment["ASEP_LEGACY_ADMIN_PASSWORD"]
    environment["ASEP_HOSTED_ROOT"] = str(tmp_path / "missing")
    versions = {"/bin/node": MINIMUM_NODE, "/bin/npm": MINIMUM_NPM, "/bin/codex": (1, 0)}
    output = "\n".join(check(environment, which=lambda name: f"/bin/{name}", command_version=versions.get))
    assert "ASEP_HOSTED_ROOT" in output
    assert secret not in output


def test_codex_state_path_is_allowlisted_but_api_keys_are_not():
    allowlist = ProcessRunner._HOST_ENVIRONMENT_ALLOWLIST
    assert "CODEX_HOME" in allowlist
    assert "OPENAI_API_KEY" not in allowlist
