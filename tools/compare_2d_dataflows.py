"""Measure identical 2D outputs for line-buffer and banked multicast models."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.two_d_dataflow import TileSpec, compare_dataflows  # noqa: E402


REPORT_DEFAULT = ROOT / "build" / "2d-dataflow-comparison.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--height", type=int, default=256)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=0x4E423202)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    parser.add_argument("--quiet", action="store_true")
    arguments = parser.parse_args()

    spec = TileSpec(
        logical_width=arguments.width,
        logical_height=arguments.height,
    )
    comparison = compare_dataflows(spec, seed=arguments.seed)
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": "reference-level 2D comparison; not FPGA timing",
        "comparison_scope": {
            "line_buffer_stall_model": "no-stall/backpressure-free upper bound; an implementation may block on SRAM/BRAM/SRL port conflicts, line/row fill, tail/Halo boundaries, or downstream backpressure",
            "numeric_result_scope": "cycle and output values are reference counters under the regular no-stall assumption, not FPGA timing or throughput measurements",
        },
        **comparison,
    }
    report_path = arguments.report
    if not report_path.is_absolute():
        report_path = (ROOT / report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if not arguments.quiet:
        summary = report["comparison"]
        print(
            "2D dataflow comparison: PASS "
            f"({arguments.width}x{arguments.height}, "
            f"{summary['output_samples']} output samples, "
            f"digest={summary['output_digest']})"
        )
        print(
            "cycles: "
            f"line-buffer={summary['line_buffer_end_to_end_cycles']} "
            f"banked-load+compute={summary['banked_multicast_end_to_end_cycles']} "
            f"banked-overlap-limit={summary['banked_load_and_compute_overlap_cycles']}"
        )
        print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
