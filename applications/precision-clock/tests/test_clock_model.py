from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from reference.clock_model import PrecisionClock, TimeMark


class PrecisionClockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = PrecisionClock(
            period_fs=10_000_000,
            propagation_delay_fs=(37, 53, 71, 89),
        )

    def test_broadcast_tick_keeps_common_emission_and_exposes_route_delay(self) -> None:
        marks = self.clock.broadcast_tick(4)

        self.assertEqual([mark.emitted_fs for mark in marks], [40_000_000] * 4)
        self.assertEqual(
            [mark.arrival_fs for mark in marks],
            [40_000_037, 40_000_053, 40_000_071, 40_000_089],
        )

    def test_calibration_reconstructs_common_time_on_a_future_tick(self) -> None:
        calibration_marks = self.clock.broadcast_tick(3)
        calibrated = self.clock.calibrate(
            [mark.arrival_fs for mark in calibration_marks],
            tick_index=3,
        )

        self.assertEqual(
            calibrated.corrected_broadcast_tick(9),
            (90_000_000, 90_000_000, 90_000_000, 90_000_000),
        )

    def test_timer_intervals_and_deadlines_are_integer_exact(self) -> None:
        self.assertEqual(self.clock.interval_fs(2, 7), 50_000_000)
        self.assertEqual(self.clock.deadline_fs(2, 5), 70_000_000)

    def test_uncalibrated_clock_does_not_hide_missing_calibration(self) -> None:
        with self.assertRaises(ValueError):
            self.clock.corrected_time_fs(self.clock.broadcast_tick(0)[0])

    def test_invalid_configuration_and_input_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PrecisionClock(period_fs=0, propagation_delay_fs=(1,))
        with self.assertRaises(ValueError):
            PrecisionClock(period_fs=1, propagation_delay_fs=())
        with self.assertRaises(ValueError):
            self.clock.interval_fs(4, 3)
        with self.assertRaises(TypeError):
            self.clock.emit_time_fs(True)
        with self.assertRaises(TypeError):
            self.clock.calibrate([1, 2, 3, 4.0], tick_index=0)

    def test_mark_type_is_part_of_the_public_contract(self) -> None:
        with self.assertRaises(TypeError):
            self.clock.corrected_time_fs(object())
        self.assertIsInstance(self.clock.broadcast_tick(0)[0], TimeMark)
