"""Tests for the reference-only ASIC dataflow comparison."""

from __future__ import annotations

import unittest

from tools.compare_asic_dataflows import compare_asic_dataflows


class AsicDataflowComparisonTests(unittest.TestCase):
    def test_common_outputs_are_equal(self) -> None:
        data = compare_asic_dataflows(8, 4, seed=0x10203040)
        self.assertTrue(data["correctness"]["outputs_equal"])
        self.assertEqual(32, data["correctness"]["output_samples"])

    def test_activity_counters_keep_path_difference_visible(self) -> None:
        data = compare_asic_dataflows(8, 4)
        line_buffer = data["activity"]["line_buffer"]
        banked = data["activity"]["banked_multicast"]
        self.assertEqual(64, line_buffer["storage_reads"])
        self.assertEqual(144, banked["storage_reads"])
        self.assertAlmostEqual(2.0, line_buffer["storage_reads_per_output"])
        self.assertAlmostEqual(4.5, banked["storage_reads_per_output"])
        self.assertEqual(0, line_buffer["multicast_deliveries"])
        self.assertGreater(banked["multicast_deliveries"], 0)

    def test_power_is_explicitly_uncalibrated(self) -> None:
        data = compare_asic_dataflows(4, 2)
        power = data["power"]
        self.assertEqual("not_calibrated", power["status"])
        self.assertIsNone(power["absolute_power_mw"])
        self.assertFalse(data["comparison_scope"]["physical_signoff"])
        self.assertIn("A/B", data["comparison_scope"]["banked_overlap_and_repeated_pass_storage"])

    def test_invalid_dimensions_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            compare_asic_dataflows(5, 4)
        with self.assertRaises(ValueError):
            compare_asic_dataflows(0, 4)


if __name__ == "__main__":
    unittest.main()
