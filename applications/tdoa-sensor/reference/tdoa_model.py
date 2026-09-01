"""Reference model for calibrated multi-sensor arrival-time differences."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Sequence


def _validate_delays(values: Sequence[int], name: str) -> tuple[int, ...]:
    delays = tuple(values)
    if not delays:
        raise ValueError(f"{name} must not be empty")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in delays):
        raise TypeError(f"{name} must contain integers")
    if any(value < 0 for value in delays):
        raise ValueError(f"{name} must be non-negative")
    return delays


@dataclass(frozen=True)
class SensorArray:
    route_delay_fs: tuple[int, ...]
    physical_delay_fs: tuple[int, ...]

    def __post_init__(self) -> None:
        route = _validate_delays(self.route_delay_fs, "route_delay_fs")
        physical = _validate_delays(self.physical_delay_fs, "physical_delay_fs")
        if len(route) != len(physical):
            raise ValueError("route and physical delay counts must match")
        object.__setattr__(self, "route_delay_fs", route)
        object.__setattr__(self, "physical_delay_fs", physical)

    @property
    def sensor_count(self) -> int:
        return len(self.route_delay_fs)

    @property
    def pair_count(self) -> int:
        return self.sensor_count * (self.sensor_count - 1) // 2

    def observe_common_pulse(self, event_time_fs: int) -> tuple[int, ...]:
        """Observe a simultaneous calibration pulse through route delays only."""

        if isinstance(event_time_fs, bool) or not isinstance(event_time_fs, int):
            raise TypeError("event_time_fs must be an integer")
        return tuple(event_time_fs + delay for delay in self.route_delay_fs)

    def observe_event(self, event_time_fs: int) -> tuple[int, ...]:
        """Observe a physical event through route and sensor delays."""

        if isinstance(event_time_fs, bool) or not isinstance(event_time_fs, int):
            raise TypeError("event_time_fs must be an integer")
        return tuple(
            event_time_fs + route + physical
            for route, physical in zip(
                self.route_delay_fs,
                self.physical_delay_fs,
                strict=True,
            )
        )

    def calibrate_route(
        self, event_time_fs: int, observed_arrivals_fs: Sequence[int]
    ) -> tuple[int, ...]:
        """Estimate one fixed route delay per sensor from a common pulse."""

        observed = tuple(observed_arrivals_fs)
        if len(observed) != self.sensor_count:
            raise ValueError("observed_arrivals_fs must match sensor count")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in observed):
            raise TypeError("observed_arrivals_fs must contain integers")
        if isinstance(event_time_fs, bool) or not isinstance(event_time_fs, int):
            raise TypeError("event_time_fs must be an integer")
        return tuple(value - event_time_fs for value in observed)

    def correct_routes(
        self,
        observed_arrivals_fs: Sequence[int],
        calibration_delay_fs: Sequence[int],
    ) -> tuple[int, ...]:
        observed = tuple(observed_arrivals_fs)
        calibration = tuple(calibration_delay_fs)
        if len(observed) != self.sensor_count or len(calibration) != self.sensor_count:
            raise ValueError("arrival and calibration counts must match sensor count")
        return tuple(
            arrival - delay
            for arrival, delay in zip(observed, calibration, strict=True)
        )

    def pairwise_tdoa(self, corrected_arrivals_fs: Sequence[int]) -> tuple[tuple[int, int, int], ...]:
        corrected = tuple(corrected_arrivals_fs)
        if len(corrected) != self.sensor_count:
            raise ValueError("corrected_arrivals_fs must match sensor count")
        return tuple(
            (first, second, corrected[second] - corrected[first])
            for first in range(self.sensor_count)
            for second in range(first + 1, self.sensor_count)
        )


@dataclass(frozen=True)
class TDOAPerformance:
    sensor_count: int
    event_count: int
    pair_count: int
    raw_route_skew_fs: int
    residual_route_error_fs: int
    physical_tdoa_span_fs: int
    pairwise_measurements: int
    corrected_tdoa_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "application": "tdoa-sensor",
            "scope": "reference-only",
            "sensor_count": self.sensor_count,
            "event_count": self.event_count,
            "pair_count": self.pair_count,
            "raw_route_skew_fs": self.raw_route_skew_fs,
            "residual_route_error_fs": self.residual_route_error_fs,
            "physical_tdoa_span_fs": self.physical_tdoa_span_fs,
            "pairwise_measurements": self.pairwise_measurements,
            "corrected_tdoa_digest": self.corrected_tdoa_digest,
        }


def run_case(event_count: int = 256) -> TDOAPerformance:
    """Run a deterministic four-sensor event stream with route calibration."""

    if event_count <= 0:
        raise ValueError("event_count must be positive")
    array = SensorArray(
        route_delay_fs=(37, 53, 71, 89),
        physical_delay_fs=(0, 23, 61, 112),
    )
    calibration_time_fs = 1_000_000
    calibration = array.calibrate_route(
        calibration_time_fs,
        array.observe_common_pulse(calibration_time_fs),
    )

    corrected_pairs: list[tuple[int, int, int]] = []
    residual_errors: list[int] = []
    for event_index in range(event_count):
        event_time_fs = 2_000_000 + event_index * 10_000
        observed = array.observe_event(event_time_fs)
        corrected = array.correct_routes(observed, calibration)
        residual_errors.extend(
            abs(value - (event_time_fs + physical))
            for value, physical in zip(corrected, array.physical_delay_fs, strict=True)
        )
        corrected_pairs.extend(array.pairwise_tdoa(corrected))

    digest = hashlib.sha256()
    for first, second, difference in corrected_pairs:
        digest.update(struct.pack(">iiq", first, second, difference))
    return TDOAPerformance(
        sensor_count=array.sensor_count,
        event_count=event_count,
        pair_count=array.pair_count,
        raw_route_skew_fs=max(array.route_delay_fs) - min(array.route_delay_fs),
        residual_route_error_fs=max(residual_errors),
        physical_tdoa_span_fs=max(array.physical_delay_fs) - min(array.physical_delay_fs),
        pairwise_measurements=len(corrected_pairs),
        corrected_tdoa_digest=digest.hexdigest(),
    )
