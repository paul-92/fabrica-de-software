from asep.intelligence import (
    KnowledgeAwareContext,
    KnowledgeAwarePlanningAdapter,
    ToolAwarePlanningAdapter,
)
from asep.planning import PlanningContext, PlanningRequest
from asep.tools import RunTestsTool, WriteFileTool


def request(workflow=None) -> PlanningRequest:
    return PlanningRequest(
        goal="Corrigir aplicação",
        context=PlanningContext(
            objective="Restaurar comportamento",
            workflow={} if workflow is None else workflow,
        ),
    )


def adapter() -> ToolAwarePlanningAdapter:
    return ToolAwarePlanningAdapter(
        KnowledgeAwarePlanningAdapter(),
        (WriteFileTool(), RunTestsTool()),
    )


def test_workflow_is_derived_from_real_tool_metadata() -> None:
    adapted = adapter().adapt(
        request(),
        KnowledgeAwareContext(knowledge_count=0),
    )

    assert adapted.context.workflow["steps"] == [
        {
            "id": "write-file-write_file",
            "description": WriteFileTool.metadata.description,
            "required_capability": "write_file",
            "tool": "write-file",
        },
        {
            "id": "run-tests-test",
            "description": RunTestsTool.metadata.description,
            "required_capability": "test",
            "tool": "run-tests",
        },
    ]


def test_explicit_workflow_is_preserved_including_empty_steps() -> None:
    explicit = {"steps": []}
    adapted = adapter().adapt(
        request(explicit),
        KnowledgeAwareContext(knowledge_count=0),
    )
    assert adapted.context.workflow == explicit


def test_operational_workflow_is_deterministic() -> None:
    context = KnowledgeAwareContext(knowledge_count=0)
    assert adapter().adapt(request(), context) == adapter().adapt(
        request(), context
    )
