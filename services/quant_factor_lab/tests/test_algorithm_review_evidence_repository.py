from datetime import UTC, datetime
import unittest

from quant_contracts import AlgorithmReviewGateEvidenceRecord
from sqlalchemy.dialects import postgresql

from quant_factor_lab.repositories.algorithm_review_evidence import (
    SqlAlchemyAlgorithmReviewEvidenceRepository,
    _build_evidence_select_statement,
    _build_evidence_values,
    normalize_database_schema_name,
)


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


class AlgorithmReviewEvidenceRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_record_evidence_with_postgresql_upsert(self) -> None:
        record = _make_evidence_record()
        session_factory = FakeSessionFactory()
        repository = SqlAlchemyAlgorithmReviewEvidenceRepository(session_factory=session_factory)

        persisted_record = await repository.record_evidence(record=record)

        self.assertIs(persisted_record, record)
        self.assertTrue(session_factory.session.is_committed)
        self.assertEqual(len(session_factory.session.statements), 1)
        sql = _compile_statement(statement=session_factory.session.statements[0])
        self.assertIn("ON CONFLICT (evidence_id) DO UPDATE", sql)

    def test_should_map_evidence_values_from_record(self) -> None:
        record = _make_evidence_record()

        values = _build_evidence_values(record=record)

        self.assertEqual(values["evidence_id"], "algorithm_gate_evidence_abc123")
        self.assertEqual(values["algorithm_id"], "technical.momentum")
        self.assertEqual(values["gate_id"], "validation_evidence")
        self.assertEqual(values["evidence_status"], "submitted")
        self.assertEqual(values["artifact_id"], "comparison_report_momentum_1d")
        self.assertEqual(values["notes"], ["source=smoke_real_factor_flow_101"])

    def test_should_build_algorithm_gate_select_statement(self) -> None:
        statement = _build_evidence_select_statement(
            algorithm_id="technical.momentum",
            gate_id="validation_evidence",
            limit=20,
        )

        sql = _compile_statement(statement=statement)

        self.assertIn("algorithm_review_gate_evidence.algorithm_id", sql)
        self.assertIn("algorithm_review_gate_evidence.gate_id", sql)
        self.assertIn("ORDER BY algorithm_review_gate_evidence.submitted_at DESC", sql)

    def test_should_normalize_database_schema_name(self) -> None:
        self.assertEqual(
            normalize_database_schema_name(schema_name=" zeta_quant_factor_lab "),
            "zeta_quant_factor_lab",
        )
        self.assertIsNone(normalize_database_schema_name(schema_name=""))

        with self.assertRaisesRegex(ValueError, "schema"):
            normalize_database_schema_name(schema_name="public;drop table algorithm_review_gate_evidence")


def _compile_statement(*, statement: object) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


def _make_evidence_record() -> AlgorithmReviewGateEvidenceRecord:
    return AlgorithmReviewGateEvidenceRecord(
        evidence_id="algorithm_gate_evidence_abc123",
        algorithm_id="technical.momentum",
        gate_id="validation_evidence",
        gate_category="validation",
        gate_title="Validation evidence",
        previous_gate_status="satisfied",
        submitted_by="codex_smoke",
        evidence_type="validation_report",
        evidence_source="factor_validation/momentum_1d/real_flow_smoke_101/comparison_report.json",
        summary="Momentum validation smoke evidence from 101 data.",
        artifact_id="comparison_report_momentum_1d",
        artifact_uri="s3://quant-factor-data/factor_validation/momentum_1d/comparison_report.json",
        notes=["source=smoke_real_factor_flow_101"],
        submitted_at=datetime(2026, 7, 2, 9, 30, tzinfo=UTC),
    )


if __name__ == "__main__":
    unittest.main()
