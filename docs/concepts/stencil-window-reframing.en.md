# Reframing the Stencil Window

> Japanese source: [stencil-window-reframing.md](stencil-window-reframing.md)<br>
> 简体中文: [stencil-window-reframing.zh-Hans.md](stencil-window-reframing.zh-Hans.md)

This note describes the data-path representation used by the repository's
measured `N=4` baseline. It does not change the stencil equation or claim that
every physical implementation can eliminate line or plane storage. The point
is to separate the logical overlap of neighboring windows from the physical
movement and delivery of their samples.

Here `N` always denotes lane count, `M` physical SRAM-bank count, and `T` tap
count. `N` and `M` are independent design parameters.

## 1. Why the window representation matters

Stencil operators occur in image processing, physical simulation, numerical
computing, and AI accelerators. A conventional materialized-window pipeline
keeps each lane-local window in a sliding, line, or plane buffer. Advancing the
window can then require shifts, alignment muxes, repeated reads, and bank-conflict
scheduling before the MAC stage.

For regular adjacent windows, the overlap is structural rather than new data.
The same input sample can be an operand for several neighboring outputs. The
alternative used here is to keep samples statically addressed in banked SRAM,
read each unique sample once, and multicast that value to every lane that
consumes it.

## 2. Concrete `N=4`, `T=3` example

Four adjacent lanes request the following three-tap windows:

| Lane | Input window |
|---|---|
| 0 | `{s0, s1, s2}` |
| 1 | `{s1, s2, s3}` |
| 2 | `{s2, s3, s4}` |
| 3 | `{s3, s4, s5}` |

The logical request count is `N*T = 12`, but the union contains only

$$
U=N+T-1=4+3-1=6
$$

unique samples. The `N=4`／`M=12` baseline reads those six samples once and
routes them to the four lanes. “No data movement” means no shift or relocation
between SRAM cells; SRAM reads and signal propagation still occur.

## 3. Two data-path representations

### Conventional materialized window

The conceptual sequence is:

`load -> align/shift -> window construction -> MAC`

The buffer state is updated as the window advances. Duplicate sample requests,
lane alignment, and bank-conflict avoidance appear as separate implementation
costs. Line and plane buffers remain valid implementation choices; they are not
being declared universally incorrect.

### Unique-sample multicast

The proposed data path uses:

1. Static placement in single-port banked SRAM; no cell-to-cell shift.
2. One read for each of the `U=N+T-1` unique samples required by the issue.
3. A multicast network that fans each SRAM output out to its consuming lanes.
4. Lane-local reconstruction of the tap operands followed by the MAC stage.

The window membership is therefore encoded by coordinates, bank mapping, and
read order rather than by materializing a shifted window buffer. The runtime
sequence is approximately:

`ordered SRAM read -> multicast -> MAC`

## 4. Representation comparison

```mermaid
flowchart LR
    Q["N=4, T=3 adjacent windows<br/>W0={s0,s1,s2}<br/>W1={s1,s2,s3}<br/>W2={s2,s3,s4}<br/>W3={s3,s4,s5}<br/>logical requests N×T=12"]:::neutral

    Q -->|"materialize windows"| C0
    Q -->|"reframe as a unique set"| R

    subgraph CONV["Conventional: materialized sliding window"]
        direction TB
        C0["sliding / line / plane buffer<br/>more state as dimensions grow"]:::old
        C0 --> C1["shift and realign<br/>extra data movement"]:::old
        C1 --> C2["duplicate reads<br/>same input requested repeatedly"]:::old
        C2 --> C3["bank-conflict avoidance<br/>multi-port or complex scheduling"]:::old
        C3 --> C4["deliver to lanes"]:::old
    end

    R["Representation change<br/>window = unique samples + fan-out"]:::pivot --> U0

    subgraph PROP["Proposed: unique-sample multicast"]
        direction TB
        U0["U={s0,s1,s2,s3,s4,s5}<br/>U=N+T-1=6"]:::new
        U0 --> U1["static banked SRAM<br/>single-port<br/>read each sample once<br/>no cell-to-cell shift"]:::new
        U1 --> U2["multicast network<br/>fan out to consuming lanes"]:::new
        U2 --> U3["Lanes 0…3<br/>receive three taps each"]:::new
        U3 --> U4["y0 y1 y2 y3"]:::new
        U1 -.-> U5["static bank map + phase<br/>pre-check R_t ∩ W_t = ∅"]:::proof
    end

    OUT["12 logical tap references → 6 unique reads<br/>separate overlap, movement, and conflict costs"]:::result
    U0 --> OUT

    classDef neutral fill:#f8fafc,stroke:#64748b,stroke-width:1px;
    classDef old fill:#fff1f2,stroke:#e11d48,stroke-width:1px;
    classDef pivot fill:#f3e8ff,stroke:#9333ea,stroke-width:1px;
    classDef new fill:#eff6ff,stroke:#2563eb,stroke-width:1px;
    classDef proof fill:#fef3c7,stroke:#d97706,stroke-width:1px;
    classDef result fill:#ecfdf5,stroke:#059669,stroke-width:1px;
```

