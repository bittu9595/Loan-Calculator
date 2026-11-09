from decimal import Decimal

import pytest

from feecalculator import LoanApplication
from feecalculator.exceptions import InvalidLoanApplicationError


class TestLoanApplication:
    def test_stores_amount_as_decimal(self):
        application = LoanApplication(term=12, amount=Decimal("2500"))
        assert application.amount == Decimal("2500.00")

    def test_accepts_float_amount_and_quantizes_to_pence(self):
        application = LoanApplication(term=12, amount=1234.5)
        assert application.amount == Decimal("1234.50")

    def test_accepts_string_amount(self):
        application = LoanApplication(term=24, amount="2750.00")
        assert application.amount == Decimal("2750.00")

    @pytest.mark.parametrize("amount", [0, -1, -100.5])
    def test_rejects_non_positive_amount(self, amount):
        with pytest.raises(InvalidLoanApplicationError):
            LoanApplication(term=12, amount=amount)

    @pytest.mark.parametrize("term", [0, -12, True])
    def test_rejects_invalid_term(self, term):
        with pytest.raises(InvalidLoanApplicationError):
            LoanApplication(term=term, amount=1000)

    def test_rejects_unparseable_amount(self):
        with pytest.raises(InvalidLoanApplicationError):
            LoanApplication(term=12, amount="not-a-number")

    @pytest.mark.parametrize("amount", ["NaN", "Infinity", "-Infinity", Decimal("NaN")])
    def test_rejects_non_finite_amount(self, amount):
        with pytest.raises(InvalidLoanApplicationError):
            LoanApplication(term=12, amount=amount)

    @pytest.mark.parametrize("amount", ["1234.567", Decimal("1000.001")])
    def test_rejects_sub_pence_amount_instead_of_rounding(self, amount):
        with pytest.raises(InvalidLoanApplicationError):
            LoanApplication(term=12, amount=amount)

    def test_accepts_trailing_zero_precision(self):
        assert LoanApplication(term=12, amount="1000.5000").amount == Decimal("1000.50")
