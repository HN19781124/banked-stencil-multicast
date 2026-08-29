"""Fetch and verify the pinned open SKY130 SRAM macro dependency."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / ".cache" / "sky130_sram_macros"
REPOSITORY = "https://github.com/VLSIDA/sky130_sram_macros.git"
COMMIT = "965df150c754fe2b3f93a0bd1f9883eb114279b2"
MACRO = DESTINATION / "sky130_sram_2kbyte_1rw1r_32x512_8"
EXPECTED = {
    "sky130_sram_2kbyte_1rw1r_32x512_8.gds": "d32efcfe8079379f94070bcbcedad7f1239e27f8996eb184141840e31c9302b2",
    "sky130_sram_2kbyte_1rw1r_32x512_8.lef": "b72c74f3a466abf48dfc57af53eb7ac18f19c071a57ece91ccdd3e6e692230b4",
    "sky130_sram_2kbyte_1rw1r_32x512_8_TT_1p8V_25C.lib": "3e0102b541b03f32ae1170ea33e968734333130a0307b7b9f002912b7f10c380",
    "sky130_sram_2kbyte_1rw1r_32x512_8.lvs.sp": "7fdb4d4ee1d3217ffcd4b05b2ebe03e4961b4106ccb2a64973cf6fafcd3bec6d",
}


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    if not (DESTINATION / ".git").is_dir():
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", REPOSITORY, str(DESTINATION))
    run("git", "-C", str(DESTINATION), "fetch", "origin", COMMIT, "--depth", "1")
    run("git", "-C", str(DESTINATION), "checkout", "--detach", COMMIT)
    actual_commit = subprocess.check_output(
        ["git", "-C", str(DESTINATION), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual_commit != COMMIT:
        raise SystemExit(f"unexpected SRAM commit: {actual_commit}")
    for name, expected_digest in EXPECTED.items():
        path = MACRO / name
        actual_digest = digest(path)
        if actual_digest != expected_digest:
            raise SystemExit(f"SHA-256 mismatch for {name}: {actual_digest}")
    print("pinned SKY130 SRAM views: PASS")


if __name__ == "__main__":
    main()
