from __future__ import annotations

from datetime import UTC, datetime
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest
from fastapi.testclient import TestClient

from asep.api.composition import create_default_app
from asep.configuration import ApplicationSettings
from asep.maintenance import MaintenanceGate, MaintenanceTimeoutError
from asep.projects import SQLiteProjectExecutionRepository, SQLiteProjectRepository, SQLiteProjectSessionRepository
from asep.projects.history_models import ProjectExecution, ProjectExecutionStatus, ProjectSession
from asep.projects.models import WorkspaceProject
from asep.ai_runtime import AIRuntimeExecutionMode
from asep.sqlite import SQLiteDatabase
from deployment.backup import BackupError, apply_retention, create_backup, restore_backup, verify_backup

NOW = datetime(2026, 8, 14, tzinfo=UTC)


def state(tmp_path: Path):
    database = tmp_path / "data" / "asep.db"
    hosted = tmp_path / "hosted"
    workspace = hosted / "org-a" / "project-a" / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (workspace / ".env").write_text("OPENAI_API_KEY=external-secret\n", encoding="utf-8")
    (workspace / "debug.log").write_text("external-secret\n", encoding="utf-8")
    SQLiteDatabase(database)
    project = WorkspaceProject(
        project_id="project-a", organization_id="org-a", created_by_user_id="user-a",
        workspace_id="workspace-a", workspace_kind="hosted", name="Project A",
        workspace_path=workspace.resolve(), created_at=NOW, updated_at=NOW,
    )
    session = ProjectSession(session_id="session-a", project_id="project-a", title="Session", created_at=NOW, updated_at=NOW)
    execution = ProjectExecution(
        execution_id="execution-a", session_id="session-a", project_id="project-a",
        organization_id="org-a", requested_by_user_id="user-a", runtime_id="codex",
        instruction="Inspect", execution_mode=AIRuntimeExecutionMode.READ_ONLY,
        status=ProjectExecutionStatus.SUCCEEDED, output="done", created_at=NOW, completed_at=NOW,
    )
    SQLiteProjectRepository(database).save(project)
    SQLiteProjectSessionRepository(database).create(session)
    SQLiteProjectExecutionRepository(database).create(execution)
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("INSERT INTO ai_usage_ledger VALUES (?,?,?,?,?,?,?)", (
            "usage-a", "org-a", "user-a", "project-a", "execution-a", NOW.isoformat(), json.dumps({"usage_id": "usage-a"}),
        ))
        connection.execute("INSERT INTO ai_quotas VALUES (?,?,?)", ("org-a", "user-a", json.dumps({"organization_id": "org-a", "user_id": "user-a"})))
        connection.commit()
    return database, hosted


def make_backup(tmp_path: Path):
    database, hosted = state(tmp_path)
    backup = create_backup(database, hosted, (tmp_path / "backups").resolve(), tmp_path / "maintenance")
    return database, hosted, backup


def test_backup_contains_consistent_sqlite_workspaces_manifest_and_checksums(tmp_path):
    _, _, backup = make_backup(tmp_path)
    manifest = verify_backup(backup)
    paths = {item["path"] for item in manifest["components"]}
    assert "asep.db" in paths
    assert "workspaces/org-a/project-a/workspace/app.py" in paths
    assert all(len(item["sha256"]) == 64 for item in manifest["components"])
    assert manifest["sqlite_schema_version"] == "4"
    assert not any(".env" in path or path.endswith(".log") for path in paths)


def test_maintenance_blocks_new_mutations_and_drains_bounded(tmp_path):
    database, hosted = state(tmp_path)
    maintenance = tmp_path / "maintenance"
    settings = ApplicationSettings(storage_backend="sqlite", sqlite_database=database, hosted_root=hosted, maintenance_directory=maintenance)
    client = TestClient(create_default_app(settings))
    gate = MaintenanceGate(maintenance)
    gate.enter()
    try:
        assert client.get("/api/v1/health").status_code == 200
        response = client.post("/api/v1/access/login", json={"email": "x", "password": "y"})
        assert response.status_code == 503
        assert str(tmp_path) not in response.text
    finally:
        gate.release()
    lease = gate.begin_mutation()
    with pytest.raises(MaintenanceTimeoutError):
        gate.enter(timeout_seconds=0)
    lease.release()


