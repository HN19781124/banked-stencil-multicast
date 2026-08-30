"""First-order model for the 18-bank, 1R1W register-exchange candidate.

This model is intentionally narrower than ``bank_schedule.py``.  It checks the
candidate discussed in Appendix C.1:

* ``N=16`` adjacent lanes and ``T=3`` taps;
* two samples retained between issues by register exchange;
* 18 physical banks, each with one read and one write port;
* 16 fresh reads and 16 prefetch writes in the steady state.

The result is a port-activity and schedule check, not a power, thermal,
timing, SRAM-macro, or physical sign-off model.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path


LANE_COUNT = 16
TAP_COUNT = 3
PHYSICAL_BANKS = 18
PORTS_PER_BANK = 2  # one read port plus one write port (1R1W)
ROW_SKEW = 2
DEFAULT_PHASE_DELTA = 2


def bank_index(sample_x: int, y: int = 0, phase: int = 0) -> int:
    """Map a logical sample to one of the 18 physical banks."""

    if sample_x < 0 or y < 0:
        raise ValueError("sample_x and y must be non-negative")
    return (sample_x + ROW_SKEW * y + phase) % PHYSICAL_BANKS


def buffer_phase(buffer: int, phase_delta: int) -> int:
    """Return the fixed bank phase for ping-pong buffer A (0) or B (1)."""

    if buffer not in (0, 1):
        raise ValueError("buffer must be 0 or 1")
    return 0 if buffer == 0 else phase_delta % PHYSICAL_BANKS


@dataclass(frozen=True)
class ExchangeCycle:
    """One cycle of the 18-bank register-exchange schedule."""

    cycle: int
    read_buffer: int
    write_buffer: int
    read_samples: tuple[int, ...]
    write_samples: tuple[int, ...]
    retained_samples: tuple[int, ...]
    read_banks: tuple[int, ...]
    write_banks: tuple[int, ...]
    bank_count: int = PHYSICAL_BANKS
    read_ports: int = 1
    write_ports: int = 1

    @property
    def overlap(self) -> frozenset[int]:
        """Banks used by both ports; legal for a true 1R1W macro."""

        return frozenset(self.read_banks) & frozenset(self.write_banks)

    @property
    def idle_banks(self) -> tuple[int, ...]:
        """Banks with neither a read nor a write in this cycle."""

        used = frozenset(self.read_banks) | frozenset(self.write_banks)
        return tuple(bank for bank in range(self.bank_count) if bank not in used)

    @property
    def read_counts(self) -> Counter[int]:
        return Counter(self.read_banks)

    @property
    def write_counts(self) -> Counter[int]:
        return Counter(self.write_banks)

    def validate(self) -> None:
        expected_read_count = LANE_COUNT if self.cycle else LANE_COUNT + TAP_COUNT - 1
        if len(self.read_samples) != expected_read_count:
            raise AssertionError(f"wrong read sample count in cycle {self.cycle}")
        if len(self.write_samples) != LANE_COUNT:
            raise AssertionError(f"wrong write sample count in cycle {self.cycle}")
        if len(self.read_banks) != len(self.read_samples):
            raise AssertionError(f"read bank/sample mismatch in cycle {self.cycle}")
        if len(self.write_banks) != len(self.write_samples):
            raise AssertionError(f"write bank/sample mismatch in cycle {self.cycle}")
        if len(set(self.read_banks)) != len(self.read_banks):
            raise AssertionError(f"read-port conflict in cycle {self.cycle}")
        if len(set(self.write_banks)) != len(self.write_banks):
            raise AssertionError(f"write-port conflict in cycle {self.cycle}")
        if self.read_buffer == self.write_buffer:
            raise AssertionError("read and write buffers must be different")
        if len(self.retained_samples) != (0 if self.cycle == 0 else TAP_COUNT - 1):
            raise AssertionError(f"wrong register-retain count in cycle {self.cycle}")
        if any(count > self.read_ports for count in self.read_counts.values()):
            raise AssertionError(f"read-port overuse in cycle {self.cycle}")
        if any(count > self.write_ports for count in self.write_counts.values()):
            raise AssertionError(f"write-port overuse in cycle {self.cycle}")


def exchange_cycle(
    cycle: int,
    phase_delta: int = DEFAULT_PHASE_DELTA,
    y: int = 0,
) -> ExchangeCycle:
    """Build and validate one warm-up or steady-state cycle.

    The output block at issue ``cycle`` covers ``N`` adjacent positions.  Its
    union is ``N+T-1`` samples.  After warm-up, the final ``T-1`` samples from
    the previous union are forwarded by registers, so only the next ``N``
    samples are read from SRAM.  The write span is a separate contiguous
    ``N``-sample prefetch span; data availability and operator semantics are
    outside this first-order port model.
    """

    if cycle < 0:
        raise ValueError("cycle must be non-negative")
    if y < 0:
        raise ValueError("y must be non-negative")
    phase_delta %= PHYSICAL_BANKS
    first_sample = LANE_COUNT * cycle
    window = tuple(first_sample + offset for offset in range(LANE_COUNT + TAP_COUNT - 1))
    retained = tuple() if cycle == 0 else window[: TAP_COUNT - 1]
    read_samples = window if cycle == 0 else window[TAP_COUNT - 1 :]
    write_samples = tuple(first_sample + offset for offset in range(LANE_COUNT))
    read_buffer = cycle % 2
    write_buffer = 1 - read_buffer
    read_phase = buffer_phase(read_buffer, phase_delta)
    write_phase = buffer_phase(write_buffer, phase_delta)
    result = ExchangeCycle(
        cycle=cycle,
        read_buffer=read_buffer,
        write_buffer=write_buffer,
        read_samples=read_samples,
        write_samples=write_samples,
        retained_samples=retained,
        read_banks=tuple(bank_index(sample, y, read_phase) for sample in read_samples),
        write_banks=tuple(bank_index(sample, y, write_phase) for sample in write_samples),
    )
    result.validate()
    return result


def validate_schedule(
    cycles: int = 37,
    phase_delta: int = DEFAULT_PHASE_DELTA,
    y_values: tuple[int, ...] = (0,),
) -> tuple[ExchangeCycle, ...]:
    """Validate both ping-pong directions over representative rows."""

    if cycles < 1:
        raise ValueError("cycles must be positive")
    if not y_values or any(y < 0 for y in y_values):
        raise ValueError("y_values must contain non-negative rows")
    plans: list[ExchangeCycle] = []
    for y in y_values:
        previous: ExchangeCycle | None = None
        for cycle in range(cycles):
            plan = exchange_cycle(cycle, phase_delta, y)
            plan.validate()
            if previous is not None:
                if plan.retained_samples != previous.read_samples[-(TAP_COUNT - 1) :]:
                    raise AssertionError(
                        f"register exchange lost overlap at cycle {cycle}"
                    )
            plans.append(plan)
            previous = plan
    return tuple(plans)


def phase_sweep(
    cycles: int = 37,
    y_values: tuple[int, ...] = (0,),
) -> tuple[dict[str, float | int], ...]:
    """Return port-safe phase choices and their idle-bank activity proxy."""

    if cycles < 2:
        raise ValueError("cycles must include warm-up and steady state")
    results: list[dict[str, float | int]] = []
    for phase_delta in range(PHYSICAL_BANKS):
        plans = tuple(
            plan
            for plan in validate_schedule(cycles, phase_delta, y_values)
            if plan.cycle > 0
        )
        idle_counts = [len(plan.idle_banks) for plan in plans]
        active_bank_counts = [PHYSICAL_BANKS - idle for idle in idle_counts]
        results.append(
            {
                "phase_delta": phase_delta,
                "average_idle_banks": sum(idle_counts) / len(idle_counts),
                "minimum_idle_banks": min(idle_counts),
                "maximum_idle_banks": max(idle_counts),
                "average_active_banks": sum(active_bank_counts) / len(active_bank_counts),
            }
        )
    return tuple(results)


def report(
    cycles: int = 37,
    phase_delta: int = DEFAULT_PHASE_DELTA,
    y_values: tuple[int, ...] = (0,),
) -> dict[str, object]:
    """Summarize the candidate without presenting a thermal claim."""

    plans = validate_schedule(cycles, phase_delta, y_values)
    steady = tuple(plan for plan in plans if plan.cycle > 0)
    if not steady:
        raise ValueError("cycles must include at least one steady-state cycle")
    all_read = sum(len(plan.read_banks) for plan in plans)
    all_write = sum(len(plan.write_banks) for plan in plans)
    steady_read = sum(len(plan.read_banks) for plan in steady) / len(steady)
    steady_write = sum(len(plan.write_banks) for plan in steady) / len(steady)
    idle_counts = [len(plan.idle_banks) for plan in steady]
    overlap_counts = [len(plan.overlap) for plan in steady]
    phase_results = phase_sweep(cycles, y_values)
    best_average_idle = max(item["average_idle_banks"] for item in phase_results)
    best_phases = tuple(
        int(item["phase_delta"])
        for item in phase_results
        if item["average_idle_banks"] == best_average_idle
    )
    return {
        "assumptions": {
            "lanes": LANE_COUNT,
            "taps": TAP_COUNT,
            "physical_banks": PHYSICAL_BANKS,
            "ports": "1R1W true dual-port per bank",
            "register_exchange": f"retain {TAP_COUNT - 1} overlap samples after warm-up",
            "thermal_model": "none; port-activity and idle-bank proxy only",
        },
        "schedule": {
            "cycles": cycles,
            "rows": list(y_values),
            "phase_delta": phase_delta % PHYSICAL_BANKS,
            "warmup_read_samples": LANE_COUNT + TAP_COUNT - 1,
            "steady_read_samples_per_cycle": LANE_COUNT,
            "steady_write_samples_per_cycle": LANE_COUNT,
            "steady_total_accesses_per_cycle": 2 * LANE_COUNT,
            "physical_port_slots_per_cycle": PHYSICAL_BANKS * PORTS_PER_BANK,
            "steady_port_utilization": (2 * LANE_COUNT) / (PHYSICAL_BANKS * PORTS_PER_BANK),
            "register_forwarded_samples_per_cycle": TAP_COUNT - 1,
        },
        "validation": {
            "port_safe": True,
            "single_port_safe": all(not plan.overlap for plan in steady),
            "all_cycles_read_samples": all_read,
            "all_cycles_write_samples": all_write,
            "steady_average_read_samples": steady_read,
            "steady_average_write_samples": steady_write,
            "steady_min_idle_banks": min(idle_counts),
            "steady_max_idle_banks": max(idle_counts),
            "steady_average_idle_banks": sum(idle_counts) / len(idle_counts),
            "steady_min_read_write_overlap": min(overlap_counts),
            "steady_max_read_write_overlap": max(overlap_counts),
        },
        "phase_sweep": {
            "max_average_idle_banks": best_average_idle,
            "best_phase_deltas": list(best_phases),
        },
    }


def print_report(data: dict[str, object]) -> None:
    assumptions = data["assumptions"]
    schedule = data["schedule"]
    validation = data["validation"]
    phase = data["phase_sweep"]
    print(
        f"N={assumptions['lanes']} T={assumptions['taps']} "
        f"M={assumptions['physical_banks']} {assumptions['ports']}"
    )
    print(
        "steady: read={steady_read_samples_per_cycle} "
        "write={steady_write_samples_per_cycle} "
        "total={steady_total_accesses_per_cycle} "
        "slots={physical_port_slots_per_cycle} "
        "utilization={steady_port_utilization:.3f}".format(**schedule)
    )
    print(
        "ports: 1R1W={port_safe} single-port={single_port_safe} "
        "overlap={steady_min_read_write_overlap}..{steady_max_read_write_overlap}".format(
            **validation
        )
    )
    print(
        "idle banks (steady): {steady_min_idle_banks}..{steady_max_idle_banks}, "
        "average={steady_average_idle_banks:.3f}".format(**validation)
    )
    print(
        "register exchange: forwarded={register_forwarded_samples_per_cycle} "
        "samples/cycle".format(**schedule)
    )
    print(
        "phase sweep: max average idle={max_average_idle_banks:.3f}, "
        "best delta={best_phase_deltas}".format(**phase)
    )
    print("thermal result: not modeled")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=37)
    parser.add_argument("--phase-delta", type=int, default=DEFAULT_PHASE_DELTA)
    parser.add_argument("--rows", type=int, default=1)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("--rows must be positive")
    data = report(
        cycles=args.cycles,
        phase_delta=args.phase_delta,
        y_values=tuple(range(args.rows)),
    )
    print_report(data)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
