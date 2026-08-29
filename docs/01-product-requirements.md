# 製品要求仕様

## 1. 製品定義

`NB2-SMA-01`は、複素FP16の1D三点ステンシルを対象とする4レーン・ストリーミングIPブロックである。12個のsingle-port SRAM bank、重複読出し除去、6サンプルから4組の三入力窓を生成する同報網、複素積和、ストリーム入出力、制御／診断機能を含む。

初回製造基準は独立したIP blockであり、CPU、外部DRAM PHY、PLL、pad ring、package、boardは統合側の責任範囲とする。公開PDK版は試作・設計検証用で、商用品はfoundry-qualified PDKへ再実装する。

## 2. 固定パラメータ

| 項目 | 基準値 |
|---|---|
| lane / tap | 4 / 3 |
| sample | complex binary16、32 bit |
| accumulation | binary32 |
| SRAM | 12 bank、各1024×32 bit、single port |
| input / output stream | AXI4-Stream、各128 bit |
| control | AXI4-Lite、32 bit data / 12 bit address |
| target clock | 100 MHz（10 ns） |
| prototype | SKY130A + `sky130_fd_sc_hd` |
| reset | active-low、async assert / sync deassert |

## 3. 機能要求

- **REQ-FUN-001**: 4個の隣接出力点について、各3 tapの複素ステンシルを処理すること。
- **REQ-FUN-002**: 12個の論理入力要求を6個のユニークsample読出しへ縮約し、各sampleを必要なlaneへ同報すること。
- **REQ-FUN-003**: buffer A/Bのping-pong方向を切り替えても、同一cycleのread/write bank衝突を発生させないこと。
- **REQ-FUN-004**: 行端はhostが供給する左1・右1以上のHaloとlane paddingを用い、内部では通常座標として処理すること。
- **REQ-FUN-005**: 部分最終issueでは無効laneをmaskし、無効laneの出力をstreamへ送らないこと。
- **REQ-FUN-006**: read行とwrite行が異なる場合、固定phaseで安全と証明された場合を除き、同時accessを禁止してtransition bubbleを挿入すること。
- **REQ-FUN-007**: downstream backpressure中は結果とsidebandを保持し、重複・欠落・順序入替を起こさないこと。
- **REQ-FUN-008**: error、FP exception、完了、idle、busyをsoftwareから読取り、mask可能なinterruptを生成できること。

## 4. 数値要求

- **REQ-NUM-001**: sampleおよびcoefficientの実部・虚部はIEEE 754 binary16 bit patternとすること。
- **REQ-NUM-002**: binary16 operandをbinary32へ正確に拡張し、binary32 fused multiply-addで累積すること。
- **REQ-NUM-003**: 全ての丸めは`roundTiesToEven`とし、binary16への縮小は最終出力で1回だけ行うこと。
- **REQ-NUM-004**: subnormalをflushせず、NaN、infinity、signed zeroを`02-numerical-specification.md`どおり処理すること。
- **REQ-NUM-005**: laneごとのNV/OF/UF/NXを生成し、transaction単位およびsticky CSRで観測可能にすること。
- **REQ-NUM-006**: 同一入力bit patternとcoefficientに対し、RTL、gate-level、reference modelがbit-exactで一致すること。

## 5. 性能要求

- **REQ-PERF-001**: prototype PDKで100 MHzをsign-off corner全てにおいて満たすこと。
- **REQ-PERF-002**: `MAC-4`基準構成は、backpressureがない場合に4出力を3 cycle以内の定常間隔で生成すること。
- **REQ-PERF-003**: SRAM側は有効issue当たり6 readと最大4 prefetch writeを受理すること。
- **REQ-PERF-004**: 公称性能・電力・面積はpost-route sign-off reportだけを根拠に公開すること。

## 6. メモリ要求

