"""Request/response models for the fee calculation API."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class FeeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Validated as a Decimal, rejecting NaN/Infinity and anything finer than
    # whole pence. Note FastAPI decodes JSON numbers as floats first; that is
    # exact for every valid amount (<= 7 significant digits), but a literal with
    # more than ~15 significant digits (e.g. 2750.0000000000001) collapses to
    # its nearest float before this check runs. Send the amount as a JSON
    # string if that level of precision must be rejected rather than rounded.
    amount: Decimal = Field(
        ...,
        gt=0,
        max_digits=12,
        decimal_places=2,
        allow_inf_nan=False,
        description="Loan amount in GBP, up to 2 decimal places",
    )
    term: StrictInt = Field(..., gt=0, description="Loan term in months (12 or 24)")


class FeeResponse(BaseModel):
    # Monetary values are serialised as JSON numbers for client convenience;
    # they are always exact to the penny as all calculation happens in Decimal.
    amount: float
    term: int
    fee: float
    total_repayable: float
