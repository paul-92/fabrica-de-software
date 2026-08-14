"""Consistent local backup, verification, retention, and empty-target restore."""

from __future__ import annotations

import argparse
from contextlib import closing, contextmanager, nullcontext
from datetime import UTC, datetime
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
from uuid import uuid4

from asep.maintenance import MaintenanceGate
from asep.sqlite import SCHEMA_VERSION

FORMAT_VERSION = 1
EXCLUDED_DIRECTORIES = frozenset({".next", "__pycache__", ".cache", "node_modules", "tmp", "temp"})


class BackupError(RuntimeError):
    pass


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _assert_disjoint(first: Path, second: Path, message: str) -> None:
    if _is_within(first, second) or _is_within(second, first):
        raise BackupError(message)


def _is_reparse(path: Path) -> bool:
    info = path.stat(follow_symlinks=False)
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _excluded(path: Path) -> bool:
    name = path.name.casefold()
    return (
        name in EXCLUDED_DIRECTORIES
        or name == ".env"
        or name.startswith(".env.")
        or name.endswith(".log")
    )


def _copy_tree_safe(source: Path, target: Path) -> None:
    if _is_reparse(source):
        raise BackupError("Symlink or reparse point found in hosted workspaces.")
    target.mkdir(parents=True, exist_ok=False)
    for item in sorted(source.iterdir(), key=lambda value: value.name):
        if _is_reparse(item):
            raise BackupError("Symlink or reparse point found in hosted workspaces.")
        if _excluded(item):
            continue
        destination = target / item.name
        if item.is_dir():
            _copy_tree_safe(item, destination)
        elif item.is_file():
            shutil.copy2(item, destination, follow_symlinks=False)
        else:
            raise BackupError("Unsupported entry found in hosted workspaces.")


def _validate_hosted_layout(root: Path) -> None:
    if not root.is_dir() or _is_reparse(root):
        raise BackupError("Hosted root must be a safe directory.")
    for organization in root.iterdir():
        if not organization.is_dir() or _is_reparse(organization):
            raise BackupError("Unsafe hosted organization layout.")
        for project in organization.iterdir():
            if not project.is_dir() or _is_reparse(project):
                raise BackupError("Unsafe hosted project layout.")
            children = tuple(project.iterdir())
            if len(children) != 1 or children[0].name != "workspace" or not children[0].is_dir() or _is_reparse(children[0]):
                raise BackupError("Hosted projects must contain exactly one safe workspace directory.")


def _schema_version(database: Path) -> str:
    try:
        uri = database.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            check = connection.execute("PRAGMA quick_check").fetchone()
            if check is None or check[0] != "ok":
                raise BackupError("SQLite integrity validation failed.")
            row = connection.execute("SELECT value FROM schema_metadata WHERE key='schema_version'").fetchone()
    except sqlite3.Error as exc:
        raise BackupError("SQLite validation failed.") from exc
    if row is None:
        raise BackupError("SQLite schema version is missing.")
    return str(row[0])


def _backup_sqlite(source_path: Path, target_path: Path) -> str:
    uri = source_path.resolve().as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as source, closing(sqlite3.connect(target_path)) as target:
            source.backup(target)
    except sqlite3.Error as exc:
        raise BackupError("SQLite online backup failed.") from exc
    schema = _schema_version(target_path)
    if schema != SCHEMA_VERSION:
        raise BackupError("SQLite schema version is not supported.")
    return schema


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    pending = [root]
    while pending:
        current = pending.pop()
        if _is_reparse(current):
            raise BackupError("Symlink or reparse point found in backup components.")
        for item in current.iterdir():
            if _is_reparse(item):
                raise BackupError("Symlink or reparse point found in backup components.")
            if item.is_dir():
                pending.append(item)
            elif item.is_file():
                files.append(item)
            else:
                raise BackupError("Unsupported backup component entry.")
    return tuple(sorted(files))


def _component_manifest(root: Path) -> list[dict[str, object]]:
    return [
        {"path": path.relative_to(root).as_posix(), "size": path.stat().st_size, "sha256": _sha256(path)}
        for path in _safe_files(root)
    ]


@contextmanager
def maintenance(gate: MaintenanceGate, timeout_seconds: float):
    gate.enter(timeout_seconds)
    try:
        yield
    finally:
        gate.release()


