from datetime import datetime, timezone
import unittest

from quant_contracts import (
    ArtifactType,
    FactorValidationManifest,
    FactorValidationMetric,
    FactorValidationResponse,
    TaskArtifact,
    TaskRun,
    TaskStatus,
)

from quant_factor_validation.tools.persistence_smoke import (
    DEFAULT_BUCKET_NAME,
    DEFAULT_RUN_ID,
    LedgerCounts,
    build_smoke_request,
    parse_bool,
    read_config_from_env,
    validate_ledger_counts,
    validate_persisted_response,
)


class PersistenceSmokeToolTest(unittest.TestCase):
    def test_should_require_persistence_environment_variables(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "VALIDATION_DATABASE_URL"):
            read_config_from_env(env={})

    def test_should_read_config_from_environment_without_printing_secrets(self) -> None:
        config = read_config_from_env(
            env={
                "VALIDATION_DATABASE_URL": "postgresql+asyncpg://user:pass@postgres:5432/db",
                "VALIDATION_OBJECT_STORE_ENDPOINT": "http://minio:9000",
                "VALIDATION_OBJECT_STORE_ACCESS_KEY": "access",
                "VALIDATION_OBJECT_STORE_SECRET_KEY": "secret",
                "VALIDATION_OBJECT_STORE_SECURE": "true",
                "VALIDATION_SMOKE_CREATE_BUCKET": "yes",
                "VALIDATION_SMOKE_RUN_ID": "smoke_run_1",
            }
        )

        self.assertEqual(config.object_store_bucket, DEFAULT_BUCKET_NAME)
        self.assertTrue(config.object_store_secure)
        self.assertTrue(config.should_create_bucket)
        self.assertEqual(config.run_id, "smoke_run_1")

    def test_should_parse_boolean_values(self) -> None:
        self.assertTrue(parse_bool(value="on", default=False))
        self.assertFalse(parse_bool(value="0", default=True))
        self.assertTrue(parse_bool(value=None, default=True))

        with self.assertRaisesRegex(RuntimeError, "invalid boolean"):
            parse_bool(value="maybe", default=False)

    def test_should_build_deterministic_smoke_request(self) -> None:
        request = build_smoke_request(run_id=DEFAULT_RUN_ID)

        self.assertEqual(request.factor_name, "smoke_momentum_1d")
        self.assertEqual(request.run_id, DEFAULT_RUN_ID)
        self.assertEqual(len(request.factor_values), 2)
        self.assertEqual(request.market_start.isoformat(), "2026-03-13")
        self.assertEqual(request.market_end.isoformat(), "2026-03-16")

    def test_should_validate_persisted_response(self) -> None:
        manifest = _make_manifest(persistence_status="persisted")
        response = FactorValidationResponse(
            metrics=_make_metrics(),
            manifest=manifest,
        )

        validated_manifest = validate_persisted_response(response=response)

        self.assertIs(validated_manifest, manifest)

    def test_should_reject_not_persisted_response(self) -> None:
        response = FactorValidationResponse(
            metrics=_make_metrics(),
            manifest=_make_manifest(persistence_status="not_persisted"),
        )

        with self.assertRaisesRegex(RuntimeError, "persistence_status"):
            validate_persisted_response(response=response)

    def test_should_validate_ledger_counts(self) -> None:
        validate_ledger_counts(
            counts=LedgerCounts(task_count=1, artifact_count=4),
            expected_artifact_count=4,
        )

        with self.assertRaisesRegex(RuntimeError, "task_artifact"):
            validate_ledger_counts(
                counts=LedgerCounts(task_count=1, artifact_count=3),
                expected_artifact_count=4,
            )


def _make_metrics() -> FactorValidationMetric:
    return FactorValidationMetric(
        factor_name="smoke_momentum_1d",
        start_date="2026-03-13",
        end_date="2026-03-13",
        forward_days=1,
        sample_count=2,
        effective_sample_count=2,
        coverage_ratio=1.0,
        missing_ratio=0.0,
        group_count=2,
    )


def _make_manifest(*, persistence_status: str) -> FactorValidationManifest:
    created_at = datetime(2026, 6, 29, tzinfo=timezone.utc)
    task_run = TaskRun(
        task_id="validation_smoke_local",
        task_type="factor_validation",
        task_name="smoke_momentum_1d_v1_1d",
        status=TaskStatus.SUCCEEDED,
        input_params={"factor_name": "smoke_momentum_1d"},
        output_summary={"effective_sample_count": 2},
        finished_at=created_at,
    )
    artifacts = [
        TaskArtifact(
            artifact_id=f"validation_smoke_local_artifact_{index}",
            task_id=task_run.task_id,
            artifact_type=ArtifactType.METRICS_TABLE,
            bucket_name=DEFAULT_BUCKET_NAME,
            object_key=f"factor_validation/smoke/{index}.json",
            uri=f"s3://{DEFAULT_BUCKET_NAME}/factor_validation/smoke/{index}.json",
            file_size_bytes=2,
            metadata={"persistence_status": persistence_status},
        )
        for index in range(4)
    ]
    return FactorValidationManifest(
        manifest_id="manifest_validation_smoke_local",
        task_run=task_run,
        artifacts=artifacts,
        persistence_status=persistence_status,
        created_at=created_at,
    )


if __name__ == "__main__":
    unittest.main()
