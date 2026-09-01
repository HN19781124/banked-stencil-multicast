"""Generate or check deterministic reference metrics for all applications."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType


APPLICATION_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = APPLICATION_ROOT / "evidence" / "three-application-performance.json"


def _load_module(name: str, path: Path) -> ModuleType:
    """Load a reference module whose parent directory contains a hyphen."""

    reference_root = str(path.parent)
    sys.path.insert(0, reference_root)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load module: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.modules.pop(name, None)
        sys.path.remove(reference_root)


def build_report() -> dict[str, object]:
    """Return deterministic, reference-only metrics for the three applications."""

    clock = _load_module(
        "precision_clock_benchmark",
        APPLICATION_ROOT / "precision-clock" / "reference" / "clock_benchmark.py",
    )
    systolic = _load_module(
        "systolic_array_model",
        APPLICATION_ROOT / "systolic-array" / "reference" / "systolic_model.py",
    )
    tdoa = _load_module(
        "tdoa_sensor_model",
        APPLICATION_ROOT / "tdoa-sensor" / "reference" / "tdoa_model.py",
    )
    return {
        "schema_version": 1,
        "scope": "reference-only",
        "core_reference": {
            "lane_count": 4,
            "tap_count": 3,
            "bank_count": 12,
            "note": "application metrics do not replace core RTL or physical sign-off",
        },
        "applications": [
            clock.run_case().to_dict(),
            systolic.run_case().to_dict(),
            tdoa.run_case().to_dict(),
        ],
    }


def _write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="check an existing report without changing it",
    )
    arguments = parser.parse_args()
    expected = build_report()

    if arguments.check:
        if not arguments.output.is_file():
            print(f"missing report: {arguments.output}")
            return 1
        actual = json.loads(arguments.output.read_text(encoding="utf-8"))
        if actual != expected:
            print(f"report mismatch: {arguments.output}")
            return 1
        print(f"application performance evidence: PASS ({arguments.output})")
        return 0

    _write_report(arguments.output, expected)
    print(f"report: {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
