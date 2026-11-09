"""Fee calculation domain package.

Public API:
    LoanApplication    - value object describing a loan request
    FeeCalculator      - orchestrates schedule lookup, interpolation and rounding
    create_default_calculator - convenience factory wired to the bundled fee data
"""

from .calculator import FeeCalculator
from .exceptions import (
    AmountOutOfRangeError,
    FeeCalculatorError,
    InvalidFeeScheduleError,
    InvalidLoanApplicationError,
    UnsupportedTermError,
)
from .factory import create_default_calculator
from .interpolation import InterpolationStrategy, LinearInterpolationStrategy
from .models import LoanApplication
from .rounding import FeeRoundingStrategy, RoundUpToNearestMultipleStrategy
from .schedule import (
    FeeBreakpoint,
    FeeSchedule,
    FeeScheduleRepository,
    InMemoryFeeScheduleRepository,
    JsonFileFeeScheduleRepository,
)

__all__ = [
    "LoanApplication",
    "FeeCalculator",
    "create_default_calculator",
    "FeeCalculatorError",
    "InvalidLoanApplicationError",
    "UnsupportedTermError",
    "AmountOutOfRangeError",
    "InvalidFeeScheduleError",
    "InterpolationStrategy",
    "LinearInterpolationStrategy",
    "FeeRoundingStrategy",
    "RoundUpToNearestMultipleStrategy",
    "FeeBreakpoint",
    "FeeSchedule",
    "FeeScheduleRepository",
    "InMemoryFeeScheduleRepository",
    "JsonFileFeeScheduleRepository",
]
