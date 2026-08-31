# External references for energy and data-movement comparison

[日本語（正本）](energy-measurement-references.md) · English · [简体中文](energy-measurement-references.zh-Hans.md)

This note places the repository's hypothesis—reducing window movement and
duplicate transfers can improve energy efficiency—next to published
measurement practice. None of the references is a direct comparison with this
design, and the current RTL has no measured power result.

## Recent primary references

| Reference | Scope | Use here |
|---|---|---|
| [TyTraCL: Optimising Stencil Code on FPGAs by Trading Data Movement for Compute using Compiler Rewrite Rules](https://doi.org/10.1007/s10766-025-00809-z) (2025) | Intel Arria 10 board power, including DRAM, measured with fpgainfo; reports energy-efficiency gains after intermediate-buffer reduction | Example of an FPGA power boundary; not a direct line-buffer comparison |
| [Exploring Efficient FPGA Acceleration of High-Order 3D Iterative Stencil Loops on Large Data Grids](https://doi.org/10.1007/s13369-025-10919-y) (2025) | 25-point 3D stencil and A100 comparison using W/GB/s, including spatial/temporal blocking | Example of a stencil energy metric; do not transplant its absolute values |
| [FlexNPU: a dataflow-aware flexible deep learning accelerator for energy-efficient edge devices](https://doi.org/10.3389/fhpcp.2025.1570210) (2025) | Intel 7 nm test chip and synthesis; separates MAC, storage/movement, and control power and evaluates SRAM-to-PE multicast and double buffering | Example of reporting movement and compute counters separately; DNN, not stencil, results |
| [HiEval: A scheduling performance estimation approach for spatial accelerators via hierarchical abstraction](https://doi.org/10.1016/j.sysarc.2024.103079) (2024) | Hierarchical performance/energy model covering placement, peer forwarding, and parent multicast | Reference for matching read/write/forward/multicast counts before physical measurement |

Background baselines are [Eyeriss](https://doi.org/10.1109/ISCA.2016.40)
(2016), which compares dataflow and local-storage reuse, and
[Horowitz, Computing's Energy Problem](https://doi.org/10.1109/ISSCC.2014.6757323)
(2014), which provides a 45 nm order-of-magnitude comparison for compute,
SRAM, and DRAM. Neither is a process-calibrated value for this repository.

## Conditions for a fair measurement

1. Fix FPGA part, speed grade, voltage, temperature, tool version, seed,
   constraints, bit width, and clock.
2. Use the same dense tile, coefficients, Halo, ready/valid trace, and output
   checks. Do not count preprocessing on only one side.
3. Separate idle, static, clock, BRAM/SRAM, DSP/MAC, routing, and I/O terms;
   report active-minus-idle power and energy per output when possible.
4. Keep board power separate from device estimates. State whether DRAM is
   included, the measurement window, sampling period, and thermal steady state.
5. Claim an advantage only after matched output, toggle activity, Fmax, and
   power conditions are available.

The current evidence stops at 1024 x 1024 output agreement and cycle/access
counts. Power is unmeasured.

## Appendix: first-order unit replication model

The 4 MHz SKY130 exploratory run provides an 11.434 mW anchor for one N=4,
12-bank unit. Under the deliberately ideal model
P(n) = n x (10.582 + 0.852) mW, shared logic, extra routing, external
bandwidth, and inter-unit backpressure are zero. Two units at 22.868 mW are
therefore a first-order extrapolation, not measured power, thermal margin, or
manufacturing sign-off.

| Traffic | Units | Power (mW) | Ideal throughput (Mresult/s) | Energy (nJ/result) | Performance/W (Mresult/s/W) |
|---|---:|---:|---:|---:|---:|
| nostall | 1 | 11.434 | 2.873 | 3.979 | 251.3 |
| nostall | 2 | 22.868 | 5.746 | 3.979 | 251.3 |
| stress | 1 | 11.434 | 2.519 | 4.540 | 220.3 |
| stress | 2 | 22.868 | 5.037 | 4.540 | 220.3 |

Reproduce the estimate with:

~~~shell
python tools/estimate_power_scaling.py --units 1,2 --report physical/evidence/power-scaling-estimate-20260831.json
~~~

The model does not mean that duplicating a single-port unit works
unconditionally. Re-check each unit's read/write bank sets, input partition,
DMA/FIFO contention, and external bandwidth. The 18-bank 1R1W
register-exchange option is a separate candidate.

This is an English companion summary; the Japanese file remains the detailed
source of truth.
