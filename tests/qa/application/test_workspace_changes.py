from pathlib import Path

import pytest

from asep.application.workspace_changes import (
    WorkspaceChangeType,
    WorkspaceSnapshotLimitError,
    WorkspaceSnapshotPolicy,
    WorkspaceSnapshotter,
)


def test_detects_created_modified_deleted_nested_and_sorted(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "modified.txt").write_text("before", encoding="utf-8")
    (tmp_path / "deleted.txt").write_text("delete", encoding="utf-8")
    snapshotter = WorkspaceSnapshotter()
    before = snapshotter.capture(tmp_path)
    (tmp_path / "modified.txt").write_text("after", encoding="utf-8")
    (tmp_path / "deleted.txt").unlink()
    (tmp_path / "nested" / "created.txt").write_text("new", encoding="utf-8")
    changes = snapshotter.changes(before, snapshotter.capture(tmp_path))
    assert [(item.path, item.change_type) for item in changes] == [
        ("deleted.txt", WorkspaceChangeType.DELETED),
        ("modified.txt", WorkspaceChangeType.MODIFIED),
        ("nested/created.txt", WorkspaceChangeType.CREATED),
    ]
    assert all(not Path(item.path).is_absolute() for item in changes)


def test_no_changes_and_sensitive_paths_are_ignored(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir(); (tmp_path / ".git" / "index").write_bytes(b"secret")
    (tmp_path / ".env").write_text("TOKEN=secret", encoding="utf-8")
    snapshotter = WorkspaceSnapshotter()
    snapshot = snapshotter.capture(tmp_path)
    assert snapshot == {}
    assert snapshotter.changes(snapshot, snapshotter.capture(tmp_path)) == ()


def test_limits_fail_closed(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("12345", encoding="utf-8")
    with pytest.raises(WorkspaceSnapshotLimitError):
        WorkspaceSnapshotter(WorkspaceSnapshotPolicy(max_file_size=4)).capture(tmp_path)


def test_symlink_escape_is_not_followed(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(); (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = tmp_path / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable on this Windows environment")
    assert WorkspaceSnapshotter().capture(tmp_path) == {}
