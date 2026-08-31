# ASIC reference comparison: line-buffer vs banked multicast

[日本語（正本）](asic-linebuffer-comparison.md) · English · [简体中文](asic-linebuffer-comparison.zh-Hans.md)

This is a reference-only model for placing the same `N=4`-lane, `M=36`-bank
candidate, 3x3 stencil, and 4-byte complex samples in an ASIC. Here `N` always
denotes lane count and `M` physical SRAM-bank count. It fixes a common input, compute, and
output contract, but does not provide line-buffer RTL, common-PDK place and
route, or technology-calibrated power. The activity counters are not absolute
power measurements.

## Comparison contract

~~~mermaid
flowchart LR
    IN[Common input tile<br/>complex sample] --> LB[Line buffer<br/>3-row SRAM + window registers]
    IN --> BM[Banked multicast<br/>N=4 / M=36-bank candidate]
    LB --> LMAC[Common four-lane complex MAC]
    BM --> BMAC[Common four-lane complex MAC]
    LMAC --> OUT[Common output FIFO / stream]
    BMAC --> OUT
    PDK[Same ASIC PDK / SRAM / clock / voltage / activity] -.-> LB
    PDK -.-> BM
~~~

Both paths must use the same tile, coefficients, FP16 and complex-MAC rules,
ready/valid trace, Halo, output checks, clock, voltage, and temperature. If a
single-port case is compared, the line-buffer path must use the same effective
port budget. A true-dual-port case must report the port count and power for
both paths.

The line-buffer path is intentionally given a no-stall, backpressure-free
upper-bound model, while the banked path retains SRAM load, unique-read,
multicast, and bank-schedule costs. This is a conservative comparison, not a
performance guarantee. A real line-buffer can block or stall on SRAM/BRAM port
conflicts, line or row fill, tail/Halo boundaries, or downstream backpressure.

The numeric rows below are reference upper bounds under that no-stall
assumption. They do not include possible line-buffer stalls or ASIC timing.
When load/compute overlap or repeated passes are used, the banked path also
needs active and prefetch A/B buffers plus Halo capacity; their capacity,
retention power, and routing cost are not hidden in the counters.

## 1024x1024 reference counters

| Metric | line-buffer | banked multicast | Interpretation |
|---|---:|---:|---|
| Output samples | 1,048,576 | 1,048,576 | Common input and compute |
| Storage reads | 2,097,152 (2.000/output) | 4,718,592 (4.500/output) | Reference counter, no-stall upper bound |
| Storage writes | 1,054,728 (1.006/output) | 1,054,728 (1.006/output) | Common input-stream holding |
| Total storage access | 3,151,880 (3.006/output) | 5,773,320 (5.506/output) | Simple read plus write sum |
| Logical window values | 9,437,184 (9.000/output) | 9,437,184 (9.000/output) | Common MAC inputs |
| Multicast deliveries | 0 | 9,437,184 (9.000/output) | Banked fixed-fan-out counter |
| Core cycles | 262,145 | 262,145 | Preloaded, no-stall reference |
| End-to-end cycles | 263,683 | 525,827 (serialized load) | No-stall upper bound; banked overlap limit 263,682 |

The matching output digest and complete counters are preserved in the
[ASIC JSON evidence](../../physical/evidence/asic-dataflow-reference-1024.json)
and reproduced by [the comparison script](../../tools/compare_asic_dataflows.py).

## Power boundary

Absolute power remains unknown until both paths use the same ASIC PDK, SRAM
macro views, clock/activity, voltage, and physical implementation. The
technology-independent symbolic terms are:

    E_LB = R_LB*e_sram_read + W_LB*e_sram_write
          + S_LB*e_window_shift + C*e_common
    E_BM = R_BM*e_sram_read + W_BM*e_sram_write
          + F_BM*e_multicast_fanout + C*e_common

S_LB represents window-register movement and F_BM represents multicast
fan-out. The existing 11.434 mW `N=4`/`M=12` SKY130 exploration is a separate banked
ASIC anchor, not a value for this 2D comparison.

This document is an English companion summary; the Japanese file remains the
detailed source of truth.
