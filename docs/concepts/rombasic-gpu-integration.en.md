# ROMBASIC and GPU integration outlook

[日本語（正本）](rombasic-gpu-integration.md) · English · [简体中文](rombasic-gpu-integration.zh-Hans.md)

> This is a future integration note. It is not part of the measured
> `N=4`/`M=12` baseline, the v0.3.0 sign-off, or a performance guarantee.

## Why a BASIC-like control description

BASIC is used here as a compact sequential reference and control notation, not
as a claim that a BASIC interpreter is a fast data path. Its loops,
assignments, branches, and fallback behavior provide a CPU-side golden path
from which a regular array/window operation can be delegated to a stream
engine.

- Sequential meaning stays available for reference, exceptions, and
  unsupported operations.
- The control plane can describe buffers, coefficients, ranges, and launch
  conditions without placing a branch on every data sample.
- A loop body can be expanded into an instruction-memory stream rather than
  interpreted for every element.

## ROMBASIC macro-instruction expansion layer

ROMBASIC is defined here as a ROMBASIC macro-instruction expansion layer. It
could expand WINDOW, BROADCAST, MAC, STREAM_IN, STREAM_OUT, and WAIT operations
into a descriptor or instruction sequence while keeping CPU fallback for
branches and exceptions. The layer is unimplemented and does not contribute
to current N=4 measurements.

~~~basic
FOR x = 0 TO W - 1 STEP 4
  y = STENCIL3(WINDOW(x), COEFF)
  STREAM_OUT y
NEXT x
~~~

~~~mermaid
flowchart LR
    SRC["BASIC source"]
    CPU["CPU process / runtime"]
    REF["sequential reference path"]
    ROM["ROMBASIC expansion<br/>loop / window / stream ops"]
    IMEM["instruction memory<br/>execution stream"]
    ACC["ASIC / GPU stream layer"]
    SRAM["banked SRAM / shared memory"]
    OUT["stream output"]
    SRC --> REF
    SRC --> ROM
    CPU -->|"program / buffer / parameters"| ROM
    ROM --> IMEM
    IMEM --> ACC
    SRAM <--> ACC
    ACC --> OUT
    ACC -. unsupported branch / exception .-> REF
    REF -. verification / fallback .-> CPU
~~~

The intended split is:

| Layer | Role |
|---|---|
| BASIC sequential path | reference semantics, branch, exception, fallback |
| ROMBASIC expansion | loop, window, multicast, and stream description |
| ASIC/GPU execution layer | parallel execution of the expanded stream |

## GPU integration contract

An integration would connect replicated 1D units to an existing GPU execution
layer rather than require a new GPU programming API. The repository fixes the
sequential meaning, abstract WINDOW/BROADCAST/MAC/stream behavior, buffer and
coefficient descriptors, and start/completion/error synchronization. The GPU
implementation chooses command format, driver, lane/warp mapping, occupancy,
cache/shared-memory path, and DMA.

The three evaluation tiers are only architectural reference points:

| Tier | Possible mapping | Main question |
|---|---|---|
| Flagship | several units per SM/CU cluster with HBM or large shared memory | bandwidth and replication ceiling |
| Mid-range | one to several units per cluster with shared dispatch/local SRAM | balance of effective throughput and area |
| Entry | one shared unit or a small CPU/GPU buffer | minimum useful configuration and launch cost |

For a unit count U, output rate R, operations per output O, and clock f, the
ideal compute ceiling is P_peak = U x R x O x f. Effective performance must
also include memory bandwidth, instruction supply, occupancy, and stalls.

For the same illustrative kernel (complex FP16, 3 taps, 24 FLOP/output, and
10 byte/output after overlap elimination), arithmetic intensity is 2.4
FLOP/byte. A 2026-08-29 GeForce snapshot gives the following bandwidth
ceilings; these are not measurements of this RTL:

| Tier | Representative GPU | Bandwidth | Bandwidth roofline | MAC-4 ratio | STENCIL-4 ratio |
|---|---|---:|---:|---:|---:|
| Flagship | RTX 5090 | 1.792 TB/s | 4.30 TFLOP/s | about 1,344x | about 448x |
| Mid-range | RTX 5070 | 672 GB/s | 1.61 TFLOP/s | about 504x | about 168x |
| Entry | RTX 5060 | 448 GB/s | 1.08 TFLOP/s | about 336x | about 112x |

The comparison target is therefore a regularized front-end or helper that
reduces duplicate global-memory reads, not replacement of a whole GPU. A
benefit requires matched-kernel measurements of movement, effective
bandwidth, power, and launch overhead.

## Exploratory appendix

Self-attention redistribution, vertical/horizontal/recursive feedback, and
arbitrary N-way expansion are retained as ideas only. They require explicit
exchange, reduction, softmax, timing, fan-out, SRAM-capacity, and power
validation; they do not imply one-cycle completion or convergence.

This is an English companion summary; the Japanese file remains the detailed
source of truth.
