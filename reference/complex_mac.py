"""Bit-exact IEEE-754 model for the four-lane complex stencil MAC.

The model deliberately uses integer arithmetic and :class:`fractions.Fraction`
instead of the host floating-point implementation.  This keeps rounding and
exception behavior reproducible on every supported Python host.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence


@dataclass(frozen=True)
class BinaryFormat:
    exponent_bits: int
    fraction_bits: int

    @property
    def bias(self) -> int:
        return (1 << (self.exponent_bits - 1)) - 1

    @property
    def exponent_max(self) -> int:
        return self.bias

    @property
    def exponent_min(self) -> int:
        return 1 - self.bias

    @property
    def exponent_mask(self) -> int:
        return (1 << self.exponent_bits) - 1

    @property
    def sign_shift(self) -> int:
        return self.exponent_bits + self.fraction_bits


BINARY16 = BinaryFormat(exponent_bits=5, fraction_bits=10)
BINARY32 = BinaryFormat(exponent_bits=8, fraction_bits=23)


@dataclass(frozen=True)
class FPFlags:
    """IEEE exception flags used by the block (DZ is intentionally absent)."""

    invalid: bool = False
    overflow: bool = False
    underflow: bool = False
    inexact: bool = False

    def __or__(self, other: "FPFlags") -> "FPFlags":
        return FPFlags(
            invalid=self.invalid or other.invalid,
            overflow=self.overflow or other.overflow,
            underflow=self.underflow or other.underflow,
            inexact=self.inexact or other.inexact,
        )

    def packed(self) -> int:
        """Return ``{NV, OF, UF, NX}`` in bits ``[3:0]``."""

        return (
            (int(self.invalid) << 3)
            | (int(self.overflow) << 2)
            | (int(self.underflow) << 1)
            | int(self.inexact)
        )


@dataclass(frozen=True)
class DecodedFloat:
    kind: str
    sign: int
    value: Fraction | None = None
    signaling: bool = False


def _canonical_nan(fmt: BinaryFormat) -> int:
    quiet_bit = 1 << (fmt.fraction_bits - 1)
    return (fmt.exponent_mask << fmt.fraction_bits) | quiet_bit


def _infinity(sign: int, fmt: BinaryFormat) -> int:
    return (sign << fmt.sign_shift) | (fmt.exponent_mask << fmt.fraction_bits)


def decode(bits: int, fmt: BinaryFormat) -> DecodedFloat:
    sign = (bits >> fmt.sign_shift) & 1
    exponent = (bits >> fmt.fraction_bits) & fmt.exponent_mask
    fraction = bits & ((1 << fmt.fraction_bits) - 1)

    if exponent == fmt.exponent_mask:
        if fraction == 0:
            return DecodedFloat("infinity", sign)
        quiet = bool(fraction & (1 << (fmt.fraction_bits - 1)))
        return DecodedFloat("nan", sign, signaling=not quiet)

    if exponent == 0:
        if fraction == 0:
            return DecodedFloat("zero", sign, Fraction(0))
        significand = fraction
        scale = fmt.exponent_min - fmt.fraction_bits
    else:
        significand = (1 << fmt.fraction_bits) | fraction
        scale = exponent - fmt.bias - fmt.fraction_bits

    if scale >= 0:
        magnitude = Fraction(significand << scale)
    else:
        magnitude = Fraction(significand, 1 << -scale)
    return DecodedFloat("finite", sign, -magnitude if sign else magnitude)


def _floor_log2(value: Fraction) -> int:
    if value <= 0:
        raise ValueError("log2 input must be positive")
    numerator = value.numerator
    denominator = value.denominator
    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        if numerator < (denominator << exponent):
            exponent -= 1
    elif (numerator << -exponent) < denominator:
        exponent -= 1
    return exponent


def _round_scaled(value: Fraction, unit_exponent: int) -> tuple[int, bool]:
    """Round ``value / 2**unit_exponent`` to nearest, ties to even."""

    numerator = value.numerator
    denominator = value.denominator
    if unit_exponent >= 0:
        denominator <<= unit_exponent
    else:
        numerator <<= -unit_exponent

    quotient, remainder = divmod(numerator, denominator)
    inexact = remainder != 0
    doubled = remainder << 1
    if doubled > denominator or (doubled == denominator and (quotient & 1)):
        quotient += 1
    return quotient, inexact


def encode_fraction(
    value: Fraction,
    fmt: BinaryFormat,
    *,
    zero_sign: int = 0,
) -> tuple[int, FPFlags]:
    """Round an exact finite value into ``fmt`` using roundTiesToEven."""

    if value == 0:
        return zero_sign << fmt.sign_shift, FPFlags()

    sign = int(value < 0)
    magnitude = abs(value)
    exponent = _floor_log2(magnitude)

    if exponent >= fmt.exponent_min:
        significand, inexact = _round_scaled(
            magnitude,
            exponent - fmt.fraction_bits,
        )
        if significand == (1 << (fmt.fraction_bits + 1)):
            significand >>= 1
            exponent += 1
        if exponent > fmt.exponent_max:
            return _infinity(sign, fmt), FPFlags(overflow=True, inexact=True)
        exponent_field = exponent + fmt.bias
        fraction_field = significand - (1 << fmt.fraction_bits)
    else:
        significand, inexact = _round_scaled(
            magnitude,
            fmt.exponent_min - fmt.fraction_bits,
        )
        if significand >= (1 << fmt.fraction_bits):
            exponent_field = 1
            fraction_field = 0
        else:
            exponent_field = 0
            fraction_field = significand

    bits = (
        (sign << fmt.sign_shift)
        | (exponent_field << fmt.fraction_bits)
        | fraction_field
    )
    tiny_after_rounding = exponent_field == 0
    return bits, FPFlags(
        underflow=tiny_after_rounding and inexact,
        inexact=inexact,
    )


def convert_bits(
    bits: int,
    source: BinaryFormat,
    target: BinaryFormat,
) -> tuple[int, FPFlags]:
    decoded = decode(bits, source)
    if decoded.kind == "nan":
        return _canonical_nan(target), FPFlags(invalid=decoded.signaling)
    if decoded.kind == "infinity":
        return _infinity(decoded.sign, target), FPFlags()
    if decoded.kind == "zero":
        return decoded.sign << target.sign_shift, FPFlags()
    assert decoded.value is not None
    return encode_fraction(decoded.value, target)


def fma_bits(
    multiplicand_bits: int,
    multiplier_bits: int,
    accumulator_bits: int,
) -> tuple[int, FPFlags]:
    """Compute binary32 ``fma(binary16, binary16, binary32)`` exactly."""

    multiplicand = decode(multiplicand_bits, BINARY16)
    multiplier = decode(multiplier_bits, BINARY16)
    accumulator = decode(accumulator_bits, BINARY32)
    operands = (multiplicand, multiplier, accumulator)

    if any(operand.kind == "nan" for operand in operands):
        invalid = any(
            operand.kind == "nan" and operand.signaling for operand in operands
        )
        return _canonical_nan(BINARY32), FPFlags(invalid=invalid)

    product_sign = multiplicand.sign ^ multiplier.sign
    product_is_zero = multiplicand.kind == "zero" or multiplier.kind == "zero"
    product_is_infinite = (
        multiplicand.kind == "infinity" or multiplier.kind == "infinity"
    )

    if product_is_infinite and product_is_zero:
        return _canonical_nan(BINARY32), FPFlags(invalid=True)

    if product_is_infinite:
        if accumulator.kind == "infinity" and accumulator.sign != product_sign:
            return _canonical_nan(BINARY32), FPFlags(invalid=True)
        return _infinity(product_sign, BINARY32), FPFlags()

    if accumulator.kind == "infinity":
        return _infinity(accumulator.sign, BINARY32), FPFlags()

    multiplicand_value = multiplicand.value or Fraction(0)
    multiplier_value = multiplier.value or Fraction(0)
    accumulator_value = accumulator.value or Fraction(0)
    exact = multiplicand_value * multiplier_value + accumulator_value

    zero_sign = 0
    if exact == 0 and product_is_zero and accumulator.kind == "zero":
        zero_sign = product_sign if product_sign == accumulator.sign else 0
    return encode_fraction(exact, BINARY32, zero_sign=zero_sign)


def unpack_complex(sample: int) -> tuple[int, int]:
    return sample & 0xFFFF, (sample >> 16) & 0xFFFF


def pack_complex(real: int, imaginary: int) -> int:
    return (imaginary << 16) | real


def _or_flags(flags: Iterable[FPFlags]) -> FPFlags:
    result = FPFlags()
    for current in flags:
        result = result | current
    return result


def complex_stencil_mac(
    unique_samples: Sequence[int],
    coefficients: Sequence[int],
) -> tuple[tuple[int, ...], tuple[FPFlags, ...]]:
    """Evaluate four adjacent three-tap complex windows.

    ``unique_samples`` contains the six values read once from SRAM.  Lane ``j``
    consumes elements ``j`` through ``j + 2``.  Results are packed exactly as
    the RTL and AXI specification: real in bits 15:0, imaginary in bits 31:16.
    """

    if len(unique_samples) != 6:
        raise ValueError("exactly six unique samples are required")
    if len(coefficients) != 3:
        raise ValueError("exactly three coefficients are required")

    outputs: list[int] = []
    lane_flags: list[FPFlags] = []
    for lane in range(4):
        real_accumulator = 0
        imaginary_accumulator = 0
        flags: list[FPFlags] = []
        for tap in range(3):
            real, imaginary = unpack_complex(unique_samples[lane + tap])
            coefficient_real, coefficient_imaginary = unpack_complex(
                coefficients[tap]
            )

            real_accumulator, current = fma_bits(
                real,
                coefficient_real,
                real_accumulator,
            )
            flags.append(current)
            real_accumulator, current = fma_bits(
                imaginary ^ 0x8000,
                coefficient_imaginary,
                real_accumulator,
            )
            flags.append(current)
            imaginary_accumulator, current = fma_bits(
                real,
                coefficient_imaginary,
                imaginary_accumulator,
            )
            flags.append(current)
            imaginary_accumulator, current = fma_bits(
                imaginary,
                coefficient_real,
                imaginary_accumulator,
            )
            flags.append(current)

        result_real, current = convert_bits(
            real_accumulator,
            BINARY32,
            BINARY16,
        )
        flags.append(current)
        result_imaginary, current = convert_bits(
            imaginary_accumulator,
            BINARY32,
            BINARY16,
        )
        flags.append(current)
        outputs.append(pack_complex(result_real, result_imaginary))
        lane_flags.append(_or_flags(flags))

    return tuple(outputs), tuple(lane_flags)


def fp_flags_word(flags: Sequence[FPFlags]) -> int:
    """Pack four lane-local flag nibbles, lane 0 in bits 3:0."""

    if len(flags) != 4:
        raise ValueError("exactly four lane flag sets are required")
    return sum(current.packed() << (4 * lane) for lane, current in enumerate(flags))
