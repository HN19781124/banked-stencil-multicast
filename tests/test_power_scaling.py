"""Tests for the first-order duplicated-unit power model."""

from __future__ import annotations

import unittest

from tools.estimate_power_scaling import (
    PowerModel,
    TrafficCase,
    estimate_units,
    report,
)


class PowerScalingTests(unittest.TestCase):
    def test_default_two_unit_anchor_and_ideal_throughput(self) -> None:
        model = PowerModel()
        traffic = TrafficCase("nostall", 71)
        one = estimate_units(1, model, traffic, 4.0)
        two = estimate_units(2, model, traffic, 4.0)
        self.assertAlmostEqual(11.434, one["power_mw"], places=3)
        self.assertAlmostEqual(22.868, two["power_mw"], places=3)
        self.assertAlmostEqual(2.8732394366, one["ideal_throughput_mresults_s"])
        self.assertAlmostEqual(5.7464788732, two["ideal_throughput_mresults_s"])
        self.assertAlmostEqual(2.0, two["power_ratio_to_one"])

    def test_report_contains_both_measured_traffic_anchors(self) -> None:
        data = report()
        self.assertEqual(["nostall", "stress"], [item["name"] for item in data["scenarios"]])
        nostall = data["scenarios"][0]
        stress = data["scenarios"][1]
        self.assertAlmostEqual(3.98, nostall["estimates"][0]["energy_nj_per_result"], places=2)
        self.assertAlmostEqual(4.54, stress["estimates"][0]["energy_nj_per_result"], places=2)
        self.assertFalse(data["assumptions"]["physical_power_or_thermal_signoff"])

    def test_budget_and_interconnect_sensitivity_are_explicit(self) -> None:
        model = PowerModel(interconnect_mw_per_extra_unit=1.0)
        estimate = estimate_units(
            2,
            model,
            TrafficCase("nostall", 71),
            4.0,
            power_budget_mw=25.0,
        )
        self.assertAlmostEqual(23.868, estimate["power_mw"], places=3)
        self.assertTrue(estimate["fits_budget"])
        self.assertAlmostEqual(1.132, estimate["budget_headroom_mw"], places=3)
        self.assertLess(estimate["performance_mresults_s_per_w"], 251.3)

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PowerModel(unit_dynamic_mw=-1.0)
        with self.assertRaises(ValueError):
            estimate_units(0, PowerModel(), TrafficCase("nostall", 71), 4.0)
        with self.assertRaises(ValueError):
            estimate_units(
                1,
                PowerModel(unit_dynamic_mw=0.0, unit_leakage_mw=0.0),
                TrafficCase("nostall", 71),
                4.0,
            )
        with self.assertRaises(ValueError):
            report(units=())


if __name__ == "__main__":
    unittest.main()
