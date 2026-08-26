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
    ]

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
