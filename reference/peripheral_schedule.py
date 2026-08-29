"""Reference checks for boundaries around the completed steady-state scheduler.

This module intentionally leaves ``bank_schedule.py`` unchanged.  It models
row-edge/Halo issue groups and the phase compensation needed when reads and
writes address different rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import lcm

from reference.bank_schedule import (
    BANK_COUNT,
    LANE_COUNT,
    PHASE_A,
    PHASE_B,
    READ_COUNT,
    TAP_COUNT,
    WRITE_COUNT,
    CyclePlan,
    bank_address,
    bank_index,
)


ROW_SKEW = 2


def _round_up(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


@dataclass(frozen=True)
class PaddedRow:
    """Physical row layout including Halo and inactive-lane padding."""

    logical_width: int
    padded_width: int
    issue_count: int
    left_halo: int
    right_halo: int


def padded_row(logical_width: int) -> PaddedRow:
    """Return the baseline 4-lane/3-tap/12-bank padded row layout."""

    if logical_width < 1:
        raise ValueError("logical_width must be at least one")
    left_halo = TAP_COUNT // 2
    right_halo = TAP_COUNT - left_halo - 1
    issue_count = (logical_width + LANE_COUNT - 1) // LANE_COUNT
    issued_output_width = issue_count * LANE_COUNT
    required_width = left_halo + issued_output_width + right_halo
    alignment = lcm(LANE_COUNT, BANK_COUNT)
    return PaddedRow(
        logical_width=logical_width,
        padded_width=_round_up(required_width, alignment),
        issue_count=issue_count,
        left_halo=left_halo,
        right_halo=right_halo,
    )


@dataclass(frozen=True)
class BoundaryIssue:
    """One issue group at a row boundary or in the steady-state interior."""

    row: PaddedRow
    y: int
    issue: int
    phase: int
    active_lanes: tuple[bool, ...]
    logical_samples: tuple[int, ...]
    physical_samples: tuple[int, ...]
    read_banks: tuple[int, ...]
    read_addresses: tuple[int, ...]
    lane_windows: tuple[tuple[int, ...], ...]

    def validate(self) -> None:
        if len(self.logical_samples) != READ_COUNT:
            raise AssertionError("wrong boundary read count")
        if len(set(self.read_banks)) != READ_COUNT:
            raise AssertionError("boundary read-bank conflict")
        if not all(0 <= x < self.row.padded_width for x in self.physical_samples):
            raise AssertionError("boundary read escaped the padded row")
        locations = set(zip(self.read_banks, self.read_addresses, strict=True))
        if len(locations) != READ_COUNT:
            raise AssertionError("boundary read locations are not unique")
        available = set(self.logical_samples)
        for lane, active in enumerate(self.active_lanes):
            if active and not set(self.lane_windows[lane]).issubset(available):
                raise AssertionError("active lane window is not fully loaded")


def boundary_issue(
    logical_width: int,
    issue: int,
    y: int = 0,
    phase: int = PHASE_A,
) -> BoundaryIssue:
    """Build an issue group after translating logical Halo coordinates."""

    if y < 0:
        raise ValueError("y must be non-negative")
    row = padded_row(logical_width)
    if not 0 <= issue < row.issue_count:
        raise ValueError("issue is outside the row")

    output_start = issue * LANE_COUNT
    first_logical_sample = output_start - row.left_halo
    logical_samples = tuple(
        first_logical_sample + offset for offset in range(READ_COUNT)
    )
    physical_samples = tuple(x + row.left_halo for x in logical_samples)
    active_lanes = tuple(
        output_start + lane < logical_width for lane in range(LANE_COUNT)
    )
    lane_windows = tuple(
        tuple(first_logical_sample + lane + tap for tap in range(TAP_COUNT))
        for lane in range(LANE_COUNT)
    )
    read_banks = tuple(bank_index(x, y, phase) for x in physical_samples)
    read_addresses = tuple(
        bank_address(x, y, row.padded_width) for x in physical_samples
    )
    result = BoundaryIssue(
        row=row,
        y=y,
        issue=issue,
        phase=phase,
        active_lanes=active_lanes,
        logical_samples=logical_samples,
        physical_samples=physical_samples,
        read_banks=read_banks,
        read_addresses=read_addresses,
        lane_windows=lane_windows,
    )
    result.validate()
    return result


def compensated_write_phase(
    read_phase: int,
    read_y: int,
    write_y: int,
    row_skew: int = ROW_SKEW,
) -> int:
    """Place a cross-row write window opposite the read window on the ring."""

    if read_y < 0 or write_y < 0:
        raise ValueError("row indices must be non-negative")
    return (read_phase + READ_COUNT - row_skew * (write_y - read_y)) % BANK_COUNT


def cross_row_cycle_plan(
    cycle: int,
    read_y: int,
    write_y: int,
    read_second_buffer: bool = False,
    row_skew: int = ROW_SKEW,
) -> CyclePlan:
    """Build a conflict-free plan for simultaneous accesses to different rows."""

    if cycle < 0:
        raise ValueError("cycle must be non-negative")
    read_phase = PHASE_B if read_second_buffer else PHASE_A
    write_phase = compensated_write_phase(read_phase, read_y, write_y, row_skew)
    first_x = LANE_COUNT * cycle
    read_banks = tuple(
        (first_x + offset + row_skew * read_y + read_phase) % BANK_COUNT
        for offset in range(READ_COUNT)
    )
    write_banks = tuple(
        (first_x + offset + row_skew * write_y + write_phase) % BANK_COUNT
        for offset in range(WRITE_COUNT)
    )
    result = CyclePlan(cycle, read_banks, write_banks)
    result.validate()
    return result


def validate_row_edges(max_width: int = 257, rows: int = 12) -> None:
    """Exhaustively check small/partial/full issue groups and both buffers."""

    if max_width < 1 or rows < 1:
        raise ValueError("max_width and rows must be positive")
    for logical_width in range(1, max_width + 1):
        layout = padded_row(logical_width)
        emitted_outputs: list[int] = []
        for y in range(rows):
            for phase in (PHASE_A, PHASE_B):
                for issue in range(layout.issue_count):
                    plan = boundary_issue(logical_width, issue, y, phase)
                    if y == 0 and phase == PHASE_A:
                        output_start = issue * LANE_COUNT
                        emitted_outputs.extend(
                            output_start + lane
                            for lane, active in enumerate(plan.active_lanes)
                            if active
                        )
        if emitted_outputs != list(range(logical_width)):
            raise AssertionError("row outputs were dropped or emitted twice")


def validate_cross_row_access(cycles: int = 256, rows: int = 16) -> None:
    """Check every read/write row pair in both ping-pong directions."""

    if cycles < 1 or rows < 1:
        raise ValueError("cycles and rows must be positive")
    for read_y in range(rows):
        for write_y in range(rows):
            for read_second_buffer in (False, True):
                for cycle in range(cycles):
                    cross_row_cycle_plan(
                        cycle,
                        read_y,
                        write_y,
                        read_second_buffer,
                    )


def main() -> None:
    validate_row_edges()
    validate_cross_row_access()
    print("row-edge/Halo schedule: PASS")
    print("cross-row phase compensation: PASS")


if __name__ == "__main__":
    main()
