# 物理設計基準

## 1. Target policy

公開再現用の第一targetはSKY130A + `sky130_fd_sc_hd`、RTL-to-GDS flowはOpenLane/OpenROADとする。SKY130 open PDKは公式にexperimental previewでありproduction用途を保証していないため、公開版の結果は試作・初期design verificationとして扱う。

商用製品は次のいずれかを満たすまでtapeout不可とする。

1. foundryが当該open PDK revisionをproduction-qualifiedとして書面承認する。
2. 契約済みfoundry PDKへ再targetし、全sign-offを再実行する。

Authority:

- [SkyWater SKY130 PDK status](https://skywater-pdk.readthedocs.io/en/main/)
- [OpenLane supported PDK and Windows/WSL guidance](https://openlane2.readthedocs.io/en/stable/faq.html)
- [OpenROAD Flow Scripts platform and GDS flow](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/blob/master/docs/index.md)

## 2. Initial constraints

| 項目 | 初期値 | sign-off条件 |
|---|---:|---|
| clock period | 10.0 ns | 全corner WNS >= 0 |
| clock uncertainty | 0.5 ns | CTS後はextracted valueへ更新 |
| input delay | 2.0 ns | integration timing budgetで再設定 |
| output delay | 2.0 ns | integration timing budgetで再設定 |
| max fanout | 8 | library/flow limitの厳しい方 |
| core utilization | 50% | congestion/IR/clockで調整 |
| placement density | 45–55% sweep | routability最良点を固定 |
| static IR drop | <= 5% VDD | 全mode |
| dynamic IR drop | <= 10% VDD | worst activity |

初期値はfloorplan探索用であり、foundry/library制約、package、integration budgetがauthorityとなる。

## 3. Floorplan

`M=12`個のSRAM macroをcompute/multicast coreの周囲へ対称配置し、read pinからoperand registerまでの距離差を抑える。推奨配置は左右6 bank、中央にscheduler/multicast/MAC、上端にCSR/FIFO、下端にDFT/MBISTである。

必須項目:

- macro haloとrouting channelをPDK推奨値以上確保
- SRAM pin側へrouting channelを向け、macro上のrouting obstructionを尊重
- power ring/stripeを全macro power pinへ直接接続
- 6 sample multicast rootにpipeline/register boundaryを置く
- high-fanout sampleごとにbalanced buffer treeを合成またはphysical toolで構築
- scan chainをmacro間の蛇行が最小になるようphysical reorder
- analog/pad/ESD blockとのkeepoutをchip integratorが定義

## 4. Timing sign-off

libraryが提供する全PVT cornerでMCMMを実行し、少なくともslow/setup、fast/hold、typical/powerを含める。名称・voltage・temperatureはpinned PDK libertyをauthorityとし、文書へ転記した値だけで判断しない。

sign-off check:

- setup/hold recovery/removal
- minimum pulse width
- clock gating setup/hold
- max transition/capacitance/fanout
- false/multicycle path justification
- input/output timing budget
- OCV/AOCV/POCV（PDK提供範囲）
- extracted RCによるsignal integrity/crosstalk

全waiverはpath、corner、slack、functional reason、owner、expiryを記録する。

## 5. Power integrity

activityはdirected worst-caseとrepresentative workloadの両方を使用する。

- worst-case: 全lane連続稼働、最大toggle data、同時SRAM read/write、output no-stall
- representative: 実workload VCD/SAIF
- idle: clock-gated、CSR accessのみ
- MBIST/scan: test clock条件

reportはcell internal/switching/leakage、SRAM、clock tree、IOを分離する。EMはpower/ground、clock、高fanout data、macro pinを確認する。IR/EM violationはplacement density、stripe、decap、buffer、frequencyを再設計し、waiverだけでtapeoutしない。

## 6. Physical verification

- foundry deckによるDRC
- schematic/netlist対GDSのLVS
- ERC、well/substrate、power short/open
- antenna checkとdiode/jumper修正
- density/fillとfill後STA/DRC
- extracted parasitic consistency
- GDS/OASIS layer mapとstream-out checksum
- MagicのGDS受渡しと通常DRC/LVSのtech選択は[`12-magic-tech-selection.md`](12-magic-tech-selection.md)に従い、GDS-only techを接続抽出へ使用しない。

未waive error 0を必須とする。open deckでPASSしてもfoundry acceptance deckが別の場合はfoundry結果をauthorityとする。

## 7. Reproducibility

physical runごとに次を固定する。

- PDK family/variant/revision and checksum
- standard-cell and SRAM macro revisions
- OpenLane/OpenROAD/Yosys/KLayout/Magic versions
- RTL commit、constraint commit、config hash
- random seed、environment、host resources
- command line and complete log

最終run directoryはread-only archiveとし、release manifestへSHA-256を記録する。

現行SKY130 runのコンテナdigest、ツール版、実行コマンド、終了コードは
[`physical/evidence/sky130-magic-gds-import-hold1/PROVENANCE.md`](../physical/evidence/sky130-magic-gds-import-hold1/PROVENANCE.md)に固定する。
