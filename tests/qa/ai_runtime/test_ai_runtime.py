from __future__ import annotations

from typing import get_type_hints

import pytest
from pydantic import ValidationError

from asep.ai_runtime import (
    AIRuntime,
    AIRuntimeAlreadyRegisteredError,
    AIRuntimeAuthenticationError,
    AIRuntimeCapability,
    AIRuntimeConfigurationError,
    AIRuntimeIdentity,
    AIRuntimeInvalidResponseError,
    AIRuntimeNotFoundError,
    AIRuntimeRateLimitError,
    AIRuntimeRegistry,
    AIRuntimeRequest,
    AIRuntimeResult,
    AIRuntimeTimeoutError,
    AIRuntimeUnavailableError,
    AIRuntimeUnexpectedError,
    AIRuntimeUsage,
    InMemoryAIRuntimeRegistry,
)


class FakeAIRuntime:
    def __init__(self, runtime_id: str = "local-test") -> None:
        self._identity = AIRuntimeIdentity(
            runtime_id=runtime_id,
            model_id="deterministic-test-model",
            capabilities=(AIRuntimeCapability(id="text-generation"),),
        )
        self.requests: list[AIRuntimeRequest] = []

    @property
    def identity(self) -> AIRuntimeIdentity:
        return self._identity

    def execute(self, request: AIRuntimeRequest) -> AIRuntimeResult:
        self.requests.append(request)
        return AIRuntimeResult(output="result", identity=self.identity)


def test_runtime_contract_is_structural_and_provider_agnostic() -> None:
    runtime: AIRuntime = FakeAIRuntime()

    result = runtime.execute(AIRuntimeRequest(instruction="Analyze failure"))

    assert isinstance(runtime, AIRuntime)
    assert result.output == "result"
    assert get_type_hints(FakeAIRuntime.execute)["request"] is AIRuntimeRequest


def test_request_is_strict_immutable_and_freezes_json_data() -> None:
    source = {"failure": {"paths": ["src/example.py"]}}
    request = AIRuntimeRequest(
        instruction="  Analyze failure  ",
        context=source,
        metadata={"correlation_id": "execution-1"},
    )
    source["failure"]["paths"].append("late.py")

    assert request.instruction == "Analyze failure"
    assert request.context["failure"]["paths"] == ("src/example.py",)
    assert request.model_dump(mode="json")["context"] == {
        "failure": {"paths": ["src/example.py"]}
    }
    with pytest.raises(ValidationError):
        request.instruction = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        request.metadata["new"] = True  # type: ignore[index]


@pytest.mark.parametrize("instruction", ["", "   "])
def test_request_rejects_blank_instruction(instruction: str) -> None:
    with pytest.raises(ValidationError, match="instruction"):
        AIRuntimeRequest(instruction=instruction)


def test_request_rejects_non_json_context() -> None:
    with pytest.raises(ValidationError, match="não serializável"):
        AIRuntimeRequest(instruction="test", context={"value": object()})


def test_identity_uses_extensible_ids_and_unique_capabilities() -> None:
    identity = AIRuntimeIdentity(
        runtime_id="custom-runtime",
        model_id="model-family/version",
        capabilities=(
            AIRuntimeCapability(id="text-generation"),
            AIRuntimeCapability(id="structured-output"),
        ),
    )

    assert identity.runtime_id == "custom-runtime"
    assert [item.id for item in identity.capabilities] == [
        "text-generation",
        "structured-output",
    ]

    with pytest.raises(ValidationError, match="duplicadas"):
        AIRuntimeIdentity(
            runtime_id="runtime",
            model_id="model",
            capabilities=(
                AIRuntimeCapability(id="text-generation"),
                AIRuntimeCapability(id="text-generation"),
            ),
        )


def test_usage_supports_optional_units_and_cost() -> None:
    usage = AIRuntimeUsage(
        input_units=10,
        output_units=5,
        total_units=15,
        cost=0.02,
    )

    assert usage.total_units == 15
    assert usage.cost == 0.02
    assert AIRuntimeUsage().model_dump() == {
        "input_units": None,
        "output_units": None,
        "total_units": None,
        "cost": None,
    }

    with pytest.raises(ValidationError, match="deve somar"):
        AIRuntimeUsage(input_units=10, output_units=5, total_units=14)


