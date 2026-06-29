from datetime import datetime, timezone
import unittest

from quant_contracts import (
    ArtifactType,
    FactorValidationManifest,
    TaskArtifact,
    TaskRun,
    TaskStatus,
)
from sqlalchemy.dialects import postgresql

from quant_factor_validation.repositories.validation_ledger import (
    SqlAlchemyValidationLedgerRepository,
    _build_task_artifact_values,
    _build_task_run_values,
)
from quant_factor_validation.services import ValidationPersistenceError


class FakeSession:
    def __init__(self) -> None:
        self.statements: list[object] = []
        self.is_committed = False

    async def execute(self, statement: object) -> None:
        self.statements.append(statement)

    async def commit(self) -> None:
        self.is_committed = True


class FakeSessionContext:
    def __init__(self, *, session: FakeSession) -> None:
        self.session = session

    async def __aenter__(self) -> FakeSession:
        return self.session

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        return None


class FakeSessionFactory:
    def __init__(self) -> None:
        self.session = FakeSession()

    def __call__(self) -> FakeSessionContext:
        return FakeSessionContext(session=self.session)


class ValidationLedgerRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_record_manifest_with_postgresql_upserts(self) -> None:
        manifest = _make_persisted_manifest()
        session_factory = FakeSessionFactory()
        repository = SqlAlchemyValidationLedgerRepository(session_factory=session_factory)

        recorded_manifest = await repository.record_validation_manifest(manifest=manifest)

        self.assertIs(recorded_manifest, manifest)
        self.assertTrue(session_factory.session.is_committed)
        self.assertEqual(len(session_factory.session.statements), 2)
        task_sql = _compile_statement(statement=session_factory.session.statements[0])
        artifact_sql = _compile_statement(statement=session_factory.session.statements[1])
        self.assertIn("ON CONFLICT (task_id) DO UPDATE", task_sql)
        self.assertIn("ON CONFLICT (artifact_id) DO UPDATE", artifact_sql)

    def test_should_map_task_run_values_from_manifest(self) -> None:
        manifest = _make_persisted_manifest()

        values = _build_task_run_values(manifest=manifest)

        self.assertEqual(values["task_id"], "validation_run_1")
        self.assertEqual(values["task_type"], "factor_validation")
        self.assertEqual(values["status"], "succeeded")
        self.assertEqual(values["input_params"]["factor_name"], "momentum_20d")
        self.assertEqual(values["output_summary"]["decision"], "candidate_pass")

    def test_should_map_artifact_values_from_persisted_manifest(self) -> None:
        artifact = _make_persisted_manifest().artifacts[0]

        values = _build_task_artifact_values(artifact=artifact)

        self.assertEqual(values["artifact_id"], "validation_run_1_validation_report")
        self.assertEqual(values["task_id"], "validation_run_1")
        self.assertEqual(values["artifact_type"], "validation_report")
        self.assertEqual(values["storage_type"], "minio_s3")
        self.assertEqual(values["bucket_name"], "quant-factor-data")
        self.assertEqual(values["content_type"], "application/json")
        self.assertEqual(values["etag"], "etag-123")

    def test_should_reject_artifact_without_storage_fields(self) -> None:
        artifact = _make_persisted_manifest().artifacts[0].model_copy(
            update={
                "bucket_name": None,
            }
        )

        with self.assertRaisesRegex(ValidationPersistenceError, "bucket_name"):
            _build_task_artifact_values(artifact=artifact)


def _compile_statement(*, statement: object) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def _make_persisted_manifest() -> FactorValidationManifest:
    finished_at = datetime(2026, 6, 29, tzinfo=timezone.utc)
    task_run = TaskRun(
        task_id="validation_run_1",
        task_type="factor_validation",
        task_name="momentum_20d_v1_1d",
        owner="researcher_a",
        status=TaskStatus.SUCCEEDED,
        input_params={
            "factor_name": "momentum_20d",
            "dataset_code": "a_share_1d",
            "forward_days": 1,
        },
        output_summary={
            "effective_sample_count": 120,
            "rank_ic_mean": 0.04,
            "decision": "candidate_pass",
        },
        finished_at=finished_at,
    )
    artifact = TaskArtifact(
        artifact_id="validation_run_1_validation_report",
        task_id=task_run.task_id,
        artifact_type=ArtifactType.VALIDATION_REPORT,
        bucket_name="quant-factor-data",
        object_key="factor_validation/momentum_20d/validation_run_1/validation_report.json",
        uri="s3://quant-factor-data/factor_validation/momentum_20d/validation_run_1/validation_report.json",
        file_size_bytes=128,
        metadata={
            "content_type": "application/json",
            "sha256": "sha-123",
            "etag": "etag-123",
            "object_store": "minio_s3",
            "persistence_status": "persisted",
        },
    )
    return FactorValidationManifest(
        manifest_id="manifest_validation_run_1",
        task_run=task_run,
        artifacts=[artifact],
        persistence_status="persisted",
        created_at=finished_at,
    )


if __name__ == "__main__":
    unittest.main()