def create_backup(
    database: Path,
    hosted_root: Path,
    backup_root: Path,
    maintenance_root: Path,
    *,
    retention_count: int = 7,
    timeout_seconds: float = 30.0,
    maintenance_already_active: bool = False,
    release_root: Path | None = None,
) -> Path:
    required_paths = (("Database", database), ("Hosted root", hosted_root), ("Backup root", backup_root), ("Maintenance root", maintenance_root))
    for name, value in required_paths:
        if not value.expanduser().is_absolute():
            raise BackupError(f"{name} must be absolute.")
    database, hosted_root, backup_root = map(_resolved, (database, hosted_root, backup_root))
    if not database.is_file():
        raise BackupError("SQLite database is unavailable.")
    _validate_hosted_layout(hosted_root)
    _assert_disjoint(backup_root, hosted_root, "Backup root and hosted root must be disjoint.")
    _assert_disjoint(backup_root, database.parent, "Backup root and database directory must be disjoint.")
    if release_root is not None:
        if not release_root.expanduser().is_absolute():
            raise BackupError("Release root must be absolute.")
        _assert_disjoint(backup_root, _resolved(release_root), "Backup root and release root must be disjoint.")
    if retention_count < 1:
        raise BackupError("Retention count must be at least one.")
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    staging = backup_root / f".{backup_id}.partial"
    final = backup_root / backup_id
    gate = MaintenanceGate(maintenance_root)
    try:
        if maintenance_already_active and (not gate.marker.exists() or any(gate.active.iterdir())):
            raise BackupError("Pre-existing maintenance boundary is not safely active.")
        boundary = nullcontext() if maintenance_already_active else maintenance(gate, timeout_seconds)
        with boundary:
            staging.mkdir(mode=0o700)
            components = staging / "components"
            components.mkdir()
            schema = _backup_sqlite(database, components / "asep.db")
            _copy_tree_safe(hosted_root, components / "workspaces")
            try:
                app_version = version("asep")
            except PackageNotFoundError:
                app_version = "unknown"
            manifest = {
                "format_version": FORMAT_VERSION,
                "backup_id": backup_id,
                "created_at": datetime.now(UTC).isoformat(),
                "app_version": app_version,
                "sqlite_schema_version": schema,
                "components": _component_manifest(components),
            }
            (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            verify_backup(staging, allow_partial=True)
            os.replace(staging, final)
        apply_retention(backup_root, retention_count, current=final)
        return final
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def verify_backup(path: Path, *, allow_partial: bool = False) -> dict[str, object]:
    root = _resolved(path)
    if not root.is_dir() or (root.name.startswith(".") and not allow_partial):
        raise BackupError("Backup directory is invalid or partial.")
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupError("Backup manifest is unavailable or invalid.") from exc
    if manifest.get("format_version") != FORMAT_VERSION:
        raise BackupError("Backup format is not supported.")
    if manifest.get("sqlite_schema_version") != SCHEMA_VERSION:
        raise BackupError("Backup SQLite schema is not supported.")
    components = root / "components"
    declared = {str(item["path"]): item for item in manifest.get("components", [])}
    actual = {item["path"]: item for item in _component_manifest(components)}
    if declared.keys() != actual.keys():
        raise BackupError("Backup component manifest does not match its files.")
    for name, expected in declared.items():
        observed = actual[name]
        if expected.get("sha256") != observed["sha256"] or expected.get("size") != observed["size"]:
            raise BackupError("Backup checksum validation failed.")
    if _schema_version(components / "asep.db") != SCHEMA_VERSION:
        raise BackupError("Backup SQLite schema is not supported.")
    _validate_hosted_layout(components / "workspaces")
    return manifest


def apply_retention(backup_root: Path, keep: int, *, current: Path | None = None) -> tuple[Path, ...]:
    root = _resolved(backup_root)
    if keep < 1:
        raise BackupError("Retention count must be at least one.")
    candidates = sorted(
        (path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")),
        key=lambda path: path.name,
        reverse=True,
    )
    protected = _resolved(current) if current is not None else None
    removed: list[Path] = []
    for path in candidates[keep:]:
        if protected is not None and path.resolve() == protected:
            continue
        if path.parent.resolve() != root:
            raise BackupError("Retention target escaped backup root.")
        shutil.rmtree(path)
        removed.append(path)
    return tuple(removed)


def _empty_target(path: Path, *, file_target: bool = False) -> None:
    if file_target:
        if path.exists():
            raise BackupError("Restore database target already exists.")
        if not path.parent.is_dir():
            raise BackupError("Restore database parent must already exist.")
    elif path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise BackupError("Restore hosted target must be absent or empty.")


def validate_restored_state(database: Path, hosted_root: Path, *, logical_hosted_root: Path | None = None) -> None:
    database, hosted_root = _resolved(database), _resolved(hosted_root)
    logical = _resolved(logical_hosted_root or hosted_root)
    if _schema_version(database) != SCHEMA_VERSION:
        raise BackupError("Restored SQLite schema is not supported.")
    _validate_hosted_layout(hosted_root)
    try:
        with closing(sqlite3.connect(database)) as connection:
            for row in connection.execute("SELECT id,organization_id,payload FROM projects"):
                payload = json.loads(row[2])
                if payload.get("organization_id") != row[1] or not payload.get("created_by_user_id"):
                    raise BackupError("Restored project ownership is inconsistent.")
                if payload.get("workspace_kind") == "hosted":
                    expected = (logical / row[1] / row[0] / "workspace").resolve()
                    staged_expected = (hosted_root / row[1] / row[0] / "workspace").resolve()
                    if Path(payload["workspace_path"]).resolve() != expected or not staged_expected.is_dir():
                        raise BackupError("Restored hosted project cannot be reconstructed.")
            for table in ("project_sessions", "project_executions", "ai_usage_ledger", "ai_quotas"):
                for (payload,) in connection.execute(f"SELECT payload FROM {table}"):
                    json.loads(payload)
    except (sqlite3.Error, json.JSONDecodeError, KeyError) as exc:
        raise BackupError("Restored persistence validation failed.") from exc


def restore_backup(backup: Path, database: Path, hosted_root: Path, maintenance_root: Path) -> None:
    manifest = verify_backup(backup)
    del manifest
    database, hosted_root = _resolved(database), _resolved(hosted_root)
    _empty_target(database, file_target=True)
    _empty_target(hosted_root)
    gate = MaintenanceGate(maintenance_root)
    if not gate.marker.exists() or any(gate.active.iterdir()):
        raise BackupError("Restore requires active maintenance with no mutations.")
    source = _resolved(backup) / "components"
    staged_database = database.parent / f".{database.name}.restore-{uuid4().hex}"
    staged_hosted = hosted_root.parent / f".{hosted_root.name}.restore-{uuid4().hex}"
    try:
        shutil.copy2(source / "asep.db", staged_database)
        _copy_tree_safe(source / "workspaces", staged_hosted)
        validate_restored_state(staged_database, staged_hosted, logical_hosted_root=hosted_root)
        if hosted_root.exists():
            hosted_root.rmdir()
        os.replace(staged_hosted, hosted_root)
        os.replace(staged_database, database)
        validate_restored_state(database, hosted_root)
    except Exception:
        staged_database.unlink(missing_ok=True)
        if staged_hosted.exists():
            shutil.rmtree(staged_hosted)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ASEP local backup operations")
    commands = parser.add_subparsers(dest="command", required=True)
    backup = commands.add_parser("backup")
    for item in (backup,):
        item.add_argument("--database", type=Path, required=True)
        item.add_argument("--hosted-root", type=Path, required=True)
        item.add_argument("--backup-root", type=Path, required=True)
        item.add_argument("--maintenance-root", type=Path, required=True)
    backup.add_argument("--retention-count", type=int, default=7)
    backup.add_argument("--maintenance-active", action="store_true")
    backup.add_argument("--release-root", type=Path, default=Path("/opt/asep/current"))
    verify = commands.add_parser("verify")
    verify.add_argument("backup", type=Path)
    restore = commands.add_parser("restore")
    restore.add_argument("backup", type=Path)
    restore.add_argument("--database", type=Path, required=True)
    restore.add_argument("--hosted-root", type=Path, required=True)
    restore.add_argument("--maintenance-root", type=Path, required=True)
    enter = commands.add_parser("maintenance-enter")
    enter.add_argument("--maintenance-root", type=Path, required=True)
    enter.add_argument("--timeout-seconds", type=float, default=30.0)
    release = commands.add_parser("maintenance-release")
    release.add_argument("--maintenance-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "backup":
            result = create_backup(args.database, args.hosted_root, args.backup_root, args.maintenance_root, retention_count=args.retention_count, maintenance_already_active=args.maintenance_active, release_root=args.release_root)
            print(result.name)
        elif args.command == "verify":
            print(verify_backup(args.backup)["backup_id"])
        elif args.command == "restore":
            restore_backup(args.backup, args.database, args.hosted_root, args.maintenance_root)
            print("restore verified")
        elif args.command == "maintenance-enter":
            MaintenanceGate(args.maintenance_root).enter(args.timeout_seconds)
            print("maintenance active")
        else:
            MaintenanceGate(args.maintenance_root).release()
            print("maintenance released")
        return 0
    except BackupError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
