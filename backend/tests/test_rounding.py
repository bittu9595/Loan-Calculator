from decimal import Decimal

import pytest

from feecalculator.rounding import RoundUpToNearestMultipleStrategy


class TestRoundUpToNearestMultipleStrategy:
    def setup_method(self):
        self.strategy = RoundUpToNearestMultipleStrategy()

    def test_no_adjustment_needed_when_already_a_multiple(self):
        # fee + loan = 115 + 2750 = 2865, already a multiple of 5
        fee = self.strategy.round(Decimal("115"), Decimal("2750"))
        assert fee == Decimal("115")

    def test_rounds_up_to_next_multiple(self):
        # fee + loan = 58 + 1200 = 1258 -> rounds up to 1260 -> fee becomes 60
        fee = self.strategy.round(Decimal("58"), Decimal("1200"))
        assert fee == Decimal("60")

    def test_rounds_up_with_half_pence_fee(self):
        # fee + loan = 107.5 + 4500 = 4607.5 -> rounds up to 4610 -> fee becomes 110
        fee = self.strategy.round(Decimal("107.5"), Decimal("4500"))
        assert fee == Decimal("110")

    def test_handles_pence_in_loan_amount(self):
        # fee + loan = 60 + 1234.56 = 1294.56 -> rounds up to 1295 -> fee becomes 60.44
        fee = self.strategy.round(Decimal("60"), Decimal("1234.56"))
        assert fee == Decimal("60.44")

    def test_custom_multiple(self):
        strategy = RoundUpToNearestMultipleStrategy(multiple=Decimal("10"))
        # fee + loan = 52 + 1000 = 1052 -> rounds up to 1060 -> fee becomes 60
        fee = strategy.round(Decimal("52"), Decimal("1000"))
        assert fee == Decimal("60")

    def test_rejects_non_positive_multiple(self):
        with pytest.raises(ValueError):
            RoundUpToNearestMultipleStrategy(multiple=Decimal("0"))
