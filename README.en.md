# Fixed-Latency 1D Streaming Complex Dataflow Coprocessor

[日本語](README.md) · English · [简体中文](README.zh-Hans.md)

[![DOI: all versions](https://zenodo.org/badge/DOI/10.5281/zenodo.22155033.svg)](https://doi.org/10.5281/zenodo.22155033)

> Defensive publication and executable reference design for conflict-free streaming stencils using single-port banked SRAM, overlap-eliminated reads, fixed multicast delivery, and ping-pong buffering.

This repository documents a **programmable streaming coprocessor outlook** for regular complex-valued local-stencil workloads. It separates the measured N=4 data path from unimplemented scaling and control-plane extensions.

## Status and scope

- **Measured baseline:** N=4 lanes, T=3 taps, M=12 single-port SRAM banks, six unique reads per issue, reference／RTL／formal evidence, and an exploratory SKY130 physical run.
- **Release:** v0.3.0 is an immutable content freeze. It is not a tapeout, production, thermal, or performance sign-off.
- **Fixed latency:** deterministic latency only inside the regular in-SRAM streaming region; external DRAM waits, backpressure, prologue／epilogue, and the unimplemented ROMBASIC layer are excluded.
- **Outlook:** N=6 is a first-order estimate and N=16 is a mathematical derivation target, not a measured implementation.

## Control plane and data plane

The control plane describes the schedule. The data plane keeps samples in statically mapped SRAM banks and multicasts each unique sample to the consuming lanes.

~~~mermaid
flowchart LR
    subgraph CTRL["Control / instruction plane"]
        CPU["CPU / host"]
        ROM["ROMBASIC macro-instruction expansion layer<br/>(future, unimplemented)"]
        CFG["Descriptor / CSR<br/>fixed schedule"]
        CPU --> ROM --> CFG
    end

    subgraph DATA["Data plane"]
        IN["Input stream / DMA boundary"] --> SRAM["Static SRAM<br/>12 banks / single-port"]
        SRAM --> UNIQUE["Unique samples"]
        UNIQUE --> MCAST["Fixed multicast network"]
        MCAST --> MAC["Complex MAC lanes<br/>N=4 baseline"]
        MAC --> OUT["Output FIFO / next stage"]
    end

    CFG -. "window / length / start" .-> SRAM
    CFG -. "instruction sequence / coefficients / valid" .-> MAC
~~~

ROMBASIC is not a general-purpose BASIC interpreter in this description. It is a future control layer that could expand WINDOW／BROADCAST／MAC／STREAM macro-instructions. It is not part of the measured baseline.

## Why the construction targets regular large data

For adjacent lanes and a contiguous T-tap stencil, N*T logical references contain only U=N+T-1 unique samples. The design reads each unique sample once, avoids shifting samples between SRAM cells, and multicasts the value to every consuming lane. A static bank map and compile-time schedule make read/write bank-set disjointness checkable before execution.

The data plane does not require window generation, shifting, write-back, or re-read as mandatory steps. Parallel results can be handed to the output FIFO as a defined beat stream. This is a structural reduction in steady-state operations and cell-to-cell movement, not a speed guarantee; SRAM, multicast, and FIFO costs remain explicit.

The comparison with a line-buffer path is conservative: the line-buffer model is given a no-stall, backpressure-free upper bound, while the banked path retains SRAM-load, unique-read, multicast, and bank-schedule costs. Real line-buffer implementations may block or stall on SRAM／BRAM／SRL port conflicts, line／row fill, tail／Halo boundaries, or downstream backpressure. Therefore the cycle and access figures in the comparison evidence are annotated reference upper bounds, not hardware guarantees.

## Evidence boundary

| Category | Included evidence | Not claimed |
|---|---|---|
| Verified | N=4／M=12 reference／RTL／formal, 64 Python tests, 2D output-digest agreement, input-load bank-uniqueness assertions, complex-MAC vectors, FIFO／CSR／MBIST, exploratory 4 MHz SKY130 run | N=6／N=12／N=16 implementation performance, full-corner timing, production sign-off |
| Estimated | N-way capacity／bandwidth／overlap reduction／endpoint／ideal MAC figures; constrained N=16 candidate | Physical routing delay, measured power, measured area, qualified SRAM margin |
| Unverified | Parameterized N-way RTL／formal, direct-vs-pyramidal multicast, external DMA／NoC, gate-level, board tests, thermal／power effect of idle banks | A product guarantee or a unique optimum |

## Specific space-use target (not evaluated)

One candidate evaluation frame is preprocessing complex I/Q (or equivalent complex samples) received by a low-Earth-orbit satellite before demodulation and decoding. Optical acquisition and tracking, modem selection, FEC／decoding, flight control, propulsion, crew safety, deep-space communications, and spacecraft-wide qualification are out of scope. Neither the measured N=4 baseline nor the 18-bank 1R1W candidate is flight-, radiation-, or thermal-vacuum-qualified. Two-port memory relaxes the access-slot constraint but does not solve SRAM radiation behavior or heat removal by itself.

| Evaluation item | Checks for this target | Current status |
|---|---|---|
| Radiation | TID, SEU／SET／SEL, SRAM bit upset, ECC／parity, scrub period | Not evaluated |
| Thermal-vacuum | Junction temperature, conduction path, thermal cycling, idle-bank effect | No thermal／power model |
| Power and bandwidth | Simultaneous read／write, peak power, idle／gating, W/sample | Port model only |
| Communications quality | BER／FER, EVM, synchronization acquisition, link margin, packet loss, processing latency | Communication／link model not evaluated |
| Determinism | Fixed latency in regular regions, backpressure, DRAM wait, fault／reset recovery | Logic conditions only |
| Fault tolerance and degraded path | Dual-port macro／bank／lane faults, alarm containment, N=4 fallback, serialization, retry, safe halt | Path and switch criteria undefined |
| Physical environment | Vibration, shock, package, EMI／EMC, wiring and power margin | Not evaluated |
| Sign-off | PVT STA, IR／EM, gate-level, radiation and thermal-vacuum tests, target qualification | Out of scope |

~~~mermaid
flowchart LR
    C[18-bank 1R1W candidate<br/>complex I/Q preprocessing] --> R[Radiation]
    C --> T[Thermal-vacuum and power]
    C --> L[BER / EVM / synchronization / link margin]
    C --> D[Determinism and fault recovery]
    C --> P[Vibration / EMI / physical sign-off]
    C --> F{Fault or constraint}
    F --> B[Degrade to N=4 / serialize<br/>or safe halt]
    R --> Q[Target qualification<br/>not performed]
    T --> Q
    L --> Q
    D --> Q
    P --> Q
    B --> Q
~~~

## Reproducible checks

~~~shell
python tools/verify.py
python tools/verify.py --bootstrap --require-rtl
python tools/compare_2d_dataflows.py --width 1024 --height 1024 --report build/2d-dataflow-comparison-1024.json
python tools/compare_asic_dataflows.py --width 1024 --height 1024 --report build/asic-dataflow-comparison.json
~~~

The machine-readable reports preserve the assumptions for the numeric results, including the no-stall line-buffer upper-bound scope. The full Japanese dossier contains the numbered requirements, interfaces, physical-design notes, and appendices.

## Related documents

- [Stencil-window reframing (English)](docs/concepts/stencil-window-reframing.en.md) ／ [简体中文](docs/concepts/stencil-window-reframing.zh-Hans.md) ／ [日本語](docs/concepts/stencil-window-reframing.md)
- [FPGA comparison contract](docs/concepts/fpga-and-simulation-comparison.en.md) ／ [日本語](docs/concepts/fpga-and-simulation-comparison.md) ／ [简体中文](docs/concepts/fpga-and-simulation-comparison.zh-Hans.md)
- [FPGA line-buffer comparison](docs/concepts/fpga-linebuffer-comparison.en.md) ／ [日本語](docs/concepts/fpga-linebuffer-comparison.md) ／ [简体中文](docs/concepts/fpga-linebuffer-comparison.zh-Hans.md)
- [ASIC reference comparison](docs/concepts/asic-linebuffer-comparison.en.md) ／ [日本語](docs/concepts/asic-linebuffer-comparison.md) ／ [简体中文](docs/concepts/asic-linebuffer-comparison.zh-Hans.md)
- [Energy and data-movement references](docs/concepts/energy-measurement-references.en.md) ／ [日本語](docs/concepts/energy-measurement-references.md) ／ [简体中文](docs/concepts/energy-measurement-references.zh-Hans.md)
- [ROMBASIC／GPU integration outlook](docs/concepts/rombasic-gpu-integration.en.md) ／ [日本語](docs/concepts/rombasic-gpu-integration.md) ／ [简体中文](docs/concepts/rombasic-gpu-integration.zh-Hans.md)
- [Design-space exploration](docs/13-design-space-exploration.md)
- [Documentation dossier index](docs/README.en.md)
- [Validation record (English)](VALIDATION.en.md) ／ [日本語](VALIDATION.md) ／ [简体中文](VALIDATION.zh-Hans.md)

The Japanese README.md and numbered docs/ files are the canonical detailed specification. This English file is a separate overview and does not add implementation claims.
