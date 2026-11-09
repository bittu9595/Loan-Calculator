"""Value objects representing a request to the fee calculator."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .exceptions import InvalidLoanApplicationError

_PENCE = Decimal("0.01")


@dataclass(frozen=True)
class LoanApplication:
    """An immutable request to calculate a fee for a loan.

    ``amount`` is coerced to a ``Decimal`` quantized to whole pence so that
    monetary arithmetic downstream never suffers from binary floating point
    rounding errors. Amounts with sub-pence precision are rejected rather than
    silently rounded, so a customer is never quoted for a different amount
    than the one they asked for.
    """

    term: int
    amount: Decimal

    def __post_init__(self) -> None:
        try:
            raw_amount = Decimal(str(self.amount))
        except InvalidOperation as exc:
            raise InvalidLoanApplicationError(f"Invalid loan amount: {self.amount!r}") from exc

        if not raw_amount.is_finite():
            raise InvalidLoanApplicationError(f"Invalid loan amount: {self.amount!r}")

        amount = raw_amount.quantize(_PENCE)
        if amount != raw_amount:
            raise InvalidLoanApplicationError("Loan amount must have at most 2 decimal places")

        if amount <= 0:
            raise InvalidLoanApplicationError("Loan amount must be greater than zero")

        if not isinstance(self.term, int) or isinstance(self.term, bool) or self.term <= 0:
            raise InvalidLoanApplicationError("Loan term must be a positive whole number of months")

        # dataclass is frozen, so fields are set via object.__setattr__
        object.__setattr__(self, "amount", amount)
