"""Tests for the bit-exact complex MAC reference model."""

from __future__ import annotations

import random
import struct
import unittest

from reference.complex_mac import (
    BINARY16,
    BINARY32,
    FPFlags,
    complex_stencil_mac,
    convert_bits,
    decode,
    fma_bits,
    pack_complex,
)
from tools.generate_mac_vectors import build_vectors


def half_bits(value: float) -> int:
    return struct.unpack("<H", struct.pack("<e", value))[0]


class ComplexMacTests(unittest.TestCase):
    def test_binary16_promotes_exactly_to_binary32(self) -> None:
        expected = {
            0x0000: 0x00000000,
            0x8000: 0x80000000,
            0x0001: 0x33800000,
            0x03FF: 0x387FC000,
            0x0400: 0x38800000,
            0x3C00: 0x3F800000,
            0xC000: 0xC0000000,
            0x7BFF: 0x477FE000,
            0x7C00: 0x7F800000,
            0xFC00: 0xFF800000,
        }
        for source, target in expected.items():
            with self.subTest(source=f"{source:04x}"):
                converted, flags = convert_bits(source, BINARY16, BINARY32)
                self.assertEqual(target, converted)
                self.assertEqual(FPFlags(), flags)

    def test_binary32_to_binary16_ties_to_even(self) -> None:
        lower_even, flags = convert_bits(0x3F801000, BINARY32, BINARY16)
        upper_even, upper_flags = convert_bits(0x3F803000, BINARY32, BINARY16)
        self.assertEqual(0x3C00, lower_even)
        self.assertEqual(0x3C02, upper_even)
        self.assertTrue(flags.inexact)
        self.assertTrue(upper_flags.inexact)

    def test_binary32_to_binary16_underflow_after_rounding(self) -> None:
        tied_to_zero, flags = convert_bits(0x33000000, BINARY32, BINARY16)
        just_above_tie, above_flags = convert_bits(0x33000001, BINARY32, BINARY16)
        rounded_to_normal, normal_flags = convert_bits(
            0x387FE000,
            BINARY32,
            BINARY16,
        )
        self.assertEqual(0x0000, tied_to_zero)
        self.assertEqual(0x0001, just_above_tie)
        self.assertTrue(flags.underflow and flags.inexact)
        self.assertTrue(above_flags.underflow and above_flags.inexact)
        self.assertEqual(0x0400, rounded_to_normal)
        self.assertTrue(normal_flags.inexact)
        self.assertFalse(normal_flags.underflow)

    def test_binary32_to_binary16_overflow(self) -> None:
        result, flags = convert_bits(0x477FF000, BINARY32, BINARY16)
        self.assertEqual(0x7C00, result)
        self.assertTrue(flags.overflow and flags.inexact)

    def test_nan_conversion_is_canonical_and_signaling_sets_invalid(self) -> None:
        quiet, quiet_flags = convert_bits(0x7FC12345, BINARY32, BINARY16)
        signaling, signaling_flags = convert_bits(0x7FA12345, BINARY32, BINARY16)
        self.assertEqual(0x7E00, quiet)
        self.assertEqual(0x7E00, signaling)
        self.assertFalse(quiet_flags.invalid)
        self.assertTrue(signaling_flags.invalid)

    def test_fma_special_cases_and_signed_zero(self) -> None:
        invalid, invalid_flags = fma_bits(0x7C00, 0x0000, 0)
        cancelled, cancelled_flags = fma_bits(0x3C00, 0x3C00, 0xBF800000)
        negative_zero, zero_flags = fma_bits(0x8000, 0x3C00, 0x80000000)
        self.assertEqual(0x7FC00000, invalid)
        self.assertTrue(invalid_flags.invalid)
        self.assertEqual(0, cancelled)
        self.assertEqual(FPFlags(), cancelled_flags)
        self.assertEqual(0x80000000, negative_zero)
        self.assertEqual(FPFlags(), zero_flags)

    def test_directed_complex_vectors(self) -> None:
        one = half_bits(1.0)
        positive_i = pack_complex(0, one)
        real_one = pack_complex(one, 0)

        outputs, flags = complex_stencil_mac([real_one] * 6, [real_one] * 3)
        self.assertEqual((pack_complex(half_bits(3.0), 0),) * 4, outputs)
        self.assertTrue(all(current == FPFlags() for current in flags))

        outputs, flags = complex_stencil_mac([positive_i] * 6, [positive_i] * 3)
        self.assertEqual((pack_complex(half_bits(-3.0), 0),) * 4, outputs)
        self.assertTrue(all(current == FPFlags() for current in flags))

    def test_lane_windows_use_the_six_unique_samples(self) -> None:
        one = half_bits(1.0)
        zero = pack_complex(0, 0)
        samples = [pack_complex(half_bits(float(index + 1)), 0) for index in range(6)]
        coefficients = [zero, pack_complex(one, 0), zero]
        outputs, _ = complex_stencil_mac(samples, coefficients)
        expected = tuple(pack_complex(half_bits(float(index + 2)), 0) for index in range(4))
        self.assertEqual(expected, outputs)

    def test_random_finite_binary32_to_half_matches_host_conversion(self) -> None:
        generator = random.Random(0x4E4232)
        checked = 0
        while checked < 10000:
            bits = generator.getrandbits(32)
            decoded = decode(bits, BINARY32)
            if decoded.kind not in {"finite", "zero"}:
                continue
            value = struct.unpack("<f", struct.pack("<I", bits))[0]
            if abs(value) > 65519.0:
                continue
            expected = half_bits(value)
            actual, _ = convert_bits(bits, BINARY32, BINARY16)
            self.assertEqual(expected, actual, f"binary32={bits:08x}")
            checked += 1

    def test_rtl_vector_set_is_deterministic_and_class_rich(self) -> None:
        first = build_vectors(32)
        second = build_vectors(32)
        self.assertEqual(first, second)
        self.assertEqual(32, len(first))
        self.assertTrue(any(flags != 0 for _, _, _, flags in first))


if __name__ == "__main__":
    unittest.main()