- **REQ-MEM-001**: 各SRAM bankは1 cycle当たりreadまたはwriteのいずれか1 access以下とすること。
- **REQ-MEM-002**: bank mappingは`B_b(x,y)=(x+2y+phi_b) mod 12`、`phi_A=0`、`phi_B=6`とすること。
- **REQ-MEM-003**: bank内addressは`base_b+y*(Wp/12)+floor(x/12)`とし、A/B領域を重複させないこと。
- **REQ-MEM-004**: padded row width `Wp`は12の正の倍数とし、全読出し座標が`0 <= x < Wp`を満たすこと。
- **REQ-MEM-005**: SRAM BISTは各bankのstuck-at、transition、address decoder、coupling故障を検出できるalgorithmを実行すること。
- **REQ-MEM-006**: runtime ECCは初回基準では実装しない。soft-error要件が発生した場合はword幅、bandwidth、macroを再baselineすること。

## 7. インターフェース要求

- **REQ-IF-001**: input/output dataはAXI4-Stream ready/valid protocolを使用すること。
- **REQ-IF-002**: input streamは4個の32-bit complex sample、output streamは4個の32-bit complex resultを1 beatに格納すること。
- **REQ-IF-003**: `TKEEP`、`TLAST`、lane-valid metadataをtransaction終端までdataと同期させること。
- **REQ-IF-004**: CSRはAXI4-Lite 32-bit single-beat accessに対応し、未定義addressへSLVERRを返すこと。
- **REQ-IF-005**: reset、clock stop、soft reset時のready/valid挙動をprotocol assertionで検証すること。
- **REQ-IF-006**: DMAはcore外部のwrapperとし、core stream境界でburst分断・FIFO枯渇・満杯を吸収すること。

## 8. クロック・電源・DFT要求

- **REQ-PWR-001**: 初回基準は1 clock・1 voltage domainとし、内部generated clockを使用しないこと。
- **REQ-PWR-002**: idle時はintegrated clock-gating cellでpipelineとSRAM周辺logicを停止できること。
- **REQ-PWR-003**: power gating、retention、DVFSは初回基準の対象外とすること。
- **REQ-DFT-001**: macroを除く全scannable flopをscan chainへ含め、stuck-at coverage 99%以上を目標とすること。
- **REQ-DFT-002**: SRAMはMBIST repairなしのpass/fail診断とbank/address failure signatureを出力すること。
- **REQ-DFT-003**: test_mode時はclock/reset/gatingを外部test controllerから制御可能にすること。
- **REQ-DFT-004**: gate-level simulationでscan shift、capture、MBIST、functional復帰を確認すること。

## 9. 物理・製造要求

- **REQ-PHY-001**: 全sign-off cornerでsetup/hold WNSを0 ns以上とし、未waiveのtiming violationを0件とすること。
- **REQ-PHY-002**: DRC、LVS、antennaの未waive errorを0件とすること。
- **REQ-PHY-003**: static IR dropをnominal core voltageの5%以下、dynamic IR dropを10%以下に抑えること。
- **REQ-PHY-004**: foundry EM limit、max transition、max capacitance、max fanoutを全netで満たすこと。
- **REQ-PHY-005**: 6-to-12 multicast pathはbuffer tree化し、post-route STAで全consumerへのskewとslewを確認すること。
- **REQ-PHY-006**: SRAM macroのLEF/GDS/liberty/Verilog/CDLが同一revisionであることをchecksumで固定すること。
- **REQ-MFG-001**: tapeout packageはGDS/OASIS、netlist、LEF、SPEF、SDF、SDC、DRC/LVS/ERC/antenna/STA/power reportを含むこと。
- **REQ-MFG-002**: 使用PDK、standard-cell、SRAM、EDA tool、third-party IPのversionとlicenseを固定すること。
- **REQ-MFG-003**: package、pad ring、ESD、IO voltage、pinout、board test pointをfoundry submission前に承認すること。
- **REQ-MFG-004**: wafer sort、package test、bring-up、characterization、failure analysisのtest planをlot release前に承認すること。
- **REQ-MFG-005**: 全必須gateのPASSと設計・検証・物理・DFT・製造責任者の署名なしにtapeoutしないこと。
