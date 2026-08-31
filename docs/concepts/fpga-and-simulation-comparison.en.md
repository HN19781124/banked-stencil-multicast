# FPGA applicability and simulation boundary

[日本語（正本）](fpga-and-simulation-comparison.md) · English · [简体中文](fpga-and-simulation-comparison.zh-Hans.md)

This companion note explains what can be checked when the measured `N=4, M=12`
baseline is mapped to an FPGA, and which quantities are suitable for a
same-condition comparison. It is an evaluation plan, not a new measured
result and not part of the v0.3.0 hardware sign-off.

Here `N` is lane count and `M` is physical SRAM-bank count.

## FPGA-visible quantities

The current RTL contains synchronous single-port SRAM behavior, FIFO,
multicast, complex MAC, and AXI-side interfaces. With a fixed target device
and tool flow, the same RTL can expose the following quantities:

~~~mermaid
flowchart LR
    HOST["CPU / host"] --> CTRL["AXI-Lite / control plane"]
    STREAM["AXI-Stream input"] --> ENGINE["N=4 / M=12 engine RTL"]
    CTRL --> ENGINE
    ENGINE --> OUT["AXI-Stream output"]
    ENGINE --> MAP{"FPGA implementation"}
    MAP --> BRAM["BRAM / URAM / M20K"]
    MAP --> DSP["DSP or LUT complex MAC"]
    MAP --> ROUTE["routing / fan-out / timing"]
    BRAM --> REPORT["resource / Fmax / power estimate"]
    DSP --> REPORT
    ROUTE --> REPORT
~~~

| Quantity | FPGA result | Current status |
|---|---|---|
| Logic portability | compile, reset, ready/valid, output match | RTL checked; vendor run not performed |
| Memory inference | block-RAM count, width/depth, read-during-write rule | Device and inference dependent |
| Compute resources | DSP, LUT, FF, multiplier inference | Device dependent |
| Timing | post-implementation Fmax and setup/hold slack | Not measured |
| Throughput | RTL cycle interval converted with an actual clock | Clock not measured |
| Power | vendor estimator or board/device measurement | Not measured |
| External memory | DDR/DMA burst, latency, backpressure | DMA wrapper not implemented |

An FPGA Fmax or power estimate must not be extrapolated directly to SKY130
silicon, production qualification, or another FPGA family. Conversely, an
FPGA mapping failure would not by itself disprove an ASIC macro with different
SRAM, DSP, and routing resources.

## Same-condition simulation contract

The detailed comparison contract is in
[FPGA line-buffer comparison](fpga-linebuffer-comparison.en.md). Both paths
must use the same input tile, coefficients, complex reference arithmetic,
output checks, Halo, and ready/valid trace. The line-buffer model is given a
no-stall, backpressure-free upper bound, while the banked path keeps its
SRAM-load, unique-read, multicast, and bank-schedule costs.

This no-stall condition is a comparison boundary, not a guarantee that a real
line-buffer never blocks. BRAM/SRL port conflicts, line or row fill, tail/Halo
handling, and downstream backpressure can introduce blocking or stall. A/B
buffers and Halo capacity required for overlap or repeated passes are also
real resources and must be reported separately.

~~~mermaid
flowchart TD
    V["same vector / coefficients / tile"]
    V --> A["unique read + multicast"]
    V --> B["lane-local window read"]
    V --> C["shift / line buffer"]
    V --> D["register exchange"]
    A --> M["cycle / access / stall / correctness comparison"]
    B --> M
    C --> M
    D --> M
~~~

Minimum metrics are first-output latency, steady output interval, lane
results per cycle, logical and unique reads, writes, bank conflicts,
multicast fan-out, FIFO occupancy, stall cycles, boundary bubbles, and
bit-exact output/sideband behavior. Simulator wall-clock time is not hardware
speed; compare cycles, then use post-route Fmax for FPGA time.

## Public boundary

- The published baseline is N=4, M=12: reference, RTL, formal checks,
  generic synthesis, and exploratory physical evidence.
- Vendor synthesis, place-and-route, board measurements, external DDR, and a
  line-buffer RTL are separate future evaluation artifacts.
- A large replay can be reproduced with the command
  python tools/compare_2d_dataflows.py --width 1024 --height 1024
- Adding a comparison model must preserve the input contract and must not
  overwrite the baseline numbers.

This is an English companion summary; the Japanese file remains the detailed
source of truth.
