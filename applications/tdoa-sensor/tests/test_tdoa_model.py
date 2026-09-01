from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
for path in (APP_ROOT, APP_ROOT / "reference"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from reference.tdoa_model import SensorArray, run_case


class TDOAModelTests(unittest.TestCase):
    def test_route_calibration_preserves_physical_pair_differences(self) -> None:
        result = run_case(event_count=8)

        self.assertEqual(result.sensor_count, 4)
        self.assertEqual(result.pair_count, 6)
        self.assertEqual(result.raw_route_skew_fs, 52)
        self.assertEqual(result.residual_route_error_fs, 0)
        self.assertEqual(result.physical_tdoa_span_fs, 112)
        self.assertEqual(result.pairwise_measurements, 48)

    def test_mismatched_sensor_shapes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            SensorArray((1, 2), (3,))
        with self.assertRaises(ValueError):
            SensorArray((1,), (2,)).pairwise_tdoa((1, 2))
