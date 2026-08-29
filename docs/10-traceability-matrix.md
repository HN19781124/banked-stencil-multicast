# 要求トレーサビリティ

Status: `PASS`は現repositoryでevidenceあり、`PARTIAL`は一部のみ、`SPECIFIED`は設計判断済みだが実装/evidence待ち、`OPEN`はtapeout blocker。

| Requirement | Design authority | Verification / artifact | Status |
|---|---|---|---|
| REQ-FUN-001 | `02`, `03` complex MAC | bit-exact end-to-end test | OPEN |
| REQ-FUN-002 | `rtl/stencil_multicast.sv` | integration RTL simulation | PASS |
| REQ-FUN-003 | `rtl/bank_scheduler.sv` | Python, 36-state RTL, SAT | PASS |
| REQ-FUN-004 | `reference/peripheral_schedule.py`, `04` | width 1–257 edge tests | PASS |
| REQ-FUN-005 | `03`, `04` lane mask | partial-lane RTL/AXI test | PARTIAL |
| REQ-FUN-006 | `04` transition bubble policy | controller assertion/formal | PARTIAL |
| REQ-FUN-007 | `03`, `04` output FIFO | AXI stall stability/formal | OPEN |
| REQ-FUN-008 | `03` CSR/error/IRQ | CSR UVM/register test | OPEN |
| REQ-NUM-001 | `02` binary16 packing | format directed vectors | SPECIFIED |
| REQ-NUM-002 | `02` FP32 FMA sequence | reference vs RTL random | OPEN |
| REQ-NUM-003 | `02` RNE rule | half-way rounding vectors | OPEN |
| REQ-NUM-004 | `02` special cases | classification cross coverage | OPEN |
| REQ-NUM-005 | `02`, `03` flags/CSR | exception injection/readback | OPEN |
| REQ-NUM-006 | `02`, `07` bit-exact gate | RTL/gate/reference scoreboard | OPEN |
| REQ-PERF-001 | `06` 10 ns constraint | all-corner post-route STA | OPEN |
| REQ-PERF-002 | `03` MAC-4 pipeline | no-stall throughput assertion | OPEN |
| REQ-PERF-003 | scheduler/memory path | integrated 6R+4W simulation | PASS |
| REQ-PERF-004 | `06`, release policy | signed physical report | SPECIFIED |
| REQ-MEM-001 | scheduler + `04` | SAT conflict property | PASS |
| REQ-MEM-002 | scheduler/reference | exhaustive periodic states | PASS |
| REQ-MEM-003 | reference address mapping | uniqueness unit test | PASS |
| REQ-MEM-004 | peripheral row layout | width 1–257 padding test | PASS |
| REQ-MEM-005 | `05` MBIST | MBIST fault simulation | OPEN |
| REQ-MEM-006 | baseline exclusion | architecture review/risk R-017 | SPECIFIED |
| REQ-IF-001 | `03` AXI stream | protocol assertions/VIP | OPEN |
| REQ-IF-002 | `03` packing | lane mapping scoreboard | OPEN |
| REQ-IF-003 | `03` sideband | partial/last/stall cross | OPEN |
| REQ-IF-004 | `03` CSR | AXI-Lite protocol/register test | OPEN |
| REQ-IF-005 | `03`, `05` reset | reset/clock-stop assertions | OPEN |
| REQ-IF-006 | `04` DMA boundary | DMA wrapper AXI VIP | OPEN |
| REQ-PWR-001 | `05` single domain | CDC/RDC and clock audit | OPEN |
| REQ-PWR-002 | `05` ICG policy | clock-gating check/power report | OPEN |
| REQ-PWR-003 | baseline exclusion | UPF/review | SPECIFIED |
| REQ-DFT-001 | `05` scan | ATPG coverage report | OPEN |
| REQ-DFT-002 | `05` MBIST status | gate-level MBIST test | OPEN |
| REQ-DFT-003 | `05` test mode | DFT DRC/test clock simulation | OPEN |
| REQ-DFT-004 | `05`, `07` | scan/MBIST gate simulation | OPEN |
| REQ-PHY-001 | `06` timing | MCMM STA | OPEN |
| REQ-PHY-002 | `06` physical verification | DRC/LVS/antenna | OPEN |
| REQ-PHY-003 | `06` PDN | static/dynamic IR report | OPEN |
| REQ-PHY-004 | `06` limits | EM/electrical DRC | OPEN |
| REQ-PHY-005 | `06` multicast tree | post-route path audit | OPEN |
| REQ-PHY-006 | `04`, `06` macro views | checksum/view consistency | OPEN |
| REQ-MFG-001 | `08` tapeout directory | manifest completeness test | SPECIFIED |
| REQ-MFG-002 | `06`, `08`, `11` | SBOM/version manifest | OPEN |
| REQ-MFG-003 | `08` package inputs | signed package review | OPEN |
| REQ-MFG-004 | `08` silicon test | signed test plan | OPEN |
| REQ-MFG-005 | `07`, `08` gates/signature | tapeout authorization record | OPEN |

## Closure

release automationは`01-product-requirements.md`の全`REQ-*`が本表へ一度以上現れることを検査する。tapeout baselineでは全行を`PASS`または署名済みwaiverへ変更し、evidence pathとchecksumを固定する。
