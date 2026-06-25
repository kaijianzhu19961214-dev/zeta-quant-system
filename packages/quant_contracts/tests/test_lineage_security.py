import unittest

from pydantic import ValidationError

from quant_contracts import ArtifactType, TaskArtifact, TaskRun


class LineageSecurityTest(unittest.TestCase):
    def test_task_run_rejects_secret_like_input_keys(self) -> None:
        with self.assertRaises(ValidationError):
            TaskRun(
                task_id="task_1",
                task_type="ingestion",
                task_name="import bars",
                input_params={"tushare_token": "should_not_be_here"},
            )

    def test_task_artifact_accepts_public_manifest_metadata(self) -> None:
        artifact = TaskArtifact(
            artifact_id="artifact_1",
            task_id="task_1",
            artifact_type=ArtifactType.MARKET_DATA,
            bucket_name="quant-factor-data",
            object_key="pilot/shared_data/sample.parquet",
            metadata={"row_count": 10, "data_version": "sample"},
        )

        self.assertEqual(artifact.metadata["row_count"], 10)


if __name__ == "__main__":
    unittest.main()

