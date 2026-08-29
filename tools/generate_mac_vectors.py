"""Generate deterministic RTL vectors from the bit-exact complex MAC model."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reference.complex_mac import complex_stencil_mac, fp_flags_word, pack_complex


DEFAULT_COUNT = 256


def _pack_words(words: list[int] | tuple[int, ...], width: int) -> int:
    return sum(word << (index * width) for index, word in enumerate(words))


def _directed_vectors() -> list[tuple[list[int], list[int]]]:
    zero = 0x0000
    negative_zero = 0x8000
    one = 0x3C00
    negative_one = 0xBC00
    positive_i = pack_complex(zero, one)
    real_one = pack_complex(one, zero)
    return [
        ([real_one] * 6, [real_one] * 3),
        ([positive_i] * 6, [positive_i] * 3),
        (
            [pack_complex(value, zero) for value in (one, 0x4000, 0x4200, 0x4400, 0x4500, 0x4600)],
            [pack_complex(zero, zero), real_one, pack_complex(zero, zero)],
        ),
        (
            [pack_complex(zero, negative_zero), pack_complex(negative_zero, zero)] * 3,
            [real_one, pack_complex(negative_one, zero), real_one],
        ),
        (
            [pack_complex(value, value) for value in (0x0001, 0x03FF, 0x0400, 0x7BFF, 0x8001, 0xFBFF)],
            [pack_complex(0x3555, 0xB555), pack_complex(0x3C00, 0x3C00), pack_complex(0x0400, 0x0001)],
        ),
        (
            [pack_complex(value, zero) for value in (0x7C00, 0xFC00, 0x7E00, 0x7D00, one, zero)],
            [real_one, pack_complex(zero, one), real_one],
        ),
        (
            [pack_complex(0x7BFF, 0x7BFF)] * 6,
            [pack_complex(0x7BFF, 0x7BFF)] * 3,
        ),
    ]


def _random_half(generator: random.Random) -> int:
    boundary_pool = (
        0x0000,
        0x8000,
        0x0001,
        0x8001,
        0x03FF,
        0x83FF,
        0x0400,
        0x8400,
        0x3C00,
        0xBC00,
        0x7BFF,
        0xFBFF,
        0x7C00,
        0xFC00,
        0x7E00,
        0x7D00,
    )
    if generator.randrange(4) == 0:
        return generator.choice(boundary_pool)
    return generator.getrandbits(16)


def build_vectors(count: int) -> list[tuple[list[int], list[int], tuple[int, ...], int]]:
    if count < len(_directed_vectors()):
        raise ValueError(f"count must be at least {len(_directed_vectors())}")
    generator = random.Random(0x4E42324D4143)
    inputs = _directed_vectors()
    while len(inputs) < count:
        unique = [
            pack_complex(_random_half(generator), _random_half(generator))
            for _ in range(6)
        ]
        coefficients = [
            pack_complex(_random_half(generator), _random_half(generator))
            for _ in range(3)
        ]
        inputs.append((unique, coefficients))

    vectors = []
    for unique, coefficients in inputs:
        outputs, flags = complex_stencil_mac(unique, coefficients)
        vectors.append((unique, coefficients, outputs, fp_flags_word(flags)))
    return vectors


def write_vectors(directory: Path, count: int = DEFAULT_COUNT) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    vectors = build_vectors(count)
    files = {
        "mac_unique.mem": [f"{_pack_words(vector[0], 32):048x}" for vector in vectors],
        "mac_coefficients.mem": [f"{_pack_words(vector[1], 32):024x}" for vector in vectors],
        "mac_expected.mem": [f"{_pack_words(vector[2], 32):032x}" for vector in vectors],
        "mac_flags.mem": [f"{vector[3]:04x}" for vector in vectors],
    }
    for name, lines in files.items():
        (directory / name).write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    arguments = parser.parse_args()
    write_vectors(arguments.output, arguments.count)
    print(f"complex MAC vectors: PASS ({arguments.count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
