"""Conversão de resultados do processo Codex para o protocolo da ASEP."""

from __future__ import annotations

from asep.providers.errors import ProviderProtocolError
from asep.providers.models import (
    AgentExecutionResult,
    AgentExecutionStatus,
)
from asep.providers.process import ProcessResult


class CodexResultParser:
    def parse(
        self,
        result: ProcessResult,
        *,
        provider_name: str,
        provider_version: str,
    ) -> AgentExecutionResult:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.exit_code == 0 and not stdout:
            raise ProviderProtocolError(
                "Codex concluiu sem produzir saída na saída padrão."
            )

        if result.exit_code < 0:
            return AgentExecutionResult(
                status=AgentExecutionStatus.CANCELLED,
                provider_name=provider_name,
                provider_version=provider_version,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                errors=(stderr or "Processo Codex cancelado.",),
            )

        if result.exit_code != 0:
            return AgentExecutionResult(
                status=AgentExecutionStatus.FAILED,
                provider_name=provider_name,
                provider_version=provider_version,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                errors=(
                    stderr
                    or f"Codex encerrou com exit code {result.exit_code}.",
                ),
            )

        return AgentExecutionResult(
            status=AgentExecutionStatus.SUCCESS,
            provider_name=provider_name,
            provider_version=provider_version,
            exit_code=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
        )
