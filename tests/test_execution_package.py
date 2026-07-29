import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from asep.execution_package import (
    ASEP_EXECUTION_PROTOCOL,
    ASEP_EXECUTION_PROTOCOL_VERSION,
    ExecutionContext,
    ExecutionContextItem,
    ExecutionContract,
    ExecutionInput,
    ExecutionMetadata,
    ExecutionPackageBuilder,
    ExecutionPackageSerializer,
    ExecutionPackageWriter,
    ExecutionQualityGate,
    ExecutionSubject,
)
from asep.prompting import PromptBuildResult

RUN_ID = "f2f1a9f1-2c60-4fa0-9120-6b9197589488"


def prompt_result() -> PromptBuildResult:
    return PromptBuildResult(
        prompt="# Tarefa\n\nProduzir análise em português.\n",
        provider_neutral=True,
        included_sections=("tarefa",),
    )


def execution_context() -> ExecutionContext:
    return ExecutionContext(
        project=ExecutionSubject(
            id="asep",
            name="ASEP",
            description="Plataforma de engenharia.",
        ),
        workflow=ExecutionSubject(id="software-project", name="Software"),
        stage=ExecutionSubject(id="analysis", name="Análise"),
        inputs=(
            ExecutionInput(name="brief", value="Objetivo confirmado"),
            ExecutionInput(name="scope", value="Escopo aprovado"),
        ),
        contract=ExecutionContract(
            id="business-analyst",
            version="0.1.0",
            mission="Analisar sem inventar.",
            required_inputs=("brief", "scope"),
            expected_outputs=("risks.md", "requirements.md"),
            constraints=("Não expor segredos.",),
        ),
        quality_gate=ExecutionQualityGate(
            id="QG-ANALYSIS",
            criteria=("Rastreabilidade", "Clareza"),
        ),
        open_questions=("Quem aprova?", "Qual é o prazo?"),
        additional_context=(
            ExecutionContextItem(name="Idioma", value="Português"),
            ExecutionContextItem(name="Prioridade", value="Alta"),
        ),
    )


def metadata() -> ExecutionMetadata:
    return ExecutionMetadata(
        generator="asep",
        generator_version="0.1.0",
        python_version="3.11.9",
    )


def package():
    return ExecutionPackageBuilder().build(
        prompt=prompt_result(),
        context=execution_context(),
        metadata=metadata(),
        run_id=RUN_ID,
        project_id="asep",
        workflow_id="software-project",
        stage_id="analysis",
        agent_id="business-analyst",
        created_by="asep",
        expected_outputs=("risks.md", "requirements.md", "risks.md"),
        constraints=("Não fazer push.", "Não fazer commit."),
    )


def test_builds_versioned_provider_neutral_execution_package() -> None:
    built = package()

    assert built.manifest.protocol == ASEP_EXECUTION_PROTOCOL
    assert (
        built.manifest.protocol_version
        == ASEP_EXECUTION_PROTOCOL_VERSION
    )
    assert built.manifest.package_version == "1.0.0"
    assert built.manifest.provider is None
    assert built.metadata.provider is None
    assert built.task == prompt_result().prompt
    assert built.expected_outputs == ("requirements.md", "risks.md")
    assert built.constraints == ("Não fazer commit.", "Não fazer push.")


def test_builder_normalizes_unordered_context_collections() -> None:
    built = package()

    assert built.context.inputs == execution_context().inputs
    assert built.context.quality_gate is not None
    assert built.context.quality_gate.criteria == (
        "Clareza",
        "Rastreabilidade",
    )
    assert built.context.open_questions == (
        "Qual é o prazo?",
        "Quem aprova?",
    )
    assert tuple(
        item.name for item in built.context.additional_context
    ) == ("Idioma", "Prioridade")


def test_same_inputs_produce_identical_package_and_serialization() -> None:
    first = package()
    second = package()
    serializer = ExecutionPackageSerializer()

    assert first == second
    assert serializer.serialize(first) == serializer.serialize(second)


