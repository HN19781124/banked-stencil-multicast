# 検証・サインオフ計画

## 1. Verification strategy

要求IDをtest、assertion、formal property、coverage、physical reportへtraceする。simulation PASSだけでなく、未検証stateが残っていないことをcoverageとformalで示す。

## 2. 現在のevidence

| 対象 | 方法 | 状態 |
|---|---|---|
| 12-bank scheduler | Python reference、36-state RTL simulation、Yosys SAT | PASS |
| scalable schedule | N=1/2/4/8/16/32、両buffer方向 | PASS |
| row edge / Halo | width 1–257、両phase、部分lane | PASS |
| cross-row reference phase | 全row pair reference model | PASS（製品はbubble policy） |
| synchronous SRAM + multicast | behavioral 12-bank model、両方向 | PASS |
| complex FP MAC | bit-exact reference / 256-vector RTL / product RTL | PASS（RTL；gate/physical pending） |
| AXI stream / CSR | randomized FIFO / AXI-Lite CSR / product RTL | PARTIAL（VIP/coverage pending） |
| DMA wrapper / backpressure | FIFO/engine/product randomized path | PARTIAL（external DMA wrapper pending） |
| reference engine performance | deterministic 17x3 tile, no-stall and LFSR backpressure RTL runs | PASS（3 cycle/output beat；physical frequency pending） |
| reset / CDC / DFT / MBIST | reset/product RTL and MBIST simulation | PARTIAL（CDC/scan/gate pending） |
| synthesis / STA / P&R / DRC / LVS / power | pinned container/PDK flow and physical evidence | PARTIAL（abstract DRC/LVS; sign-off pending） |

`PASS`は現在repositoryの範囲に限定する。上表のPARTIAL/OPENはtapeout blockerであり、抽象DEF/LEFの物理結果をGDS/SRAM内部のsign-offとみなさない。

## 3. Test levels

### L0: static

- formatting、lint、uninitialized/X、width/sign、latch、combinational loop
- CSR specification consistency
- license/header/source manifest
- CDC/RDC/clock/reset structural check

### L1: unit

- bank scheduler、address generator、multicast
- FIFO、AXI channel、CSR
- FP conversion/FMA/special case
- MBIST controller、clock gate wrapper

### L2: subsystem

- SRAM + multicast + MAC
- input FIFO + prefetch + ping-pong
- output FIFO + backpressure
- CSR start/abort/error/interrupt
- reset at everypipeline stage

### L3: end-to-end

- random tile width/height/stride/padding
- random binary16 data/coefficient against bit-exact model
- random AXI wait-state and row boundary
- both buffer directions and repeated transactions
- injected AXI/SRAM/FP/watchdog/MBIST error
- long run with transaction scoreboard and no loss/duplication

### L4: netlist / physical

- post-synthesis equivalence
- scan-inserted gate simulation
- SDF min/max simulation
- post-route STA and power
- DRC/LVS/ERC/antenna

## 4. Formal properties

必須property:

1. read/write bank intersection is always empty when request fires.
2. each read/write bank list has no duplicate.
3. FIFO count remains in `[0, DEPTH]`.
4. accepted input beat is emitted exactly once unless hard reset/abort contract permits discard.
5. stalled AXI output remains stable.
6. transaction IDs preserve order.
7. partial lane mask never asserts invalid output bytes.
8. busy eventually clears under fair input/output assumptions.
9. reset converges to IDLE within bounded cycles.
10. MBIST and functional SRAM enables are mutually exclusive.

## 5. Coverage closure

最低基準:

- requirement coverage: 100%
- assertion coverage: 100% reachable mandatory properties
- functional coverpoint: 100% mandatory bins、95%以上total
- line/toggle/branch/FSM: 95% / 90% / 90% / 100%
- FP classification cross: zero/subnormal/normal/infinity/qNaN/sNaN × sign × operation position
- width cross: 1,2,3,4,5,11,12,13,47,48,49,maximum
- stall cross: input/output/row boundary/reset/error

unreachable/waived binはproofまたはdesign review承認を必要とする。

## 6. Sign-off gates

| Gate | 必須成果物 | 合格条件 |
|---|---|---|
| G0 Requirements | baseline、要求、traceability | 未割当要求0 |
| G1 RTL freeze | lint/CDC/RDC/formal/unit regressions | mandatory error 0 |
| G2 Functional | end-to-end random、coverage | scoreboard mismatch 0、coverage達成 |
| G3 DFT | scan/ATPG/MBIST | coverage目標、DRC error 0 |
| G4 Synthesis | netlist、equivalence、area | equivalence PASS、constraint complete |
| G5 P&R | routed database、STA、power | timing/IR/EM PASS |
| G6 Physical | DRC/LVS/ERC/antenna | unwaived error 0 |
| G7 Manufacturing | package/test/foundry review | 全署名、manifest checksum一致 |

## 7. Regression command

```shell
python tools/verify.py --bootstrap --require-rtl
python tools/measure_performance.py --report physical/evidence/rtl-performance-report-20260829.json
```

CIはこのcommandをclean checkoutで実行し、`build/verification-report.json`をartifactとして保存する。性能測定の詳細は[`physical/evidence/RTL-PERFORMANCE-REPORT.md`](../physical/evidence/RTL-PERFORMANCE-REPORT.md)へ保存する。物理flowは別jobでpinned container/PDKを使用し、report summaryをreleaseへ添付する。
