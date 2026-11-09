"""Domain-specific exceptions for the fee calculator package."""


class FeeCalculatorError(Exception):
    """Base class for all fee calculator errors."""


class InvalidLoanApplicationError(FeeCalculatorError):
    """Raised when a loan application fails basic validation."""


class UnsupportedTermError(FeeCalculatorError):
    """Raised when no fee schedule exists for the requested loan term."""


class AmountOutOfRangeError(FeeCalculatorError):
    """Raised when a loan amount falls outside the supported schedule range."""


class InvalidFeeScheduleError(FeeCalculatorError):
    """Raised when fee schedule data is missing, malformed or inconsistent.

    This signals a configuration problem on our side, not a bad client request.
    """
