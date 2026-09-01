from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from reference.clock_benchmark import run_case


class ClockBenchmarkTests(unittest.TestCase):
    def test_fixed_route_case_is_deterministic(self) -> None:
        result = run_case(tick_count=16)

        self.assertEqual(result.broadcast_count, 16)
        self.assertEqual(result.timestamp_count, 64)
        self.assertEqual(result.raw_route_skew_fs, 52)
        self.assertEqual(result.corrected_skew_fs, 0)
        self.assertEqual(result.calibration_error_fs, 0)
        self.assertEqual(result.common_tick_interval_fs, 10_000_000)

    def test_invalid_tick_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            run_case(tick_count=0)
