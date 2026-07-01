import unittest

from quant_ops_api.repositories import normalize_async_postgres_database_url, normalize_database_schema_name


class ValidationLedgerReaderTest(unittest.TestCase):
    def test_should_normalize_sync_postgres_url_to_asyncpg_url(self) -> None:
        self.assertEqual(
            normalize_async_postgres_database_url(database_url=" postgresql://reader:secret@postgres:5432/ledger "),
            "postgresql+asyncpg://reader:secret@postgres:5432/ledger",
        )
        self.assertEqual(
            normalize_async_postgres_database_url(database_url="postgres://reader:secret@postgres:5432/ledger"),
            "postgresql+asyncpg://reader:secret@postgres:5432/ledger",
        )
        self.assertEqual(
            normalize_async_postgres_database_url(database_url="postgresql+asyncpg://reader@postgres:5432/ledger"),
            "postgresql+asyncpg://reader@postgres:5432/ledger",
        )
        self.assertIsNone(normalize_async_postgres_database_url(database_url=""))

    def test_should_normalize_database_schema_name(self) -> None:
        self.assertEqual(
            normalize_database_schema_name(schema_name=" zeta_quant_factor_validation "),
            "zeta_quant_factor_validation",
        )
        self.assertIsNone(normalize_database_schema_name(schema_name=""))

        with self.assertRaisesRegex(ValueError, "schema"):
            normalize_database_schema_name(schema_name="public;drop table task_runs")


if __name__ == "__main__":
    unittest.main()
