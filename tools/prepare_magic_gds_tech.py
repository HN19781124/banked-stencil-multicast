"""Fetch and materialize a pinned SKY130 GDS-only Magic technology file.

The open_pdks source is a preprocessor template.  This helper materializes the
same ``sky130A-GDS.tech`` form produced by open_pdks without changing the
installed PDK, so a GDS import can be reproduced beside the normal PDK tech.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
COMMIT = "9ca6f00b4360922e095033945f36198060b65086"
OPEN_PDKS_VERSION = "1.0.529"
RAW_URL = (
    "https://raw.githubusercontent.com/fossi-foundation/open-pdks/"
    f"{COMMIT}/sky130/magic/sky130gds.tech"
)
EXPECTED_SOURCE_SHA256 = (
    "60214b3a16e445830782cdaa012a1d8869a3638da34e9b02ed94ace88648f8ae"
)
REVISION = f"{OPEN_PDKS_VERSION}-0-g{COMMIT[:7]}"
CACHE_DIR = ROOT / ".cache" / "open_pdks_gds" / COMMIT
SOURCE_PATH = CACHE_DIR / "sky130gds.tech.in"
TECH_PATH = CACHE_DIR / "sky130A-GDS.tech"
MANIFEST_PATH = CACHE_DIR / "manifest.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_source() -> bytes:
    if SOURCE_PATH.is_file():
        data = SOURCE_PATH.read_bytes()
    else:
        request = Request(RAW_URL, headers={"User-Agent": "neumann-bottleneck2"})
        with urlopen(request, timeout=30) as response:
            data = response.read()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        SOURCE_PATH.write_bytes(data)
    actual = sha256(data)
    if actual != EXPECTED_SOURCE_SHA256:
        raise SystemExit(
            f"unexpected open_pdks source hash: {actual} (expected {EXPECTED_SOURCE_SHA256})"
        )
    return data


def materialize(source: bytes) -> bytes:
    text = source.decode("utf-8")
    output: list[str] = []
    active = [True]
    for line in text.splitlines(keepends=True):
        directive = line.strip()
        if directive == "#ifdef RERAM":
            active.append(False)
            continue
        if directive == "#else":
            if len(active) == 1:
                raise SystemExit("unexpected #else in sky130gds.tech")
            active[-1] = not active[-1]
            continue
        if directive == "#endif":
            if len(active) == 1:
                raise SystemExit("unexpected #endif in sky130gds.tech")
            active.pop()
            continue
        if directive.startswith("#define ") or directive.startswith("#undef "):
            continue
        if all(active):
            line = re.sub(r"\bTECHNAME-GDS\b", "sky130A-GDS", line)
            line = re.sub(r"\bREVISION\b", REVISION, line)
            output.append(line)
    if len(active) != 1:
        raise SystemExit("unterminated conditional in sky130gds.tech")
    data = "".join(output).encode("utf-8")
    if b"TECHNAME" in data or b"REVISION" in data or b"#ifdef" in data:
        raise SystemExit("unmaterialized token remains in generated tech file")
    return data


def main() -> None:
    source = fetch_source()
    generated = materialize(source)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TECH_PATH.write_bytes(generated)
    manifest = {
        "open_pdks_commit": COMMIT,
        "open_pdks_version": OPEN_PDKS_VERSION,
        "source_url": RAW_URL,
        "source_sha256": sha256(source),
        "generated_path": str(TECH_PATH),
        "generated_sha256": sha256(generated),
        "magic_tech": "sky130A-GDS",
        "connectivity_extraction": False,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
