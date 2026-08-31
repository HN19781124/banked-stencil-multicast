"""Reference-level 2D comparison of line-buffer and banked multicast paths.

Both models consume the same dense complex-integer tile and evaluate the same
3x3 stencil.  The cycle numbers are explicit model assumptions, not FPGA
timing measurements; the output vectors are checked bit-for-bit.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Sequence


Sample = tuple[int, int]
Kernel = tuple[tuple[Sample, ...], ...]

DEFAULT_LANES = 4
DEFAULT_TAPS = 3
DEFAULT_BANK_COUNT = 36
DEFAULT_ROW_SKEW = DEFAULT_LANES + DEFAULT_TAPS - 1
DEFAULT_KERNEL: Kernel = (
    ((1, 0), (-1, 1), (0, -1)),
    ((0, 2), (1, 0), (-2, 0)),
    ((-1, 0), (0, -1), (1, 1)),
)


def _round_up(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


@dataclass(frozen=True)
class TileSpec:
    """Common 2D input/output contract for both reference models.

    ``logical_width`` and ``logical_height`` are the number of valid output
    samples.  The input tile includes a right/bottom ``T-1`` halo and is padded
    in X to a whole input beat.  Width is lane-aligned so the comparison has a
    fixed four-sample issue shape at every output group.
    """

    logical_width: int
    logical_height: int
    lanes: int = DEFAULT_LANES
    taps: int = DEFAULT_TAPS
    sample_bytes: int = 4

    def __post_init__(self) -> None:
        if self.logical_width < 1 or self.logical_height < 1:
            raise ValueError("logical dimensions must be positive")
        if self.lanes < 1 or self.taps < 1:
            raise ValueError("lanes and taps must be positive")
        if self.logical_width % self.lanes:
            raise ValueError("logical_width must be lane-aligned for this comparison")
        if self.taps != 3:
            raise ValueError("the reference comparison currently uses a 3x3 stencil")
        if self.sample_bytes != 4:
            raise ValueError("complex FP16 samples use four bytes")

    @property
    def input_width(self) -> int:
        return self.logical_width + self.taps - 1

    @property
    def stream_width(self) -> int:
        return _round_up(self.input_width, self.lanes)

    @property
    def input_height(self) -> int:
        return self.logical_height + self.taps - 1

    @property
    def input_samples(self) -> int:
        return self.stream_width * self.input_height

    @property
    def input_beats_per_row(self) -> int:
        return self.stream_width // self.lanes

    @property
    def input_beats(self) -> int:
        return self.input_beats_per_row * self.input_height

    @property
    def output_samples(self) -> int:
        return self.logical_width * self.logical_height

    @property
    def output_beats_per_row(self) -> int:
        return self.logical_width // self.lanes

    @property
    def output_beats(self) -> int:
        return self.output_beats_per_row * self.logical_height


def _xorshift32(state: int) -> int:
    state &= 0xFFFFFFFF
    state ^= (state << 13) & 0xFFFFFFFF
    state ^= state >> 17
    state ^= (state << 5) & 0xFFFFFFFF
    return state & 0xFFFFFFFF


def generate_tile(spec: TileSpec, seed: int = 0x4E423202) -> tuple[tuple[Sample, ...], ...]:
    """Generate one deterministic dense complex tile shared by both models."""

    if seed == 0:
        raise ValueError("seed must be non-zero for the xorshift generator")
    state = seed & 0xFFFFFFFF
    rows: list[tuple[Sample, ...]] = []
    for _y in range(spec.input_height):
        row: list[Sample] = []
        for x in range(spec.stream_width):
            if x >= spec.input_width:
                row.append((0, 0))
                continue
            state = _xorshift32(state)
            real = (state & 0x1F) - 16
            state = _xorshift32(state)
            imag = (state & 0x1F) - 16
            row.append((real, imag))
        rows.append(tuple(row))
    return tuple(rows)


def _validate_grid(
    grid: Sequence[Sequence[Sample]],
    spec: TileSpec,
) -> None:
    if len(grid) != spec.input_height:
        raise ValueError("grid height does not match TileSpec")
    if any(len(row) != spec.stream_width for row in grid):
        raise ValueError("grid width does not match TileSpec")


def complex_mul(a: Sample, b: Sample) -> Sample:
    return (a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0])


def complex_add(a: Sample, b: Sample) -> Sample:
    return (a[0] + b[0], a[1] + b[1])


def _stencil_at(
    samples: Sequence[Sequence[Sample]],
    x: int,
    y: int,
    kernel: Kernel,
) -> Sample:
    total: Sample = (0, 0)
    for ky, kernel_row in enumerate(kernel):
        for kx, coefficient in enumerate(kernel_row):
            total = complex_add(
                total,
                complex_mul(samples[y + ky][x + kx], coefficient),
            )
    return total


def _line_buffer_stencil_at(
    row_buffers: Sequence[Sequence[Sample]],
    x: int,
    output_y: int,
    kernel: Kernel,
) -> Sample:
    """Read one window from the three circular rows currently in flight."""

    total: Sample = (0, 0)
    row_count = len(row_buffers)
    for ky, kernel_row in enumerate(kernel):
        row = row_buffers[(output_y + ky) % row_count]
        for kx, coefficient in enumerate(kernel_row):
            total = complex_add(total, complex_mul(row[x + kx], coefficient))
    return total


def reference_outputs(
    grid: Sequence[Sequence[Sample]],
    spec: TileSpec,
    kernel: Kernel = DEFAULT_KERNEL,
) -> tuple[Sample, ...]:
    """Return row-major valid 2D stencil outputs."""

    _validate_grid(grid, spec)
    if len(kernel) != spec.taps or any(len(row) != spec.taps for row in kernel):
        raise ValueError("kernel shape does not match taps")
    return tuple(
        _stencil_at(grid, x, y, kernel)
        for y in range(spec.logical_height)
        for x in range(spec.logical_width)
    )


def _digest_samples(samples: Sequence[Sample]) -> str:
    digest = hashlib.sha256()
    for real, imag in samples:
        digest.update(struct.pack(">qq", real, imag))
    return digest.hexdigest()


@dataclass(frozen=True)
class SimulationResult:
    name: str
    spec: TileSpec
    outputs: tuple[Sample, ...]
    input_beats: int
    output_beats: int
    preload_cycles: int
    core_cycles: int
    end_to_end_cycles: int
    first_output_cycle: int
    last_output_cycle: int
    steady_output_interval: float
    storage_reads: int
    storage_writes: int
    logical_window_values: int
    multicast_deliveries: int
    bank_count: int | None
    bank_conflict_checks: int
    fifo_max_occupancy: int

    @property
    def output_digest(self) -> str:
        return _digest_samples(self.outputs)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "input_beats": self.input_beats,
            "output_beats": self.output_beats,
            "preload_cycles": self.preload_cycles,
            "core_cycles": self.core_cycles,
            "end_to_end_cycles": self.end_to_end_cycles,
            "first_output_cycle": self.first_output_cycle,
            "last_output_cycle": self.last_output_cycle,
            "steady_output_interval": self.steady_output_interval,
            "storage_reads": self.storage_reads,
            "storage_writes": self.storage_writes,
            "logical_window_values": self.logical_window_values,
            "multicast_deliveries": self.multicast_deliveries,
            "bank_count": self.bank_count,
            "bank_conflict_checks": self.bank_conflict_checks,
            "fifo_max_occupancy": self.fifo_max_occupancy,
            "output_digest": self.output_digest,
        }


def _steady_interval(cycles: Sequence[int]) -> float:
    if len(cycles) < 2:
        return 0.0
    return (cycles[-1] - cycles[0]) / (len(cycles) - 1)


def simulate_line_buffer(
    grid: Sequence[Sequence[Sample]],
    spec: TileSpec,
    kernel: Kernel = DEFAULT_KERNEL,
    mac_latency: int = 1,
) -> SimulationResult:
    """Simulate a three-row line buffer with one four-sample input beat/cycle.

    The current row is written from the stream; the two preceding rows are read
    from the line buffers.  A one-cycle flush is added only when a partial final
    lane group exists (the normal comparison contract is lane-aligned).
    """

    if mac_latency < 0:
        raise ValueError("mac_latency must be non-negative")
    _validate_grid(grid, spec)
    row_buffers: list[list[Sample]] = [
        [(0, 0)] * spec.stream_width for _ in range(spec.taps)
    ]
    outputs: list[Sample] = []
    output_cycles: list[int] = []
    cycle = 0
    storage_writes = 0
    output_beats = 0

    for input_y in range(spec.input_height):
        slot = input_y % spec.taps
        for beat in range(spec.input_beats_per_row):
            x = beat * spec.lanes
            row_buffers[slot][x : x + spec.lanes] = grid[input_y][
                x : x + spec.lanes
            ]
            storage_writes += spec.lanes

            if input_y >= spec.taps - 1 and beat >= 1:
                output_y = input_y - (spec.taps - 1)
                output_x = (beat - 1) * spec.lanes
                if output_x < spec.logical_width:
                    active = min(spec.lanes, spec.logical_width - output_x)
                    for lane in range(active):
                        outputs.append(
                            _line_buffer_stencil_at(
                                row_buffers,
                                output_x + lane,
                                output_y,
                                kernel,
                            )
                        )
                    output_beats += 1
                    output_cycles.append(cycle + mac_latency)
            cycle += 1

        # A non-aligned logical width needs one drain beat for the final tail.
        output_x = (spec.input_beats_per_row - 1) * spec.lanes
        if input_y >= spec.taps - 1 and output_x < spec.logical_width:
            output_y = input_y - (spec.taps - 1)
            active = min(spec.lanes, spec.logical_width - output_x)
            for lane in range(active):
                outputs.append(
                    _line_buffer_stencil_at(
                        row_buffers, output_x + lane, output_y, kernel
                    )
                )
            output_beats += 1
            output_cycles.append(cycle + mac_latency)
            cycle += 1

    expected_beats = spec.output_beats
    if output_beats != expected_beats or len(outputs) != spec.output_samples:
        raise AssertionError(
            f"line-buffer schedule emitted {output_beats} beats / {len(outputs)} samples; "
            f"expected {expected_beats} / {spec.output_samples}"
        )
    return SimulationResult(
        name="line-buffer",
        spec=spec,
        outputs=tuple(outputs),
        input_beats=spec.input_beats,
        output_beats=output_beats,
        preload_cycles=0,
        core_cycles=output_beats + mac_latency,
        end_to_end_cycles=cycle + mac_latency,
        first_output_cycle=output_cycles[0],
        last_output_cycle=output_cycles[-1],
        steady_output_interval=_steady_interval(output_cycles),
        storage_reads=output_beats * (spec.taps - 1) * spec.lanes,
        storage_writes=storage_writes,
        logical_window_values=spec.output_samples * spec.taps * spec.taps,
        multicast_deliveries=0,
        bank_count=None,
        bank_conflict_checks=0,
        fifo_max_occupancy=0,
    )


def _bank_index(x: int, y: int, bank_count: int, row_skew: int, phase: int = 0) -> int:
    return (x + row_skew * y + phase) % bank_count


def _bank_address(x: int, y: int, stream_width: int, bank_count: int) -> int:
    words_per_row = (stream_width + bank_count - 1) // bank_count
    return y * words_per_row + x // bank_count


def simulate_banked_multicast(
    grid: Sequence[Sequence[Sample]],
    spec: TileSpec,
    kernel: Kernel = DEFAULT_KERNEL,
    bank_count: int = DEFAULT_BANK_COUNT,
    row_skew: int = DEFAULT_ROW_SKEW,
    mac_latency: int = 1,
) -> SimulationResult:
    """Simulate a 2D static-bank/unique-read/multicast path.

    For a 3x3 stencil and four horizontal lanes, one issue consumes 18 unique
    samples (three rows by six columns).  Thirty-six banks are used so that the
    read set and a half-ring-shifted four-sample write set have separate bank
    space in the corresponding ping-pong construction.
    """

    if bank_count < spec.taps * (spec.lanes + spec.taps - 1):
        raise ValueError("bank_count is too small for the 2D unique-read set")
    if mac_latency < 0:
        raise ValueError("mac_latency must be non-negative")
    _validate_grid(grid, spec)
    unique_x = spec.lanes + spec.taps - 1
    unique_reads = spec.taps * unique_x
    words_per_row = (spec.stream_width + bank_count - 1) // bank_count
    bank_depth = spec.input_height * words_per_row
    bank_memory: list[list[Sample | None]] = [
        [None] * bank_depth for _ in range(bank_count)
    ]
    storage_writes = 0
    conflict_checks = 0

    for y, row in enumerate(grid):
        for beat in range(spec.input_beats_per_row):
            x0 = beat * spec.lanes
            write_banks = tuple(
                _bank_index(x0 + slot, y, bank_count, row_skew)
                for slot in range(spec.lanes)
            )
            if len(set(write_banks)) != spec.lanes:
                raise AssertionError(
                    f"input write-bank conflict row={y} beat={beat}: {write_banks}"
                )
            conflict_checks += 1
            for slot, sample in enumerate(row[x0 : x0 + spec.lanes]):
                x = x0 + slot
                bank = write_banks[slot]
                address = _bank_address(x, y, spec.stream_width, bank_count)
                bank_memory[bank][address] = sample
                storage_writes += 1

    outputs: list[Sample] = []
    output_cycles: list[int] = []
    for output_y in range(spec.logical_height):
        for output_beat in range(spec.output_beats_per_row):
            output_x = output_beat * spec.lanes
            read_locations = tuple(
                (x, output_y + ky)
                for ky in range(spec.taps)
                for x in range(output_x, output_x + unique_x)
            )
            read_banks = tuple(
                _bank_index(x, y, bank_count, row_skew)
                for x, y in read_locations
            )
            if len(set(read_banks)) != unique_reads:
                raise AssertionError(
                    f"2D read-bank conflict row={output_y} beat={output_beat}: "
                    f"{read_banks}"
                )
            conflict_checks += 1

            unique_samples: list[list[Sample]] = []
            for ky in range(spec.taps):
                row_samples: list[Sample] = []
                for offset in range(unique_x):
                    x = output_x + offset
                    y = output_y + ky
                    bank = _bank_index(x, y, bank_count, row_skew)
                    address = _bank_address(x, y, spec.stream_width, bank_count)
                    sample = bank_memory[bank][address]
                    if sample is None:
                        raise AssertionError(
                            f"missing banked sample at x={x} y={y}"
                        )
                    row_samples.append(sample)
                unique_samples.append(row_samples)

            for lane in range(spec.lanes):
                total: Sample = (0, 0)
                for ky, kernel_row in enumerate(kernel):
                    for kx, coefficient in enumerate(kernel_row):
                        total = complex_add(
                            total,
                            complex_mul(unique_samples[ky][lane + kx], coefficient),
                        )
                outputs.append(total)
            output_cycles.append(
                spec.input_beats + len(output_cycles) + mac_latency
            )

    if len(outputs) != spec.output_samples:
        raise AssertionError(
            f"banked multicast emitted {len(outputs)} samples; "
            f"expected {spec.output_samples}"
        )
    core_cycles = spec.output_beats + mac_latency
    end_to_end_cycles = spec.input_beats + core_cycles
    return SimulationResult(
        name="banked-multicast",
        spec=spec,
        outputs=tuple(outputs),
        input_beats=spec.input_beats,
        output_beats=spec.output_beats,
        preload_cycles=spec.input_beats,
        core_cycles=core_cycles,
        end_to_end_cycles=end_to_end_cycles,
        first_output_cycle=output_cycles[0],
        last_output_cycle=output_cycles[-1],
        steady_output_interval=_steady_interval(output_cycles),
        storage_reads=spec.output_beats * unique_reads,
        storage_writes=storage_writes,
        logical_window_values=spec.output_samples * spec.taps * spec.taps,
        multicast_deliveries=spec.output_samples * spec.taps * spec.taps,
        bank_count=bank_count,
        bank_conflict_checks=conflict_checks,
        fifo_max_occupancy=0,
    )


def compare_dataflows(
    spec: TileSpec,
    seed: int = 0x4E423202,
    kernel: Kernel = DEFAULT_KERNEL,
) -> dict[str, object]:
    """Run both models and require identical final outputs."""

    grid = generate_tile(spec, seed)
    expected = reference_outputs(grid, spec, kernel)
    line_buffer = simulate_line_buffer(grid, spec, kernel)
    banked = simulate_banked_multicast(grid, spec, kernel)
    if line_buffer.outputs != expected:
        raise AssertionError("line-buffer output disagrees with common reference")
    if banked.outputs != expected:
        raise AssertionError("banked multicast output disagrees with common reference")
    if line_buffer.outputs != banked.outputs:
        for index, (left, right) in enumerate(
            zip(line_buffer.outputs, banked.outputs)
        ):
            if left != right:
                raise AssertionError(
                    f"dataflow output mismatch at sample {index}: {left} != {right}"
                )
        raise AssertionError("dataflow output lengths differ")

    return {
        "input": {
            "logical_width": spec.logical_width,
            "logical_height": spec.logical_height,
            "input_width": spec.input_width,
            "stream_width": spec.stream_width,
            "input_height": spec.input_height,
            "lanes": spec.lanes,
            "taps": spec.taps,
            "sample_bytes": spec.sample_bytes,
            "seed": seed,
            "kernel": kernel,
        },
        "comparison": {
            "outputs_equal": True,
            "output_samples": spec.output_samples,
            "output_beats": spec.output_beats,
            "output_digest": line_buffer.output_digest,
            "line_buffer_end_to_end_cycles": line_buffer.end_to_end_cycles,
            "banked_multicast_end_to_end_cycles": banked.end_to_end_cycles,
            "banked_preloaded_core_cycles": banked.core_cycles,
            "banked_load_and_compute_overlap_cycles": max(
                banked.preload_cycles, banked.core_cycles
            ),
        },
        "line_buffer": line_buffer.to_dict(),
        "banked_multicast": banked.to_dict(),
    }


__all__ = [
    "DEFAULT_KERNEL",
    "Kernel",
    "Sample",
    "SimulationResult",
    "TileSpec",
    "compare_dataflows",
    "complex_add",
    "complex_mul",
    "generate_tile",
    "reference_outputs",
    "simulate_banked_multicast",
    "simulate_line_buffer",
]
