"""Tests for the executable 12-bank schedule specification."""

from __future__ import annotations

import unittest

from reference.bank_schedule import (
    PHASE_A,
    PHASE_B,
    bank_address,
    bank_index,
    cycle_plan,
    lane_windows,
    scalable_bank_count,
    scalable_cycle_plan,
    validate_scalable_family,
    validate_steady_state,
)


class BankScheduleTests(unittest.TestCase):
    def test_expected_three_cycle_pattern(self) -> None:
        expected = (
            ((0, 1, 2, 3, 4, 5), (6, 7, 8, 9), (10, 11)),
            ((4, 5, 6, 7, 8, 9), (10, 11, 0, 1), (2, 3)),
            ((8, 9, 10, 11, 0, 1), (2, 3, 4, 5), (6, 7)),
        )
        for cycle, (reads, writes, idle) in enumerate(expected):
            plan = cycle_plan(cycle, PHASE_A, PHASE_B)
            self.assertEqual(reads, plan.read_banks)
            self.assertEqual(writes, plan.write_banks)
            self.assertEqual(idle, plan.idle_banks)

    def test_both_ping_pong_directions_are_conflict_free(self) -> None:
        validate_steady_state(cycles=1_024, rows=32)

    def test_lane_windows_share_six_unique_samples(self) -> None:
        windows = lane_windows(20)
        self.assertEqual(
            ((20, 21, 22), (21, 22, 23), (22, 23, 24), (23, 24, 25)),
            windows,
        )
        self.assertEqual(6, len({sample for window in windows for sample in window}))

    def test_bank_and_address_pair_is_unique(self) -> None:
        width = 48
        height = 16
        locations = {
            (bank_index(x, y, PHASE_A), bank_address(x, y, width))
            for y in range(height)
            for x in range(width)
        }
        self.assertEqual(width * height, len(locations))

    def test_invalid_width_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            bank_address(0, 0, 50)

    def test_scalable_family_resource_formula(self) -> None:
        expected = {
            1: (6, 3, 1, 2),
            2: (8, 4, 2, 2),
            4: (12, 6, 4, 2),
            8: (20, 10, 8, 2),
        }
        for lanes, (banks, reads, writes, idle) in expected.items():
            plan = scalable_cycle_plan(0, lanes)
            plan.validate()
            self.assertEqual(banks, scalable_bank_count(lanes))
            self.assertEqual(reads, len(plan.read_banks))
            self.assertEqual(writes, len(plan.write_banks))
            self.assertEqual(idle, len(plan.idle_banks))

    def test_scalable_family_both_directions(self) -> None:
        validate_scalable_family(cycles=256, rows=16)

    def test_zero_lanes_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            scalable_bank_count(0)


if __name__ == "__main__":
    unittest.main()
