"""Measure the reference banked engine under deterministic stream traffic."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

from bootstrap_cad import find_suite, suite_environment, tool_path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DEFAULT = ROOT / "build" / "performance-report.json"
IMAGE_DEFAULT = ROOT / "build" / "banked_stencil_performance_tb.vvp"
REFERENCE_CLOCK_MHZ = 100
LANES = 4
TAPS = 3
SAMPLE_BYTES = 4
INPUT_BEAT_BYTES = LANES * SAMPLE_BYTES
UNIQUE_READS_PER_ISSUE = 6
PREFETCH_WRITES_PER_INPUT_BEAT = 4
REAL_FLOPS_PER_COMPLEX_MAC = 8
FIFO_DEPTH = 16
RTL_SOURCES = [
    "rtl/axis_fifo.sv",
    "rtl/bank_scheduler.sv",
    "rtl/single_port_sram.sv",
    "rtl/sram_mbist.sv",
    "rtl/stencil_multicast.sv",
    "rtl/fp16_fma_accumulator.sv",
    "rtl/fp32_to_fp16_rne.sv",
    "rtl/complex_stencil_mac.sv",
    "rtl/banked_stencil_engine.sv",
    "rtl/tb_banked_stencil_performance.sv",
]
PERF_LINE = re.compile(r"^PERF\s+(?P<body>.*)$", re.MULTILINE)
STAGE_LINE = re.compile(r"^STAGE\s+(?P<body>.*)$", re.MULTILINE)
FIELD = re.compile(r"(?P<key>[a-z_]+)=(?P<value>[^\s]+)")
INTEGER_FIELDS = {
    "width",
    "height",
    "padded",
    "input_beats",
    "output_beats",
    "cycles",
    "start",
    "first_output",
    "last_output",
    "done",
    "input_accepts",
    "output_accepts",
    "input_stalls",
    "output_stalls",
    "errors",
    "input_max_occupancy",
    "output_max_occupancy",
}
STAGE_INTEGER_FIELDS = {
    "control_cycles",
    "load_cycles",
    "read_cycles",
    "capture_cycles",
    "submit_cycles",
    "wait_output_cycles",
    "mac_busy_cycles",
    "read_issues",
    "captures",
    "mac_accepts",
    "mac_outputs",
}


def run_command(
    command: list[str],
    environment: dict[str, str],
    timeout: float | None = None,
) -> dict[str, object]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    output = (result.stdout + result.stderr).strip()
    return {
        "command": command,
        "returncode": result.returncode,
        "output": output,
    }


def parse_measurement(output: str) -> dict[str, object]:
    matches = PERF_LINE.findall(output)
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one PERF line, found {len(matches)}")
    fields: dict[str, object] = {}
    for match in FIELD.finditer(matches[0]):
        key = match.group("key")
        value = match.group("value")
        fields[key] = int(value) if key in INTEGER_FIELDS else value
    stage_matches = STAGE_LINE.findall(output)
    if len(stage_matches) != 1:
        raise RuntimeError(
            f"expected exactly one STAGE line, found {len(stage_matches)}"
        )
    stage: dict[str, object] = {}
    for match in FIELD.finditer(stage_matches[0]):
        key = match.group("key")
        value = match.group("value")
        stage[key] = int(value) if key in STAGE_INTEGER_FIELDS else value
    required_stage = {
        "mode",
        "control_cycles",
        "load_cycles",
        "read_cycles",
        "capture_cycles",
        "submit_cycles",
        "wait_output_cycles",
        "mac_busy_cycles",
        "read_issues",
        "captures",
        "mac_accepts",
        "mac_outputs",
    }
    missing_stage = sorted(required_stage - stage.keys())
    if missing_stage:
        raise RuntimeError(
            f"STAGE line missing fields: {', '.join(missing_stage)}"
        )
    if stage["mode"] != fields.get("mode"):
        raise RuntimeError(
            f"PERF/STAGE mode mismatch: {fields.get('mode')} vs {stage['mode']}"
        )
    required = {
        "mode",
        "width",
        "height",
        "padded",
        "input_beats",
        "output_beats",
        "cycles",
        "start",
        "first_output",
        "last_output",
        "done",
        "input_accepts",
        "output_accepts",
        "input_stalls",
        "output_stalls",
        "errors",
        "input_max_occupancy",
        "output_max_occupancy",
    }
    missing = sorted(required - fields.keys())
    if missing:
        raise RuntimeError(f"PERF line missing fields: {', '.join(missing)}")
    output_beats = int(fields["output_beats"])
    first_output = int(fields["first_output"])
    last_output = int(fields["last_output"])
    start = int(fields["start"])
    done = int(fields["done"])
    if output_beats < 1 or last_output < first_output:
        raise RuntimeError("invalid output timing in PERF line")
    if int(fields["errors"]) != 0:
        raise RuntimeError(f"performance run reported {fields['errors']} errors")
    if output_beats > 1 and last_output == first_output:
        raise RuntimeError("output timing has zero steady-state interval")
    transaction_cycles = done - start
    steady_intervals = output_beats - 1
    valid_lane_results = int(fields["width"]) * int(fields["height"])
    input_beats = int(fields["input_beats"])
    output_stalls = int(fields["output_stalls"])
    input_stalls = int(fields["input_stalls"])
    stage_cycle_sum = sum(
        int(stage[key])
        for key in (
            "control_cycles",
            "load_cycles",
            "read_cycles",
            "capture_cycles",
            "submit_cycles",
            "wait_output_cycles",
        )
    )
    if stage_cycle_sum != transaction_cycles:
        raise RuntimeError(
            "stage cycle sum does not cover transaction: "
            f"{stage_cycle_sum} != {transaction_cycles}"
        )
    for key, expected in (
        ("read_issues", output_beats),
        ("captures", output_beats),
        ("mac_accepts", output_beats),
        ("mac_outputs", output_beats),
    ):
        if int(stage[key]) != expected:
            raise RuntimeError(
                f"stage count mismatch for {key}: {stage[key]} != {expected}"
            )
    fields["stage"] = stage
    steady_interval = (
        (last_output - first_output) / steady_intervals
        if steady_intervals
        else 0.0
    )
    reference_cycles_per_second = REFERENCE_CLOCK_MHZ * 1_000_000
    sram_read_bytes = output_beats * UNIQUE_READS_PER_ISSUE * SAMPLE_BYTES
    sram_write_bytes = input_beats * PREFETCH_WRITES_PER_INPUT_BEAT * SAMPLE_BYTES
    fields["derived"] = {
        "transaction_cycles": transaction_cycles,
        "load_to_first_output_cycles": first_output - start,
        "first_to_last_output_cycles": last_output - first_output,
        "steady_output_interval_cycles": steady_interval,
        "steady_output_beats_per_cycle": (
            1.0 / steady_interval if steady_interval else 0.0
        ),
        "transaction_output_beats_per_cycle": (
            output_beats / transaction_cycles if transaction_cycles > 0 else 0.0
        ),
        "output_stall_rate": (
            output_stalls / transaction_cycles if transaction_cycles > 0 else 0.0
        ),
        "input_stall_rate": (
            input_stalls / transaction_cycles if transaction_cycles > 0 else 0.0
        ),
        "output_beats_per_second_at_100mhz": (
            output_beats / transaction_cycles * reference_cycles_per_second
            if transaction_cycles > 0
            else 0.0
        ),
        "valid_lane_results": valid_lane_results,
        "valid_lane_results_per_second_at_100mhz": (
            valid_lane_results / transaction_cycles * reference_cycles_per_second
            if transaction_cycles > 0
            else 0.0
        ),
        "stream_tdata_bytes_per_second_at_100mhz": (
            output_beats
            * INPUT_BEAT_BYTES
            / transaction_cycles
            * reference_cycles_per_second
            if transaction_cycles > 0
            else 0.0
        ),
        "valid_output_bytes_per_second_at_100mhz": (
            valid_lane_results
            * SAMPLE_BYTES
            / transaction_cycles
            * reference_cycles_per_second
            if transaction_cycles > 0
            else 0.0
        ),
        "sram_read_bytes": sram_read_bytes,
        "sram_write_bytes": sram_write_bytes,
        "sram_total_bytes": sram_read_bytes + sram_write_bytes,
        "sram_read_bytes_per_valid_lane_result": (
            sram_read_bytes / valid_lane_results if valid_lane_results else 0.0
        ),
        "sram_write_bytes_per_valid_lane_result": (
            sram_write_bytes / valid_lane_results if valid_lane_results else 0.0
        ),
        "sram_total_bytes_per_valid_lane_result": (
            (sram_read_bytes + sram_write_bytes) / valid_lane_results
            if valid_lane_results
            else 0.0
        ),
        "input_fifo_occupancy_fraction": (
            int(fields["input_max_occupancy"]) / FIFO_DEPTH
        ),
        "output_fifo_occupancy_fraction": (
            int(fields["output_max_occupancy"]) / FIFO_DEPTH
        ),
        "transaction_ns_at_100mhz": transaction_cycles * (1000.0 / REFERENCE_CLOCK_MHZ),
        "first_output_ns_at_100mhz": (
            (first_output - start) * (1000.0 / REFERENCE_CLOCK_MHZ)
        ),
    }
    fields["derived"]["transaction_lane_results_per_cycle"] = (
        fields["derived"]["valid_lane_results"] / transaction_cycles
        if transaction_cycles > 0
        else 0.0
    )
    fields["derived"]["stage_cycle_sum"] = stage_cycle_sum
    fields["derived"]["mac_overlap_cycles"] = int(stage["mac_busy_cycles"])
    fields["derived"]["stage_cycle_fraction"] = {
        key: int(stage[key]) / transaction_cycles
        for key in (
            "control_cycles",
            "load_cycles",
            "read_cycles",
            "capture_cycles",
            "submit_cycles",
            "wait_output_cycles",
        )
    }
    fields["derived"]["mac_busy_fraction"] = (
        int(stage["mac_busy_cycles"]) / transaction_cycles
        if transaction_cycles > 0
        else 0.0
    )
    return fields


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT_DEFAULT)
    parser.add_argument("--image", type=Path, default=IMAGE_DEFAULT)
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="per-command simulation timeout in seconds",
    )
    arguments = parser.parse_args()

    suite = find_suite()
    environment = suite_environment(suite)
    iverilog = tool_path("iverilog", suite)
    vvp = tool_path("vvp", suite)
    if not iverilog or not vvp:
        missing = [
            name
            for name, executable in (("iverilog", iverilog), ("vvp", vvp))
            if not executable
        ]
        raise RuntimeError(f"missing RTL tools: {', '.join(missing)}")

    arguments.image = arguments.image.resolve()
    arguments.image.parent.mkdir(parents=True, exist_ok=True)
    vector_command = [sys.executable, "-B", "tools/generate_engine_vectors.py"]
    vector_result = run_command(vector_command, environment, arguments.timeout)
    if vector_result["returncode"] != 0:
        raise RuntimeError(f"vector generation failed: {vector_result['output']}")

    compile_command = [
        str(iverilog),
        "-g2012",
        "-Wall",
        "-s",
        "tb_banked_stencil_performance",
        "-o",
        str(arguments.image),
        *RTL_SOURCES,
    ]
    compile_result = run_command(compile_command, environment, arguments.timeout)
    if compile_result["returncode"] != 0:
        raise RuntimeError(f"performance testbench compile failed: {compile_result['output']}")

    measurements: list[dict[str, object]] = []
    for mode, plusarg in (("nostall", None), ("stress", "+PERF_STRESS")):
        command = [str(vvp), str(arguments.image)]
        if plusarg:
            command.append(plusarg)
        result = run_command(command, environment, arguments.timeout)
        if result["returncode"] != 0:
            raise RuntimeError(f"{mode} performance run failed: {result['output']}")
        measurement = parse_measurement(str(result["output"]))
        if measurement["mode"] != mode:
            raise RuntimeError(
                f"expected mode={mode}, received mode={measurement['mode']}"
            )
        measurement["command"] = command
        measurement["raw_output"] = result["output"]
        measurements.append(measurement)

    report_path = arguments.report
    if not report_path.is_absolute():
        report_path = (ROOT / report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "platform": sys.platform,
        "python": sys.version,
        "cwd": str(ROOT),
        "toolchain": {
            "suite": str(suite) if suite else None,
            "iverilog": str(iverilog),
            "vvp": str(vvp),
        },
        "design": {
            "testbench": "tb_banked_stencil_performance",
            "sources": RTL_SOURCES,
            "clock_period_ns": 10,
            "architecture": {
                "bank_count": 12,
                "lanes": LANES,
            "taps": TAPS,
            "unique_reads_per_issue": UNIQUE_READS_PER_ISSUE,
            "prefetch_writes_per_input_beat": PREFETCH_WRITES_PER_INPUT_BEAT,
            "fifo_depth": FIFO_DEPTH,
            "logical_reads_per_issue": LANES * TAPS,
            "steady_duplicate_read_reduction_fraction": (
                1.0 - UNIQUE_READS_PER_ISSUE / (LANES * TAPS)
            ),
        },
            "reference_clock_mhz": REFERENCE_CLOCK_MHZ,
            "specification_metrics": {
                "input_stream_gbps_at_reference_clock": (
                    REFERENCE_CLOCK_MHZ * INPUT_BEAT_BYTES / 1000.0
                ),
                "output_stream_gbps_at_reference_clock": (
                    REFERENCE_CLOCK_MHZ * INPUT_BEAT_BYTES / 1000.0
                ),
                "sram_read_gbps_at_reference_clock": (
                    REFERENCE_CLOCK_MHZ
                    * UNIQUE_READS_PER_ISSUE
                    * SAMPLE_BYTES
                    / 1000.0
                ),
                "sram_write_gbps_at_reference_clock": (
                    REFERENCE_CLOCK_MHZ
                    * PREFETCH_WRITES_PER_INPUT_BEAT
                    * SAMPLE_BYTES
                    / 1000.0
                ),
                "sram_total_gbps_at_reference_clock": (
                    REFERENCE_CLOCK_MHZ
                    * (UNIQUE_READS_PER_ISSUE + PREFETCH_WRITES_PER_INPUT_BEAT)
                    * SAMPLE_BYTES
                    / 1000.0
                ),
                "mac4_gflops_at_reference_clock": round(
                    REFERENCE_CLOCK_MHZ
                    * LANES
                    * TAPS
                    * REAL_FLOPS_PER_COMPLEX_MAC
                    / 1000.0
                    / TAPS,
                    6,
                ),
                "stencil4_gflops_at_reference_clock": round(
                    REFERENCE_CLOCK_MHZ
                    * LANES
                    * TAPS
                    * REAL_FLOPS_PER_COMPLEX_MAC
                    / 1000.0,
                    6,
                ),
                "logical_reads_per_issue": LANES * TAPS,
                "unique_reads_per_issue": UNIQUE_READS_PER_ISSUE,
                "duplicate_read_reduction_percent": round(
                    100.0
                    * (1.0 - UNIQUE_READS_PER_ISSUE / (LANES * TAPS)),
                    6,
                ),
            },
            "traffic_modes": {
                "nostall": "input valid whenever the source is ready; output always ready",
                "stress": "deterministic LFSR input gaps and output backpressure",
            },
        },
        "commands": {
            "vector_generation": vector_result,
            "compile": compile_result,
        },
        "measurements": measurements,
        "overall": "PASS",
    }
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"report: {report_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"performance measurement: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
