from datetime import UTC, datetime

import pytest

from asep.application import ProjectService, ProjectSessionService
from asep.errors import ProjectExecutionNotFoundError, ProjectNotFoundError, ProjectSessionNotFoundError
from asep.projects import InMemoryProjectExecutionRepository, InMemoryProjectRepository, InMemoryProjectSessionRepository


def test_session_service_validates_project_and_isolation(tmp_path) -> None:
    projects = ProjectService(InMemoryProjectRepository(), id_generator=iter(("p-1", "p-2")).__next__)
    projects.create("One", tmp_path); projects.create("Two", tmp_path)
    sessions = InMemoryProjectSessionRepository(); executions = InMemoryProjectExecutionRepository()
    service = ProjectSessionService(projects, sessions, executions, clock=lambda: datetime(2026, 8, 7, tzinfo=UTC), id_generator=lambda: "s-1")
    created = service.create("p-1", " Session ")
    assert created.title == "Session"
    assert service.list("p-1") == (created,)
    assert service.get("p-1", "s-1") == created
    with pytest.raises(ProjectSessionNotFoundError): service.get("p-2", "s-1")
    with pytest.raises(ProjectNotFoundError): service.create("missing", "x")
    with pytest.raises(ProjectExecutionNotFoundError): service.get_execution("p-1", "missing")
