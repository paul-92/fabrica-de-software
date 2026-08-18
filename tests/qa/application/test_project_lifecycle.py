import pytest
from asep.project_lifecycle import InMemoryProjectLifecycleRepository, InvalidLifecycleTransitionError, LifecycleConcurrencyError, ProjectPhase, ProjectPhaseStatus
from asep.project_lifecycle import SQLiteProjectLifecycleRepository

def test_state_sprint_and_history():
    repo=InMemoryProjectLifecycleRepository(); assert repo.get("p").phase is ProjectPhase.PLANNING
    repo.transition("p",to_phase=ProjectPhase.ARCHITECTURE,reason_code="architecture_approved",expected_version=1)
    state=repo.transition("p",to_phase=ProjectPhase.DEVELOPMENT,reason_code="sprint_started",expected_version=2,current_sprint="Sprint 1 — Fundação técnica",source_execution_id="e")
    assert state.current_sprint and len(repo.history("p"))==2
def test_invalid_blocked_and_concurrency():
    repo=InMemoryProjectLifecycleRepository()
    with pytest.raises(InvalidLifecycleTransitionError): repo.transition("p",to_phase=ProjectPhase.DEVELOPMENT,reason_code="text_pass",expected_version=1)
    repo.transition("p",to_phase=ProjectPhase.PLANNING,reason_code="blocked",expected_version=1,status=ProjectPhaseStatus.BLOCKED,blocker="dependencies unavailable")
    with pytest.raises(LifecycleConcurrencyError): repo.transition("p",to_phase=ProjectPhase.ARCHITECTURE,reason_code="approved",expected_version=1)

def test_dependency_blocker_does_not_regress_testing_phase():
    repo=InMemoryProjectLifecycleRepository(); state=repo.get("p")
    for phase in (ProjectPhase.ARCHITECTURE,ProjectPhase.DEVELOPMENT,ProjectPhase.TESTING):
        state=repo.transition("p",to_phase=phase,reason_code="structured_event",expected_version=state.version)
    blocked=repo.transition("p",to_phase=ProjectPhase.TESTING,reason_code="preparation_created",expected_version=state.version,status=ProjectPhaseStatus.BLOCKED,blocker="Dependências aguardando revisão",blocker_code="dependency_plan_missing_source",next_action="Defina ou aprove a stack técnica na preparação da sprint.")
    assert (blocked.phase,blocked.phase_status,blocked.blocker_code)==(ProjectPhase.TESTING,ProjectPhaseStatus.BLOCKED,"dependency_plan_missing_source")

def test_sqlite_restart_preserves_testing_state_and_transition(tmp_path):
    database=tmp_path/"lifecycle.db"; repo=SQLiteProjectLifecycleRepository(database)
    state=repo.transition("p",to_phase=ProjectPhase.DEVELOPMENT,reason_code="preparation_created",expected_version=1,status=ProjectPhaseStatus.ACTIVE,current_sprint="sprint-1 — Foundation",source_execution_id="e")
    state=repo.transition("p",to_phase=ProjectPhase.TESTING,reason_code="validation_started",expected_version=state.version,status=ProjectPhaseStatus.ACTIVE,current_sprint=state.current_sprint,source_execution_id="e")
    state=repo.transition("p",to_phase=ProjectPhase.TESTING,reason_code="quality_gate_blocked",expected_version=state.version,status=ProjectPhaseStatus.BLOCKED,current_sprint=state.current_sprint,blocker="gate",next_action="fix",source_execution_id="e")
    restarted=SQLiteProjectLifecycleRepository(database); saved=restarted.get("p")
    assert (saved.phase,saved.phase_status,saved.current_sprint,saved.blocker,saved.next_action)==(ProjectPhase.TESTING,ProjectPhaseStatus.BLOCKED,"sprint-1 — Foundation","gate","fix")
    assert restarted.history("p")[-1].source_execution_id=="e"
