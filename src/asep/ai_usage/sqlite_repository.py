import json
from datetime import datetime
from pathlib import Path
from asep.ai_usage.models import AIUsageRecord
from asep.sqlite import SQLiteDatabase

class SQLiteAIUsageRepository:
    def __init__(self, path: Path): self._database = SQLiteDatabase(path)
    def append(self, record: AIUsageRecord) -> None:
        with self._database.connect() as connection:
            connection.execute("INSERT INTO ai_usage_ledger (id,organization_id,user_id,project_id,execution_id,started_at,payload) VALUES (?,?,?,?,?,?,?)",
                (record.usage_id,record.organization_id,record.user_id,record.project_id,record.execution_id,record.started_at.isoformat(),json.dumps(record.model_dump(mode="json"),sort_keys=True)))
    def query(self, organization_id: str, *, user_id: str | None = None, project_id: str | None = None,
              execution_id: str | None = None, started_from: datetime | None = None, started_to: datetime | None = None):
        clauses=["organization_id=?"]; values:list[object]=[organization_id]
        for field,value in (("user_id",user_id),("project_id",project_id),("execution_id",execution_id)):
            if value is not None: clauses.append(f"{field}=?"); values.append(value)
        if started_from is not None: clauses.append("started_at>=?"); values.append(started_from.isoformat())
        if started_to is not None: clauses.append("started_at<=?"); values.append(started_to.isoformat())
        with self._database.connect() as connection:
            rows=connection.execute(f"SELECT payload FROM ai_usage_ledger WHERE {' AND '.join(clauses)} ORDER BY started_at,id",tuple(values)).fetchall()
        return tuple(AIUsageRecord.model_validate_json(row["payload"]) for row in rows)

