import unittest
from typing import Any

from quant_contracts import FactorComparisonReport

from quant_ops_api.integrations import ArtifactObjectReadError
from quant_ops_api.schemas import FactorComparisonArtifactReference
from quant_ops_api.services.factor_comparison_artifact_service import FactorComparisonArtifactService


class FakeArtifactObjectReader:
    def __init__(self, *, payload: dict[str, Any] | None = None, should_fail: bool = False) -> None:
        self.payload = payload or _make_report_payload()
        self.should_fail = should_fail
        self.latest_bucket_name: str | None = None
        self.latest_object_key: str | None = None

    async def read_json_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> dict[str, Any]:
        self.latest_bucket_name = bucket_name
        self.latest_object_key = object_key
        if self.should_fail:
            raise ArtifactObjectReadError("object not found")
        return self.payload


class FactorComparisonArtifactServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_return_not_configured_when_reader_is_missing(self) -> None:
        service = FactorComparisonArtifactService()

        result = await service.read_comparison_report(
            artifact_reference=_make_artifact_reference(),
        )

        self.assertEqual(result.status, "object_reader_not_configured")
        self.assertFalse(result.is_loaded)

    async def test_should_load_factor_comparison_report_from_object_reader(self) -> None:
        reader = FakeArtifactObjectReader()
        service = FactorComparisonArtifactService(object_reader=reader)

        result = await service.read_comparison_report(
            artifact_reference=_make_artifact_reference(),
        )

        self.assertEqual(result.status, "loaded")
        self.assertTrue(result.is_loaded)
        self.assertIsInstance(result.comparison_report, FactorComparisonReport)
        self.assertEqual(result.comparison_report.factor_name, "momentum_20d")
        self.assertEqual(reader.latest_bucket_name, "quant-factor-data")
        self.assertEqual(
            reader.latest_object_key,
            "factor_validation/momentum_20d/validation_run_1/comparison_report.json",
        )

    async def test_should_resolve_object_location_from_s3_uri(self) -> None:
        reader = FakeArtifactObjectReader()
        service = FactorComparisonArtifactService(object_reader=reader)

        result = await service.read_comparison_report(
            artifact_reference=_make_artifact_reference(
                bucket_name=None,
                object_key=None,
                uri="s3://quant-factor-data/factor_validation/momentum_20d/validation_run_1/comparison_report.json",
            ),
        )

        self.assertEqual(result.status, "loaded")
        self.assertEqual(reader.latest_bucket_name, "quant-factor-data")
        self.assertEqual(
            reader.latest_object_key,
            "factor_validation/momentum_20d/validation_run_1/comparison_report.json",
        )

    async def test_should_return_invalid_payload_when_contract_validation_fails(self) -> None:
        service = FactorComparisonArtifactService(
            object_reader=FakeArtifactObjectReader(payload={"factor_name": "momentum_20d"})
        )

        result = await service.read_comparison_report(
            artifact_reference=_make_artifact_reference(),
        )

        self.assertEqual(result.status, "invalid_payload")
        self.assertFalse(result.is_loaded)

    async def test_should_return_read_failed_when_object_reader_fails(self) -> None:
        service = FactorComparisonArtifactService(
            object_reader=FakeArtifactObjectReader(should_fail=True)
        )

        result = await service.read_comparison_report(
            artifact_reference=_make_artifact_reference(),
        )

        self.assertEqual(result.status, "read_failed")
        self.assertFalse(result.is_loaded)


def _make_artifact_reference(
    *,
    bucket_name: str | None = "quant-factor-data",
    object_key: str | None = "factor_validation/momentum_20d/validation_run_1/comparison_report.json",
    uri: str | None = None,
) -> FactorComparisonArtifactReference:
    return FactorComparisonArtifactReference(
        artifact_id="validation_run_1_comparison_report",
        task_id="validation_run_1",
        storage_type="minio_s3",
        bucket_name=bucket_name,
        object_key=object_key,
        uri=uri,
        schema_version="factor_comparison_report.v1",
    )


def _make_report_payload() -> dict[str, Any]:
    return {
        "factor_name": "momentum_20d",
        "primary_engine": "alphalens",
        "engine_results": [],
        "engine_count": 1,
        "has_engine_disagreement": False,
        "comparison_summary": "Loaded from persisted artifact.",
    }


if __name__ == "__main__":
    unittest.main()
