from pathlib import Path

from fastapi.testclient import TestClient

from asep.api import create_default_app
from asep.configuration import ApplicationSettings


def test_project_http_round_trip(tmp_path: Path) -> None:
    client = TestClient(create_default_app(ApplicationSettings()))
    payload = {"name": "Local project", "workspace_path": str(tmp_path)}
    created = client.post("/api/v1/projects", json=payload)
    assert created.status_code == 201
    project = created.json()
    assert project["name"] == "Local project"
    assert Path(project["workspace_path"]) == tmp_path.resolve()
    assert client.get("/api/v1/projects").json()["items"] == [project]
    assert client.get(f"/api/v1/projects/{project['project_id']}").json() == project


def test_project_http_validation_and_not_found(tmp_path: Path) -> None:
    client = TestClient(create_default_app(ApplicationSettings()))
    assert client.post("/api/v1/projects", json={"name": "", "workspace_path": str(tmp_path)}).status_code == 422
    assert client.post("/api/v1/projects", json={"name": "x", "workspace_path": str(tmp_path / 'missing')}).status_code == 400
    assert client.get("/api/v1/projects/missing").status_code == 404
