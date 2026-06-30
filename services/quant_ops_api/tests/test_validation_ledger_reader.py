import unittest

from quant_ops_api.repositories import normalize_database_schema_name


class ValidationLedgerReaderTest(unittest.TestCase):
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
