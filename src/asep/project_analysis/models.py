"""Modelos públicos e imutáveis da análise determinística de projetos."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_serializer,
    field_validator,
)

from asep._json_values import freeze_json, json_value


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ScannedFile(_FrozenModel):
    path: Path
    size_bytes: int = Field(ge=0)


class ScannedProject(_FrozenModel):
    root_path: Path
    files: tuple[ScannedFile, ...] = ()
    directories: tuple[Path, ...] = ()
    maximum_depth: int = Field(default=0, ge=0)


class LanguageStatistics(_FrozenModel):
    name: str
    file_count: int = Field(ge=0)
    line_count: int = Field(ge=0)
    extensions: tuple[str, ...] = ()


class FrameworkDetection(_FrozenModel):
    name: str
    ecosystem: str
    evidence: tuple[str, ...] = ()


class PackageManagerDetection(_FrozenModel):
    name: str
    manifest: Path


class ProjectModule(_FrozenModel):
    name: str
    path: Path


class Entrypoint(_FrozenModel):
    path: Path
    language: str


class Dependency(_FrozenModel):
    name: str
    version: str | None = None
    source: Path
    scope: str = "runtime"


class ArchitectureDetection(_FrozenModel):
    name: str
    evidence: tuple[str, ...] = ()


class ProjectStatistics(_FrozenModel):
    file_count: int = Field(ge=0)
    directory_count: int = Field(ge=0)
    lines_of_code: int = Field(ge=0)
    lines_by_language: Mapping[str, int] = Field(default_factory=dict)
    test_file_count: int = Field(ge=0)
    documentation_file_count: int = Field(ge=0)
    maximum_depth: int = Field(ge=0)
    module_count: int = Field(ge=0)
    entrypoint_count: int = Field(ge=0)
    dependency_count: int = Field(ge=0)

    @field_validator("lines_by_language")
    @classmethod
    def lines_are_immutable(
        cls, value: Mapping[str, int]
    ) -> Mapping[str, int]:
        return freeze_json(value, location="lines_by_language")

    @field_serializer("lines_by_language")
    def serialize_lines(
        self, value: Mapping[str, int]
    ) -> dict[str, int]:
        return json_value(value)


class ProjectAnalysis(_FrozenModel):
    root_path: Path
    project_name: str
    languages: tuple[LanguageStatistics, ...] = ()
    frameworks: tuple[FrameworkDetection, ...] = ()
    package_managers: tuple[PackageManagerDetection, ...] = ()
    modules: tuple[ProjectModule, ...] = ()
    entrypoints: tuple[Entrypoint, ...] = ()
    architecture: tuple[ArchitectureDetection, ...] = ()
    dependencies: tuple[Dependency, ...] = ()
    statistics: ProjectStatistics
    metadata: Mapping[str, JsonValue] = Field(default_factory=dict)
    generated_at: datetime

    @field_validator("project_name")
    @classmethod
    def name_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project_name não pode ser vazio")
        return value

    @field_validator("generated_at")
    @classmethod
    def generated_at_is_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at deve possuir timezone")
        return value

    @field_validator("metadata")
    @classmethod
    def metadata_is_immutable(
        cls, value: Mapping[str, JsonValue]
    ) -> Mapping[str, JsonValue]:
        return freeze_json(value, location="metadata")

    @field_serializer("metadata")
    def serialize_metadata(
        self, value: Mapping[str, JsonValue]
    ) -> dict[str, JsonValue]:
        return json_value(value)


__all__ = [
    "ArchitectureDetection",
    "Dependency",
    "Entrypoint",
    "FrameworkDetection",
    "LanguageStatistics",
    "PackageManagerDetection",
    "ProjectAnalysis",
    "ProjectModule",
    "ProjectStatistics",
    "ScannedFile",
    "ScannedProject",
]
