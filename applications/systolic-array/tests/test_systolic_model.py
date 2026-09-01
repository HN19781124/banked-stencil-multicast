from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = APP_ROOT / "reference"
for path in (APP_ROOT, REFERENCE_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from reference.systolic_model import evaluate, run_case


class SystolicModelTests(unittest.TestCase):
    def test_reference_case_matches_broadcast_traffic_contract(self) -> None:
        result = run_case()

        self.assertEqual(result.lane_count, 4)
        self.assertEqual(result.step_count, 16)
        self.assertEqual(result.mac_operations, 64)
        self.assertEqual(result.unique_input_reads, 16)
        self.assertEqual(result.replicated_input_reads, 64)
        self.assertEqual(result.storage_reads_saved, 48)
        self.assertEqual(result.input_read_reduction_factor, 4.0)
        self.assertEqual(result.multicast_deliveries, 64)
        self.assertEqual(result.issue_cycles, 16)
        self.assertEqual(len(result.outputs), 4)

    def test_shape_and_type_contracts_are_enforced(self) -> None:
        with self.assertRaises(ValueError):
            evaluate((), ((1,),))
        with self.assertRaises(ValueError):
            evaluate((1, 2), ((1,),))
        with self.assertRaises(TypeError):
            evaluate((1, True), ((1, 1),))
