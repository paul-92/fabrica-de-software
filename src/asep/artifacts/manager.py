"""Artifact Manager com paths restritos, checksum e colisão explícita."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

import yaml

from asep.errors import ArtifactError
from asep.execution.models import ArtifactDraft, ArtifactReference


class ArtifactManager:
    def persist(
        self,
        draft: ArtifactDraft,
        artifacts_root: Path,
        *,
        run_id: str,
        project_id: str,
        stage_id: str,
        agent_id: str,
    ) -> ArtifactReference:
        relative = PurePosixPath(draft.relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ArtifactError(
                f"Path de artefato não autorizado: {draft.relative_path}"
            )
        root = artifacts_root.resolve()
        target = root.joinpath(*relative.parts).resolve()
        if root != target and root not in target.parents:
            raise ArtifactError(
                f"Path de artefato sai do diretório da execução: {draft.relative_path}"
            )
        if target.exists():
            raise ArtifactError("Colisão de artefato detectada.", path=target)
        target.parent.mkdir(parents=True, exist_ok=True)
        checksum = hashlib.sha256(draft.content.encode("utf-8")).hexdigest()
        created_at = datetime.now(UTC)
        reference = ArtifactReference(
            artifact_id=str(uuid4()),
            run_id=run_id,
            project_id=project_id,
            stage_id=stage_id,
            agent_id=agent_id,
            path=target.relative_to(root).as_posix(),
            type=draft.type,
            created_at=created_at,
            checksum=checksum,
        )
        temporary = target.with_name(f".{target.name}.{run_id}.tmp")
        metadata = target.with_suffix(target.suffix + ".metadata.yaml")
        metadata_temporary = metadata.with_name(f".{metadata.name}.{run_id}.tmp")
        try:
            temporary.write_text(draft.content, encoding="utf-8")
            metadata_temporary.write_text(
                yaml.safe_dump(
                    reference.model_dump(mode="json"),
                    allow_unicode=True,
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            os.replace(temporary, target)
            os.replace(metadata_temporary, metadata)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            metadata_temporary.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise ArtifactError(
                f"Falha ao persistir artefato: {exc}", path=target
            ) from exc
        return reference
