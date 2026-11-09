from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from api.main import app, create_app
from feecalculator import FeeCalculator, LoanApplication

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestCalculateFeeEndpoint:
    def test_returns_expected_fee_for_worked_example(self):
        response = client.post("/api/fee", json={"amount": 2750, "term": 24})
        assert response.status_code == 200
        assert response.json() == {"amount": 2750.0, "term": 24, "fee": 115.0, "total_repayable": 2865.0}

    def test_returns_fee_at_exact_breakpoint(self):
        response = client.post("/api/fee", json={"amount": 1000, "term": 12})
        assert response.status_code == 200
        assert response.json()["fee"] == 50.0

    def test_preserves_pence_precision(self):
        response = client.post("/api/fee", json={"amount": 1234.56, "term": 12})
        assert response.status_code == 200
        body = response.json()
        assert body["amount"] == 1234.56
        assert Decimal(str(body["total_repayable"])) % 5 == 0

    def test_accepts_amount_as_numeric_string(self):
        response = client.post("/api/fee", json={"amount": "2750.00", "term": 24})
        assert response.status_code == 200
        assert response.json()["fee"] == 115.0

    @pytest.mark.parametrize("amount", [999.99, 20000.01])
    def test_rejects_amount_outside_supported_range(self, amount):
        response = client.post("/api/fee", json={"amount": amount, "term": 12})
        assert response.status_code == 400

    def test_rejects_unsupported_term(self):
        response = client.post("/api/fee", json={"amount": 5000, "term": 36})
        assert response.status_code == 400

    def test_rejects_non_positive_amount(self):
        response = client.post("/api/fee", json={"amount": 0, "term": 12})
        assert response.status_code == 422

    def test_rejects_missing_fields(self):
        response = client.post("/api/fee", json={"amount": 5000})
        assert response.status_code == 422

    def test_rejects_sub_pence_amount_rather_than_rounding(self):
        response = client.post("/api/fee", json={"amount": 1234.567, "term": 12})
        assert response.status_code == 422

    @pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
    def test_rejects_non_finite_amount_without_server_error(self, literal):
        response = client.post(
            "/api/fee",
            content=f'{{"amount": {literal}, "term": 12}}',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("term", [True, "12", 12.0, 0, -12])
    def test_rejects_non_integer_term(self, term):
        response = client.post("/api/fee", json={"amount": 5000, "term": term})
        assert response.status_code == 422

    def test_rejects_sub_pence_amount_sent_as_string(self):
        response = client.post("/api/fee", json={"amount": "2750.0000000000001", "term": 24})
        assert response.status_code == 422

    @pytest.mark.parametrize("body", ["{\"amount\": 27", "[1, 2]", "{\"amount\": null, \"term\": 12}"])
    def test_rejects_malformed_bodies(self, body):
        response = client.post("/api/fee", content=body, headers={"Content-Type": "application/json"})
        assert response.status_code == 422

    def test_rejects_unknown_fields(self):
        response = client.post("/api/fee", json={"amount": 5000, "term": 12, "discount": 100})
        assert response.status_code == 422

    def test_validation_errors_do_not_echo_input(self):
        response = client.post("/api/fee", json={"amount": "<script>", "term": 12})
        assert response.status_code == 422
        assert "<script>" not in response.text
        assert all(set(err) == {"loc", "msg", "type"} for err in response.json()["detail"])


class TestServerErrors:
    def test_internal_errors_are_500_and_do_not_leak_details(self):
        class BrokenCalculator(FeeCalculator):
            def __init__(self):
                pass

            def calculate(self, application: LoanApplication) -> Decimal:
                raise ValueError("secret internal detail")

        broken_client = TestClient(create_app(BrokenCalculator()), raise_server_exceptions=False)
        response = broken_client.post("/api/fee", json={"amount": 5000, "term": 12})

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}
