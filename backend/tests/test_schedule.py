import json
from decimal import Decimal
from pathlib import Path

import pytest

from feecalculator.exceptions import AmountOutOfRangeError, InvalidFeeScheduleError, UnsupportedTermError
from feecalculator.schedule import (
    FeeBreakpoint,
    FeeSchedule,
    InMemoryFeeScheduleRepository,
    JsonFileFeeScheduleRepository,
)


def make_schedule():
    return FeeSchedule(
        [
            FeeBreakpoint(Decimal("1000"), Decimal("50")),
            FeeBreakpoint(Decimal("2000"), Decimal("90")),
            FeeBreakpoint(Decimal("3000"), Decimal("90")),
        ]
    )


class TestFeeSchedule:
    def test_requires_at_least_two_breakpoints(self):
        breakpoints = [FeeBreakpoint(Decimal("1000"), Decimal("50"))]
        with pytest.raises(InvalidFeeScheduleError):
            FeeSchedule(breakpoints)

    def test_sorts_breakpoints_by_amount_regardless_of_input_order(self):
        schedule = FeeSchedule(
            [
                FeeBreakpoint(Decimal("2000"), Decimal("90")),
                FeeBreakpoint(Decimal("1000"), Decimal("50")),
            ]
        )
        assert [bp.amount for bp in schedule.breakpoints] == [Decimal("1000"), Decimal("2000")]

    def test_min_and_max_amount(self):
        schedule = make_schedule()
        assert schedule.minimum_amount == Decimal("1000")
        assert schedule.maximum_amount == Decimal("3000")

    def test_bounding_breakpoints_exact_lower_breakpoint(self):
        schedule = make_schedule()
        lower, upper = schedule.bounding_breakpoints(Decimal("1000"))
        assert lower.amount == Decimal("1000")
        assert upper.amount == Decimal("2000")

    def test_bounding_breakpoints_exact_upper_boundary(self):
        schedule = make_schedule()
        lower, upper = schedule.bounding_breakpoints(Decimal("3000"))
        assert lower.fee == upper.fee == Decimal("90")

    def test_bounding_breakpoints_between_points(self):
        schedule = make_schedule()
        lower, upper = schedule.bounding_breakpoints(Decimal("1500"))
        assert (lower.amount, upper.amount) == (Decimal("1000"), Decimal("2000"))

    def test_bounding_breakpoints_exact_interior_breakpoint(self):
        schedule = make_schedule()
        lower, upper = schedule.bounding_breakpoints(Decimal("2000"))
        assert (lower.amount, upper.amount) == (Decimal("1000"), Decimal("2000"))

    def test_rejects_duplicate_breakpoint_amounts(self):
        breakpoints = [
            FeeBreakpoint(Decimal("1000"), Decimal("50")),
            FeeBreakpoint(Decimal("1000.00"), Decimal("60")),
        ]
        with pytest.raises(InvalidFeeScheduleError):
            FeeSchedule(breakpoints)

    def test_rejects_negative_fee(self):
        breakpoints = [
            FeeBreakpoint(Decimal("1000"), Decimal("-1")),
            FeeBreakpoint(Decimal("2000"), Decimal("90")),
        ]
        with pytest.raises(InvalidFeeScheduleError):
            FeeSchedule(breakpoints)

    def test_bounding_breakpoints_below_minimum_raises(self):
        schedule = make_schedule()
        with pytest.raises(AmountOutOfRangeError):
            schedule.bounding_breakpoints(Decimal("999"))

    def test_bounding_breakpoints_above_maximum_raises(self):
        schedule = make_schedule()
        with pytest.raises(AmountOutOfRangeError):
            schedule.bounding_breakpoints(Decimal("3001"))


class TestInMemoryFeeScheduleRepository:
    def test_returns_schedule_for_known_term(self):
        schedule = make_schedule()
        repository = InMemoryFeeScheduleRepository({12: schedule})
        assert repository.get_schedule(12) is schedule

    def test_raises_for_unknown_term(self):
        repository = InMemoryFeeScheduleRepository({12: make_schedule()})
        with pytest.raises(UnsupportedTermError):
            repository.get_schedule(36)


class TestJsonFileFeeScheduleRepository:
    def test_loads_schedule_from_file(self, tmp_path: Path):
        data = {"12": {"1000": 50, "2000": 90}, "24": {"1000": 70, "2000": 100}}
        path = tmp_path / "fee_schedule.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        repository = JsonFileFeeScheduleRepository(path)

        schedule_12 = repository.get_schedule(12)
        assert schedule_12.minimum_amount == Decimal("1000")
        assert schedule_12.maximum_amount == Decimal("2000")

        schedule_24 = repository.get_schedule(24)
        assert schedule_24.maximum_amount == Decimal("2000")
        lower, upper = schedule_24.bounding_breakpoints(Decimal("1000"))
        assert lower.fee == Decimal("70")

    def test_raises_for_unknown_term(self, tmp_path: Path):
        path = tmp_path / "fee_schedule.json"
        path.write_text(json.dumps({"12": {"1000": 50, "2000": 90}}), encoding="utf-8")

        repository = JsonFileFeeScheduleRepository(path)
        with pytest.raises(UnsupportedTermError):
            repository.get_schedule(24)

    def test_reads_file_once_at_construction(self, tmp_path: Path):
        path = tmp_path / "fee_schedule.json"
        path.write_text(json.dumps({"12": {"1000": 50, "2000": 90}}), encoding="utf-8")
        repository = JsonFileFeeScheduleRepository(path)

        path.write_text(json.dumps({"12": {"1000": 999, "2000": 999}}), encoding="utf-8")

        lower, _ = repository.get_schedule(12).bounding_breakpoints(Decimal("1000"))
        assert lower.fee == Decimal("50")

    def test_missing_file_fails_fast(self, tmp_path: Path):
        with pytest.raises(InvalidFeeScheduleError):
            JsonFileFeeScheduleRepository(tmp_path / "does-not-exist.json")

    @pytest.mark.parametrize(
        "content",
        [
            "not json",
            "[]",
            "{}",
            json.dumps({"twelve": {"1000": 50, "2000": 90}}),
            json.dumps({"12": [50, 90]}),
            json.dumps({"12": {"1000": "abc", "2000": 90}}),
            json.dumps({"12": {"1000": 50}}),
            json.dumps({"12": {"1000": -5, "2000": 90}}),
            json.dumps({"12": {"1000": 50, "1000.00": 60, "2000": 90}}),
        ],
    )
    def test_malformed_file_fails_fast(self, tmp_path: Path, content: str):
        path = tmp_path / "fee_schedule.json"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(InvalidFeeScheduleError):
            JsonFileFeeScheduleRepository(path)
