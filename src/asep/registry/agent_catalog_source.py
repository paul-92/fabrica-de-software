"""Adapter seguro entre o Registry declarativo e a Application Layer."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from asep.application.agent_catalog import AgentCatalogEntry
from asep.errors import AsepError, AgentCatalogUnavailableError
from asep.registry.loader import RegistryLoader


class DeclarativeAgentCatalogSource:
    def __init__(
        self,
        registry_directory: Path,
        loader: RegistryLoader | None = None,
    ) -> None:
        self._registry_directory = registry_directory
        self._loader = loader or RegistryLoader()

    def list_agents(self) -> tuple[AgentCatalogEntry, ...]:
        try:
            snapshot = self._loader.load(self._registry_directory)
            return tuple(
                AgentCatalogEntry(
                    agent_id=item.id,
                    name=item.name,
                    version=item.version,
                    lifecycle_status=item.status,
                    department=item.department,
                    capabilities=tuple(item.capabilities),
                )
                for item in snapshot.agents.values()
            )
        except AgentCatalogUnavailableError:
            raise
        except (AsepError, ValidationError, ValueError, OSError) as exc:
            raise AgentCatalogUnavailableError(
                "Agent catalog could not be loaded."
            ) from exc


__all__ = ["DeclarativeAgentCatalogSource"]
