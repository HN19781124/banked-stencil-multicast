"""Build a reference-only ASIC comparison for two 2D dataflow paths.

The functional models share the same input and stencil, so this tool reports
the activity counts that a technology-calibrated ASIC power model would need.
It intentionally does not invent absolute mW: line-buffer RTL/P&R and
technology-specific SRAM, register, and routing energy are not available in
the repository yet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.two_d_dataflow import (  # noqa: E402
    TileSpec,
    compare_dataflows,
)


REPORT_DEFAULT = ROOT / "build" / "asic-dataflow-comparison.json"


def _activity_summary(
    result: dict[str, object],
    output_samples: int,
    sample_bytes: int,
) -> dict[str, object]:
    """Normalize path counters for a technology-independent comparison."""

    storage_reads = int(result["storage_reads"])
    storage_writes = int(result["storage_writes"])
    logical_window_values = int(result["logical_window_values"])
    multicast_deliveries = int(result["multicast_deliveries"])
    storage_accesses = storage_reads + storage_writes
    return {
        "name": result["name"],
        "storage_reads": storage_reads,
        "storage_writes": storage_writes,
        "storage_accesses": storage_accesses,
        "storage_read_bytes": storage_reads * sample_bytes,
        "storage_write_bytes": storage_writes * sample_bytes,
        "logical_window_values": logical_window_values,
        "multicast_deliveries": multicast_deliveries,
        "bank_count": result["bank_count"],
        "storage_reads_per_output": storage_reads / output_samples,
        "storage_writes_per_output": storage_writes / output_samples,
        "storage_accesses_per_output": storage_accesses / output_samples,
        "logical_window_values_per_output": logical_window_values / output_samples,
        "multicast_deliveries_per_output": multicast_deliveries / output_samples,
    }


def compare_asic_dataflows(
    width: int,
    height: int,
    seed: int = 0x4E423202,
) -> dict[str, object]:
    """Return common correctness and ASIC activity evidence."""

    comparison = compare_dataflows(TileSpec(logical_width=width, logical_height=height), seed)
    input_data = comparison["input"]
    comparison_data = comparison["comparison"]
    output_samples = int(comparison_data["output_samples"])
    sample_bytes = int(input_data["sample_bytes"])
    line_buffer = _activity_summary(comparison["line_buffer"], output_samples, sample_bytes)
    banked = _activity_summary(
        comparison["banked_multicast"], output_samples, sample_bytes
    )
    return {
        "model": "reference-only ASIC dataflow comparison; no line-buffer RTL/P&R or power sign-off",
        "input": input_data,
        "correctness": {
            "outputs_equal": comparison_data["outputs_equal"],
            "output_samples": output_samples,
            "output_digest": comparison_data["output_digest"],
        },
        "cycle_reference": {
            "line_buffer_end_to_end_cycles": comparison_data[
                "line_buffer_end_to_end_cycles"
            ],
            "banked_multicast_end_to_end_cycles": comparison_data[
                "banked_multicast_end_to_end_cycles"
            ],
            "banked_preloaded_core_cycles": comparison_data[
                "banked_preloaded_core_cycles"
            ],
            "banked_load_and_compute_overlap_cycles": comparison_data[
                "banked_load_and_compute_overlap_cycles"
            ],
        },
        "activity": {
            "line_buffer": line_buffer,
            "banked_multicast": banked,
        },
        "power": {
            "status": "not_calibrated",
            "absolute_power_mw": None,
            "energy_per_output_pj": None,
            "reason": "requires the same ASIC PDK, SRAM macro views, clock/activity, voltage, and physical implementation for both paths",
            "common_terms": [
                "complex MAC and coefficient activity",
                "input/output interface activity",
                "reset and control baseline",
            ],
            "path_specific_terms": {
                "line_buffer": [
                    "line-buffer SRAM read/write energy",
                    "window-register shift and toggle energy",
                    "line-buffer control and mux energy",
                ],
                "banked_multicast": [
                    "banked SRAM read/write energy",
                    "multicast wire/fan-out energy",
                    "bank address and conflict-free schedule logic energy",
                ],
            },
            "symbolic_energy": {
                "line_buffer": "R_lb*e_sram_read + W_lb*e_sram_write + S_lb*e_window_shift + C*e_common",
                "banked_multicast": "R_bm*e_sram_read + W_bm*e_sram_write + F_bm*e_multicast_fanout + C*e_common",
            },
        },
        "comparison_scope": {
            "same_workload": True,
            "same_complex_stencil": True,
            "same_sample_bytes": sample_bytes,
            "single_port_condition": "must be held equal or explicitly reported; line-buffer storage banking cannot silently use extra ports",
            "banked_overlap_and_repeated_pass_storage": "active/prefetch A/B buffers plus Halo capacity must be reserved when load/compute overlap or multiple passes are required; not included in the activity-only power result",
            "line_buffer_storage_scope": "rows-in-flight and window state only in this reference; implementation-specific capacity remains separate",
            "line_buffer_stall_scope": "reference uses a no-stall/backpressure-free upper bound; an implementation may block on SRAM/BRAM port conflicts, line/row fill, tail/Halo boundaries, or downstream backpressure; such stalls are not in cycle or activity counts",
            "numeric_result_scope": "cycle and activity values are reference counters under the regular no-stall assumption, not ASIC timing or throughput measurements",
            "physical_signoff": False,
        },
    }


def print_table(data: dict[str, object]) -> None:
    activity = data["activity"]
    assert isinstance(activity, dict)
    print("path reads/output writes/output storage/output multicast/output banks")
    for key in ("line_buffer", "banked_multicast"):
        item = activity[key]
        assert isinstance(item, dict)
        print(
            f"{key:16s} {item['storage_reads_per_output']:12.3f} "
            f"{item['storage_writes_per_output']:13.3f} "
            f"{item['storage_accesses_per_output']:15.3f} "
            f"{item['multicast_deliveries_per_output']:17.3f} "
            f"{item['bank_count'] if item['bank_count'] is not None else 'n/a'}"
        )
    print("power: not calibrated (activity counters only; no absolute mW)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--height", type=int, default=256)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0x4E423202)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    parser.add_argument("--quiet", action="store_true")
    arguments = parser.parse_args()
    try:
        data = compare_asic_dataflows(arguments.width, arguments.height, arguments.seed)
    except ValueError as exc:
        parser.error(str(exc))
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        **data,
    }
    report_path = arguments.report
    if not report_path.is_absolute():
        report_path = (ROOT / report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if not arguments.quiet:
        print_table(report)
        print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
