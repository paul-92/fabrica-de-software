"""Explicit storage codec for Quality Gate results."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import ValidationError

from asep.quality_results.errors import InvalidQualityGateResultStorageFormatError
from asep.quality_results.models import StoredQualityGateResult


class QualityGateResultCodec:
    @staticmethod
    def encode(result: StoredQualityGateResult) -> dict[str, Any]:
        return result.model_dump(mode="json")

    @staticmethod
    def decode(data: Mapping[str, Any]) -> StoredQualityGateResult:
        try:
            return StoredQualityGateResult.model_validate(data)
        except (TypeError, ValidationError) as exc:
            raise InvalidQualityGateResultStorageFormatError(
                "Quality Gate result persistido possui formato inválido."
            ) from exc


__all__ = ["QualityGateResultCodec"]