def test_manifest_checksums_match_canonical_content() -> None:
    built = package()
    serializer = ExecutionPackageSerializer()

    assert built.manifest.prompt_checksum == serializer.checksum_text(
        built.task
    )
    assert built.manifest.context_checksum == serializer.checksum_json(
        built.context
    )
    assert (
        built.manifest.expected_outputs_checksum
        == serializer.checksum_json(list(built.expected_outputs))
    )
    assert (
        built.manifest.constraints_checksum
        == serializer.checksum_json(list(built.constraints))
    )


def test_serializer_generates_protocol_files_with_unicode() -> None:
    serialized = ExecutionPackageSerializer().serialize(package())
    by_name = {item.name: item.content for item in serialized}

    assert tuple(by_name) == (
        "manifest.yaml",
        "task.md",
        "context.json",
        "metadata.json",
        "expected_outputs.json",
        "constraints.md",
    )
    manifest = yaml.safe_load(by_name["manifest.yaml"].decode("utf-8"))
    context = json.loads(by_name["context.json"].decode("utf-8"))
    metadata_document = json.loads(
        by_name["metadata.json"].decode("utf-8")
    )
    assert manifest["provider"] is None
    assert context["stage"]["name"] == "Análise"
    assert context["additional_context"][0]["value"] == "Português"
    assert metadata_document["provider"] is None
    assert "português" in by_name["task.md"].decode("utf-8")


def test_writer_creates_missing_directories_and_persists_all_files(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "missing" / "project"

    result = ExecutionPackageWriter().write(package(), project_path)

    expected_path = (
        project_path.resolve()
        / ".asep"
        / "runs"
        / RUN_ID
        / "packages"
        / "analysis"
    )
    assert result.package_path == expected_path
    assert result.written_files == (
        "manifest.yaml",
        "task.md",
        "context.json",
        "metadata.json",
        "expected_outputs.json",
        "constraints.md",
    )
    assert result.unchanged_files == ()
    assert all(item.path.is_file() for item in result.files)
    assert not list(result.package_path.glob(".asep-package-*.tmp"))


def test_repeated_write_is_idempotent(tmp_path: Path) -> None:
    writer = ExecutionPackageWriter()
    first = writer.write(package(), tmp_path)
    original = {
        item.name: item.path.read_bytes() for item in first.files
    }

    second = writer.write(package(), tmp_path)

    assert second.written_files == ()
    assert second.unchanged_files == tuple(original)
    assert {
        item.name: item.path.read_bytes() for item in second.files
    } == original


def test_writer_supports_deep_paths_without_long_temporary_names(
    tmp_path: Path,
) -> None:
    project_path = tmp_path
    final_relative = (
        Path(".asep")
        / "runs"
        / RUN_ID
        / "packages"
        / "analysis"
        / "manifest.yaml"
    )
    while len(str(project_path / final_relative)) < 220:
        project_path /= "deep-segment"

    result = ExecutionPackageWriter().write(package(), project_path)

    assert all(item.path.is_file() for item in result.files)
    assert not list(result.package_path.glob("*.tmp"))


@pytest.mark.parametrize("platform_directory", ["windows", "linux", "macos"])
def test_writer_uses_portable_path_construction(
    tmp_path: Path, platform_directory: str
) -> None:
    result = ExecutionPackageWriter().write(
        package(),
        tmp_path / platform_directory,
    )

    assert result.package_path.parts[-4:] == (
        "runs",
        RUN_ID,
        "packages",
        "analysis",
    )
    assert (result.package_path / "manifest.yaml").is_file()


def test_rejects_path_traversal_in_manifest_identifiers() -> None:
    with pytest.raises(ValidationError, match="separadores de path"):
        ExecutionPackageBuilder().build(
            prompt=prompt_result(),
            context=execution_context(),
            metadata=metadata(),
            run_id=RUN_ID,
            project_id="asep",
            workflow_id="software-project",
            stage_id="../escape",
            agent_id="business-analyst",
            created_by="asep",
        )
