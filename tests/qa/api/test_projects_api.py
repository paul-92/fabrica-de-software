from pathlib import Path

from fastapi.testclient import TestClient

from asep.api import create_default_app
from asep.configuration import ApplicationSettings


def test_project_http_round_trip(tmp_path: Path) -> None:
    hosted_root = tmp_path / "hosted"
    client = TestClient(create_default_app(ApplicationSettings(hosted_root=hosted_root)))
    payload = {"name": "Hosted project"}
    created = client.post("/api/v1/projects", json=payload)
    assert created.status_code == 201
    project = created.json()
    assert project["name"] == "Hosted project"
    assert project["workspace_kind"] == "hosted" and project["workspace_id"]
    assert "workspace_path" not in project
    assert (hosted_root / "legacy-local" / project["project_id"] / "workspace").is_dir()
    assert client.get("/api/v1/projects").json()["items"] == [project]
    assert client.get(f"/api/v1/projects/{project['project_id']}").json() == project


def test_project_http_validation_and_not_found(tmp_path: Path) -> None:
    client = TestClient(create_default_app(ApplicationSettings(hosted_root=tmp_path / "hosted")))
    assert client.post("/api/v1/projects", json={"name": ""}).status_code == 422
    assert client.post("/api/v1/projects", json={"name": "x", "workspace_path": str(tmp_path)}).status_code == 422
    assert client.get("/api/v1/projects/missing").status_code == 404


def test_session_http_round_trip_and_strict_contract(tmp_path: Path) -> None:
    client = TestClient(create_default_app(ApplicationSettings(hosted_root=tmp_path / "hosted")))
    project = client.post("/api/v1/projects", json={"name": "P"}).json()
    created = client.post(f"/api/v1/projects/{project['project_id']}/sessions", json={"title": " Work "})
    assert created.status_code == 201
    session = created.json()
    assert session["title"] == "Work"
    assert client.get(f"/api/v1/projects/{project['project_id']}/sessions").json()["items"] == [session]
    assert client.get(f"/api/v1/projects/{project['project_id']}/sessions/{session['session_id']}").json() == session
    assert client.post(f"/api/v1/projects/{project['project_id']}/sessions", json={"title": "x", "unknown": 1}).status_code == 422
    assert client.get(f"/api/v1/projects/{project['project_id']}/sessions/missing").status_code == 404


def test_workspace_listing_read_and_safe_errors(tmp_path: Path) -> None:
    hosted_root = tmp_path / "hosted"
    client = TestClient(create_default_app(ApplicationSettings(hosted_root=hosted_root)))
    project = client.post("/api/v1/projects", json={"name": "P"}).json()
    workspace = hosted_root / "legacy-local" / project["project_id"] / "workspace"
    (workspace / "src").mkdir(); (workspace / "src" / "sample.py").write_text("print('olá')\n", encoding="utf-8")
    (workspace / "binary").write_bytes(b"\x00\xff")
    (workspace / ".env").write_text("SECRET=x")
    base = f"/api/v1/projects/{project['project_id']}/workspace"
    listing = client.get(base).json()
    assert listing == {"path": "", "entries": [{"path": "src", "name": "src", "kind": "directory", "size": None}, {"path": "binary", "name": "binary", "kind": "file", "size": 2}]}
    content = client.get(f"{base}/file", params={"path": "src/sample.py"}).json()
    assert content["content"].splitlines() == ["print('olá')"] and content["path"] == "src/sample.py"
    assert str(tmp_path) not in str(listing) + str(content)
    assert client.get(f"{base}/file", params={"path": "..\\..\\Windows"}).status_code == 400
    assert client.get(f"{base}/file", params={"path": "binary"}).json()["error"]["code"] == "WORKSPACE_BINARY_FILE"
    assert client.get("/api/v1/projects/missing/workspace").status_code == 404
