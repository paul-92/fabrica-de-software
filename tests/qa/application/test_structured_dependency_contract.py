import pytest
from asep.application.project_ai_runtime import ProjectAIRuntimeExecutionRequest

def test_duplicates_normalized_and_conflicts_rejected():
    item={"package":"react","requested_version":"19.0.0","reason":"UI"}
    request=ProjectAIRuntimeExecutionRequest(project_id="p",session_id="s",runtime_id="r",instruction="x",dependency_requests=(item,item))
    assert len(request.dependency_requests)==1
    with pytest.raises(ValueError,match="conflicting"):
        ProjectAIRuntimeExecutionRequest(project_id="p",session_id="s",runtime_id="r",instruction="x",dependency_requests=(item,{**item,"requested_version":"18.0.0"}))

@pytest.mark.parametrize("version",["https://evil/x","git:main","file:x","latest"])
def test_invalid_versions_are_rejected(version):
    with pytest.raises(ValueError): ProjectAIRuntimeExecutionRequest(project_id="p",session_id="s",runtime_id="r",instruction="x",dependency_requests=({"package":"x","requested_version":version,"reason":"x"},))

def test_registry_allowlist():
    with pytest.raises(ValueError,match="registry"):
        ProjectAIRuntimeExecutionRequest(project_id="p",session_id="s",runtime_id="r",instruction="x",dependency_requests=({"package":"x","requested_version":"1.0.0","reason":"x","registry":"https://evil.example"},))
