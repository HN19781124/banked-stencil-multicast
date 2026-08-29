"""Sweep the first-order N-lane/T-tap design space.

This is an analytical sizing tool, not a timing, power, or area sign-off tool.
It uses the symmetric single-port ping-pong family already defined by
``reference.bank_schedule`` and reports the resulting resource and bandwidth
envelope.  The constrained selection is deliberately explicit so that a
"best" candidate is reproducible rather than an unstated claim of optimum.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_LANES = tuple(range(1, 33))
DEFAULT_TAPS = 3
DEFAULT_SAMPLE_BYTES = 4
DEFAULT_CLOCK_MHZ = 100.0
DEFAULT_DEPTH_WORDS = 1024
DEFAULT_MAX_CAPACITY_KIB = 144.0
DEFAULT_MAX_ENDPOINTS = 48
DEFAULT_MIN_REDUCTION = 0.60


@dataclass(frozen=True)
class Candidate:
    lanes: int
    taps: int
    unique_reads: int
    banks: int
    logical_reads: int
    duplicate_reduction: float
    total_accesses: int
    utilization: float
    idle_banks: int
    multicast_endpoints: int
    average_fanout: float
    capacity_kib: float
    read_gbps: float
    write_gbps: float
    total_gbps: float
    serialized_outputs_per_cycle: float
    unrolled_outputs_per_cycle: int
    serialized_gflops: float
    unrolled_gflops: float
    binary_tree_levels: int


def make_candidate(
    lanes: int,
    taps: int = DEFAULT_TAPS,
    sample_bytes: int = DEFAULT_SAMPLE_BYTES,
    clock_mhz: float = DEFAULT_CLOCK_MHZ,
    depth_words: int = DEFAULT_DEPTH_WORDS,
) -> Candidate:
    """Return one candidate using the symmetric conflict-free family."""

    if lanes < 1:
        raise ValueError("lanes must be at least one")
    if taps < 1:
        raise ValueError("taps must be at least one")
    if sample_bytes < 1:
        raise ValueError("sample_bytes must be positive")
    if clock_mhz <= 0:
        raise ValueError("clock_mhz must be positive")
    if depth_words < 1:
        raise ValueError("depth_words must be positive")

    unique_reads = lanes + taps - 1
    banks = 2 * unique_reads
    logical_reads = lanes * taps
    total_accesses = unique_reads + lanes
    duplicate_reduction = 1.0 - unique_reads / logical_reads
    bytes_per_cycle = sample_bytes
    capacity_kib = banks * depth_words * sample_bytes / 1024.0
    read_gbps = unique_reads * bytes_per_cycle * clock_mhz / 1000.0
    write_gbps = lanes * bytes_per_cycle * clock_mhz / 1000.0
    total_gbps = read_gbps + write_gbps
    serialized_outputs_per_cycle = lanes / taps
    # A serialized lane performs one tap MAC every cycle.  It emits one
    # complete result every T cycles, but the MAC FLOP rate is still N*8/f.
    serialized_gflops = lanes * 8.0 * clock_mhz / 1000.0
    unrolled_gflops = lanes * taps * 8.0 * clock_mhz / 1000.0
    binary_tree_levels = math.ceil(math.log2(lanes)) if lanes > 1 else 0

    return Candidate(
        lanes=lanes,
        taps=taps,
        unique_reads=unique_reads,
        banks=banks,
        logical_reads=logical_reads,
        duplicate_reduction=duplicate_reduction,
        total_accesses=total_accesses,
        utilization=total_accesses / banks,
        idle_banks=banks - total_accesses,
        multicast_endpoints=logical_reads,
        average_fanout=logical_reads / unique_reads,
        capacity_kib=capacity_kib,
        read_gbps=read_gbps,
        write_gbps=write_gbps,
        total_gbps=total_gbps,
        serialized_outputs_per_cycle=serialized_outputs_per_cycle,
        unrolled_outputs_per_cycle=lanes,
        serialized_gflops=serialized_gflops,
        unrolled_gflops=unrolled_gflops,
        binary_tree_levels=binary_tree_levels,
    )


def parse_lanes(value: str) -> tuple[int, ...]:
    """Parse a comma-separated positive lane list."""

    try:
        lanes = tuple(sorted({int(item.strip()) for item in value.split(",")}))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("lanes must be comma-separated integers") from exc
    if not lanes or any(lane < 1 for lane in lanes):
        raise argparse.ArgumentTypeError("lanes must contain positive integers")
    return lanes


def select_feasible(
    candidates: tuple[Candidate, ...],
    max_capacity_kib: float,
    max_endpoints: int,
    min_reduction: float,
) -> tuple[Candidate, ...]:
    """Apply the explicit design envelope used for the reproducible selection."""

    return tuple(
        candidate
        for candidate in candidates
        if candidate.capacity_kib <= max_capacity_kib
        and candidate.multicast_endpoints <= max_endpoints
        and candidate.duplicate_reduction >= min_reduction
    )


def select_peak(candidates: tuple[Candidate, ...]) -> Candidate:
    """Select the highest ideal unrolled throughput, then the largest lane count."""

    if not candidates:
        raise ValueError("the constraint envelope has no feasible candidate")
    return max(candidates, key=lambda candidate: (candidate.unrolled_gflops, candidate.lanes))


def report(
    lanes: tuple[int, ...] = DEFAULT_LANES,
    taps: int = DEFAULT_TAPS,
    sample_bytes: int = DEFAULT_SAMPLE_BYTES,
    clock_mhz: float = DEFAULT_CLOCK_MHZ,
    depth_words: int = DEFAULT_DEPTH_WORDS,
    max_capacity_kib: float = DEFAULT_MAX_CAPACITY_KIB,
    max_endpoints: int = DEFAULT_MAX_ENDPOINTS,
    min_reduction: float = DEFAULT_MIN_REDUCTION,
) -> dict[str, object]:
    candidates = tuple(
        make_candidate(lane, taps, sample_bytes, clock_mhz, depth_words)
        for lane in lanes
    )
    feasible = select_feasible(candidates, max_capacity_kib, max_endpoints, min_reduction)
    selected = select_peak(feasible)
    return {
        "assumptions": {
            "taps": taps,
            "sample_bytes": sample_bytes,
            "clock_mhz": clock_mhz,
            "depth_words": depth_words,
            "complex_mac_real_flop_count": 8,
            "bank_family": "U=N+T-1, M=2U, phase difference U",
            "serialized_mac_model": "one tap MAC per lane per cycle",
            "unrolled_mac_model": "T tap MACs per lane per cycle",
        },
        "constraints": {
            "max_capacity_kib": max_capacity_kib,
            "max_multicast_endpoints": max_endpoints,
            "min_duplicate_reduction": min_reduction,
        },
        "selected_lane_count": selected.lanes,
        "feasible_lane_counts": [candidate.lanes for candidate in feasible],
        "candidates": [asdict(candidate) for candidate in candidates],
    }


def print_table(data: dict[str, object]) -> None:
    candidates = data["candidates"]
    selected = data["selected_lane_count"]
    print("N  U  M  red%  capKiB  readGB/s  totalGB/s  serGFLOP/s  unrollGFLOP/s  endpoints  feasible")
    for item in candidates:
        assert isinstance(item, dict)
        feasible = item["lanes"] in data["feasible_lane_counts"]
        marker = "*" if item["lanes"] == selected else " "
        print(
            f"{marker}{item['lanes']:2d} {item['unique_reads']:2d} {item['banks']:2d} "
            f"{item['duplicate_reduction'] * 100:5.1f} {item['capacity_kib']:7.1f} "
            f"{item['read_gbps']:9.2f} {item['total_gbps']:10.2f} "
            f"{item['serialized_gflops']:11.2f} {item['unrolled_gflops']:14.2f} "
            f"{item['multicast_endpoints']:9d} {'yes' if feasible else 'no'}"
        )
    print(f"selected N={selected} (maximum ideal unrolled throughput within constraints)")


def write_csv(path: Path, data: dict[str, object]) -> None:
    candidates = data["candidates"]
    assert isinstance(candidates, list)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(candidates[0].keys()))
        writer.writeheader()
        writer.writerows(candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lanes", type=parse_lanes, default=DEFAULT_LANES)
    parser.add_argument("--taps", type=int, default=DEFAULT_TAPS)
    parser.add_argument("--sample-bytes", type=int, default=DEFAULT_SAMPLE_BYTES)
    parser.add_argument("--clock-mhz", type=float, default=DEFAULT_CLOCK_MHZ)
    parser.add_argument("--depth-words", type=int, default=DEFAULT_DEPTH_WORDS)
    parser.add_argument("--max-capacity-kib", type=float, default=DEFAULT_MAX_CAPACITY_KIB)
    parser.add_argument("--max-endpoints", type=int, default=DEFAULT_MAX_ENDPOINTS)
    parser.add_argument("--min-reduction", type=float, default=DEFAULT_MIN_REDUCTION)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    data = report(
        lanes=args.lanes,
        taps=args.taps,
        sample_bytes=args.sample_bytes,
        clock_mhz=args.clock_mhz,
        depth_words=args.depth_words,
        max_capacity_kib=args.max_capacity_kib,
        max_endpoints=args.max_endpoints,
        min_reduction=args.min_reduction,
    )
    print_table(data)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if args.csv:
        write_csv(args.csv, data)


if __name__ == "__main__":
    main()
