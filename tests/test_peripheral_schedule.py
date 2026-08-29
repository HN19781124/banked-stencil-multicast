"""Tests for validation kept outside the completed core scheduler."""

from __future__ import annotations

import unittest

from reference.bank_schedule import PHASE_A, PHASE_B
from reference.peripheral_schedule import (
    boundary_issue,
    compensated_write_phase,
    cross_row_cycle_plan,
    padded_row,
    validate_cross_row_access,
    validate_row_edges,
)


class PeripheralScheduleTests(unittest.TestCase):
    def test_minimum_width_uses_both_halos(self) -> None:
        plan = boundary_issue(logical_width=1, issue=0)
        self.assertEqual((-1, 0, 1, 2, 3, 4), plan.logical_samples)
        self.assertEqual((0, 1, 2, 3, 4, 5), plan.physical_samples)
        self.assertEqual((True, False, False, False), plan.active_lanes)
        self.assertEqual((-1, 0, 1), plan.lane_windows[0])

    def test_partial_final_issue_masks_inactive_lanes(self) -> None:
        plan = boundary_issue(logical_width=6, issue=1)
        self.assertEqual((True, True, False, False), plan.active_lanes)
        self.assertEqual((3, 4, 5, 6, 7, 8), plan.logical_samples)
        self.assertEqual((3, 4, 5), plan.lane_windows[0])
        self.assertEqual((4, 5, 6), plan.lane_windows[1])

    def test_padding_satisfies_lane_and_bank_alignment(self) -> None:
        for width in range(1, 129):
            layout = padded_row(width)
            self.assertEqual(0, layout.padded_width % 4)
            self.assertEqual(0, layout.padded_width % 12)
            last = boundary_issue(width, layout.issue_count - 1)
            self.assertLess(last.physical_samples[-1], layout.padded_width)

    def test_row_edge_family(self) -> None:
        validate_row_edges(max_width=257, rows=12)

    def test_same_row_compensation_preserves_buffer_phases(self) -> None:
        self.assertEqual(PHASE_B, compensated_write_phase(PHASE_A, 4, 4))
        self.assertEqual(PHASE_A, compensated_write_phase(PHASE_B, 4, 4))

    def test_cross_row_phase_changes_with_row_delta(self) -> None:
        self.assertEqual(4, compensated_write_phase(PHASE_A, 3, 4))
        self.assertEqual(8, compensated_write_phase(PHASE_A, 4, 3))

    def test_cross_row_plan_places_writes_opposite_reads(self) -> None:
        for read_y, write_y in ((0, 1), (1, 0), (2, 9), (15, 3)):
            plan = cross_row_cycle_plan(7, read_y, write_y)
            self.assertEqual(
                tuple((plan.read_banks[0] + offset) % 12 for offset in range(6)),
                plan.read_banks,
            )
            self.assertEqual(
                tuple((plan.read_banks[0] + 6 + offset) % 12 for offset in range(4)),
                plan.write_banks,
            )

    def test_cross_row_family(self) -> None:
        validate_cross_row_access(cycles=256, rows=16)

    def test_invalid_boundary_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            padded_row(0)
        with self.assertRaises(ValueError):
            boundary_issue(8, -1)
        with self.assertRaises(ValueError):
            boundary_issue(8, 2)
        with self.assertRaises(ValueError):
            compensated_write_phase(PHASE_A, -1, 0)


if __name__ == "__main__":
    unittest.main()
