"""Strategies for computing a fee between two known schedule breakpoints.

Kept separate from ``FeeCalculator`` so the interpolation method (currently
linear) can be swapped - e.g. for a stepped or logarithmic strategy - without
touching the rest of the calculation pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from .schedule import FeeBreakpoint


class InterpolationStrategy(ABC):
    @abstractmethod
    def interpolate(self, amount: Decimal, lower: FeeBreakpoint, upper: FeeBreakpoint) -> Decimal:
        """Return the fee for ``amount`` given its surrounding breakpoints."""
        raise NotImplementedError


class LinearInterpolationStrategy(InterpolationStrategy):
    """Linearly interpolates the fee between the lower and upper breakpoint."""

    def interpolate(self, amount: Decimal, lower: FeeBreakpoint, upper: FeeBreakpoint) -> Decimal:
        if lower.amount == upper.amount:
            return lower.fee

        fraction = (amount - lower.amount) / (upper.amount - lower.amount)
        return lower.fee + fraction * (upper.fee - lower.fee)
