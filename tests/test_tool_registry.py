from datetime import UTC, datetime
from pathlib import Path

import pytest

from asep.tools import (
    InMemoryToolRegistry,
    InvalidToolRegistrationError,
    ToolAlreadyRegisteredError,
    ToolCapability,
    ToolContext,
    ToolExecutionPolicy,
    ToolId,
    ToolMetadata,
    ToolNotRegisteredError,
    ToolRequest,
    ToolResult,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


class FakeTool:
    def __init__(
        self,
        tool_id: str = "fake",
        capabilities: tuple[str, ...] = ("read",),
    ) -> None:
        self._metadata = ToolMetadata(
            id=ToolId(value=tool_id),
            name="Fake Tool",
            description="Test double.",
            version="1.0",
            author="tests",
            category="testing",
            capabilities=tuple(
                ToolCapability(id=value) for value in capabilities
            ),
        )

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    def execute(
        self, request: ToolRequest, context: ToolContext
    ) -> ToolResult:
        raise NotImplementedError


def test_registry_register_resolve_and_list_deterministically() -> None:
    registry = InMemoryToolRegistry()
    second = FakeTool("z-tool")
    first = FakeTool("a-tool")

    registry.register(second)
    registry.register(first)

    assert registry.resolve(ToolId(value="a-tool")) is first
    assert registry.list() == (first, second)


def test_registry_rejects_duplicate() -> None:
    registry = InMemoryToolRegistry()
    registry.register(FakeTool())

    with pytest.raises(ToolAlreadyRegisteredError):
        registry.register(FakeTool())


def test_registry_remove_and_missing_lookup() -> None:
    registry = InMemoryToolRegistry()
    registry.register(FakeTool())
    registry.remove(ToolId(value="fake"))

    with pytest.raises(ToolNotRegisteredError):
        registry.resolve(ToolId(value="fake"))
    with pytest.raises(ToolNotRegisteredError):
        registry.remove(ToolId(value="fake"))


def test_registry_finds_by_capability() -> None:
    registry = InMemoryToolRegistry()
    reader = FakeTool("reader", ("read",))
    writer = FakeTool("writer", ("write",))
    registry.register(writer)
    registry.register(reader)

    assert registry.find_by_capability(
        ToolCapability(id="read")
    ) == (reader,)


@pytest.mark.parametrize("invalid", [None, object()])
def test_registry_rejects_invalid_tool(invalid) -> None:
    registry = InMemoryToolRegistry()
    with pytest.raises(InvalidToolRegistrationError):
        registry.register(invalid)


def test_registry_rejects_invalid_metadata() -> None:
    class InvalidMetadataTool:
        metadata = object()

        def execute(self, request, context):
            raise AssertionError

    with pytest.raises(InvalidToolRegistrationError):
        InMemoryToolRegistry().register(InvalidMetadataTool())


def test_registry_rejects_invalid_identifiers_and_capabilities() -> None:
    registry = InMemoryToolRegistry()
    with pytest.raises(InvalidToolRegistrationError):
        registry.resolve("fake")
    with pytest.raises(InvalidToolRegistrationError):
        registry.find_by_capability("read")


def test_tool_id_is_hashable_comparable_and_validated() -> None:
    first = ToolId(value="a")
    second = ToolId(value="b")

    assert first < second
    assert {first, ToolId(value="a")} == {first}
    with pytest.raises(ValueError):
        ToolId(value=" ")


def test_metadata_rejects_duplicate_or_missing_capabilities() -> None:
    base = {
        "id": ToolId(value="fake"),
        "name": "Fake",
        "description": "Fake.",
        "version": "1",
        "author": "tests",
        "category": "testing",
    }
    with pytest.raises(ValueError):
        ToolMetadata(**base, capabilities=())
    with pytest.raises(ValueError):
        ToolMetadata(
            **base,
            capabilities=(
                ToolCapability(id="read"),
                ToolCapability(id="read"),
            ),
        )


def test_tool_request_is_immutable_and_hides_payload(tmp_path: Path) -> None:
    request = ToolRequest(
        execution_id="tool-1",
        tool_id=ToolId(value="fake"),
        capability=ToolCapability(id="read"),
        workspace=tmp_path,
        payload={"secret": "payload-value"},
    )

    assert "payload-value" not in repr(request)
    with pytest.raises(ValueError):
        request.execution_id = "changed"


def test_policy_context_and_request_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ToolExecutionPolicy(retry_enabled=False, max_attempts=2)
    with pytest.raises(ValueError):
        ToolRequest(
            execution_id=" ",
            tool_id=ToolId(value="fake"),
            capability=ToolCapability(id="read"),
            workspace=tmp_path,
        )
    with pytest.raises(ValueError):
        ToolContext(
            execution_id="context",
            started_at=datetime(2026, 7, 30),
            workspace=tmp_path,
        )
