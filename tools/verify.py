"""Run the repository's reproducible software and RTL checks."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from bootstrap_cad import (
    RELEASE,
    find_suite,
    install,
    suite_environment,
    tool_path,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def run_check(
    name: str,
    command: list[str],
    environment: dict[str, str] | None = None,
) -> dict[str, object]:
    print(f"[{name}] {' '.join(command)}")
    result = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if output:
        print(output)
    status = "PASS" if result.returncode == 0 else "FAIL"
    print(f"[{name}] {status}")
    return {
        "name": name,
        "status": status,
        "returncode": result.returncode,
        "command": command,
        "output": output,
    }


def write_report(path: Path, checks: list[dict[str, object]], suite: Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
        "oss_cad_suite_release": RELEASE if suite else None,
        "oss_cad_suite_path": str(suite) if suite else None,
        "checks": checks,
        "overall": "PASS" if all(check["status"] in ("PASS", "SKIP") for check in checks) else "FAIL",
    }
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"report: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="download the pinned OSS CAD Suite when RTL tools are absent",
    )
    parser.add_argument(
        "--require-rtl",
        action="store_true",
        help="fail instead of skipping when RTL tools are absent",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "verification-report.json",
    )
    arguments = parser.parse_args()

    checks = [
        run_check(
            "python-unit-tests",
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
        ),
        run_check(
            "schedule-reference",
            [sys.executable, "-B", "reference/bank_schedule.py"],
        ),
        run_check(
            "peripheral-schedule",
            [sys.executable, "-B", "-m", "reference.peripheral_schedule"],
        ),
        run_check(
            "2d-dataflow-comparison",
            [
                sys.executable,
                "-B",
                "tools/compare_2d_dataflows.py",
                "--width",
                "64",
                "--height",
                "32",
                "--report",
                "build/2d-dataflow-comparison.json",
            ],
        ),
        run_check(
            "power-scaling-estimate",
            [
                sys.executable,
                "-B",
                "tools/estimate_power_scaling.py",
                "--units",
                "1,2",
                "--report",
                "build/power-scaling-estimate.json",
            ],
        ),
        run_check(
            "asic-dataflow-reference",
            [
                sys.executable,
                "-B",
                "tools/compare_asic_dataflows.py",
                "--width",
                "64",
                "--height",
                "32",
                "--report",
                "build/asic-dataflow-comparison.json",
            ],
        ),
    ]
    vector_check = run_check(
        "complex-mac-vector-generation",
        [sys.executable, "-B", "tools/generate_mac_vectors.py"],
    )
    checks.append(vector_check)
    engine_vector_check = run_check(
        "engine-vector-generation",
        [sys.executable, "-B", "tools/generate_engine_vectors.py"],
    )
    checks.append(engine_vector_check)

    suite = find_suite()
    if not suite and arguments.bootstrap:
        suite = install()
    environment = suite_environment(suite)
    iverilog = tool_path("iverilog", suite)
    vvp = tool_path("vvp", suite)
    yosys = tool_path("yosys", suite)
    rtl_available = bool(iverilog and vvp and yosys)

    if rtl_available:
        build_directory = REPOSITORY_ROOT / "build"
        build_directory.mkdir(parents=True, exist_ok=True)
        simulation_image = build_directory / "bank_scheduler_tb.vvp"
        checks.append(
            run_check(
                "rtl-compile",
                [
                    str(iverilog),
                    "-g2012",
                    "-Wall",
                    "-s",
                    "tb_bank_scheduler",
                    "-o",
                    str(simulation_image),
                    "rtl/bank_scheduler.sv",
                    "rtl/tb_bank_scheduler.sv",
                ],
                environment,
            )
        )
        if checks[-1]["status"] == "PASS":
            checks.append(run_check("rtl-simulation", [str(vvp), str(simulation_image)], environment))
        integration_image = build_directory / "banked_stencil_path_tb.vvp"
        checks.append(
            run_check(
                "integration-rtl-compile",
                [
                    str(iverilog),
                    "-g2012",
                    "-Wall",
                    "-s",
                    "tb_banked_stencil_path",
                    "-o",
                    str(integration_image),
                    "rtl/bank_scheduler.sv",
                    "rtl/stencil_multicast.sv",
                    "rtl/tb_banked_stencil_path.sv",
                ],
                environment,
            )
        )
        if checks[-1]["status"] == "PASS":
            checks.append(
                run_check(
                    "integration-rtl-simulation",
                    [str(vvp), str(integration_image)],
                    environment,
                )
            )
        complex_mac_image = build_directory / "complex_stencil_mac_tb.vvp"
        checks.append(
            run_check(
                "complex-mac-rtl-compile",
                [
                    str(iverilog),
                    "-g2012",
                    "-Wall",
                    "-s",
                    "tb_complex_stencil_mac",
                    "-o",
                    str(complex_mac_image),
                    "rtl/stencil_multicast.sv",
                    "rtl/fp16_fma_accumulator.sv",
                    "rtl/fp32_to_fp16_rne.sv",
                    "rtl/complex_stencil_mac.sv",
                    "rtl/tb_complex_stencil_mac.sv",
                ],
                environment,
            )
        )
        if checks[-1]["status"] == "PASS" and vector_check["status"] == "PASS":
            checks.append(
                run_check(
                    "complex-mac-rtl-simulation",
                    [str(vvp), str(complex_mac_image)],
                    environment,
                )
            )
        axis_fifo_image = build_directory / "axis_fifo_tb.vvp"
        checks.append(
            run_check(
                "axis-fifo-rtl-compile",
                [
                    str(iverilog), "-g2012", "-Wall", "-s", "tb_axis_fifo",
                    "-o", str(axis_fifo_image),
                    "rtl/axis_fifo.sv", "rtl/tb_axis_fifo.sv",
                ],
                environment,
            )
        )
        if checks[-1]["status"] == "PASS":
            checks.append(
                run_check(
                    "axis-fifo-rtl-simulation",
                    [str(vvp), str(axis_fifo_image)],
                    environment,
                )
            )
        csr_image = build_directory / "axi_lite_csr_tb.vvp"
        checks.append(
            run_check(
                "axi-lite-csr-rtl-compile",
                [
                    str(iverilog), "-g2012", "-Wall", "-s", "tb_axi_lite_csr",
                    "-o", str(csr_image),
                    "rtl/axi_lite_csr.sv", "rtl/tb_axi_lite_csr.sv",
                ],
                environment,
            )
        )
        if checks[-1]["status"] == "PASS":
            checks.append(
                run_check(
                    "axi-lite-csr-rtl-simulation",
                    [str(vvp), str(csr_image)],
                    environment,
                )
            )
        mbist_image = build_directory / "sram_mbist_tb.vvp"
        checks.append(
            run_check(
                "sram-mbist-rtl-compile",
                [
                    str(iverilog), "-g2012", "-Wall", "-s", "tb_sram_mbist",
                    "-o", str(mbist_image),
                    "rtl/single_port_sram.sv", "rtl/sram_mbist.sv",
                    "rtl/tb_sram_mbist.sv",
                ],
                environment,
            )
        )
        if checks[-1]["status"] == "PASS":
            checks.append(
                run_check(
                    "sram-mbist-rtl-simulation",
                    [str(vvp), str(mbist_image)],
                    environment,
                )
            )
        product_sources = [
            "rtl/reset_synchronizer.sv",
            "rtl/axis_fifo.sv",
            "rtl/axi_lite_csr.sv",
            "rtl/bank_scheduler.sv",
            "rtl/single_port_sram.sv",
            "rtl/sram_mbist.sv",
            "rtl/stencil_multicast.sv",
            "rtl/fp16_fma_accumulator.sv",
            "rtl/fp32_to_fp16_rne.sv",
            "rtl/complex_stencil_mac.sv",
            "rtl/banked_stencil_engine.sv",
        ]
        engine_image = build_directory / "banked_stencil_engine_tb.vvp"
        checks.append(
            run_check(
                "engine-rtl-compile",
                [
                    str(iverilog), "-g2012", "-Wall", "-s",
                    "tb_banked_stencil_engine", "-o", str(engine_image),
                    *product_sources[1:], "rtl/tb_banked_stencil_engine.sv",
                ],
                environment,
            )
        )
        if checks[-1]["status"] == "PASS" and engine_vector_check["status"] == "PASS":
            checks.append(
                run_check(
                    "engine-rtl-simulation",
                    [str(vvp), str(engine_image)],
                    environment,
                )
            )
        product_image = build_directory / "banked_stencil_accelerator_tb.vvp"
        checks.append(
            run_check(
                "product-rtl-compile",
                [
                    str(iverilog), "-g2012", "-Wall", "-s",
                    "tb_banked_stencil_accelerator", "-o", str(product_image),
                    *product_sources, "rtl/banked_stencil_accelerator.sv",
                    "rtl/tb_banked_stencil_accelerator.sv",
                ],
                environment,
            )
        )
        if checks[-1]["status"] == "PASS" and engine_vector_check["status"] == "PASS":
            checks.append(
                run_check(
                    "product-rtl-simulation",
                    [str(vvp), str(product_image)],
                    environment,
                )
            )
        checks.append(
            run_check(
                "yosys-formal-and-synthesis",
                [
                    str(yosys),
                    "-p",
                    (
                        "read_verilog -sv rtl/bank_scheduler.sv; "
                        "prep -top bank_scheduler; check; stat; "
                        "sat -verify -prove conflict_o 0 -set-def-inputs"
                    ),
                ],
                environment,
            )
        )
        checks.append(
            run_check(
                "yosys-multicast-synthesis",
                [
                    str(yosys),
                    "-p",
                    (
                        "read_verilog -sv rtl/stencil_multicast.sv; "
                        "prep -top stencil_multicast; check; stat"
                    ),
                ],
                environment,
            )
        )
        checks.append(
            run_check(
                "yosys-complex-mac-synthesis",
                [
                    str(yosys),
                    "-p",
                    (
                        "read_verilog -sv rtl/fp16_fma_accumulator.sv "
                        "rtl/fp32_to_fp16_rne.sv rtl/complex_stencil_mac.sv; "
                        "prep -top complex_stencil_mac; check; stat"
                    ),
                ],
                environment,
            )
        )
        top_log = build_directory / "top-synthesis-check.log"
        top_check = run_check(
            "yosys-product-structural-synthesis",
            [
                str(yosys),
                "-q",
                "-l",
                str(top_log),
                "-p",
                (
                    "read_verilog -sv "
                    + " ".join(product_sources)
                    + " rtl/banked_stencil_accelerator.sv; "
                    "prep -top banked_stencil_accelerator; check; stat"
                ),
            ],
            environment,
        )
        prohibited = ("Latch inferred", "multiple conflicting drivers", "logic loop")
        if any(pattern in str(top_check["output"]) for pattern in prohibited):
            top_check["status"] = "FAIL"
            top_check["returncode"] = 1
        checks.append(top_check)
    else:
        status = "FAIL" if arguments.require_rtl or arguments.bootstrap else "SKIP"
        missing = [
            name
            for name, executable in (("iverilog", iverilog), ("vvp", vvp), ("yosys", yosys))
            if not executable
        ]
        print(f"[rtl-toolchain] {status}: missing {', '.join(missing)}")
        checks.append(
            {
                "name": "rtl-toolchain",
                "status": status,
                "returncode": 1 if status == "FAIL" else 0,
                "command": [],
                "output": f"missing: {', '.join(missing)}",
            }
        )

    report_path = arguments.report
    if not report_path.is_absolute():
        report_path = (REPOSITORY_ROOT / report_path).resolve()
    write_report(report_path, checks, suite)
    return 0 if all(check["status"] in ("PASS", "SKIP") for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
