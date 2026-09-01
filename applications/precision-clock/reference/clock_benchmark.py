"""Deterministic reference metrics for the precision-clock application."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from .clock_model import PrecisionClock
except ImportError:  # pragma: no cover - supports direct script loading
    from clock_model import PrecisionClock


DEFAULT_PERIOD_FS = 10_000_000
DEFAULT_ROUTE_DELAYS_FS = (37, 53, 71, 89)


@dataclass(frozen=True)
class ClockPerformance:
    """Reference-only metrics; no physical timing guarantee is implied."""

    tick_count: int
    lane_count: int
    period_fs: int
    broadcast_count: int
    timestamp_count: int
    raw_route_skew_fs: int
    corrected_skew_fs: int
    calibration_error_fs: int
    common_tick_interval_fs: int

    def to_dict(self) -> dict[str, object]:
        return {
            "application": "precision-clock",
            "scope": "reference-only",
            "tick_count": self.tick_count,
            "lane_count": self.lane_count,
            "period_fs": self.period_fs,
            "broadcast_count": self.broadcast_count,
            "timestamp_count": self.timestamp_count,
            "raw_route_skew_fs": self.raw_route_skew_fs,
            "corrected_skew_fs": self.corrected_skew_fs,
            "calibration_error_fs": self.calibration_error_fs,
            "common_tick_interval_fs": self.common_tick_interval_fs,
        }


def run_case(
    tick_count: int = 1024,
    period_fs: int = DEFAULT_PERIOD_FS,
    route_delays_fs: tuple[int, ...] = DEFAULT_ROUTE_DELAYS_FS,
) -> ClockPerformance:
    """Measure a fixed route-delay case over a deterministic tick stream."""

    if tick_count <= 0:
        raise ValueError("tick_count must be positive")
    clock = PrecisionClock(period_fs, route_delays_fs)
    calibration_marks = clock.broadcast_tick(0)
    calibrated = clock.calibrate(
        [mark.arrival_fs for mark in calibration_marks],
        tick_index=0,
    )

    raw_skews: list[int] = []
    corrected_skews: list[int] = []
    calibration_errors: list[int] = []
    for tick_index in range(tick_count):
        marks = clock.broadcast_tick(tick_index)
        raw_arrivals = [mark.arrival_fs for mark in marks]
        corrected_arrivals = calibrated.corrected_broadcast_tick(tick_index)
        raw_skews.append(max(raw_arrivals) - min(raw_arrivals))
        corrected_skews.append(max(corrected_arrivals) - min(corrected_arrivals))
        expected = clock.emit_time_fs(tick_index)
        calibration_errors.extend(abs(value - expected) for value in corrected_arrivals)

    return ClockPerformance(
        tick_count=tick_count,
        lane_count=clock.lane_count,
        period_fs=clock.period_fs,
        broadcast_count=tick_count,
        timestamp_count=tick_count * clock.lane_count,
        raw_route_skew_fs=max(raw_skews),
        corrected_skew_fs=max(corrected_skews),
        calibration_error_fs=max(calibration_errors),
        common_tick_interval_fs=clock.interval_fs(0, 1),
    )
