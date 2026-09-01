"""Reference model for a broadcast-fed, weight-stationary PE array."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Sequence


@dataclass(frozen=True)
class SystolicResult:
    """Exact integer result and traffic metrics for one vector tile."""

    lane_count: int
    step_count: int
    outputs: tuple[int, ...]
    mac_operations: int
    unique_input_reads: int
    replicated_input_reads: int
    multicast_deliveries: int
    issue_cycles: int

    @property
    def storage_reads_saved(self) -> int:
        return self.replicated_input_reads - self.unique_input_reads

    @property
    def input_read_reduction_factor(self) -> float:
        return self.replicated_input_reads / self.unique_input_reads

    @property
    def output_digest(self) -> str:
        digest = hashlib.sha256()
        for value in self.outputs:
            digest.update(struct.pack(">q", value))
        return digest.hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {
            "application": "systolic-array",
            "scope": "reference-only",
            "lane_count": self.lane_count,
            "step_count": self.step_count,
            "mac_operations": self.mac_operations,
            "unique_input_reads": self.unique_input_reads,
            "replicated_input_reads": self.replicated_input_reads,
            "storage_reads_saved": self.storage_reads_saved,
            "input_read_reduction_factor": self.input_read_reduction_factor,
            "multicast_deliveries": self.multicast_deliveries,
            "issue_cycles": self.issue_cycles,
            "output_digest": self.output_digest,
        }


def evaluate(
    inputs: Sequence[int], weights: Sequence[Sequence[int]]
) -> SystolicResult:
    """Evaluate one vector tile with one stationary weight row per lane."""

    input_values = tuple(inputs)
    if not input_values:
        raise ValueError("inputs must not be empty")
    if not weights:
        raise ValueError("weights must not be empty")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in input_values):
        raise TypeError("inputs must contain integers")
    weight_rows = tuple(tuple(row) for row in weights)
    if any(len(row) != len(input_values) for row in weight_rows):
        raise ValueError("every weight row must match input length")
    if any(
        isinstance(value, bool) or not isinstance(value, int)
        for row in weight_rows
        for value in row
    ):
        raise TypeError("weights must contain integers")

    outputs = tuple(
        sum(input_value * weight for input_value, weight in zip(input_values, row, strict=True))
        for row in weight_rows
    )
    step_count = len(input_values)
    lane_count = len(weight_rows)
    return SystolicResult(
        lane_count=lane_count,
        step_count=step_count,
        outputs=outputs,
        mac_operations=lane_count * step_count,
        unique_input_reads=step_count,
        replicated_input_reads=lane_count * step_count,
        multicast_deliveries=lane_count * step_count,
        issue_cycles=step_count,
    )


def run_case() -> SystolicResult:
    """Return a deterministic four-lane, sixteen-step reference case."""

    inputs = tuple((step * 7) - 9 for step in range(16))
    weights = tuple(
        tuple((lane + 1) * ((step % 5) - 2) for step in range(16))
        for lane in range(4)
    )
    return evaluate(inputs, weights)