def test_result_is_immutable_and_contains_generic_runtime_data() -> None:
    identity = FakeAIRuntime().identity
    result = AIRuntimeResult(
        output="structured response",
        identity=identity,
        usage=AIRuntimeUsage(total_units=7),
        metadata={"finish_reason": "complete"},
    )

    assert result.identity is identity
    assert result.usage == AIRuntimeUsage(total_units=7)
    assert result.model_dump(mode="json")["metadata"] == {
        "finish_reason": "complete"
    }
    with pytest.raises(ValidationError):
        result.output = "changed"  # type: ignore[misc]


def test_registry_registers_resolves_and_lists_deterministically() -> None:
    registry: AIRuntimeRegistry = InMemoryAIRuntimeRegistry()
    runtime_z = FakeAIRuntime("z-runtime")
    runtime_a = FakeAIRuntime("a-runtime")

    registry.register(runtime_z)
    registry.register(runtime_a)

    assert isinstance(registry, AIRuntimeRegistry)
    assert registry.get("a-runtime") is runtime_a
    assert registry.contains("z-runtime") is True
    assert [item.identity.runtime_id for item in registry.list_all()] == [
        "a-runtime",
        "z-runtime",
    ]


def test_registry_rejects_duplicate_unknown_and_invalid_runtime() -> None:
    registry = InMemoryAIRuntimeRegistry()
    runtime = FakeAIRuntime()
    registry.register(runtime)

    with pytest.raises(AIRuntimeAlreadyRegisteredError):
        registry.register(runtime)
    with pytest.raises(AIRuntimeNotFoundError):
        registry.get("unknown")
    with pytest.raises(AIRuntimeConfigurationError):
        registry.register(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "error_type",
    [
        AIRuntimeConfigurationError,
        AIRuntimeAuthenticationError,
        AIRuntimeUnavailableError,
        AIRuntimeRateLimitError,
        AIRuntimeTimeoutError,
        AIRuntimeInvalidResponseError,
    ],
)
def test_runtime_error_messages_do_not_require_provider_details(
    error_type: type[Exception],
) -> None:
    error = error_type("runtime-x")

    assert "runtime-x" in str(error)
    assert "http" not in str(error).lower()


def test_unexpected_error_does_not_leak_original_secret() -> None:
    error = AIRuntimeUnexpectedError(
        "runtime-x",
        RuntimeError("api_key=super-secret-value"),
    )

    assert error.cause_type == "RuntimeError"
    assert "super-secret-value" not in str(error)
    assert "api_key" not in str(error)


def test_package_public_api_contains_only_intentional_contracts() -> None:
    import asep.ai_runtime as api

    assert set(api.__all__) == {
        "AIRuntime",
        "AIRuntimeAlreadyRegisteredError",
        "AIRuntimeAuthenticationError",
        "AIRuntimeCapability",
        "AIRuntimeConfigurationError",
        "AIRuntimeError",
        "AIRuntimeIdentity",
        "AIRuntimeInvalidResponseError",
        "AIRuntimeNotFoundError",
        "AIRuntimeRateLimitError",
        "AIRuntimeRegistry",
        "AIRuntimeRegistryError",
        "AIRuntimeRequest",
        "AIRuntimeResult",
        "AIRuntimeTimeoutError",
        "AIRuntimeUnavailableError",
        "AIRuntimeUnexpectedError",
        "AIRuntimeUsage",
        "CodexAIRuntime",
        "CodexAIRuntimeConfig",
        "InMemoryAIRuntimeRegistry",
        "create_codex_ai_runtime_registry",
    }


def test_core_ai_runtime_contracts_have_no_vendor_dependencies() -> None:
    import asep.ai_runtime.contracts as contracts
    import asep.ai_runtime.models as models

    names = " ".join((*contracts.__all__, *models.__all__)).lower()
    assert "openai" not in names
    assert "anthropic" not in names
    assert "codex" not in names
    assert "credential" not in names
