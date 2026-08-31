"""Estimate first-order power scaling for duplicated streaming units.

The model starts from the provisional OpenROAD power estimate recorded in
``physical/evidence/RTL-PERFORMANCE-REPORT.md``.  It is deliberately a
bookkeeping model, not a physical power or thermal sign-off: unit throughput
is assumed to scale ideally, while shared logic, interconnect, bandwidth,
contention, and frequency changes must be supplied or measured separately.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "build" / "power-scaling-estimate.json"

# Provisional OpenROAD anchor: nominal TT, exploratory 4 MHz run.  These are
# intentionally kept as separate terms so a user can expose shared overheads
# or an inter-unit routing allowance instead of silently assuming linearity.
DEFAULT_UNIT_DYNAMIC_MW = 7.938 + 2.644
DEFAULT_UNIT_LEAKAGE_MW = 0.852
DEFAULT_CLOCK_MHZ = 4.0
DEFAULT_VALID_LANE_RESULTS = 51
DEFAULT_NOSTALL_CYCLES = 71
DEFAULT_STRESS_CYCLES = 81
DEFAULT_UNITS = (1, 2)


def _finite_nonnegative(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number")


def _positive_units(units: int) -> None:
    if units < 1:
        raise ValueError("units must be at least one")


@dataclass(frozen=True)
class PowerModel:
    """First-order power terms, all expressed in mW."""

    unit_dynamic_mw: float = DEFAULT_UNIT_DYNAMIC_MW
    unit_leakage_mw: float = DEFAULT_UNIT_LEAKAGE_MW
    shared_static_mw: float = 0.0
    shared_dynamic_mw: float = 0.0
    interconnect_mw_per_extra_unit: float = 0.0

    def __post_init__(self) -> None:
        for name in (
            "unit_dynamic_mw",
            "unit_leakage_mw",
            "shared_static_mw",
            "shared_dynamic_mw",
            "interconnect_mw_per_extra_unit",
        ):
            _finite_nonnegative(name, float(getattr(self, name)))

    @property
    def unit_total_mw(self) -> float:
        return self.unit_dynamic_mw + self.unit_leakage_mw

    def total_power_mw(self, units: int) -> float:
        """Return the estimated total power for ``units`` duplicated units."""

        _positive_units(units)
        return (
            self.shared_static_mw
            + self.shared_dynamic_mw
            + units * self.unit_total_mw
            + (units - 1) * self.interconnect_mw_per_extra_unit
        )


@dataclass(frozen=True)
class TrafficCase:
    """A measured RTL transaction anchor at a fixed clock."""

    name: str
    transaction_cycles: int
    valid_lane_results: int = DEFAULT_VALID_LANE_RESULTS

    def __post_init__(self) -> None:
        if self.transaction_cycles < 1:
            raise ValueError("transaction_cycles must be positive")
        if self.valid_lane_results < 1:
            raise ValueError("valid_lane_results must be positive")

    def throughput_mresults_s(self, clock_mhz: float) -> float:
        _finite_nonnegative("clock_mhz", clock_mhz)
        if clock_mhz <= 0:
            raise ValueError("clock_mhz must be positive")
        return self.valid_lane_results / self.transaction_cycles * clock_mhz


def estimate_units(
    units: int,
    model: PowerModel,
    traffic: TrafficCase,
    clock_mhz: float,
    power_budget_mw: float | None = None,
) -> dict[str, float | int | bool | None]:
    """Estimate power and ideal independent throughput for one traffic case."""

    _positive_units(units)
    if power_budget_mw is not None:
        _finite_nonnegative("power_budget_mw", power_budget_mw)

    one_unit_throughput = traffic.throughput_mresults_s(clock_mhz)
    one_unit_power = model.total_power_mw(1)
    if one_unit_power <= 0:
        raise ValueError("one-unit power must be positive")
    power_mw = model.total_power_mw(units)
    throughput = one_unit_throughput * units
    energy = power_mw / throughput
    performance_per_w = throughput / (power_mw / 1000.0)
    return {
        "units": units,
        "power_mw": power_mw,
        "power_ratio_to_one": power_mw / one_unit_power,
        "ideal_throughput_mresults_s": throughput,
        "throughput_ratio_to_one": float(units),
        "energy_nj_per_result": energy,
        "energy_ratio_to_one": energy / (one_unit_power / one_unit_throughput),
        "performance_mresults_s_per_w": performance_per_w,
        "power_budget_mw": power_budget_mw,
        "budget_headroom_mw": (
            power_budget_mw - power_mw if power_budget_mw is not None else None
        ),
        "fits_budget": (
            power_mw <= power_budget_mw if power_budget_mw is not None else None
        ),
    }


def _normalize_units(units: tuple[int, ...]) -> tuple[int, ...]:
    normalized = tuple(sorted(set(units)))
    if not normalized:
        raise ValueError("units must contain at least one positive integer")
    for unit_count in normalized:
        _positive_units(unit_count)
    return normalized


def report(
    units: tuple[int, ...] = DEFAULT_UNITS,
    clock_mhz: float = DEFAULT_CLOCK_MHZ,
    valid_lane_results: int = DEFAULT_VALID_LANE_RESULTS,
    nostall_cycles: int = DEFAULT_NOSTALL_CYCLES,
    stress_cycles: int = DEFAULT_STRESS_CYCLES,
    power_model: PowerModel | None = None,
    power_budget_mw: float | None = None,
) -> dict[str, object]:
    """Build a machine-readable first-order scaling report."""

    _finite_nonnegative("clock_mhz", clock_mhz)
    if clock_mhz <= 0:
        raise ValueError("clock_mhz must be positive")
    if valid_lane_results < 1:
        raise ValueError("valid_lane_results must be positive")
    model = power_model or PowerModel()
    selected_units = _normalize_units(units)
    cases = (
        TrafficCase("nostall", nostall_cycles, valid_lane_results),
        TrafficCase("stress", stress_cycles, valid_lane_results),
    )
    return {
        "model": "first-order duplicated-unit power scaling; not physical sign-off",
        "source": {
            "power_anchor": "physical/evidence/RTL-PERFORMANCE-REPORT.md",
            "power_anchor_condition": "OpenROAD estimate, nominal TT, exploratory 4 MHz run",
            "power_anchor_components_mw": {
                "internal": 7.938,
                "switching": 2.644,
                "leakage": 0.852,
                "total": 11.434,
            },
        },
        "assumptions": {
            "ideal_independent_unit_throughput_scaling": True,
            "same_clock_mhz": clock_mhz,
            "off_chip_bandwidth_saturation_modeled": False,
            "cross_unit_backpressure_modeled": False,
            "single_port_bank_conflict_recheck": "required for each duplicated unit; not inferred by this power model",
            "physical_power_or_thermal_signoff": False,
        },
        "power_model": {
            **asdict(model),
            "unit_total_mw": model.unit_total_mw,
        },
        "traffic_anchor": {
            "clock_mhz": clock_mhz,
            "valid_lane_results": valid_lane_results,
            "nostall_cycles": nostall_cycles,
            "stress_cycles": stress_cycles,
        },
        "power_budget_mw": power_budget_mw,
        "scenarios": [
            {
                "name": traffic.name,
                "transaction_cycles": traffic.transaction_cycles,
                "baseline_throughput_mresults_s": traffic.throughput_mresults_s(clock_mhz),
                "estimates": [
                    estimate_units(
                        unit_count,
                        model,
                        traffic,
                        clock_mhz,
                        power_budget_mw,
                    )
                    for unit_count in selected_units
                ],
            }
            for traffic in cases
        ],
    }


def _parse_units(value: str) -> tuple[int, ...]:
    try:
        units = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "units must be comma-separated positive integers"
        ) from exc
    try:
        return _normalize_units(units)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return parsed


def _nonnegative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError(
            "must be a finite non-negative number"
        )
    return parsed


def print_table(data: dict[str, object]) -> None:
    print(
        "scenario units power_mW ideal_Mresult/s energy_nJ/result "
        "performance_Mresult/s/W budget"
    )
    for scenario in data["scenarios"]:
        assert isinstance(scenario, dict)
        for estimate in scenario["estimates"]:
            assert isinstance(estimate, dict)
            budget = estimate["fits_budget"]
            budget_label = "n/a" if budget is None else ("yes" if budget else "no")
            print(
                f"{scenario['name']:7s} {estimate['units']:5d} "
                f"{estimate['power_mw']:8.3f} "
                f"{estimate['ideal_throughput_mresults_s']:16.6f} "
                f"{estimate['energy_nj_per_result']:16.6f} "
                f"{estimate['performance_mresults_s_per_w']:22.3f} "
                f"{budget_label}"
            )
    print("note: ideal scaling only; shared bandwidth, contention, routing, and thermal effects are not modeled")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--units", type=_parse_units, default=DEFAULT_UNITS)
    parser.add_argument("--clock-mhz", type=_positive_float, default=DEFAULT_CLOCK_MHZ)
    parser.add_argument(
        "--valid-lane-results", type=_positive_int, default=DEFAULT_VALID_LANE_RESULTS
    )
    parser.add_argument("--nostall-cycles", type=_positive_int, default=DEFAULT_NOSTALL_CYCLES)
    parser.add_argument("--stress-cycles", type=_positive_int, default=DEFAULT_STRESS_CYCLES)
    parser.add_argument(
        "--unit-dynamic-mw", type=_nonnegative_float, default=DEFAULT_UNIT_DYNAMIC_MW
    )
    parser.add_argument(
        "--unit-leakage-mw", type=_nonnegative_float, default=DEFAULT_UNIT_LEAKAGE_MW
    )
    parser.add_argument("--shared-static-mw", type=_nonnegative_float, default=0.0)
    parser.add_argument("--shared-dynamic-mw", type=_nonnegative_float, default=0.0)
    parser.add_argument(
        "--interconnect-mw-per-extra-unit",
        type=_nonnegative_float,
        default=0.0,
    )
    parser.add_argument("--power-budget-mw", type=_nonnegative_float)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    model = PowerModel(
        unit_dynamic_mw=args.unit_dynamic_mw,
        unit_leakage_mw=args.unit_leakage_mw,
        shared_static_mw=args.shared_static_mw,
        shared_dynamic_mw=args.shared_dynamic_mw,
        interconnect_mw_per_extra_unit=args.interconnect_mw_per_extra_unit,
    )
    data = report(
        units=args.units,
        clock_mhz=args.clock_mhz,
        valid_lane_results=args.valid_lane_results,
        nostall_cycles=args.nostall_cycles,
        stress_cycles=args.stress_cycles,
        power_model=model,
        power_budget_mw=args.power_budget_mw,
    )
    data["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    print_table(data)
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
