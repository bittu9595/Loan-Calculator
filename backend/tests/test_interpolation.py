from decimal import Decimal

from feecalculator.interpolation import LinearInterpolationStrategy
from feecalculator.schedule import FeeBreakpoint


class TestLinearInterpolationStrategy:
    def setup_method(self):
        self.strategy = LinearInterpolationStrategy()

    def test_returns_lower_fee_at_lower_bound(self):
        lower = FeeBreakpoint(Decimal("1000"), Decimal("50"))
        upper = FeeBreakpoint(Decimal("2000"), Decimal("90"))
        assert self.strategy.interpolate(Decimal("1000"), lower, upper) == Decimal("50")

    def test_returns_upper_fee_at_upper_bound(self):
        lower = FeeBreakpoint(Decimal("1000"), Decimal("50"))
        upper = FeeBreakpoint(Decimal("2000"), Decimal("90"))
        assert self.strategy.interpolate(Decimal("2000"), lower, upper) == Decimal("90")

    def test_interpolates_midpoint(self):
        lower = FeeBreakpoint(Decimal("1000"), Decimal("50"))
        upper = FeeBreakpoint(Decimal("2000"), Decimal("90"))
        assert self.strategy.interpolate(Decimal("1500"), lower, upper) == Decimal("70")

    def test_interpolates_quarter_point(self):
        lower = FeeBreakpoint(Decimal("2000"), Decimal("100"))
        upper = FeeBreakpoint(Decimal("3000"), Decimal("120"))
        assert self.strategy.interpolate(Decimal("2750"), lower, upper) == Decimal("115")

    def test_handles_decreasing_fee_between_breakpoints(self):
        lower = FeeBreakpoint(Decimal("4000"), Decimal("115"))
        upper = FeeBreakpoint(Decimal("5000"), Decimal("100"))
        assert self.strategy.interpolate(Decimal("4500"), lower, upper) == Decimal("107.5")

    def test_returns_fee_when_lower_equals_upper(self):
        point = FeeBreakpoint(Decimal("20000"), Decimal("400"))
        assert self.strategy.interpolate(Decimal("20000"), point, point) == Decimal("400")
