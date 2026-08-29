# リスク登録簿

尺度: Severity / Likelihood は H/M/L。`Gate`は解消必須時点。

| ID | risk | S | L | mitigation / evidence | owner | Gate |
|---|---|---|---|---|---|---|
| R-001 | open SKY130 PDKがproduction-qualifiedでない | H | H | 試作限定表示、商用foundry PDKへ再target、foundry書面承認 | product/physical | G7 |
| R-002 | complex FP MAC RTLとbit-exact model未実装 | H | H | FPnew等のpinned permissive IP評価、独立reference、100万random vector | design/verification | G1/G2 |
| R-003 | FP underflow/NaN flag規則のIP差異 | H | M | `02`をauthority化、directed境界、third-party errata review | verification | G2 |
| R-004 | qualified 1024×32 single-port SRAM macro未選定 | H | H | compiler/vendor確認、全view checksum、behavior/timing correlation | physical | G4 |
| R-005 | read/write異rowで固定phase conflict | H | M | 初回製品はtransition bubbleを強制、assertionとformal proof | design | G1 |
| R-006 | multicast fanout/配線遅延で100 MHz未達 | H | M | floorplan proximity、buffer tree、pipeline option、density sweep | physical | G5 |
| R-007 | MAC-4 throughput/areaが要求に不適合 | M | M | synthesis sweep、serialized/parallel option比較、baseline ECO | architecture | G4 |
| R-008 | AXI backpressureでloss/duplication | H | M | formal FIFO/AXI property、random wait-state scoreboard | verification | G2 |
| R-009 | DMA wrapperのburst/4KiB/error corner | H | M | AXI VIP、error injection、descriptor wrap test | integration | G2 |
| R-010 | reset/clock gate/CDCによるdeadlockまたはX | H | M | RDC/CDC、reset-at-every-stage、gate simulation | design/verification | G2 |
| R-011 | scan/MBISTがmacro/clock gateと競合 | H | M | DFT DRC、test_mode bypass、gate-level pattern simulation | DFT | G3 |
| R-012 | IR/EMまたはsimultaneous switching violation | H | M | representative/worst SAIF、PDN sweep、decap、frequency derate | physical | G5 |
| R-013 | package/IO/ESD未定でchip-level製造不可 | H | H | IP block scopeを明示、chip integratorがpackage sign-off | product | G7 |
| R-014 | third-party FP/SRAM IP licenseが公開配布を制限 | H | M | license review、source非同梱bootstrap、NOTICE/SBOM | legal | G1/G7 |
| R-015 | tool/PDK driftで結果再現不能 | M | M | commit/hash/container/seed固定、clean CI、archive | release | every gate |
| R-016 | performance claimがpre-layout値を混同 | M | M | post-route reportのみ公開、READMEにscope表示 | product | release |
| R-017 | runtime SRAM soft errorを検出できない | M | M | 初回は明示的非対応、用途FIT評価後ECC再baseline | product | G0 |
| R-018 | public defensive publicationとcommercial claimsの混同 | M | M | originalとmanufacturing extensionを分離、version/license明記 | release/legal | release |

## Closure rule

H severity riskは、該当Gateまでに`closed`または署名済みresidual-risk acceptanceへ変更する。riskを削除して履歴を失わず、status、evidence link、決定日を追記する。
