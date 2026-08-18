"""Provisionamento seguro e reproduzível de dependências de projeto."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict
from asep.providers.process import ProcessRunner


class DependencyProvisioningMode(StrEnum):
    CACHED = "cached"
    ONLINE_CONTROLLED = "online-controlled"

class DependencyProvisioningStatus(StrEnum):
    AVAILABLE="dependency_available"; PROVISIONED="dependency_provisioned"; MISSING="dependency_missing"; POLICY_BLOCKED="dependency_policy_blocked"; REGISTRY_UNAVAILABLE="dependency_registry_unavailable"; APPROVAL_REQUIRED="dependency_approval_required"; FAILED="dependency_provisioning_failed"

class StructuredDependencyRequest(BaseModel):
    model_config=ConfigDict(extra="forbid", frozen=True)
    package:str; version:str; reason:str; ecosystem:str="node"
    status:DependencyProvisioningStatus=DependencyProvisioningStatus.APPROVAL_REQUIRED

class DependencyRequestDecision(StrEnum): PENDING="pending"; APPROVED="approved"; REJECTED="rejected"
class StoredDependencyRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",frozen=True)
    request_id:str; project_id:str; session_id:str; execution_id:str; ecosystem:str; package:str
    requested_version:str; reason:str; registry:str; status:DependencyRequestDecision=DependencyRequestDecision.PENDING
    created_at:datetime; resolved_at:datetime|None=None; resolved_by:str|None=None; version:int=1

class SQLiteDependencyRequestRepository:
    def __init__(self,database:Path):
        self.database=database.expanduser().resolve(); self.database.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.database) as db: db.execute("CREATE TABLE IF NOT EXISTS dependency_request (request_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, payload TEXT NOT NULL)")
    def create(self,*,project_id:str,session_id:str,execution_id:str,package:str,requested_version:str,reason:str,registry:str)->StoredDependencyRequest:
        item=StoredDependencyRequest(request_id=str(uuid4()),project_id=project_id,session_id=session_id,execution_id=execution_id,ecosystem="node",package=package,requested_version=requested_version,reason=reason,registry=registry,created_at=datetime.now(UTC))
        with sqlite3.connect(self.database) as db: db.execute("INSERT INTO dependency_request VALUES (?,?,?)",(item.request_id,project_id,item.model_dump_json()))
        return item
    def get(self,project_id:str,request_id:str)->StoredDependencyRequest|None:
        with sqlite3.connect(self.database) as db: row=db.execute("SELECT payload FROM dependency_request WHERE project_id=? AND request_id=?",(project_id,request_id)).fetchone()
        return None if row is None else StoredDependencyRequest.model_validate_json(row[0])
    def list(self,project_id:str)->tuple[StoredDependencyRequest,...]:
        with sqlite3.connect(self.database) as db: rows=db.execute("SELECT payload FROM dependency_request WHERE project_id=? ORDER BY rowid",(project_id,)).fetchall()
        return tuple(StoredDependencyRequest.model_validate_json(row[0]) for row in rows)
    def resolve(self,project_id:str,request_id:str,decision:DependencyRequestDecision,resolved_by:str,expected_version:int)->StoredDependencyRequest:
        item=self.get(project_id,request_id)
        if item is None: raise KeyError(request_id)
        if item.version!=expected_version or decision is DependencyRequestDecision.PENDING: raise ValueError("dependency request conflict")
        updated=item.model_copy(update={"status":decision,"resolved_at":datetime.now(UTC),"resolved_by":resolved_by,"version":item.version+1})
        with sqlite3.connect(self.database) as db: db.execute("UPDATE dependency_request SET payload=? WHERE request_id=? AND project_id=?",(updated.model_dump_json(),request_id,project_id))
        return updated

class ProvisioningEvidence(BaseModel):
    model_config=ConfigDict(extra="forbid",frozen=True)
    evidence_id:str; execution_id:str; project_id:str; dependency_request_id:str|None=None
    ecosystem:str="node"; package_manager:str; registry:str; status:DependencyProvisioningStatus
    cache_mode:str="runtime-managed"; created_at:datetime; completed_at:datetime|None=None; error_code:str|None=None
class SQLiteProvisioningEvidenceRepository:
    def __init__(self,database:Path):
        self.database=database.expanduser().resolve(); self.database.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.database) as db: db.execute("CREATE TABLE IF NOT EXISTS provisioning_evidence (evidence_id TEXT PRIMARY KEY, execution_id TEXT NOT NULL, project_id TEXT NOT NULL, payload TEXT NOT NULL)")
    def save(self,item:ProvisioningEvidence):
        with sqlite3.connect(self.database) as db: db.execute("INSERT OR REPLACE INTO provisioning_evidence VALUES (?,?,?,?)",(item.evidence_id,item.execution_id,item.project_id,item.model_dump_json()))
    def for_execution(self,project_id:str,execution_id:str):
        with sqlite3.connect(self.database) as db: rows=db.execute("SELECT payload FROM provisioning_evidence WHERE project_id=? AND execution_id=?",(project_id,execution_id)).fetchall()
        return tuple(ProvisioningEvidence.model_validate_json(row[0]) for row in rows)

class DependencyBrokerRunner(Protocol):
    def run(self, command:tuple[str,...], *, working_directory:Path, environment:Mapping[str,str], timeout:float): ...

class ControlledDependencyBrokerRunner:
    def __init__(self, runner:ProcessRunner|None=None): self._runner=runner or ProcessRunner()
    def run(self,command:tuple[str,...],*,working_directory:Path,environment:Mapping[str,str],timeout:float):
        return self._runner.run(command,input_text="",timeout=timeout,working_directory=working_directory,environment=environment,encoding="utf-8")


class DependencyProvisioningBlockedError(RuntimeError):
    """A política não permite provisionar a dependência solicitada."""


class DependencyProvisioningEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ecosystem: str
    package_manager: str
    registry: str
    mode: DependencyProvisioningMode
    dependencies_resolved: tuple[str, ...] = ()
    cache_location: str = "runtime-managed"
    succeeded: bool
    blocker: str | None = None
    status: DependencyProvisioningStatus = DependencyProvisioningStatus.AVAILABLE


class DependencyProvisioningPreparation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    environment: Mapping[str, str]
    evidence: DependencyProvisioningEvidence


class ProjectDependencyProvisioningService:
    """Prepara caches confinados; não instala pacotes nem amplia a rede do Codex."""

    _PACKAGE_MANAGER = re.compile(r"^(npm|pnpm)@([0-9]+(?:\.[0-9]+){2}(?:[-+][0-9A-Za-z.-]+)?)$")
    _PACKAGE_NAME = re.compile(r"^(?:@[a-z0-9._-]+/)?[a-z0-9._-]+$")

    def __init__(self, registries: tuple[str, ...] = ("https://registry.npmjs.org/",)) -> None:
        self._registries = tuple(self._validate_registry(item) for item in registries)
        if not self._registries:
            raise ValueError("ao menos um registry aprovado é obrigatório")

    def prepare_node(self, workspace: Path, *, registry: str | None = None) -> DependencyProvisioningPreparation | None:
        root = workspace.expanduser().resolve()
        manifest_path = root / "package.json"
        if not manifest_path.is_file():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DependencyProvisioningBlockedError("package.json inválido") from exc
        package_manager = manifest.get("packageManager", "npm@10.0.0")
        match = self._PACKAGE_MANAGER.fullmatch(package_manager) if isinstance(package_manager, str) else None
        if match is None:
            raise DependencyProvisioningBlockedError("packageManager deve declarar npm ou pnpm com versão exata")
        manager = match.group(1)
        selected_registry = self._validate_registry(registry or self._registries[0])
        if selected_registry not in self._registries:
            raise DependencyProvisioningBlockedError("registry não aprovado")
        dependencies = self._declared_dependencies(manifest)
        runtime = (root / ".asep" / "runtime").resolve()
        runtime.relative_to(root)
        npm_cache, corepack, pnpm_home, pnpm_store = (
            runtime / "npm-cache", runtime / "corepack", runtime / "pnpm-home", runtime / "pnpm-store"
        )
        for directory in (npm_cache, corepack, pnpm_home, pnpm_store):
            directory.mkdir(parents=True, exist_ok=True)
        environment = {
            "NPM_CONFIG_CACHE": str(npm_cache),
            "NPM_CONFIG_OFFLINE": "true",
            "NPM_CONFIG_REGISTRY": selected_registry,
            "COREPACK_HOME": str(corepack),
            "PNPM_HOME": str(pnpm_home),
            "PNPM_STORE_DIR": str(pnpm_store),
        }
        return DependencyProvisioningPreparation(
            environment=environment,
            evidence=DependencyProvisioningEvidence(
                ecosystem="node", package_manager=manager, registry=selected_registry,
                mode=DependencyProvisioningMode.CACHED,
                dependencies_resolved=dependencies, succeeded=True,
            ),
        )

    def request_undeclared(self, workspace: Path, *, package: str, version: str, reason: str) -> StructuredDependencyRequest:
        prepared=self.prepare_node(workspace); declared=() if prepared is None else prepared.evidence.dependencies_resolved
        if package in declared: raise ValueError("dependency is already declared")
        if self._PACKAGE_NAME.fullmatch(package) is None or not version.strip() or not reason.strip(): raise DependencyProvisioningBlockedError("invalid dependency request")
        return StructuredDependencyRequest(package=package,version=version,reason=reason)

    def provision_node(self, workspace:Path, runner:DependencyBrokerRunner, *, registry:str|None=None, timeout:float=300.0)->DependencyProvisioningPreparation:
        prepared=self.prepare_node(workspace,registry=registry)
        if prepared is None: raise DependencyProvisioningBlockedError("dependency_missing")
        root=workspace.expanduser().resolve(); manifest=json.loads((root/"package.json").read_text(encoding="utf-8"))
        specs=[]
        for field in ("dependencies","devDependencies","optionalDependencies"):
            specs.extend(f"{name}@{version}" for name,version in sorted(manifest.get(field,{}).items()))
        online_env={key:value for key,value in prepared.environment.items() if key!="NPM_CONFIG_OFFLINE"}
        online_env["NPM_CONFIG_IGNORE_SCRIPTS"]="true"
        manager=prepared.evidence.package_manager
        commands=(("corepack","pnpm","fetch","--frozen-lockfile","--ignore-scripts"),) if manager=="pnpm" else tuple(("npm","cache","add",spec,"--ignore-scripts") for spec in specs)
        try:
            for command in commands:
                result=runner.run(command,working_directory=root,environment=online_env,timeout=timeout)
                if result.exit_code!=0:
                    status=DependencyProvisioningStatus.REGISTRY_UNAVAILABLE if any(token in result.stderr.casefold() for token in ("enotfound","econn","timeout")) else DependencyProvisioningStatus.FAILED
                    raise DependencyProvisioningBlockedError(status.value)
        except DependencyProvisioningBlockedError: raise
        except Exception as exc: raise DependencyProvisioningBlockedError(DependencyProvisioningStatus.FAILED.value) from exc
        return prepared.model_copy(update={"evidence":prepared.evidence.model_copy(update={"mode":DependencyProvisioningMode.ONLINE_CONTROLLED,"status":DependencyProvisioningStatus.PROVISIONED})})

    def provision_requests(self, workspace: Path, runner: DependencyBrokerRunner, *,
                           requests: tuple[Mapping[str, str], ...], timeout: float = 300.0
                           ) -> DependencyProvisioningPreparation:
        """Populate the confined npm cache from already-approved structured requests."""
        root = workspace.expanduser().resolve()
        registry = self._validate_registry(requests[0].get("registry") or self._registries[0])
        if registry not in self._registries:
            raise DependencyProvisioningBlockedError("dependency_policy_blocked")
        runtime = (root / ".asep" / "runtime").resolve()
        runtime.relative_to(root)
        npm_cache = runtime / "npm-cache"
        npm_cache.mkdir(parents=True, exist_ok=True)
        environment = {
            "NPM_CONFIG_CACHE": str(npm_cache),
            "NPM_CONFIG_REGISTRY": registry,
            "NPM_CONFIG_IGNORE_SCRIPTS": "true",
        }
        specs = tuple(f'{item["package"]}@{item["requested_version"]}' for item in requests)
        try:
            for spec in specs:
                result = runner.run(("npm", "cache", "add", spec, "--ignore-scripts"),
                                    working_directory=root, environment=environment, timeout=timeout)
                if result.exit_code != 0:
                    status = (DependencyProvisioningStatus.REGISTRY_UNAVAILABLE
                              if any(token in result.stderr.casefold() for token in ("enotfound", "econn", "timeout"))
                              else DependencyProvisioningStatus.FAILED)
                    raise DependencyProvisioningBlockedError(status.value)
        except DependencyProvisioningBlockedError:
            raise
        except Exception as exc:
            raise DependencyProvisioningBlockedError(DependencyProvisioningStatus.FAILED.value) from exc
        return DependencyProvisioningPreparation(
            environment=environment,
            evidence=DependencyProvisioningEvidence(
                ecosystem="node", package_manager="npm", registry=registry,
                mode=DependencyProvisioningMode.ONLINE_CONTROLLED,
                dependencies_resolved=tuple(item["package"] for item in requests),
                succeeded=True, status=DependencyProvisioningStatus.PROVISIONED,
            ),
        )

    @classmethod
    def _declared_dependencies(cls, manifest: object) -> tuple[str, ...]:
        if not isinstance(manifest, dict):
            raise DependencyProvisioningBlockedError("package.json deve ser um objeto")
        names: set[str] = set()
        for field in ("dependencies", "devDependencies", "optionalDependencies"):
            values = manifest.get(field, {})
            if not isinstance(values, dict):
                raise DependencyProvisioningBlockedError(f"{field} inválido")
            for name, version in values.items():
                if not isinstance(name, str) or cls._PACKAGE_NAME.fullmatch(name) is None:
                    raise DependencyProvisioningBlockedError("nome de dependência inválido")
                if not isinstance(version, str) or any(token in version.casefold() for token in ("http:", "https:", "git:", "file:")):
                    raise DependencyProvisioningBlockedError("fontes arbitrárias de dependência não são permitidas")
                names.add(name)
        return tuple(sorted(names))

    @staticmethod
    def _validate_registry(value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise DependencyProvisioningBlockedError("registry deve ser uma URL HTTPS sem credenciais")
        path = parsed.path or "/"
        return f"https://{parsed.hostname.casefold()}{path if path.endswith('/') else path + '/'}"


__all__ = [
    "DependencyProvisioningBlockedError", "DependencyProvisioningEvidence",
    "DependencyProvisioningMode", "DependencyProvisioningPreparation",
    "ProjectDependencyProvisioningService", "DependencyProvisioningStatus", "StructuredDependencyRequest", "DependencyBrokerRunner", "ControlledDependencyBrokerRunner",
]
