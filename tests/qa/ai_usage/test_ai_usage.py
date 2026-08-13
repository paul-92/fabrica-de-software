from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asep.ai_runtime import AIRuntimeExecutionMode, AIRuntimeIdentity, AIRuntimeResult, AIRuntimeUsage, InMemoryAIRuntimeRegistry
from asep.ai_usage import AIUsageOperation, AIUsageService, AIUsageStatus, InMemoryAIUsageRepository, SQLiteAIUsageRepository
from asep.api import create_project_engineering_operational_composition
from asep.configuration import ApplicationSettings, StorageBackend

NOW=datetime.now(UTC)

def record(service:AIUsageService, *, usage=True, operation=AIUsageOperation.IMPLEMENTATION, status=AIUsageStatus.SUCCEEDED):
    result=AIRuntimeResult(output="ok",identity=AIRuntimeIdentity(runtime_id="codex",model_id="gpt"),
        usage=AIRuntimeUsage(input_units=10,output_units=4,total_units=14) if usage else None,
        metadata={"provider_request_id":"req-safe"}) if status is AIUsageStatus.SUCCEEDED else None
    return service.record(organization_id="org-a",user_id="user-a",project_id="p",session_id="s",execution_id="e",
        runtime_id="codex",provider="openai",model="gpt",operation=operation,started_at=NOW,status=status,result=result)

def test_known_unknown_failed_multiple_operations_and_aggregation():
    service=AIUsageService(InMemoryAIUsageRepository())
    known=record(service); unknown=record(service,usage=False,operation=AIUsageOperation.PLANNING); failed=record(service,status=AIUsageStatus.FAILED,operation=AIUsageOperation.REPAIR)
    assert known.total_tokens == 14 and known.provider_request_id == "req-safe"
    assert unknown.input_tokens is None and failed.status is AIUsageStatus.FAILED
    assert {x.operation for x in service.query("org-a",execution_id="e")} == {AIUsageOperation.PLANNING,AIUsageOperation.IMPLEMENTATION,AIUsageOperation.REPAIR}
    assert service.aggregate("org-a",execution_id="e").model_dump() == {"calls":3,"known_input_tokens":10,"known_output_tokens":4,"known_total_tokens":14,"calls_with_unknown_usage":2}
    assert service.query("org-b") == ()
    assert "secret" not in known.model_dump_json().lower() and "prompt" not in known.model_dump_json().lower()

def test_sqlite_restart_and_date_queries(tmp_path:Path):
    path=tmp_path/"asep.db"; first=AIUsageService(SQLiteAIUsageRepository(path)); record(first)
    second=AIUsageService(SQLiteAIUsageRepository(path))
    assert len(second.query("org-a",user_id="user-a",project_id="p",execution_id="e",started_from=NOW-timedelta(seconds=1),started_to=NOW+timedelta(seconds=1))) == 1

class Runtime:
    identity=AIRuntimeIdentity(runtime_id="metered",model_id="model")
    def execute(self,request): return AIRuntimeResult(output="done",identity=self.identity,usage=AIRuntimeUsage(input_units=3,output_units=2,total_units=5))

def test_authenticated_execution_usage_api_and_legacy_history(tmp_path:Path):
    registry=InMemoryAIRuntimeRegistry(); registry.register(Runtime())
    settings=ApplicationSettings(storage_backend=StorageBackend.SQLITE,sqlite_database=tmp_path/"db.sqlite",hosted_root=tmp_path/"hosted")
    composition=create_project_engineering_operational_composition(settings,runtime_registry=registry)
    client=TestClient(composition.app)
    project=client.post("/api/v1/projects",json={"name":"P"}).json(); pid=project["project_id"]
    session=client.post(f"/api/v1/projects/{pid}/sessions",json={"title":"S"}).json(); sid=session["session_id"]
    executed=client.post(f"/api/v1/projects/{pid}/ai-runtime/execute",json={"session_id":sid,"runtime_id":"metered","instruction":"inspect","execution_mode":"read_only"})
    assert executed.status_code == 200; eid=executed.json()["execution_id"]
    body=client.get(f"/api/v1/projects/{pid}/executions/{eid}/ai-usage").json()
    assert body["aggregate"] == {"calls":1,"known_input_tokens":3,"known_output_tokens":2,"known_total_tokens":5,"calls_with_unknown_usage":0}
    assert body["items"][0]["execution_id"] == eid
    assert client.get(f"/api/v1/projects/{pid}/executions/{eid}").status_code == 200

def test_metering_persistence_failure_is_fail_closed():
    class Broken:
        def append(self,record): raise RuntimeError("ledger unavailable")
        def query(self,*args,**kwargs): return ()
    with pytest.raises(RuntimeError,match="ledger unavailable"): record(AIUsageService(Broken()))
