from decimal import Decimal

import pytest

from feecalculator import LoanApplication, create_default_calculator
from feecalculator.exceptions import AmountOutOfRangeError, UnsupportedTermError

TERM_12_BREAKPOINTS = {
    1000: 50, 2000: 90, 3000: 90, 4000: 115, 5000: 100,
    6000: 120, 7000: 140, 8000: 160, 9000: 180, 10000: 200,
    11000: 220, 12000: 240, 13000: 260, 14000: 280, 15000: 300,
    16000: 320, 17000: 340, 18000: 360, 19000: 380, 20000: 400,
}

TERM_24_BREAKPOINTS = {
    1000: 70, 2000: 100, 3000: 120, 4000: 160, 5000: 200,
    6000: 240, 7000: 280, 8000: 320, 9000: 360, 10000: 400,
    11000: 440, 12000: 480, 13000: 520, 14000: 560, 15000: 600,
    16000: 640, 17000: 680, 18000: 720, 19000: 760, 20000: 800,
}


@pytest.fixture
def calculator():
    return create_default_calculator()


class TestExactBreakpoints:
    """Every published breakpoint should already yield (fee + loan) as a multiple of 5,
    so the fee charged should match the published value exactly."""

    @pytest.mark.parametrize("amount,expected_fee", list(TERM_12_BREAKPOINTS.items()))
    def test_term_12_breakpoints(self, calculator, amount, expected_fee):
        application = LoanApplication(term=12, amount=Decimal(amount))
        assert calculator.calculate(application) == Decimal(expected_fee)

    @pytest.mark.parametrize("amount,expected_fee", list(TERM_24_BREAKPOINTS.items()))
    def test_term_24_breakpoints(self, calculator, amount, expected_fee):
        application = LoanApplication(term=24, amount=Decimal(amount))
        assert calculator.calculate(application) == Decimal(expected_fee)


class TestInterpolatedAmounts:
    def test_readme_example(self, calculator):
        # The worked example from the spec: term=24, amount=2750 -> fee=115
        application = LoanApplication(term=24, amount=Decimal("2750"))
        assert calculator.calculate(application) == Decimal("115")

    def test_term_12_midpoint_requiring_round_up(self, calculator):
        # Between 1000:50 and 2000:90 -> raw fee 58 at 1200, sum 1258 -> rounds to 1260
        application = LoanApplication(term=12, amount=Decimal("1200"))
        assert calculator.calculate(application) == Decimal("60")

    def test_term_12_decreasing_segment(self, calculator):
        # Between 4000:115 and 5000:100 -> raw fee 107.5 at 4500, sum 4607.5 -> rounds to 4610
        application = LoanApplication(term=12, amount=Decimal("4500"))
        assert calculator.calculate(application) == Decimal("110")

    def test_term_24_midpoint_already_multiple_of_five(self, calculator):
        # Between 1000:70 and 2000:100 -> raw fee 85 at 1500, sum 1585 already a multiple of 5
        application = LoanApplication(term=24, amount=Decimal("1500"))
        assert calculator.calculate(application) == Decimal("85")

    def test_amount_with_pence(self, calculator):
        application = LoanApplication(term=12, amount=Decimal("1234.56"))
        fee = calculator.calculate(application)
        total = application.amount + fee
        assert total % 5 == 0


class TestBoundaryAmounts:
    def test_minimum_loan_amount(self, calculator):
        application = LoanApplication(term=12, amount=Decimal("1000"))
        assert calculator.calculate(application) == Decimal("50")

    def test_maximum_loan_amount(self, calculator):
        application = LoanApplication(term=24, amount=Decimal("20000"))
        assert calculator.calculate(application) == Decimal("800")


class TestErrorHandling:
    def test_unsupported_term_raises(self, calculator):
        application = LoanApplication(term=36, amount=Decimal("5000"))
        with pytest.raises(UnsupportedTermError):
            calculator.calculate(application)

    def test_amount_below_minimum_raises(self, calculator):
        application = LoanApplication(term=12, amount=Decimal("999.99"))
        with pytest.raises(AmountOutOfRangeError):
            calculator.calculate(application)

    def test_amount_above_maximum_raises(self, calculator):
        application = LoanApplication(term=12, amount=Decimal("20000.01"))
        with pytest.raises(AmountOutOfRangeError):
            calculator.calculate(application)


class TestFeePlusLoanIsAlwaysMultipleOfFive:
    """Property-style check across a spread of amounts and both terms."""

    @pytest.mark.parametrize("term", [12, 24])
    @pytest.mark.parametrize(
        "amount",
        [
            "1000", "1000.01", "1500.50", "2750", "3333.33",
            "7777.77", "12345.67", "19999.99", "20000",
        ],
    )
    def test_sum_is_multiple_of_five(self, calculator, term, amount):
        application = LoanApplication(term=term, amount=Decimal(amount))
        fee = calculator.calculate(application)
        total = application.amount + fee
        assert total % 5 == 0

    @pytest.mark.parametrize("term", [12, 24])
    @pytest.mark.parametrize("amount", ["1500.50", "3333.33", "7777.77", "12345.67"])
    def test_fee_is_non_negative(self, calculator, term, amount):
        application = LoanApplication(term=term, amount=Decimal(amount))
        assert calculator.calculate(application) >= 0
