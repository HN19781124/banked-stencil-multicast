"""Tests for the common 2D line-buffer/multicast comparison model."""

from __future__ import annotations

import unittest

from reference.two_d_dataflow import (
    DEFAULT_KERNEL,
    TileSpec,
    compare_dataflows,
    generate_tile,
    reference_outputs,
    simulate_banked_multicast,
    simulate_line_buffer,
)


class TwoDDataflowTests(unittest.TestCase):
    def test_common_tile_contract(self) -> None:
        spec = TileSpec(logical_width=8, logical_height=6)
        self.assertEqual(10, spec.input_width)
        self.assertEqual(12, spec.stream_width)
        self.assertEqual(8, spec.input_height)
        self.assertEqual(24, spec.input_beats)
        self.assertEqual(12, spec.output_beats)

    def test_generated_tile_is_deterministic_and_padded(self) -> None:
        spec = TileSpec(logical_width=8, logical_height=4)
        first = generate_tile(spec, seed=12345)
        second = generate_tile(spec, seed=12345)
        self.assertEqual(first, second)
        self.assertTrue(all(sample == (0, 0) for sample in first[0][10:]))

    def test_both_dataflows_match_common_reference(self) -> None:
        spec = TileSpec(logical_width=12, logical_height=8)
        result = compare_dataflows(spec, seed=0x12345678)
        self.assertTrue(result["comparison"]["outputs_equal"])
        self.assertEqual(
            result["line_buffer"]["output_digest"],
            result["banked_multicast"]["output_digest"],
        )

    def test_models_match_for_small_tile(self) -> None:
        spec = TileSpec(logical_width=4, logical_height=2)
        grid = generate_tile(spec, seed=0x10203040)
        expected = reference_outputs(grid, spec, DEFAULT_KERNEL)
        line_buffer = simulate_line_buffer(grid, spec)
        banked = simulate_banked_multicast(grid, spec)
        self.assertEqual(expected, line_buffer.outputs)
        self.assertEqual(expected, banked.outputs)
        self.assertEqual(line_buffer.outputs, banked.outputs)

    def test_width_must_be_lane_aligned(self) -> None:
        with self.assertRaises(ValueError):
            TileSpec(logical_width=5, logical_height=4)

    def test_banked_model_requires_enough_banks(self) -> None:
        spec = TileSpec(logical_width=8, logical_height=4)
        grid = generate_tile(spec)
        with self.assertRaises(ValueError):
            simulate_banked_multicast(grid, spec, bank_count=17)


if __name__ == "__main__":
    unittest.main()
