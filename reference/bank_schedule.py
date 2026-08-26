"""Reference model for the 12-bank steady-state access schedule.

The model proves only the explicitly defined steady-state case: four adjacent
three-tap lanes read six samples from one logical buffer while DMA writes four
samples to the other buffer at the same local y coordinate.
"""

from __future__ import annotations

from dataclasses import dataclass


BANK_COUNT = 12
LANE_COUNT = 4
TAP_COUNT = 3
READ_COUNT = LANE_COUNT + TAP_COUNT - 1
WRITE_COUNT = LANE_COUNT
PHASE_A = 0
PHASE_B = 6


def bank_index(x: int, y: int = 0, phase: int = 0) -> int:
    """Return the physical bank for one logical sample."""

    return (x + 2 * y + phase) % BANK_COUNT


def bank_address(
    x: int,
    y: int,
    padded_width: int,
    buffer_base: int = 0,
) -> int:
    """Return the in-bank address for a padded row-major tile."""

    if x < 0 or y < 0:
        raise ValueError("x and y must use non-negative, halo-adjusted coordinates")
    if padded_width <= 0 or padded_width % BANK_COUNT:
        raise ValueError("padded_width must be a positive multiple of 12")
    if x >= padded_width:
        raise ValueError("x must be inside padded_width")
    return buffer_base + y * (padded_width // BANK_COUNT) + x // BANK_COUNT


def lane_windows(first_sample_x: int) -> tuple[tuple[int, ...], ...]:
    """Return the three input coordinates routed to each output lane."""

    samples = tuple(first_sample_x + offset for offset in range(READ_COUNT))
    return tuple(
        samples[lane : lane + TAP_COUNT]
        for lane in range(LANE_COUNT)
    )


@dataclass(frozen=True)
class CyclePlan:
    cycle: int
    read_banks: tuple[int, ...]
    write_banks: tuple[int, ...]
    bank_count: int = BANK_COUNT
    expected_reads: int = READ_COUNT
    expected_writes: int = WRITE_COUNT

    @property
    def overlap(self) -> frozenset[int]:
        return frozenset(self.read_banks) & frozenset(self.write_banks)

    @property
    def idle_banks(self) -> tuple[int, ...]:
        used = frozenset(self.read_banks) | frozenset(self.write_banks)
        return tuple(bank for bank in range(self.bank_count) if bank not in used)

    def validate(self) -> None:
        if len(self.read_banks) != self.expected_reads:
            raise AssertionError(f"wrong read count in cycle {self.cycle}")
        if len(self.write_banks) != self.expected_writes:
            raise AssertionError(f"wrong write count in cycle {self.cycle}")
        if len(set(self.read_banks)) != self.expected_reads:
            raise AssertionError(f"read conflict in cycle {self.cycle}")
        if len(set(self.write_banks)) != self.expected_writes:
            raise AssertionError(f"write conflict in cycle {self.cycle}")
        if self.overlap:
            raise AssertionError(
                f"read/write conflict in cycle {self.cycle}: {sorted(self.overlap)}"
            )


def cycle_plan(
    cycle: int,
    read_phase: int,
    write_phase: int,
    y: int = 0,
) -> CyclePlan:
    """Build one steady-state plan for corresponding rows of two buffers."""

    if cycle < 0:
        raise ValueError("cycle must be non-negative")
    first_x = LANE_COUNT * cycle
    read_banks = tuple(
        bank_index(first_x + offset, y, read_phase)
        for offset in range(READ_COUNT)
    )
    write_banks = tuple(
        bank_index(first_x + offset, y, write_phase)
        for offset in range(WRITE_COUNT)
    )
    return CyclePlan(cycle, read_banks, write_banks)


def validate_steady_state(cycles: int = 256, rows: int = 8) -> None:
    """Validate both ping-pong directions over representative cycles and rows."""

    if cycles <= 0 or rows <= 0:
        raise ValueError("cycles and rows must be positive")
    for y in range(rows):
        for read_phase, write_phase in (
            (PHASE_A, PHASE_B),
            (PHASE_B, PHASE_A),
        ):
            for cycle in range(cycles):
                cycle_plan(cycle, read_phase, write_phase, y).validate()


def scalable_bank_count(lane_count: int, tap_count: int = TAP_COUNT) -> int:
    """Return the symmetric ping-pong bank count for an N-lane stencil."""

    if lane_count < 1:
        raise ValueError("lane_count must be at least one")
    if tap_count < 1:
        raise ValueError("tap_count must be at least one")
    unique_reads = lane_count + tap_count - 1
    return 2 * unique_reads


def scalable_cycle_plan(
    cycle: int,
    lane_count: int,
    tap_count: int = TAP_COUNT,
    read_second_buffer: bool = False,
    y: int = 0,
    row_skew: int = 2,
) -> CyclePlan:
    """Build one plan for the general N-lane, T-tap construction."""

    if cycle < 0 or y < 0:
        raise ValueError("cycle and y must be non-negative")
    bank_count = scalable_bank_count(lane_count, tap_count)
    unique_reads = lane_count + tap_count - 1
    phase_a = 0
    phase_b = unique_reads
    read_phase = phase_b if read_second_buffer else phase_a
    write_phase = phase_a if read_second_buffer else phase_b
    first_x = lane_count * cycle
    read_banks = tuple(
        (first_x + offset + row_skew * y + read_phase) % bank_count
        for offset in range(unique_reads)
    )
    write_banks = tuple(
        (first_x + offset + row_skew * y + write_phase) % bank_count
        for offset in range(lane_count)
    )
    return CyclePlan(
        cycle,
        read_banks,
        write_banks,
        bank_count,
        unique_reads,
        lane_count,
    )


def validate_scalable_family(
    lane_counts: tuple[int, ...] = (1, 2, 4, 8, 16, 32),
    tap_count: int = TAP_COUNT,
    cycles: int = 128,
    rows: int = 8,
) -> None:
    """Validate representative members of the general scalable family."""

    for lane_count in lane_counts:
        for y in range(rows):
            for read_second_buffer in (False, True):
                for cycle in range(cycles):
                    scalable_cycle_plan(
                        cycle,
                        lane_count,
                        tap_count,
                        read_second_buffer,
                        y,
                    ).validate()


def main() -> None:
    validate_steady_state()
    validate_scalable_family()
    print("steady-state schedule: PASS")
    print("scalable family: PASS (N=1,2,4,8,16,32)")
    print("t mod 3 | reads             | writes       | idle")
    for cycle in range(3):
        plan = cycle_plan(cycle, PHASE_A, PHASE_B)
        print(
            f"{cycle:7d} | {str(plan.read_banks):17s} "
            f"| {str(plan.write_banks):12s} | {plan.idle_banks}"
        )


if __name__ == "__main__":
    main()