def test_symlink_escape_and_unsafe_destination_are_rejected(tmp_path, monkeypatch):
    database, hosted = state(tmp_path)
    link = hosted / "org-a" / "project-a" / "workspace" / "outside"
    link.mkdir()
    from deployment import backup as backup_module
    original = backup_module._is_reparse
    monkeypatch.setattr(backup_module, "_is_reparse", lambda path: path == link or original(path))
    with pytest.raises(BackupError, match="Symlink"):
        create_backup(database, hosted, (tmp_path / "backups").resolve(), tmp_path / "maintenance")
    monkeypatch.setattr(backup_module, "_is_reparse", original)
    link.rmdir()
    with pytest.raises(BackupError, match="disjoint"):
        create_backup(database, hosted, (hosted / "backups").resolve(), tmp_path / "maintenance")
    with pytest.raises(BackupError, match="absolute"):
        create_backup(database, hosted, Path("relative-backups"), tmp_path / "maintenance")


def test_retention_never_removes_current_backup(tmp_path):
    root = tmp_path / "backups"; root.mkdir()
    backups = [root / f"2026080{day}T000000Z-id" for day in range(1, 5)]
    for path in backups: path.mkdir()
    removed = apply_retention(root, 2, current=backups[-1])
    assert backups[-1].is_dir()
    assert len(removed) == 2


def test_restore_empty_state_preserves_projects_history_ownership_usage_and_quota(tmp_path):
    database, hosted, backup = make_backup(tmp_path)
    database.unlink(); shutil.rmtree(hosted)
    hosted.mkdir()
    gate = MaintenanceGate(tmp_path / "maintenance"); gate.enter()
    try:
        restore_backup(backup, database, hosted, tmp_path / "maintenance")
    finally:
        gate.release()
    project = SQLiteProjectRepository(database).get_for_organization("org-a", "project-a")
    assert project.created_by_user_id == "user-a"
    assert SQLiteProjectSessionRepository(database).get("session-a").project_id == "project-a"
    assert SQLiteProjectExecutionRepository(database).get("execution-a").organization_id == "org-a"
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM ai_usage_ledger").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM ai_quotas").fetchone()[0] == 1
    settings = ApplicationSettings(storage_backend="sqlite", sqlite_database=database, hosted_root=hosted, maintenance_directory=tmp_path / "maintenance")
    assert TestClient(create_default_app(settings)).get("/api/v1/ready").json() == {"status": "ready"}


def test_corruption_checksum_and_unsupported_schema_are_rejected(tmp_path):
    _, _, backup = make_backup(tmp_path)
    app = backup / "components" / "workspaces" / "org-a" / "project-a" / "workspace" / "app.py"
    app.write_text("corrupt", encoding="utf-8")
    with pytest.raises(BackupError, match="checksum"):
        verify_backup(backup)
    _, _, second = make_backup(tmp_path / "second")
    manifest_path = second / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")); manifest["sqlite_schema_version"] = "999"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(BackupError, match="schema"):
        verify_backup(second)


def test_restore_rejects_active_target_and_requires_stopped_mutations(tmp_path):
    database, hosted, backup = make_backup(tmp_path)
    gate = MaintenanceGate(tmp_path / "maintenance")
    with pytest.raises(BackupError, match="maintenance"):
        restore_backup(backup, tmp_path / "new.db", tmp_path / "new-hosted", tmp_path / "maintenance")
    gate.enter()
    try:
        with pytest.raises(BackupError, match="already exists"):
            restore_backup(backup, database, tmp_path / "new-hosted", tmp_path / "maintenance")
        with pytest.raises(BackupError, match="empty"):
            restore_backup(backup, tmp_path / "new.db", hosted, tmp_path / "maintenance")
    finally:
        gate.release()
