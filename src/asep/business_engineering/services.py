"""Serviços determinísticos da camada de Business Engineering."""

from __future__ import annotations

import re

from asep.business_engineering.models import (
    BusinessDescription,
    ProjectBlueprint,
    Requirement,
    RequirementPriority,
)

class RequirementAnalyzer:
    """Transforma uma descrição de negócio em requisitos estruturados.

    Nesta primeira versão, a análise é totalmente determinística.
    Cada frase não vazia da descrição origina um requisito funcional.
    """

    _SENTENCE_SEPARATOR = re.compile(r"[.!?\n]+")

    def analyze(
        self,
        description: BusinessDescription,
    ) -> tuple[Requirement, ...]:
        """Analisa uma descrição e retorna requisitos estruturados."""

        normalized_description = description.text.strip()

        if not normalized_description:
            raise ValueError("description não pode ser vazia")

        sentences = self._extract_sentences(normalized_description)

        return tuple(
            Requirement(
                id=f"REQ-{index:03d}",
                title=self._build_title(sentence),
                description=sentence,
                priority=RequirementPriority.MEDIUM,
                functional=True,
            )
            for index, sentence in enumerate(sentences, start=1)
        )

    def _extract_sentences(self, description: str) -> tuple[str, ...]:
        sentences = tuple(
            sentence.strip()
            for sentence in self._SENTENCE_SEPARATOR.split(description)
            if sentence.strip()
        )

        if not sentences:
            raise ValueError(
                "description deve possuir ao menos uma informação válida"
            )

        return sentences

    @staticmethod
    def _build_title(sentence: str) -> str:
        maximum_length = 60

        if len(sentence) <= maximum_length:
            return sentence

        shortened = sentence[:maximum_length].rstrip()
        return f"{shortened}..."

class BlueprintBuilder:
    """Constrói um ProjectBlueprint a partir de uma descrição de negócio."""

    def __init__(
        self,
        requirement_analyzer: RequirementAnalyzer | None = None,
    ) -> None:
        self._requirement_analyzer = (
            requirement_analyzer or RequirementAnalyzer()
        )

    def build(
        self,
        project_name: str,
        description: BusinessDescription,
    ) -> ProjectBlueprint:
        """Cria um blueprint inicial com requisitos analisados."""

        normalized_project_name = project_name.strip()

        if not normalized_project_name:
            raise ValueError("project_name não pode ser vazio")

        requirements = self._requirement_analyzer.analyze(description)

        return ProjectBlueprint(
            project_name=normalized_project_name,
            description=description.text,
            requirements=requirements,
        )
__all__ = [
    "BlueprintBuilder",
    "RequirementAnalyzer",
]