## 5. What the speed figures mean

The figures below describe different observables and are not independent
multipliers.

| Effect | Comparison | Interpretation | Status |
|---|---|---|---|
| Lane utilization | 3 effective lanes/cycle → 4 | `4/3 = 133%` (+33%) ideal lane-rate ratio | Conditional first-order estimate |
| Issue interval | 2 cycles/issue → 1 | `2/1 = 2x` (+100%) steady-state throughput limit | Conditional theoretical upper bound |
| Data representation | `N*T=12` logical tap references → `U=6` physical reads | 50% fewer SRAM reads; each unique sample is reused through multicast | Measured for `N=4` |
| Window-formation front end | `load → align/shift → construction` → ordered read and multicast | Dedicated shift/alignment bubbles can be removed or overlapped | No matched conventional measurement |

The `2x` issue-interval statement assumes the same clock, lane/tap count, I/O
shape, and regular no-stall region, excluding DRAM waits, backpressure,
prologue/epilogue, and tail handling. It compares issue-to-issue spacing, not
zero pipeline latency or end-to-end tile latency. The two-cycle conventional
baseline is not measured in this repository.

The `12 -> 6` result is a physical-read reduction, not an additional `2x`
factor. A matched cycle model is needed before combining front-end savings with
the issue-interval model.

## 6. SRAM-fit bulk/tile partitioning

A large stream can be partitioned into tiles sized for the available SRAM,
bank count, and multicast fan-out. Each tile retains the same local
unique-sample read and multicast structure; only tile boundaries require Halo
exchange.

```mermaid
flowchart LR
    IN["continuous bulk stream"] --> P["bulk/tile partitioner<br/>SRAM capacity, bank count, and fan-out budget"]

    P --> T0["Tile 0<br/>local banked SRAM<br/>unique read → multicast → MAC"]
    P --> T1["Tile 1<br/>local banked SRAM<br/>unique read → multicast → MAC"]
    P --> T2["Tile 2 … Tile K<br/>local banked SRAM<br/>unique read → multicast → MAC"]

    T0 <-->|"Halo / boundary exchange"| T1
    T1 <-->|"Halo / boundary exchange"| T2

    T0 --> O["output merge / next-stage stream"]
    T1 --> O
    T2 --> O

    classDef stream fill:#f8fafc,stroke:#64748b,stroke-width:1px;
    classDef partition fill:#fef3c7,stroke:#d97706,stroke-width:1px;
    classDef tile fill:#eff6ff,stroke:#2563eb,stroke-width:1px;
    classDef output fill:#ecfdf5,stroke:#059669,stroke-width:1px;
    class IN stream;
    class P partition;
    class T0,T1,T2 tile;
    class O output;
```

Partitioning is a scaling option, not a claim that every larger tile is faster.
Halo traffic, DMA behavior, merge latency, fan-out, timing, power, and capacity
are separate design variables.

## 7. Evidence boundary

- The measured baseline is `N=4`／`M=12`: reference, RTL, formal conflict checks,
  generic synthesis, and the documented RTL performance run.
- `N=6` is a first-order design-space estimate.
- `N=16` is a mathematical derivation under `T=3`, single-port SRAM, contiguous
  windows, ping-pong buffering, and a common row: `U=18`, `M=36`, and a phase
  difference of 18. It is not a 16-lane RTL or physical measurement.
- “Fixed latency” means deterministic latency inside a regular on-chip SRAM
  streaming region, excluding external DRAM waits and backpressure.
- Regular 2D/3D tiles can use the same set-based construction algebraically;
  concrete tile geometry, Halo supply, hierarchy, physical timing, and power
  remain outside the measured baseline.

Evidence links: [validation scope](../../VALIDATION.md), [RTL performance
report](../../physical/evidence/RTL-PERFORMANCE-REPORT.md), and [physical
verification report](../../physical/evidence/PHYSICAL-VERIFICATION-REPORT.md).
