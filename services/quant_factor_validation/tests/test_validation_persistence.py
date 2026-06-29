from datetime import date
import unittest

from quant_contracts import (
    FactorDailyValue,
    FactorGroupReturnPoint,
    FactorIcPoint,
    FactorValidationFinding,
    FactorValidationManifest,
    FactorValidationMetric,
    FactorValidationReport,
    FactorValidationRequest,
)
from quant_factor_validation.services import (
    StoredValidationArtifact,
    ValidationArtifactPayload,
    ValidationPersistenceError,
    ValidationPersistenceService,
    build_validation_artifact_payloads,
    build_validation_manifest,
    enrich_manifest_with_artifact_payloads,
)


class FakeArtifactStore:
    def __init__(self, *, should_corrupt_sha256: bool = False) -> None:
        self.should_corrupt_sha256 = should_corrupt_sha256
        self.payloads: list[ValidationArtifactPayload] = []

    async def put_validation_artifact(
        self,
        *,
        payload: ValidationArtifactPayload,
    ) -> StoredValidationArtifact:
        self.payloads.append(payload)
        return StoredValidationArtifact(
            artifact_id=payload.artifact_id,
            object_key=payload.object_key,
            bucket_name="quant-factor-data",
            uri=f"s3://quant-factor-data/{payload.object_key}",
            file_size_bytes=payload.size_bytes,
            sha256="bad-sha256" if self.should_corrupt_sha256 else payload.sha256,
            content_type=payload.content_type,
            metadata={"etag": f"etag-{payload.artifact_id}"},
        )


class FakeLedgerRepository:
    def __init__(self) -> None:
        self.manifests: list[FactorValidationManifest] = []

    async def record_validation_manifest(
        self,
        *,
        manifest: FactorValidationManifest,
    ) -> FactorValidationManifest:
        self.manifests.append(manifest)
        return manifest


class ValidationPersistenceServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_return_manifest_unchanged_when_persistence_is_disabled(self) -> None:
        manifest, payloads = _make_enriched_manifest_and_payloads()
        store = FakeArtifactStore()
        ledger = FakeLedgerRepository()
        service = ValidationPersistenceService(
            is_enabled=False,
            artifact_store=store,
            ledger_repository=ledger,
        )

        persisted_manifest = await service.persist(
            manifest=manifest,
            artifact_payloads=payloads,
        )

        self.assertEqual(persisted_manifest.persistence_status, "not_persisted")
        self.assertEqual(len(store.payloads), 0)
        self.assertEqual(len(ledger.manifests), 0)

    async def test_should_upload_payloads_and_record_manifest_when_persistence_is_enabled(self) -> None:
        manifest, payloads = _make_enriched_manifest_and_payloads()
        store = FakeArtifactStore()
        ledger = FakeLedgerRepository()
        service = ValidationPersistenceService(
            is_enabled=True,
            artifact_store=store,
            ledger_repository=ledger,
        )

        persisted_manifest = await service.persist(
            manifest=manifest,
            artifact_payloads=payloads,
        )

        self.assertEqual(persisted_manifest.persistence_status, "persisted")
        self.assertEqual(len(store.payloads), 4)
        self.assertEqual(len(ledger.manifests), 1)
        self.assertEqual(persisted_manifest.artifacts[0].bucket_name, "quant-factor-data")
        self.assertEqual(
            persisted_manifest.artifacts[0].uri,
            f"s3://quant-factor-data/{payloads[0].object_key}",
        )
        self.assertEqual(
            persisted_manifest.artifacts[0].metadata["persistence_status"],
            "persisted",
        )
        self.assertEqual(
            persisted_manifest.artifacts[0].metadata["etag"],
            "etag-validation_run_1_validation_report",
        )

    async def test_should_reject_store_result_when_checksum_does_not_match(self) -> None:
        manifest, payloads = _make_enriched_manifest_and_payloads()
        service = ValidationPersistenceService(
            is_enabled=True,
            artifact_store=FakeArtifactStore(should_corrupt_sha256=True),
            ledger_repository=FakeLedgerRepository(),
        )

        with self.assertRaisesRegex(ValidationPersistenceError, "sha256"):
            await service.persist(
                manifest=manifest,
                artifact_payloads=payloads,
            )

    async def test_should_reject_missing_stored_artifact_when_payloads_are_incomplete(self) -> None:
        manifest, payloads = _make_enriched_manifest_and_payloads()
        service = ValidationPersistenceService(
            is_enabled=True,
            artifact_store=FakeArtifactStore(),
            ledger_repository=FakeLedgerRepository(),
        )

        with self.assertRaisesRegex(ValidationPersistenceError, "missing"):
            await service.persist(
                manifest=manifest,
                artifact_payloads=payloads[:-1],
            )

    async def test_should_require_adapters_when_persistence_is_enabled(self) -> None:
        manifest, payloads = _make_enriched_manifest_and_payloads()
        service = ValidationPersistenceService(is_enabled=True)

        with self.assertRaisesRegex(ValidationPersistenceError, "artifact_store"):
            await service.persist(
                manifest=manifest,
                artifact_payloads=payloads,
            )


def _make_enriched_manifest_and_payloads() -> tuple[
    FactorValidationManifest,
    list[ValidationArtifactPayload],
]:
    manifest = build_validation_manifest(
        request=FactorValidationRequest(
            factor_name="momentum_20d",
            factor_values=[_make_factor_value()],
            market_start="2026-01-01",
            market_end="2026-03-31",
            run_id="validation run 1",
        ),
        metrics=_make_metrics(),
        report=_make_report(),
        ic_series=_make_ic_series(),
        group_returns=_make_group_returns(),
    )
    payloads = build_validation_artifact_payloads(
        manifest=manifest,
        metrics=_make_metrics(),
        report=_make_report(),
        ic_series=_make_ic_series(),
        group_returns=_make_group_returns(),
    )
    return (
        enrich_manifest_with_artifact_payloads(
            manifest=manifest,
            artifact_payloads=payloads,
        ),
        payloads,
    )


def _make_factor_value() -> FactorDailyValue:
    return FactorDailyValue(
        symbol="000001.SZ",
        trade_date=date(2026, 3, 13),
        factor_name="momentum_20d",
        factor_value="0.1",
    )


def _make_metrics() -> FactorValidationMetric:
    return FactorValidationMetric(
        factor_name="momentum_20d",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        forward_days=1,
        sample_count=120,
        effective_sample_count=90,
        coverage_ratio=0.75,
        missing_ratio=0.01,
        ic_mean=0.02,
        rank_ic_mean=0.04,
        ic_ir=0.2,
        group_count=5,
        group_return_spread_mean=0.03,
        dataset_code="a_share_1d",
        batch_id="qfq_20260331",
        validation_version="v1",
        run_id="validation run 1",
    )


def _make_report() -> FactorValidationReport:
    return FactorValidationReport(
        decision="review_required",
        summary="Manual review is required.",
        findings=[
            FactorValidationFinding(
                severity="info",
                code="manual_review_required",
                message="Sample size is not enough for an automatic decision.",
            )
        ],
    )


def _make_ic_series() -> list[FactorIcPoint]:
    return [
        FactorIcPoint(
            trade_date=date(2026, 3, 13),
            sample_size=3,
            ic=0.1,
            rank_ic=0.2,
        )
    ]


def _make_group_returns() -> list[FactorGroupReturnPoint]:
    return [
        FactorGroupReturnPoint(
            trade_date=date(2026, 3, 13),
            group_index=1,
            group_count=5,
            sample_size=10,
            average_forward_return=0.01,
        )
    ]


if __name__ == "__main__":
    unittest.main()
