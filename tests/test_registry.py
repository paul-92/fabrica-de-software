from pathlib import Path

import pytest

from asep.errors import RegistryValidationError
from asep.registry.loader import RegistryLoader


def test_registry_loads_all_required_catalogs(sample_repository: Path) -> None:
    snapshot = RegistryLoader().load(sample_repository / "registry")

    assert set(snapshot.agents) == {"orchestrator", "business-analyst"}
    assert set(snapshot.contracts) == {"orchestrator", "business-analyst"}
    assert set(snapshot.workflows) == {"software-project"}
    assert set(snapshot.quality_gates) == {"QG-INTAKE"}
    assert set(snapshot.playbooks) == {"intake"}
    assert set(snapshot.knowledge) == {"foundations"}


def test_registry_reports_the_file_with_broken_reference(
    sample_repository: Path,
) -> None:
    (sample_repository / "agents/orchestrator.md").unlink()

    with pytest.raises(RegistryValidationError, match="Referência inexistente") as error:
        RegistryLoader().load(sample_repository / "registry")

    assert error.value.path == sample_repository / "agents/orchestrator.md"


def test_registry_rejects_unknown_field(sample_repository: Path) -> None:
    path = sample_repository / "registry/agents.yaml"
    path.write_text(
        path.read_text(encoding="utf-8") + "unexpected: true\n",
        encoding="utf-8",
    )

    with pytest.raises(RegistryValidationError, match="extra_forbidden"):
        RegistryLoader().load(sample_repository / "registry")


def test_registry_validates_individual_contract(sample_repository: Path) -> None:
    path = sample_repository / "contracts/orchestrator.yaml"
    path.write_text("id: orchestrator\n", encoding="utf-8")

    with pytest.raises(RegistryValidationError, match="Contrato inválido"):
        RegistryLoader().load(sample_repository / "registry")


def test_registry_reports_invalid_yaml_source(sample_repository: Path) -> None:
    path = sample_repository / "registry/workflows.yaml"
    path.write_text("workflows: [", encoding="utf-8")

    with pytest.raises(RegistryValidationError) as error:
        RegistryLoader().load(sample_repository / "registry")

    assert error.value.path == path
