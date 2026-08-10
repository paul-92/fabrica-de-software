from pathlib import Path

import pytest

from asep.application import ProjectService, ProjectWorkspaceService, WorkspaceBrowsingPolicy
from asep.errors import (
    ProjectNotFoundError, WorkspaceBinaryFileError, WorkspaceDirectoryTooLargeError,
    WorkspaceEntryNotFileError, WorkspaceFileTooLargeError, WorkspacePathForbiddenError, WorkspacePathInvalidError,
)
from asep.projects import InMemoryProjectRepository


def browsing(root: Path, policy: WorkspaceBrowsingPolicy | None = None) -> ProjectWorkspaceService:
    projects = ProjectService(InMemoryProjectRepository(), id_generator=lambda: "p-1")
    projects.create("P", root)
    return ProjectWorkspaceService(projects, policy)


def test_lists_immediate_children_lazily_and_deterministically(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "A").mkdir(); (tmp_path / "A" / "nested.py").write_text("print('á')\n", encoding="utf-8")
    (tmp_path / ".git").mkdir(); (tmp_path / ".env").write_text("SECRET=x", encoding="utf-8")
    root = browsing(tmp_path).list_directory("p-1")
    assert [(item.path, item.kind.value) for item in root.entries] == [("A", "directory"), ("z.txt", "file")]
    assert [item.path for item in browsing(tmp_path).list_directory("p-1", "A").entries] == ["A/nested.py"]


def test_reads_utf8_bom_unicode_multiline_and_language(tmp_path: Path) -> None:
    (tmp_path / "code.py").write_bytes(b"\xef\xbb\xbfprint('ol\xc3\xa1')\nsecond\n")
    content = browsing(tmp_path).read_file("p-1", "code.py")
    assert content.content == "print('olá')\nsecond\n"
    assert content.language == "python" and not content.truncated
    assert str(tmp_path) not in content.path


def test_rejects_traversal_absolute_sensitive_binary_large_and_directory(tmp_path: Path) -> None:
    (tmp_path / "binary").write_bytes(b"\x00\xff")
    (tmp_path / "large.txt").write_text("12345", encoding="utf-8")
    (tmp_path / ".env.local").write_text("x", encoding="utf-8")
    service = browsing(tmp_path, WorkspaceBrowsingPolicy(max_file_size=4))
    for path in ("../outside", "..\\..\\Windows", "C:\\Windows", "//server/share", ".env.local"):
        with pytest.raises(WorkspacePathForbiddenError): service.read_file("p-1", path)
    with pytest.raises(WorkspaceBinaryFileError): browsing(tmp_path).read_file("p-1", "binary")
    with pytest.raises(WorkspaceFileTooLargeError): service.read_file("p-1", "large.txt")
    with pytest.raises(WorkspacePathInvalidError): service.read_file("p-1", "")


def test_limits_directory_and_rejects_unknown_project(tmp_path: Path) -> None:
    (tmp_path / "a").write_text("a"); (tmp_path / "b").write_text("b")
    service = browsing(tmp_path, WorkspaceBrowsingPolicy(max_directory_entries=1))
    with pytest.raises(WorkspaceDirectoryTooLargeError): service.list_directory("p-1")
    with pytest.raises(ProjectNotFoundError): service.list_directory("missing")


def test_symlink_escape_is_forbidden(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(); (outside / "secret.txt").write_text("secret")
    link = tmp_path / "link"
    try: link.symlink_to(outside, target_is_directory=True)
    except OSError: pytest.skip("symlink creation unavailable")
    service = browsing(tmp_path)
    assert all(item.name != "link" for item in service.list_directory("p-1").entries)
    with pytest.raises(WorkspacePathForbiddenError): service.read_file("p-1", "link/secret.txt")
