"""Orchestrates schedule lookup, interpolation and rounding into a single fee."""

from __future__ import annotations

from decimal import Decimal

from .interpolation import InterpolationStrategy, LinearInterpolationStrategy
from .models import LoanApplication
from .rounding import FeeRoundingStrategy, RoundUpToNearestMultipleStrategy
from .schedule import FeeScheduleRepository


class FeeCalculator:
    """Calculates the fee payable for a given ``LoanApplication``.

    Collaborators are injected so each concern (data source, interpolation
    method, rounding rule) can be swapped independently - e.g. to source the
    fee schedule from a REST API or database, or to change the interpolation
    or rounding behaviour - without modifying this class.
    """

    def __init__(
        self,
        schedule_repository: FeeScheduleRepository,
        interpolation_strategy: InterpolationStrategy | None = None,
        rounding_strategy: FeeRoundingStrategy | None = None,
    ):
        self._schedule_repository = schedule_repository
        self._interpolation_strategy = interpolation_strategy or LinearInterpolationStrategy()
        self._rounding_strategy = rounding_strategy or RoundUpToNearestMultipleStrategy()

    def calculate(self, application: LoanApplication) -> Decimal:
        schedule = self._schedule_repository.get_schedule(application.term)
        lower, upper = schedule.bounding_breakpoints(application.amount)
        raw_fee = self._interpolation_strategy.interpolate(application.amount, lower, upper)
        return self._rounding_strategy.round(raw_fee, application.amount)
