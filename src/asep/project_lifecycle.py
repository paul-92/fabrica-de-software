"""Estado persistível do macro-lifecycle, sem inferência de texto de IA."""
from __future__ import annotations
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from uuid import uuid4
import sqlite3
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

class ProjectPhase(StrEnum):
    PLANNING="PLANNING"; ARCHITECTURE="ARCHITECTURE"; DEVELOPMENT="DEVELOPMENT"; TESTING="TESTING"; DELIVERY="DELIVERY"
class ProjectPhaseStatus(StrEnum):
    PENDING="pending"; ACTIVE="active"; BLOCKED="blocked"; COMPLETED="completed"
class LifecycleConcurrencyError(RuntimeError): pass
class InvalidLifecycleTransitionError(RuntimeError): pass
class ProjectLifecycleState(BaseModel):
    model_config=ConfigDict(extra="forbid", frozen=True)
    project_id:str; phase:ProjectPhase=ProjectPhase.PLANNING; phase_status:ProjectPhaseStatus=ProjectPhaseStatus.ACTIVE
    current_sprint:str|None=None; blocker:str|None=None; blocker_code:str|None=None; next_action:str|None=None
    updated_at:datetime=Field(default_factory=lambda:datetime.now(UTC)); version:int=1
class ProjectLifecycleTransition(BaseModel):
    model_config=ConfigDict(extra="forbid", frozen=True)
    transition_id:str; project_id:str; from_phase:ProjectPhase; to_phase:ProjectPhase; reason_code:str
    source_execution_id:str|None=None; created_at:datetime=Field(default_factory=lambda:datetime.now(UTC))
class InMemoryProjectLifecycleRepository:
    def __init__(self): self._states={}; self._history={}; self._lock=Lock()
    def get(self, project_id:str)->ProjectLifecycleState:
        with self._lock: return self._states.setdefault(project_id,ProjectLifecycleState(project_id=project_id))
    def history(self, project_id:str)->tuple[ProjectLifecycleTransition,...]:
        with self._lock: return tuple(self._history.get(project_id,()))
    def transition(self,project_id:str,*,to_phase:ProjectPhase,reason_code:str,expected_version:int,status:ProjectPhaseStatus=ProjectPhaseStatus.ACTIVE,current_sprint:str|None=None,blocker:str|None=None,blocker_code:str|None=None,next_action:str|None=None,source_execution_id:str|None=None)->ProjectLifecycleState:
        with self._lock:
            state=self._states.setdefault(project_id,ProjectLifecycleState(project_id=project_id)); order=list(ProjectPhase)
            if state.version!=expected_version: raise LifecycleConcurrencyError("lifecycle version conflict")
            if reason_code!="preparation_created" and (order.index(to_phase)<order.index(state.phase) or order.index(to_phase)>order.index(state.phase)+1): raise InvalidLifecycleTransitionError("invalid lifecycle transition")
            if status is ProjectPhaseStatus.BLOCKED and not blocker: raise InvalidLifecycleTransitionError("blocked lifecycle requires reason")
            new=ProjectLifecycleState(project_id=project_id,phase=to_phase,phase_status=status,current_sprint=current_sprint,blocker=blocker,blocker_code=blocker_code,next_action=next_action,version=state.version+1); self._states[project_id]=new
            self._history.setdefault(project_id,[]).append(ProjectLifecycleTransition(transition_id=str(uuid4()),project_id=project_id,from_phase=state.phase,to_phase=to_phase,reason_code=reason_code,source_execution_id=source_execution_id))
            return new

class SQLiteProjectLifecycleRepository(InMemoryProjectLifecycleRepository):
    """Durable repository with optimistic writes serialized by SQLite."""
    def __init__(self,database:Path):
        super().__init__(); self._database=database.expanduser().resolve(); self._database.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self._database) as db:
            db.execute("CREATE TABLE IF NOT EXISTS project_lifecycle (project_id TEXT PRIMARY KEY, state_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS project_lifecycle_transition (transition_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, transition_json TEXT NOT NULL)")
    def get(self,project_id:str)->ProjectLifecycleState:
        with sqlite3.connect(self._database) as db: row=db.execute("SELECT state_json FROM project_lifecycle WHERE project_id=?",(project_id,)).fetchone()
        if row: return ProjectLifecycleState.model_validate_json(row[0])
        state=ProjectLifecycleState(project_id=project_id); self._save(state); return state
    def _save(self,state):
        with sqlite3.connect(self._database) as db: db.execute("INSERT OR REPLACE INTO project_lifecycle VALUES (?,?)",(state.project_id,state.model_dump_json()))
    def history(self,project_id):
        with sqlite3.connect(self._database) as db: rows=db.execute("SELECT transition_json FROM project_lifecycle_transition WHERE project_id=? ORDER BY rowid",(project_id,)).fetchall()
        return tuple(ProjectLifecycleTransition.model_validate_json(row[0]) for row in rows)
    def transition(self,project_id,**kwargs):
        current=self.get(project_id)
        if current.version!=kwargs["expected_version"]: raise LifecycleConcurrencyError("lifecycle version conflict")
        with self._lock: self._states[project_id]=current
        state=super().transition(project_id,**kwargs); self._save(state)
        for item in super().history(project_id):
            with sqlite3.connect(self._database) as db: db.execute("INSERT OR IGNORE INTO project_lifecycle_transition VALUES (?,?,?)",(item.transition_id,project_id,item.model_dump_json()))
        return state
