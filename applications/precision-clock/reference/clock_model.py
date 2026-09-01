"""Integer timebase model for a broadcast tick and calibrated route delays."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence


def _require_int(value: object, name: str, *, nonnegative: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if nonnegative and value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _require_int_sequence(
    values: Sequence[int], name: str, *, nonnegative: bool = False
) -> tuple[int, ...]:
    result = tuple(values)
    if not result:
        raise ValueError(f"{name} must not be empty")
    return tuple(
        _require_int(value, f"{name}[{index}]", nonnegative=nonnegative)
        for index, value in enumerate(result)
    )


@dataclass(frozen=True)
class TimeMark:
    """One lane's arrival mark for a broadcast tick."""

    lane: int
    tick_index: int
    emitted_fs: int
    arrival_fs: int


@dataclass(frozen=True)
class PrecisionClock:
    """A deterministic, integer-valued broadcast timebase.

    ``period_fs`` and delays use femtoseconds as a simulation unit.  The model
    deliberately separates raw arrival marks from per-lane calibration; it does
    not claim that a physical implementation can resolve one femtosecond.
    """

    period_fs: int
    propagation_delay_fs: tuple[int, ...]
    calibration_delay_fs: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        period = _require_int(self.period_fs, "period_fs", nonnegative=True)
        if period == 0:
            raise ValueError("period_fs must be positive")
        delays = _require_int_sequence(
            self.propagation_delay_fs,
            "propagation_delay_fs",
            nonnegative=True,
        )
        calibration = self.calibration_delay_fs
        if calibration is not None:
            calibration = tuple(calibration)
            if len(calibration) != len(delays):
                raise ValueError("calibration_delay_fs must match lane count")
            calibration = tuple(
                _require_int(value, f"calibration_delay_fs[{index}]")
                for index, value in enumerate(calibration)
            )
        object.__setattr__(self, "period_fs", period)
        object.__setattr__(self, "propagation_delay_fs", delays)
        object.__setattr__(self, "calibration_delay_fs", calibration)

    @property
    def lane_count(self) -> int:
        return len(self.propagation_delay_fs)

    def emit_time_fs(self, tick_index: int) -> int:
        tick = _require_int(tick_index, "tick_index", nonnegative=True)
        return tick * self.period_fs

    def broadcast_tick(self, tick_index: int) -> tuple[TimeMark, ...]:
        """Return the raw arrival marks produced by one common tick."""

        emitted = self.emit_time_fs(tick_index)
        return tuple(
            TimeMark(
                lane=lane,
                tick_index=tick_index,
                emitted_fs=emitted,
                arrival_fs=emitted + delay,
            )
            for lane, delay in enumerate(self.propagation_delay_fs)
        )

    def calibrate(
        self, observed_arrival_fs: Sequence[int], tick_index: int
    ) -> "PrecisionClock":
        """Fit one fixed delay value per lane from a known broadcast tick."""

        observed = tuple(observed_arrival_fs)
        if len(observed) != self.lane_count:
            raise ValueError("observed_arrival_fs must match lane count")
        observed = tuple(
            _require_int(value, f"observed_arrival_fs[{index}]")
            for index, value in enumerate(observed)
        )
        emitted = self.emit_time_fs(tick_index)
        return replace(
            self,
            calibration_delay_fs=tuple(value - emitted for value in observed),
        )

    def corrected_time_fs(self, mark: TimeMark) -> int:
        """Remove the calibrated lane delay from one raw arrival mark."""

        if not isinstance(mark, TimeMark):
            raise TypeError("mark must be a TimeMark")
        if not 0 <= mark.lane < self.lane_count:
            raise ValueError("mark lane is outside this clock")
        if self.calibration_delay_fs is None:
            raise ValueError("clock has not been calibrated")
        return mark.arrival_fs - self.calibration_delay_fs[mark.lane]

    def corrected_broadcast_tick(self, tick_index: int) -> tuple[int, ...]:
        """Return the reconstructed common emission time for every lane."""

        return tuple(
            self.corrected_time_fs(mark) for mark in self.broadcast_tick(tick_index)
        )

    def interval_fs(self, first_tick: int, second_tick: int) -> int:
        """Return the exact elapsed time between two non-decreasing ticks."""

        first = _require_int(first_tick, "first_tick", nonnegative=True)
        second = _require_int(second_tick, "second_tick", nonnegative=True)
        if second < first:
            raise ValueError("second_tick must not precede first_tick")
        return (second - first) * self.period_fs

    def deadline_fs(self, start_tick: int, delay_ticks: int) -> int:
        """Return the absolute deadline after an integer tick delay."""

        start = _require_int(start_tick, "start_tick", nonnegative=True)
        delay = _require_int(delay_ticks, "delay_ticks", nonnegative=True)
        return self.emit_time_fs(start + delay)
