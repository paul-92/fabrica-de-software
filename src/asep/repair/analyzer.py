"""Análise determinística de falhas produzidas pela validação."""

from __future__ import annotations

import re

from asep.repair.models import FailureAnalysis


class PytestFailureAnalyzer:
    """Converte saída textual do pytest em diagnóstico estruturado."""

    _FAILED_TEST_PATTERN = re.compile(
        r"FAILED\s+(?P<path>[^\s:]+(?:\.py)?)(?:::[^\s]+)?"
    )

    _TRACEBACK_PATH_PATTERN = re.compile(
        r"(?P<path>[A-Za-z0-9_./\\-]+\.py):\d+"
    )

    def analyze(
        self,
        failure_output: str,
    ) -> FailureAnalysis:
        output = failure_output.strip()

        if not output:
            return FailureAnalysis(
                summary="Falha de validação sem saída disponível.",
                failure_output="",
            )

        affected_paths = self._affected_paths(output)

        return FailureAnalysis(
            summary=self._summary(output),
            failure_output=failure_output,
            affected_paths=affected_paths,
            probable_cause=self._probable_cause(output),
        )

    @classmethod
    def _affected_paths(
        cls,
        output: str,
    ) -> tuple[str, ...]:
        paths: list[str] = []

        for pattern in (
            cls._FAILED_TEST_PATTERN,
            cls._TRACEBACK_PATH_PATTERN,
        ):
            for match in pattern.finditer(output):
                path = match.group("path").replace("\\", "/")

                if path not in paths:
                    paths.append(path)

        return tuple(paths)

    @staticmethod
    def _summary(
        output: str,
    ) -> str:
        for line in output.splitlines():
            stripped = line.strip()

            if stripped.startswith("FAILED "):
                return stripped

        return "Pytest reportou falha de validação."

    @staticmethod
    def _probable_cause(
        output: str,
    ) -> str | None:
        for line in output.splitlines():
            stripped = line.strip()

            if stripped.startswith("E "):
                cause = stripped[2:].strip()

                if cause:
                    return cause

        return None


__all__ = [
    "PytestFailureAnalyzer",
]