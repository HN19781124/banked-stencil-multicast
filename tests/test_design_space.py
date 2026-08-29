"""Tests for the first-order design-space sweep."""

from __future__ import annotations

import unittest

from tools.explore_design_space import (
    make_candidate,
    report,
    select_feasible,
    select_peak,
)


class DesignSpaceTests(unittest.TestCase):
    def test_baseline_matches_specification(self) -> None:
        candidate = make_candidate(4)
        self.assertEqual(6, candidate.unique_reads)
        self.assertEqual(12, candidate.banks)
        self.assertEqual(10, candidate.total_accesses)
        self.assertAlmostEqual(0.5, candidate.duplicate_reduction)
        self.assertAlmostEqual(2.4, candidate.read_gbps)
        self.assertAlmostEqual(4.0, candidate.total_gbps)
        self.assertAlmostEqual(3.2, candidate.serialized_gflops)
        self.assertAlmostEqual(9.6, candidate.unrolled_gflops)

    def test_n16_is_selected_by_default_envelope(self) -> None:
        data = report()
        self.assertEqual(16, data["selected_lane_count"])
        self.assertEqual(list(range(10, 17)), data["feasible_lane_counts"])
        candidate = next(item for item in data["candidates"] if item["lanes"] == 16)
        self.assertEqual(36, candidate["banks"])
        self.assertEqual(48, candidate["multicast_endpoints"])
        self.assertAlmostEqual(0.625, candidate["duplicate_reduction"])
        self.assertAlmostEqual(144.0, candidate["capacity_kib"])

    def test_reduction_increases_with_lane_count(self) -> None:
        small = make_candidate(4)
        large = make_candidate(16)
        self.assertLess(small.duplicate_reduction, large.duplicate_reduction)
        self.assertLess(small.average_fanout, large.average_fanout)

    def test_constraints_are_explicit(self) -> None:
        candidates = tuple(make_candidate(lanes) for lanes in (4, 8, 16, 32))
        feasible = select_feasible(candidates, 160.0, 64, 0.60)
        self.assertEqual((16,), tuple(candidate.lanes for candidate in feasible))
        self.assertEqual(16, select_peak(feasible).lanes)

    def test_invalid_candidate_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            make_candidate(0)
        with self.assertRaises(ValueError):
            make_candidate(4, taps=0)


if __name__ == "__main__":
    unittest.main()
