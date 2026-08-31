# FPGA comparison: line-buffer and banked multicast

[日本語（正本）](fpga-linebuffer-comparison.md) · English · [简体中文](fpga-linebuffer-comparison.zh-Hans.md)

This companion defines a fair reference comparison for the same 3-tap,
4-lane workload on an FPGA. Here `N` is the lane count and `M` is the physical
SRAM-bank count; the 1D baseline is `N=4, T=3, M=12`. It uses the dense
4-byte complex-sample grid and the 2D reference model; it does not claim that
either path has already been placed and routed on a particular device.

## Two data paths

~~~mermaid
flowchart LR
    IN["same AXI-Stream input<br/>4-byte complex sample"] --> LB
    IN --> BM
    subgraph LB["line-buffer path"]
        LB0["BRAM / SRL row and window storage"]
        LB1["shift / window update"]
        LB2["four-lane MAC"]
        LB0 --> LB1 --> LB2
    end
    subgraph BM["banked multicast path"]
        BM0["static bank placement<br/>M=12-bank baseline"]
        BM1["six unique reads"]
        BM2["fixed multicast"]
        BM3["four-lane MAC"]
        BM0 --> BM1 --> BM2 --> BM3
    end
    LB2 --> OUT["same AXI-Stream output"]
    BM3 --> OUT
~~~

Both paths share the input FIFO, output FIFO, coefficients, FP16 adapter
rules, Halo, boundary policy, and ready/valid trace. A 2D reference candidate
uses 18 unique reads and `M=36`;
that candidate is not an RTL or FPGA measurement.

## Input and implementation contract

Use the same dense row-major W x H grid for both paths. Do not give one path a
pre-expanded window array as hidden preprocessing. Minimum stimulus is the
same-seed impulse, ramp, and finite-random data, with identical coefficients,
padding, valid output coordinates, and sideband.

| Condition | Fixed value |
|---|---|
| Device | FPGA part, speed grade, BRAM/DSP/SRL resources |
| Tool | vendor synthesis/P&R version, seed, retiming |
| Clock | same clock constraint and I/O delay assumptions |
| Workload | N=4, T=3, 4-byte complex samples, same tile/Halo/coefficients |
| Memory | same effective single-port or same true-dual-port budget |
| MAC | same DSP-inference permission; do not mix LUT and DSP cases |
| Checks | bit-exact output, lane mask, TLAST, reset, stall hold |

The line-buffer side is intentionally a no-stall, backpressure-free optimized
upper-bound model. The banked side retains SRAM load, unique-read, multicast,
and bank-schedule costs, so the comparison is conservative against the
proposed path. Real line-buffer hardware may block or stall on BRAM/SRL port
conflicts, line/row fill, tail/Halo boundaries, or downstream backpressure.
A/B buffers and Halo reservation for overlap or repeated passes must also be
counted as BRAM/SRL capacity, retention power, and routing.

## Metrics and interpretation

Measure first-output latency, steady output interval, effective lane
throughput, input bytes per cycle, logical and unique reads, writes, BRAM port
use, LUT/FF/BRAM/SRL/DSP resources, post-route Fmax, fan-out, FIFO occupancy,
stall cycles, and power under identical activity. Compare cycles in simulation;
only post-route Fmax converts them to FPGA time.

The reference replay below has matching output digest and equal core output
rate. It is a no-stall upper bound and excludes Fmax, real time, and any
line-buffer stall.

## 1024 x 1024 reference replay

Input digest:
92f25b9ca748fe02a4d7d14a7fc0df7d36507f6af090dc1f25f175414de39ba9

| Metric | Line-buffer | Banked multicast |
|---|---:|---:|
| Output beats | 262,144 | 262,144 |
| End-to-end cycles | 263,683 | 525,827 (serialized load) |
| Core cycles with preload | 262,145 | 262,145 |
| Load/compute overlap limit | — | 263,682 |

The overlap row is a model limit, not an implemented schedule. A serialized
load is deliberately shown so that the banked path does not hide its loading
cost. The complete conditions and counters are in
[2D JSON evidence](../../physical/evidence/2d-dataflow-comparison-1024.json).

## Current status

Completed: banked `N=4`/`M=12` reference, RTL, formal checks, and the common 2D output
digest/cycle baseline. Not completed: line-buffer RTL, vendor P&R, board
measurement, and a unified FPGA result. Therefore no FPGA speed, area, or
power advantage is claimed.

This is an English companion summary; the Japanese file remains the detailed
source of truth.
