from __future__ import annotations

from typing import get_type_hints

import pytest
from pydantic import ValidationError

from asep.execution_package import ExecutionPackage
from asep.providers import (
    AgentExecutionResult,
    AgentExecutionStatus,
    AgentProvider,
    ProducedFile,
    ProducedFileOperation,
    ProviderError,
    ProviderExecutionError,
    ProviderProtocolError,
    ProviderUnavailableError,
)


class FakeProvider:
    name = "fake"

    def execute(
        self, package: ExecutionPackage
    ) -> AgentExecutionResult:
        return AgentExecutionResult(
            status=AgentExecutionStatus.SUCCESS,
            provider_name=self.name,
            provider_version="1.0",
            exit_code=0,
            stdout="Execution completed.",
        )


def test_fake_provider_conforms_structurally_to_protocol() -> None:
    provider: AgentProvider = FakeProvider()

    assert isinstance(provider, AgentProvider)
    assert provider.name == "fake"
    assert get_type_hints(FakeProvider.execute)["package"] is ExecutionPackage


def test_builds_success_result_with_immutable_defaults() -> None:
    result = AgentExecutionResult(
        status=AgentExecutionStatus.SUCCESS,
        provider_name="fake",
        provider_version="1.0",
    )

    assert result.exit_code is None
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.produced_files == ()
    assert result.warnings == ()
    assert result.errors == ()
    assert dict(result.metadata) == {}

    with pytest.raises(ValidationError):
        result.stdout = "changed"  # type: ignore[misc]


def test_builds_failed_result_with_failure_evidence() -> None:
    result = AgentExecutionResult(
        status=AgentExecutionStatus.FAILED,
        provider_name="fake",
        provider_version="1.0",
        exit_code=1,
        stderr="provider failed",
        errors=("execution failed",),
    )

    assert result.status is AgentExecutionStatus.FAILED
    assert result.exit_code == 1
    assert result.errors == ("execution failed",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("errors", ("fatal",)),
        ("stderr", "fatal"),
        ("exit_code", 1),
    ],
)
def test_failed_result_accepts_each_supported_failure_evidence(
    field: str, value: object
) -> None:
    data = {
        "status": AgentExecutionStatus.FAILED,
        "provider_name": "fake",
        "provider_version": "1.0",
        field: value,
    }

    result = AgentExecutionResult(**data)

    assert result.status is AgentExecutionStatus.FAILED


def test_failed_result_requires_failure_evidence() -> None:
    with pytest.raises(
        ValidationError, match="deve conter evidência da falha"
    ):
        AgentExecutionResult(
            status=AgentExecutionStatus.FAILED,
            provider_name="fake",
            provider_version="1.0",
        )


def test_success_result_rejects_errors() -> None:
    with pytest.raises(
        ValidationError, match="SUCCESS não pode conter erros"
    ):
        AgentExecutionResult(
            status=AgentExecutionStatus.SUCCESS,
            provider_name="fake",
            provider_version="1.0",
            errors=("fatal",),
        )


@pytest.mark.parametrize("provider_name", ["", "   "])
def test_provider_name_is_required(provider_name: str) -> None:
    with pytest.raises(ValidationError, match="não pode ser vazia"):
        AgentExecutionResult(
            status=AgentExecutionStatus.SUCCESS,
            provider_name=provider_name,
            provider_version="1.0",
        )


def test_status_is_a_str_enum_and_rejects_unknown_values() -> None:
    assert AgentExecutionStatus.SUCCESS == "success"

    with pytest.raises(ValidationError):
        AgentExecutionResult(
            status="unknown",  # type: ignore[arg-type]
            provider_name="fake",
            provider_version="1.0",
        )


def test_produced_files_and_messages_are_immutable() -> None:
    files = [
        ProducedFile(
            path="src/example.py",
            operation=ProducedFileOperation.CREATED,
            checksum="abc123",
            size=42,
        )
    ]
    warnings = ["review recommended"]
    result = AgentExecutionResult(
        status=AgentExecutionStatus.PARTIAL,
        provider_name="fake",
        provider_version="1.0",
        produced_files=files,
        warnings=warnings,
    )
    files.append(
        ProducedFile(
            path="src/other.py",
            operation=ProducedFileOperation.MODIFIED,
        )
    )
    warnings.append("late mutation")

    assert len(result.produced_files) == 1
    assert result.produced_files[0].operation == "created"
    assert result.warnings == ("review recommended",)
    with pytest.raises(ValidationError):
        result.produced_files[0].size = 10  # type: ignore[misc]


@pytest.mark.parametrize(
    "path",
    [
        "/absolute/file.py",
        r"C:\absolute\file.py",
        "../escape.py",
        r"..\escape.py",
        "",
    ],
)
def test_produced_file_rejects_unsafe_or_absolute_paths(path: str) -> None:
    with pytest.raises(ValidationError):
        ProducedFile(
            path=path,
            operation=ProducedFileOperation.CREATED,
        )


def test_metadata_is_deeply_immutable_and_defensively_copied() -> None:
    source = {"attempt": 1, "nested": {"labels": ["qa"]}}
    result = AgentExecutionResult(
        status=AgentExecutionStatus.SUCCESS,
        provider_name="fake",
        provider_version="1.0",
        metadata=source,
    )
    source["attempt"] = 2
    source["nested"]["labels"].append("changed")  # type: ignore[index]

    assert result.metadata["attempt"] == 1
    assert result.metadata["nested"]["labels"] == ("qa",)
    with pytest.raises(TypeError):
        result.metadata["attempt"] = 3  # type: ignore[index]
    with pytest.raises(TypeError):
        result.metadata["nested"]["labels"][0] = "changed"  # type: ignore[index]
    assert result.model_dump()["metadata"] == {
        "attempt": 1,
        "nested": {"labels": ["qa"]},
    }


def test_public_exports_include_only_the_provider_api() -> None:
    import asep.providers as providers

    assert set(providers.__all__) == {
        "AgentExecutionResult",
        "AgentExecutionStatus",
        "AgentProvider",
        "CodexProvider",
        "CodexProviderConfig",
        "ProducedFile",
        "ProducedFileOperation",
        "ProviderError",
        "ProviderExecutionError",
        "ProviderProtocolError",
        "ProviderUnavailableError",
    }
    assert issubclass(ProviderUnavailableError, ProviderError)
    assert issubclass(ProviderExecutionError, ProviderError)
    assert issubclass(ProviderProtocolError, ProviderError)


def test_provider_layer_has_no_vendor_dependencies() -> None:
    import asep.providers.protocol as protocol

    source_names = set(protocol.__dict__)
    assert not {"Codex", "Claude", "Gemini", "subprocess"} & source_names
