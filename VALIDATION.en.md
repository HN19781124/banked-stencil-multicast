# Validation summary

[日本語（正本）](VALIDATION.md) · English · [简体中文](VALIDATION.zh-Hans.md)

The surrounding functions and physical-flow checks were replayed against the
initial bank-scheduler disclosure. Here `N` denotes lane count and `M` physical
SRAM-bank count; “12-bank / 4-lane” means `N=4, M=12`. Each PASS applies only to the boundary in
the table; manufacturing sign-off authority remains
[docs/07-verification-and-signoff.md](docs/07-verification-and-signoff.md).

| Item | Method | Status |
|---|---|---|
| Row edges, Halo, and partial lanes | Reference model over widths 1–257, every issue, and both buffer directions | Complete |
| Simultaneous access across rows | Reference phase compensation for every row pair; transition bubble fixed for the initial product | Reference complete／controller not implemented |
| SRAM read latency and multicast RTL | Cycle-accurate simulation of 12 synchronous single-port SRAM models and 6-to-4x3 multicast | Complete |
| Complex MAC and FP16 rules | Bit-exact reference, 256-vector RTL, and product RTL | Complete (RTL)／gate-level not run |
| Input load and FIFO safety | Simulation-only bank assertions at the STATE_LOAD FIFO boundary, occupancy／underflow／overflow checks, and 18 accepted input beats | Complete for baseline RTL; external DMA／CDC out of scope |
| 2D dataflow comparison | Common dense complex tile, 3x3 stencil, output digest, cycle／bandwidth indicators; 1024x1024 digest match | Complete at reference level; FPGA RTL／P&R not run ([evidence](physical/evidence/2d-dataflow-comparison-1024.json)) |
| ASIC reference comparison | Common-input line-buffer／banked-multicast activity counters and technology-calibrated power boundary | Reference only; no absolute power, line-buffer RTL, or P&R ([evidence](physical/evidence/asic-dataflow-reference-1024.json)) |
| DMA and backpressure | FIFO／engine／product randomized path | Partial; external DMA wrapper not implemented |
| Baseline engine performance | 17x3 tile, no-stall／fixed-LFSR backpressure, Icarus RTL | Complete ([report](physical/evidence/RTL-PERFORMANCE-REPORT.md)); physical frequency not evaluated |
| Stage-by-stage performance | Control／load／window read／capture-multicast／MAC／output cycle measurement | Complete ([report](physical/evidence/RTL-PERFORMANCE-REPORT.md#段別サイクル分解)) |
| GPU comparison | Stage mapping for 3-tap complex FP16 and roofline from published memory bandwidth | Complete as a specification comparison; GPU run not performed ([report](physical/evidence/GPU-COMPARISON-REPORT.md)) |
| N-way design-space estimate | First-order bandwidth, capacity, multicast endpoint, and ideal MAC sweep | Complete; N=16 selected as the next RTL candidate, physical performance unverified |
| Duplicated-unit power estimate | Ideal 1／2-unit linear scaling from the 4 MHz OpenROAD anchor | Complete as an estimate ([report](physical/evidence/power-scaling-estimate-20260831.json)); real power／thermal margin unverified |
| Halo exchange and NoC multicast | Initial baseline stops at the AXI boundary; NoC is a future extension | Out of scope |
| STA, place-and-route, fan-out, and power | Fixed SKY130A exploratory run at 250 ns (4 MHz) with OpenROAD／Magic／Netgen | Run completed; sign-off incomplete |

Hold／antenna violations, GDS／SRAM-internal sign-off gaps, and the exact
preserved evidence scope are fixed in the
[physical verification report](physical/evidence/PHYSICAL-VERIFICATION-REPORT.md).
