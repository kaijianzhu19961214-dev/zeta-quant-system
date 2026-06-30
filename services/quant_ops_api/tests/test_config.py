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


if __name__ == "__main__":
    unittest.main()
