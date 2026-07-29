"""Loader tipado dos catálogos do Registry."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from asep.errors import (
    ConfigurationError,
    RegistryValidationError,
    describe_validation_error,
)
from asep.models import (
    AgentContract,
    AgentRegistryDocument,
    ContractRegistryDocument,
    KnowledgeRegistryDocument,
    PlaybookRegistryDocument,
    QualityGateRegistryDocument,
    RegistrySnapshot,
    WorkflowRegistryDocument,
)
from asep.yaml_io import load_yaml

DocumentT = TypeVar("DocumentT", bound=BaseModel)


class RegistryLoader:
    """Carrega os seis catálogos necessários à Sprint 1."""

    def load(self, root: Path) -> RegistrySnapshot:
        root = root.resolve()
        agents_doc = self._parse(root / "agents.yaml", AgentRegistryDocument)
        contracts_doc = self._parse(root / "contracts.yaml", ContractRegistryDocument)
        workflows_doc = self._parse(root / "workflows.yaml", WorkflowRegistryDocument)
        gates_doc = self._parse(
            root / "quality-gates.yaml", QualityGateRegistryDocument
        )
        playbooks_doc = self._parse(root / "playbooks.yaml", PlaybookRegistryDocument)
        knowledge_doc = self._parse(root / "knowledge.yaml", KnowledgeRegistryDocument)

        snapshot = RegistrySnapshot(
            root=root,
            agents=self._index(agents_doc.agents, root / "agents.yaml"),
            contracts=self._index(contracts_doc.contracts, root / "contracts.yaml"),
            workflows=self._index(workflows_doc.workflows, root / "workflows.yaml"),
            quality_gates=self._index(
                gates_doc.quality_gates, root / "quality-gates.yaml"
            ),
            playbooks=self._index(playbooks_doc.playbooks, root / "playbooks.yaml"),
            knowledge=self._index(knowledge_doc.knowledge, root / "knowledge.yaml"),
        )
        self._validate_paths(snapshot)
        self._validate_cross_references(snapshot)
        return snapshot

    @staticmethod
    def _parse(path: Path, model: type[DocumentT]) -> DocumentT:
        try:
            return model.model_validate(load_yaml(path))
        except ValidationError as exc:
            raise RegistryValidationError(
                f"Registry inválido: {describe_validation_error(exc)}", path=path
            ) from exc
        except ConfigurationError as exc:
            raise RegistryValidationError(exc.message, path=path) from exc

    @staticmethod
    def _index(
        items: Iterable[DocumentT], source: Path
    ) -> dict[str, DocumentT]:
        indexed: dict[str, DocumentT] = {}
        for item in items:
            item_id = str(getattr(item, "id"))
            if item_id in indexed:
                raise RegistryValidationError(
                    f"ID duplicado no Registry: {item_id}", path=source
                )
            indexed[item_id] = item
        return indexed

    def _validate_paths(self, snapshot: RegistrySnapshot) -> None:
        references: list[tuple[str, str]] = []
        for agent in snapshot.agents.values():
            references.extend(
                [(f"agent:{agent.id}:contract", agent.contract), (f"agent:{agent.id}:manual", agent.manual)]
            )
        for catalog in (
            snapshot.contracts,
            snapshot.workflows,
            snapshot.quality_gates,
            snapshot.playbooks,
            snapshot.knowledge,
        ):
            for item in catalog.values():
                path = getattr(item, "path", None) or getattr(item, "definition", None)
                if path:
                    references.append((str(getattr(item, "id")), str(path)))
        for label, raw_path in references:
            resolved = self._resolve(snapshot.root, raw_path)
            if not resolved.is_file():
                raise RegistryValidationError(
                    f"Referência inexistente ({label}): {raw_path}",
                    path=resolved,
                )

    def _validate_cross_references(self, snapshot: RegistrySnapshot) -> None:
        agent_ids = set(snapshot.agents)
        gate_ids = set(snapshot.quality_gates)

        for gate in snapshot.quality_gates.values():
            if gate.owner not in agent_ids:
                raise RegistryValidationError(
                    f"Owner do quality gate não está registrado: {gate.id} -> {gate.owner}",
                    path=snapshot.root / "quality-gates.yaml",
                )

        for agent in snapshot.agents.values():
            contract_ref = snapshot.contracts.get(agent.id)
            if contract_ref is None:
                raise RegistryValidationError(
                    f"Agente sem contrato no Registry: {agent.id}",
                    path=snapshot.root / "contracts.yaml",
                )
            agent_contract_path = self._resolve(snapshot.root, agent.contract)
            registered_contract_path = self._resolve(snapshot.root, contract_ref.path)
            if agent_contract_path != registered_contract_path:
                raise RegistryValidationError(
                    f"Contrato divergente para agente {agent.id}.",
                    path=snapshot.root / "agents.yaml",
                )
            self._validate_contract(
                agent.id,
                agent.version,
                agent.capabilities,
                registered_contract_path,
                agent_ids,
                gate_ids,
                snapshot.root.parent,
            )

        unbound_contracts = set(snapshot.contracts) - agent_ids
        if unbound_contracts:
            raise RegistryValidationError(
                f"Contratos sem agente registrado: {sorted(unbound_contracts)}",
                path=snapshot.root / "contracts.yaml",
            )

        for workflow in snapshot.workflows.values():
            unknown_agents = set(workflow.agents) - agent_ids
            unknown_gates = set(workflow.gates) - gate_ids
            if unknown_agents or unknown_gates:
                raise RegistryValidationError(
                    f"Workflow {workflow.id} referencia agentes/gates desconhecidos; "
                    f"agentes={sorted(unknown_agents)}, gates={sorted(unknown_gates)}",
                    path=snapshot.root / "workflows.yaml",
                )

    def _validate_contract(
        self,
        agent_id: str,
        agent_version: str,
        registry_capabilities: list[str],
        path: Path,
        agent_ids: set[str],
        gate_ids: set[str],
        repository_root: Path,
    ) -> None:
        try:
            contract = AgentContract.model_validate(load_yaml(path))
        except ValidationError as exc:
            raise RegistryValidationError(
                f"Contrato inválido para {agent_id}: "
                f"{describe_validation_error(exc)}",
                path=path,
            ) from exc
        except ConfigurationError as exc:
            raise RegistryValidationError(
                f"Contrato inválido para {agent_id}: {exc.message}", path=path
            ) from exc
        if contract.id != agent_id or contract.version != agent_version:
            raise RegistryValidationError(
                f"ID ou versão do contrato diverge do agente {agent_id}.", path=path
            )
        missing_capabilities = set(registry_capabilities) - set(contract.capabilities)
        unknown_next_agents = set(contract.next_agents) - agent_ids
        unknown_gates = set(contract.quality_gates) - gate_ids
        if missing_capabilities or unknown_next_agents or unknown_gates:
            raise RegistryValidationError(
                f"Contrato {agent_id} inconsistente; capacidades ausentes="
                f"{sorted(missing_capabilities)}, próximos agentes desconhecidos="
                f"{sorted(unknown_next_agents)}, gates desconhecidos="
                f"{sorted(unknown_gates)}",
                path=path,
            )
        for consultation in contract.consults:
            consultation_path = (path.parent / consultation).resolve()
            if (
                consultation_path != repository_root
                and repository_root not in consultation_path.parents
            ):
                raise RegistryValidationError(
                    f"Consulta sai da raiz do repositório: {consultation}", path=path
                )
            if not consultation_path.is_file():
                raise RegistryValidationError(
                    f"Consulta obrigatória inexistente: {consultation}",
                    path=consultation_path,
                )

    @staticmethod
    def _resolve(root: Path, raw_path: str) -> Path:
        resolved = (root / raw_path).resolve()
        repository_root = root.parent.resolve()
        if resolved != repository_root and repository_root not in resolved.parents:
            raise RegistryValidationError(
                f"Referência sai da raiz do repositório: {raw_path}", path=resolved
            )
        return resolved
