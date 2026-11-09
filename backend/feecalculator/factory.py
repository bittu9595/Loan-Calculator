"""Convenience factory wiring the calculator to the bundled fee schedule data."""

from __future__ import annotations

from pathlib import Path

from .calculator import FeeCalculator
from .schedule import JsonFileFeeScheduleRepository

_DEFAULT_SCHEDULE_PATH = Path(__file__).parent / "data" / "fee_schedule.json"


def create_default_calculator() -> FeeCalculator:
    """Build a ``FeeCalculator`` backed by the fee schedule shipped with this package."""
    repository = JsonFileFeeScheduleRepository(_DEFAULT_SCHEDULE_PATH)
    return FeeCalculator(repository)
