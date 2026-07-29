"""Validação documental da ASEP. Não executa agentes nem integra modelos."""

from __future__ import annotations

import pathlib
import re
import sys

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def load(path: pathlib.Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_yaml() -> None:
    for path in ROOT.rglob("*.yaml"):
        try:
            load(path)
        except Exception as exc:  # evidence includes the parser message
            ERRORS.append(f"YAML inválido: {path.relative_to(ROOT)}: {exc}")


def validate_markdown_links() -> None:
    pattern = re.compile(r"\[[^\]]*]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        for raw in pattern.findall(path.read_text(encoding="utf-8")):
            destination = raw.split("#", 1)[0].strip().strip("<>")
            if not destination or re.match(r"^[a-z]+://", destination):
                continue
            if not (path.parent / destination).resolve().exists():
                ERRORS.append(
                    f"Link quebrado: {path.relative_to(ROOT)} -> {raw}"
                )


def validate_registry_paths() -> None:
    path_keys = {"path", "contract", "manual", "definition"}

    def walk(registry: pathlib.Path, value) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in path_keys and isinstance(child, str):
                    if not (registry.parent / child).resolve().exists():
                        ERRORS.append(
                            f"Caminho inválido no Registry: {registry.name}: {child}"
                        )
                walk(registry, child)
        elif isinstance(value, list):
            for child in value:
                walk(registry, child)

    for path in (ROOT / "registry").glob("*.yaml"):
        walk(path, load(path) or {})


def validate_composition() -> tuple[int, int, int]:
    agents = {item["id"] for item in load(ROOT / "registry/agents.yaml")["agents"]}
    contracts = {
        item["id"] for item in load(ROOT / "registry/contracts.yaml")["contracts"]
    }
    gates = {
        item["id"]
        for item in load(ROOT / "registry/quality-gates.yaml")["quality_gates"]
    }
    roles = {item["id"] for item in load(ROOT / "registry/roles.yaml")["roles"]}
    departments = {
        item["id"]
        for item in load(ROOT / "registry/departments.yaml")["departments"]
    }
    if agents != contracts:
        ERRORS.append(f"Agentes sem contrato ou contratos órfãos: {agents ^ contracts}")

    contracts_by_id = {}
    producers = {}
    for path in (ROOT / "contracts").glob("*.yaml"):
        contract = load(path)
        contracts_by_id[contract["id"]] = contract
        for output in contract.get("produces") or []:
            producers.setdefault(output, set()).add(contract["id"])
        if contract.get("role") not in roles:
            ERRORS.append(f"{path.name}: role não registrado: {contract.get('role')}")
        if contract.get("department") not in departments:
            ERRORS.append(
                f"{path.name}: department não registrado: {contract.get('department')}"
            )
        if contract["id"] == contract.get("reports_to"):
            ERRORS.append(f"{path.name}: reports_to aponta para o próprio agente")
        for agent in contract.get("next_agents") or []:
            if agent not in agents:
                ERRORS.append(f"{path.name}: next_agent inexistente: {agent}")
        for gate in contract.get("quality_gates") or []:
            if gate not in gates:
                ERRORS.append(f"{path.name}: quality gate inexistente: {gate}")

    for contract_id, contract in contracts_by_id.items():
        for required_input in contract.get("required_inputs") or []:
            if required_input not in producers and required_input != "project-brief":
                ERRORS.append(
                    f"{contract_id}: required_input sem produtor: {required_input}"
                )

    for path in (ROOT / "workflows").glob("*.yaml"):
        workflow = load(path)
        for assigned in (workflow.get("assigned_agents") or {}).values():
            for agent in assigned or []:
                if agent not in agents:
                    ERRORS.append(f"{path.name}: agente inexistente: {agent}")
        for gate in workflow.get("quality_gates") or []:
            if gate not in gates:
                ERRORS.append(f"{path.name}: quality gate inexistente: {gate}")

    workflow_registry = {
        item["id"]: item
        for item in load(ROOT / "registry/workflows.yaml")["workflows"]
    }
    for path in (ROOT / "workflows").glob("*-project.yaml"):
        workflow = load(path)
        registered = workflow_registry.get(workflow["id"])
        if not registered:
            ERRORS.append(f"{path.name}: workflow ausente do Registry")
            continue
        assigned = {
            agent
            for values in (workflow.get("assigned_agents") or {}).values()
            for agent in (values or [])
        }
        registered_agents = set(registered.get("agents") or [])
        if assigned != registered_agents:
            ERRORS.append(
                f"{path.name}: agentes divergem do Registry: "
                f"{sorted(assigned ^ registered_agents)}"
            )

    return len(agents), len(contracts), len(gates)


def validate_agent_structure() -> None:
    agent_ids = {
        item["id"] for item in load(ROOT / "registry/agents.yaml")["agents"]
    }
    expected = set(range(1, 28))
    for agent_id in agent_ids:
        path = ROOT / "agents" / f"{agent_id}.md"
        headings = {
            int(number)
            for number in re.findall(
                r"^## (\d+)\.", path.read_text(encoding="utf-8"), re.MULTILINE
            )
        }
        if headings != expected:
            ERRORS.append(f"{path.name}: estrutura de 27 seções incompleta")


def validate_empty_content() -> None:
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and path.stat().st_size == 0:
            ERRORS.append(f"Arquivo vazio: {path.relative_to(ROOT)}")
        if path.is_dir() and not any(path.iterdir()):
            ERRORS.append(f"Pasta vazia: {path.relative_to(ROOT)}")


def validate_control_characters() -> None:
    allowed = {"\n", "\r", "\t"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        invalid = sorted(
            {ord(char) for char in text if ord(char) < 32 and char not in allowed}
        )
        if invalid:
            ERRORS.append(
                f"Caracteres de controle em {path.relative_to(ROOT)}: {invalid}"
            )


def main() -> int:
    validate_yaml()
    validate_markdown_links()
    validate_registry_paths()
    agents, contracts, gates = validate_composition()
    validate_agent_structure()
    validate_empty_content()
    validate_control_characters()
    yaml_count = len(list(ROOT.rglob("*.yaml")))
    markdown_count = len(list(ROOT.rglob("*.md")))
    print(
        f"ASEP validation: yaml={yaml_count}, markdown={markdown_count}, "
        f"agents={agents}, contracts={contracts}, gates={gates}, "
        f"errors={len(ERRORS)}"
    )
    for error in ERRORS:
        print(f"ERROR: {error}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
