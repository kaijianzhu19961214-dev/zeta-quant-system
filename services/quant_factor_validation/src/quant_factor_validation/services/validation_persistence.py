from dataclasses import dataclass, field
from typing import Any, Protocol

from quant_contracts import FactorValidationManifest

from quant_factor_validation.services.validation_artifacts import ValidationArtifactPayload


class ValidationPersistenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredValidationArtifact:
    artifact_id: str
    object_key: str
    file_size_bytes: int
    sha256: str
    content_type: str
    bucket_name: str | None = None
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ValidationArtifactStore(Protocol):
    async def put_validation_artifact(
        self,
        *,
        payload: ValidationArtifactPayload,
    ) -> StoredValidationArtifact:
        raise NotImplementedError


class ValidationLedgerRepository(Protocol):
    async def record_validation_manifest(
        self,
        *,
        manifest: FactorValidationManifest,
    ) -> FactorValidationManifest:
        raise NotImplementedError


class ValidationPersistenceService:
    def __init__(
        self,
        *,
        is_enabled: bool = False,
        artifact_store: ValidationArtifactStore | None = None,
        ledger_repository: ValidationLedgerRepository | None = None,
    ) -> None:
        self.is_enabled = is_enabled
        self.artifact_store = artifact_store
        self.ledger_repository = ledger_repository

    @classmethod
    def disabled(cls) -> "ValidationPersistenceService":
        return cls(is_enabled=False)

    async def persist(
        self,
        *,
        manifest: FactorValidationManifest,
        artifact_payloads: list[ValidationArtifactPayload],
    ) -> FactorValidationManifest:
        if not self.is_enabled:
            return manifest
        if self.artifact_store is None:
            raise ValidationPersistenceError("artifact_store is required when persistence is enabled")
        if self.ledger_repository is None:
            raise ValidationPersistenceError("ledger_repository is required when persistence is enabled")

        stored_artifacts: list[StoredValidationArtifact] = []
        for payload in artifact_payloads:
            stored_artifact = await self.artifact_store.put_validation_artifact(payload=payload)
            _validate_stored_artifact(payload=payload, stored_artifact=stored_artifact)
            stored_artifacts.append(stored_artifact)

        persisted_manifest = _mark_manifest_persisted(
            manifest=manifest,
            stored_artifacts=stored_artifacts,
        )
        return await self.ledger_repository.record_validation_manifest(manifest=persisted_manifest)


def _validate_stored_artifact(
    *,
    payload: ValidationArtifactPayload,
    stored_artifact: StoredValidationArtifact,
) -> None:
    if stored_artifact.artifact_id != payload.artifact_id:
        raise ValidationPersistenceError("stored artifact_id does not match payload artifact_id")
    if stored_artifact.object_key != payload.object_key:
        raise ValidationPersistenceError("stored object_key does not match payload object_key")
    if stored_artifact.file_size_bytes != payload.size_bytes:
        raise ValidationPersistenceError("stored file size does not match payload size")
    if stored_artifact.sha256 != payload.sha256:
        raise ValidationPersistenceError("stored sha256 does not match payload sha256")
    if stored_artifact.content_type != payload.content_type:
        raise ValidationPersistenceError("stored content_type does not match payload content_type")


def _mark_manifest_persisted(
    *,
    manifest: FactorValidationManifest,
    stored_artifacts: list[StoredValidationArtifact],
) -> FactorValidationManifest:
    stored_by_artifact_id = {artifact.artifact_id: artifact for artifact in stored_artifacts}
    persisted_artifacts = []

    for artifact in manifest.artifacts:
        stored_artifact = stored_by_artifact_id.get(artifact.artifact_id)
        if stored_artifact is None:
            raise ValidationPersistenceError("stored artifact is missing for manifest artifact")

        persisted_artifacts.append(
            artifact.__class__.model_validate(
                {
                    **artifact.model_dump(mode="python"),
                    "bucket_name": stored_artifact.bucket_name,
                    "object_key": stored_artifact.object_key,
                    "uri": stored_artifact.uri,
                    "file_size_bytes": stored_artifact.file_size_bytes,
                    "metadata": {
                        **artifact.metadata,
                        **stored_artifact.metadata,
                        "content_type": stored_artifact.content_type,
                        "sha256": stored_artifact.sha256,
                        "persistence_status": "persisted",
                    },
                }
            )
        )

    return manifest.model_copy(
        update={
            "artifacts": persisted_artifacts,
            "persistence_status": "persisted",
        }
    )
