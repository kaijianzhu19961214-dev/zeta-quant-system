import unittest

from fastapi.testclient import TestClient

from quant_data_hub.main import create_app


class HealthRouteTest(unittest.TestCase):
    def test_should_return_ok_when_health_endpoint_is_called(self) -> None:
        client = TestClient(create_app())

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["service"], "quant-data-hub")


if __name__ == "__main__":
    unittest.main()

