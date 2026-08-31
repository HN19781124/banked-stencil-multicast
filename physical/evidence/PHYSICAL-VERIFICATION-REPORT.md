# Physical verification report

Date: 2026-08-29  
Run: `sky130-pnr-250ns-hold1`  
Target: SKY130, `N=4` lanes / `M=12` banks / `T=3` taps banked-stencil accelerator

The reproducible RTL/formal baseline was rerun on this worktree: **24/24 checks PASS** (`build/verification-report-container-digest-20260829.json`, SHA-256 `48a456c9fbccc60d1fa4ba571675f1d64cf740154c7446819f366927c9fbbd6d`).

## Result at a glance

| Check | Result |
|---|---|
| OpenROAD placement, CTS, global/detail route | Completed |
| Routing DRC | **0** errors |
| Critical disconnected pins | **0** (8 non-critical unused top-level pins) |
| Setup timing | **0** WNS / **0** TNS violations |
| Hold timing | WNS **-1.36 ns**, TNS **-849.97 ns** at worst corner |
| IR drop | VPWR **0.000328 V (0.02%)**, VGND **0.000209 V (0.01%)** |
| Antenna after repair | 49 nets / 59 pins remain |
| Magic stream-out | **Stopped** on SRAM GDS layer/datatype incompatibility |
| Magic GDS-only import check | **Top cell loaded** with pinned `sky130A-GDS.tech`; target purpose-layer unknowns **0**; non-target label/duplicate-reference warnings remain |
| Magic normal-tech DRC (DEF/LEF, labels off) | **Completed**; 7,140 `nwell.4` findings; provisional abstract-view result, not sign-off |
| Magic normal-tech extraction (DEF/LEF) | **Completed**; SPICE generated with empty feedback database; provisional abstract-view result |
| Netgen normal-tech LVS (DEF/LEF-derived SPICE vs powered Verilog) | **Circuits match uniquely**; 124,368 devices / 114,395 nets on both sides; no bad nets/elements; provisional abstract-view result |
| KLayout stream-out (same saved DEF) | **Completed**; GDS SHA-256 `75f6c422204d110bc5d8769541b492b1df0a42e95973d7ff311a3faffee727ed` |
| KLayout full DRC | **Stopped after ~42 min** at rule 530 (`ct.1_b`); no DRC report was emitted |
| Full sign-off / tape-out | **Not claimed** |

## Frozen physical numbers

- Die: 4000 x 4000 um (16.0 mm²); core area: 15.6708 mm².
- SRAM macros: 24; macro area: 6.82892 mm².
- Standard cells: 348,678; standard-cell area: 1.58693 mm².
- Reported placement utilization: 0.54.
- Routing wirelength: 8,188,646 um; vias: 1,116,823.
- Clock constraint: 250 ns (4 MHz). This run does not establish 100 MHz operation.

## Limitation and next action

OpenROAD reached a routable state and completed post-route STA and IRDrop. The original flow stopped in `Magic.StreamOut` while reading the vendor SRAM GDS, reporting unknown records on layers/datatype pairs `(33,42)`, `(33,43)`, `(22,21)`, `(22,22)`, and `(235,0)`. A read-only rerun with the pinned GDS-only tech loads the SRAM top cell and accepts those five target pairs; it still reports three `65/5` marker-label warnings and repeated self-placement warnings, so this is an import check rather than sign-off. Separate normal-tech DRC, extraction, and Netgen LVS now run from the unchanged PNR state; the DRC/extraction/LVS results are DEF/LEF-abstract checks and are not GDS/SRAM-internal sign-off. Do not remap purpose layers or edit the installed PDK.

## Selected evidence

- [run summary](sky130-pnr-250ns-hold1/README.md)
- [Magic GDS-tech import evidence](sky130-magic-gds-import-hold1/README.md)
- [container/tool/command provenance](sky130-magic-gds-import-hold1/PROVENANCE.md)
- [RTL performance evidence](RTL-PERFORMANCE-REPORT.md)
- [machine-readable RTL performance report](rtl-performance-report-20260829.json)

Generated verification reports are recreated under `build/` by
`python tools/verify.py --bootstrap --require-rtl`; `build/` is intentionally
not versioned. Raw OpenLane/Magic/KLayout logs, GDS/DEF/ODB artifacts, and the
9.17 GB recovery ZIP remain local. Their recorded SHA-256 values preserve the
link between this compact report and the frozen local archive.

The KLayout GDS hash above applies to both generated GDS copies in the frozen
local run. A full KLayout DRC was attempted from that GDS, but the
single-container environment spent about 42 minutes in rule 530 (`ct.1_b`)
without producing a report. No KLayout DRC PASS is claimed.

The 9.17 GB `neumann-bottleneck-physical-full-artifacts-20260829.zip` is retained as a local recovery archive; this report is the shareable record.
