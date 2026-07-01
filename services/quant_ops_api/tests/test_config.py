import unittest

from quant_ops_api.core.config import Settings


class SettingsTest(unittest.TestCase):
    def test_should_treat_blank_artifact_ledger_urls_as_not_configured(self) -> None:
        settings = Settings(
            ARTIFACT_LEDGER_DATABASE_URL="",
            VALIDATION_DATABASE_URL="",
        )

        self.assertIsNone(settings.artifact_ledger_read_database_url())

    def test_should_prefer_artifact_ledger_database_url(self) -> None:
        settings = Settings(
            ARTIFACT_LEDGER_DATABASE_URL=" postgresql+asyncpg://reader@postgres:5432/ledger ",
            VALIDATION_DATABASE_URL="postgresql+asyncpg://writer@postgres:5432/ledger",
        )

        self.assertEqual(
            settings.artifact_ledger_read_database_url(),
            "postgresql+asyncpg://reader@postgres:5432/ledger",
        )

    def test_should_prefer_artifact_ledger_database_schema(self) -> None:
        settings = Settings(
            ARTIFACT_LEDGER_DATABASE_SCHEMA=" zeta_quant_factor_validation ",
            VALIDATION_DATABASE_SCHEMA="validation",
        )

        self.assertEqual(
            settings.artifact_ledger_read_database_schema(),
            "zeta_quant_factor_validation",
        )

    def test_should_fall_back_to_validation_database_url(self) -> None:
        settings = Settings(
            ARTIFACT_LEDGER_DATABASE_URL="",
            VALIDATION_DATABASE_URL="postgresql+asyncpg://reader@postgres:5432/ledger",
        )

        self.assertEqual(
            settings.artifact_ledger_read_database_url(),
            "postgresql+asyncpg://reader@postgres:5432/ledger",
        )

    def test_should_fall_back_to_validation_database_schema(self) -> None:
        settings = Settings(
            ARTIFACT_LEDGER_DATABASE_SCHEMA="",
            VALIDATION_DATABASE_SCHEMA="zeta_quant_factor_validation",
        )

        self.assertEqual(
            settings.artifact_ledger_read_database_schema(),
            "zeta_quant_factor_validation",
        )

    def test_should_prefer_artifact_object_store_config(self) -> None:
        settings = Settings(
            ARTIFACT_OBJECT_STORE_ENDPOINT=" http://ops-minio:9000 ",
            VALIDATION_OBJECT_STORE_ENDPOINT="http://validation-minio:9000",
            ARTIFACT_OBJECT_STORE_ACCESS_KEY=" ops_reader ",
            VALIDATION_OBJECT_STORE_ACCESS_KEY="validation_reader",
            ARTIFACT_OBJECT_STORE_SECRET_KEY=" ops_secret ",
            VALIDATION_OBJECT_STORE_SECRET_KEY="validation_secret",
            ARTIFACT_OBJECT_STORE_SECURE=True,
            VALIDATION_OBJECT_STORE_SECURE=False,
        )

        self.assertEqual(settings.artifact_object_store_read_endpoint(), "http://ops-minio:9000")
        self.assertEqual(settings.artifact_object_store_read_access_key(), "ops_reader")
        self.assertEqual(settings.artifact_object_store_read_secret_key(), "ops_secret")
        self.assertTrue(settings.artifact_object_store_read_secure())

    def test_should_fall_back_to_validation_object_store_config(self) -> None:
        settings = Settings(
            ARTIFACT_OBJECT_STORE_ENDPOINT="",
            VALIDATION_OBJECT_STORE_ENDPOINT="http://validation-minio:9000",
            ARTIFACT_OBJECT_STORE_ACCESS_KEY="",
            VALIDATION_OBJECT_STORE_ACCESS_KEY="validation_reader",
            ARTIFACT_OBJECT_STORE_SECRET_KEY="",
            VALIDATION_OBJECT_STORE_SECRET_KEY="validation_secret",
            VALIDATION_OBJECT_STORE_SECURE=True,
        )

        self.assertEqual(settings.artifact_object_store_read_endpoint(), "http://validation-minio:9000")
        self.assertEqual(settings.artifact_object_store_read_access_key(), "validation_reader")
        self.assertEqual(settings.artifact_object_store_read_secret_key(), "validation_secret")
        self.assertTrue(settings.artifact_object_store_read_secure())


if __name__ == "__main__":
    unittest.main()
