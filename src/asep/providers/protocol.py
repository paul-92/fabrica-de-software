"""Contrato estrutural que futuros providers da ASEP devem implementar."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from asep.execution_package import ExecutionPackage
from asep.providers.models import AgentExecutionResult


@runtime_checkable
class AgentProvider(Protocol):
    name: str

    def execute(self, package: ExecutionPackage) -> AgentExecutionResult: ...
