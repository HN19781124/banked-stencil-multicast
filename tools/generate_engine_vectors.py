"""Generate one deterministic end-to-end tile for the integrated RTL engine."""

from __future__ import annotations

import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.complex_mac import complex_stencil_mac, pack_complex


LOGICAL_WIDTH = 17
HEIGHT = 3
PADDED_WIDTH = 24
COEFFICIENTS = (
    pack_complex(0x3800, 0x3400),
    pack_complex(0xBC00, 0x3800),
    pack_complex(0x4000, 0xB400),
)


def _finite_half(generator: random.Random) -> int:
    bits = generator.getrandbits(16)
    if ((bits >> 10) & 0x1F) == 0x1F:
        bits ^= 0x0400
    return bits


def build_tile() -> tuple[list[int], list[int], list[int]]:
    generator = random.Random(0x4E4232454E47494E45)
    rows = [
        [pack_complex(_finite_half(generator), _finite_half(generator)) for _ in range(PADDED_WIDTH)]
        for _ in range(HEIGHT)
    ]
    input_beats = []
    for row in rows:
        for offset in range(0, PADDED_WIDTH, 4):
            input_beats.append(
                sum(row[offset + lane] << (32 * lane) for lane in range(4))
            )

    expected_outputs = []
    expected_flags = []
    for row in rows:
        for issue_x in range(0, LOGICAL_WIDTH, 4):
            outputs, flags = complex_stencil_mac(
                row[issue_x : issue_x + 6],
                COEFFICIENTS,
            )
            expected_outputs.append(
                sum(output << (32 * lane) for lane, output in enumerate(outputs))
            )
            valid_lanes = min(4, LOGICAL_WIDTH - issue_x)
            aggregate = 0
            for lane in range(valid_lanes):
                aggregate |= flags[lane].packed()
            expected_flags.append(aggregate)
    return input_beats, expected_outputs, expected_flags


def write_vectors(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    inputs, outputs, flags = build_tile()
    (directory / "engine_input.mem").write_text(
        "\n".join(f"{value:032x}" for value in inputs) + "\n",
        encoding="ascii",
    )
    (directory / "engine_expected.mem").write_text(
        "\n".join(f"{value:032x}" for value in outputs) + "\n",
        encoding="ascii",
    )
    (directory / "engine_flags.mem").write_text(
        "\n".join(f"{value:x}" for value in flags) + "\n",
        encoding="ascii",
    )
    print(
        f"engine tile vectors: PASS ({len(inputs)} input, {len(outputs)} output beats)"
    )


if __name__ == "__main__":
    write_vectors(ROOT / "build")
