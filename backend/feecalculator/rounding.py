"""Strategies for rounding a raw, interpolated fee to a payable amount."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import ROUND_CEILING, Decimal


class FeeRoundingStrategy(ABC):
    @abstractmethod
    def round(self, fee: Decimal, loan_amount: Decimal) -> Decimal:
        """Return the adjusted fee to charge for ``loan_amount``."""
        raise NotImplementedError


class RoundUpToNearestMultipleStrategy(FeeRoundingStrategy):
    """Rounds the fee up so that ``fee + loan_amount`` is an exact multiple of ``multiple``.

    This matches the required behaviour: "the fee should be rounded up such
    that (fee + loan amount) is an exact multiple of 5".
    """

    def __init__(self, multiple: Decimal = Decimal("5")):
        if multiple <= 0:
            raise ValueError("multiple must be a positive value")
        self._multiple = multiple

    def round(self, fee: Decimal, loan_amount: Decimal) -> Decimal:
        total = fee + loan_amount
        rounded_total = (total / self._multiple).to_integral_value(rounding=ROUND_CEILING) * self._multiple
        return rounded_total - loan_amount
