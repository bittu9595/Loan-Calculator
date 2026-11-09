"""Fee schedules: the fixed breakpoints a loan term's fee is interpolated between.

This module deliberately separates *where the data comes from*
(``FeeScheduleRepository`` implementations) from *what the data looks like*
(``FeeSchedule`` / ``FeeBreakpoint``). Swapping the hardcoded JSON file for a
database, a remote REST API or a YAML file only requires a new
``FeeScheduleRepository`` implementation - nothing else in the package needs
to change.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from bisect import bisect_left
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .exceptions import AmountOutOfRangeError, InvalidFeeScheduleError, UnsupportedTermError


@dataclass(frozen=True)
class FeeBreakpoint:
    """A single (loan amount -> fee) anchor point in a fee schedule."""

    amount: Decimal
    fee: Decimal


class FeeSchedule:
    """An ordered, immutable set of breakpoints for a single loan term."""

    def __init__(self, breakpoints: Iterable[FeeBreakpoint]):
        ordered = tuple(sorted(breakpoints, key=lambda bp: bp.amount))
        _validate_breakpoints(ordered)
        self._breakpoints = ordered
        self._amounts = tuple(bp.amount for bp in ordered)

    @property
    def breakpoints(self) -> tuple[FeeBreakpoint, ...]:
        return self._breakpoints

    @property
    def minimum_amount(self) -> Decimal:
        return self._breakpoints[0].amount

    @property
    def maximum_amount(self) -> Decimal:
        return self._breakpoints[-1].amount

    def bounding_breakpoints(self, amount: Decimal) -> tuple[FeeBreakpoint, FeeBreakpoint]:
        """Return the (lower, upper) breakpoints that ``amount`` falls between."""
        if amount < self.minimum_amount or amount > self.maximum_amount:
            raise AmountOutOfRangeError(
                f"Loan amount {amount} is outside the supported range "
                f"[{self.minimum_amount}, {self.maximum_amount}]"
            )

        upper_index = max(bisect_left(self._amounts, amount), 1)
        return self._breakpoints[upper_index - 1], self._breakpoints[upper_index]


def _validate_breakpoints(breakpoints: tuple[FeeBreakpoint, ...]) -> None:
    if len(breakpoints) < 2:
        raise InvalidFeeScheduleError("A fee schedule requires at least two breakpoints")

    for bp in breakpoints:
        if not (bp.amount.is_finite() and bp.fee.is_finite()):
            raise InvalidFeeScheduleError(f"Breakpoint values must be finite numbers: {bp}")
        if bp.amount <= 0:
            raise InvalidFeeScheduleError(f"Breakpoint amount must be positive: {bp}")
        if bp.fee < 0:
            raise InvalidFeeScheduleError(f"Breakpoint fee must not be negative: {bp}")

    for lower, upper in zip(breakpoints, breakpoints[1:]):
        if lower.amount == upper.amount:
            raise InvalidFeeScheduleError(f"Duplicate breakpoint amount: {lower.amount}")


class FeeScheduleRepository(ABC):
    """Abstraction over wherever fee schedules are persisted or sourced from."""

    @abstractmethod
    def get_schedule(self, term: int) -> FeeSchedule:
        """Return the fee schedule for the given loan term (in months)."""
        raise NotImplementedError


class InMemoryFeeScheduleRepository(FeeScheduleRepository):
    """A repository backed by schedules already held in memory (e.g. in tests)."""

    def __init__(self, schedules: Mapping[int, FeeSchedule]):
        self._schedules = dict(schedules)

    def get_schedule(self, term: int) -> FeeSchedule:
        try:
            return self._schedules[term]
        except KeyError as exc:
            raise UnsupportedTermError(f"No fee schedule configured for term {term}") from exc


class JsonFileFeeScheduleRepository(InMemoryFeeScheduleRepository):
    """A repository that loads fee schedules from a JSON file on disk.

    Expected file format::

        {
            "12": {"1000": 50, "2000": 90, ...},
            "24": {"1000": 70, "2000": 100, ...}
        }

    The file is read and validated once, at construction time, so that missing
    or malformed data fails fast at application startup rather than on the
    first customer request.
    """

    def __init__(self, path: Path | str):
        self._path = Path(path)
        super().__init__(self._load())

    def _load(self) -> dict[int, FeeSchedule]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidFeeScheduleError(f"Could not read fee schedule from {self._path}: {exc}") from exc

        if not isinstance(raw, dict) or not raw:
            raise InvalidFeeScheduleError(f"Fee schedule file {self._path} must be a non-empty JSON object")

        try:
            return {
                int(term): FeeSchedule(
                    FeeBreakpoint(Decimal(str(amount)), Decimal(str(fee))) for amount, fee in points.items()
                )
                for term, points in raw.items()
            }
        except (AttributeError, TypeError, ValueError, InvalidOperation) as exc:
            raise InvalidFeeScheduleError(f"Malformed fee schedule in {self._path}: {exc}") from exc
