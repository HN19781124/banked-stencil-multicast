"""Tests for the bounded 18-bank register-exchange reference model."""

from __future__ import annotations

import unittest

from reference.register_exchange import (
    DEFAULT_PHASE_DELTA,
    exchange_cycle,
    phase_sweep,
    report,
    validate_schedule,
)


class RegisterExchangeTests(unittest.TestCase):
    def test_warmup_and_register_forwarding(self) -> None:
        warmup = exchange_cycle(0, DEFAULT_PHASE_DELTA)
        steady = exchange_cycle(1, DEFAULT_PHASE_DELTA)
        self.assertEqual(18, len(warmup.read_samples))
        self.assertEqual((), warmup.retained_samples)
        self.assertEqual(16, len(steady.read_samples))
        self.assertEqual((16, 17), steady.retained_samples)
        self.assertEqual(steady.retained_samples, warmup.read_samples[-2:])

    def test_one_read_and_one_write_port_per_bank(self) -> None:
        plans = validate_schedule(cycles=37, phase_delta=DEFAULT_PHASE_DELTA, y_values=(0, 1, 2, 3))
        for plan in plans:
            self.assertLessEqual(max(plan.read_counts.values()), 1)
            self.assertLessEqual(max(plan.write_counts.values()), 1)
        self.assertTrue(any(plan.overlap for plan in plans if plan.cycle > 0))

    def test_18_bank_report_uses_36_port_slots(self) -> None:
        data = report(cycles=37, phase_delta=DEFAULT_PHASE_DELTA)
        schedule = data["schedule"]
        validation = data["validation"]
        self.assertEqual(36, schedule["physical_port_slots_per_cycle"])
        self.assertEqual(16, schedule["steady_read_samples_per_cycle"])
        self.assertEqual(16, schedule["steady_write_samples_per_cycle"])
        self.assertEqual(32, schedule["steady_total_accesses_per_cycle"])
        self.assertAlmostEqual(32 / 36, schedule["steady_port_utilization"])
        self.assertTrue(validation["port_safe"])
        self.assertFalse(validation["single_port_safe"])

    def test_phase_sweep_finds_two_symmetric_idle_friendly_choices(self) -> None:
        results = phase_sweep(cycles=37, y_values=(0, 1, 2, 3))
        best = max(item["average_idle_banks"] for item in results)
        deltas = {
            item["phase_delta"]
            for item in results
            if item["average_idle_banks"] == best
        }
        self.assertEqual({2, 16}, deltas)
        self.assertAlmostEqual(1.0, best)

    def test_phase_sweep_requires_steady_state(self) -> None:
        with self.assertRaises(ValueError):
            phase_sweep(cycles=1)


if __name__ == "__main__":
    unittest.main()
