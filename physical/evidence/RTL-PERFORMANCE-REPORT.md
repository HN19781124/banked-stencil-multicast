# RTL性能計測レポート

基準`N=4`／`M=12` bank／`T=3` tapの`banked_stencil_engine`を、behavioral SRAMモデルで測定した。ここでは`N`をlane数、`M`を物理SRAM bank数として表記する。これはRTLの機能・定常間隔の測定であり、配置配線後の周波数、電力、SRAM macro sign-offを保証しない。

## 固定条件

- ケース: logical width 17、height 3、padded width 24
- 入力18 beat、出力15 beat（各行の最後は1 lane）
- `M=12` bank、`N=4` lane、`T=3` tap、1 beatあたり128 bit、clock period 10 ns
- 1 issueのユニーク読み出し`U=6` bank、入力beatのprefetch書き込み4 bank（write count=`N=4`）
- `nostall`: 入力をready時に連続提示、出力ready固定1
- `stress`: 固定LFSRによる入力間隔＋出力backpressure
- サンプルタイルのアクセス語数: 読み出し15×6=90、書き込み18×4=72

## 再現コマンドと証跡

実行環境はOpenLaneコンテナのdigestを固定した。

```text
ghcr.io/efabless/openlane2@sha256:37c3bd4ea0534a276cb2deb88d601044857bad2807b9bc5b36efe9d02c62624e
```

```shell
docker run --rm -v "$WORKTREE:/work" -w /work --entrypoint bash \
  ghcr.io/efabless/openlane2@sha256:37c3bd4ea0534a276cb2deb88d601044857bad2807b9bc5b36efe9d02c62624e \
  -lc 'python3 -u tools/measure_performance.py --report physical/evidence/rtl-performance-report-20260829.json'
```

終了コードは`0`。Python 3.11.9、Icarus Verilog 12.0を使用し、ベクタ生成、コンパイル、2条件のシミュレーションをすべてPASSした。機械可読な全出力は[`rtl-performance-report-20260829.json`](rtl-performance-report-20260829.json)（SHA-256 `3c6c0b8da8e2578343e0028dd3cb353dbe4dce01da6a92d7ccebd19f7f6369f8`）に保存した。

## 実測値

サイクル番号は、start受理を`start`、AXI出力handshakeを`first_output`／`last_output`、done pulse観測を`done`としている。`steady_output_interval_cycles`は最初と最後の出力間を出力beat数−1で割った値である。

| 条件 | 全体cycle (`done-start`) | first output | last output | done | steady interval | output stalls | 判定 |
|---|---:|---:|---:|---:|---:|---:|---|
| nostall | 71 | 30 | 72 | 73 | 3.0000 cycle | 0 | PASS |
| stress | 81 | 41 | 82 | 83 | 2.9286 cycle | 8 | PASS |

両条件とも入力18 beat、出力15 beatを欠落なく受理し、エラーなしで完了した。`nostall`の定常出力間隔は3 cycleで、10 ns clockを仮定した場合の換算式は `output_beats/s = clock_hz / 3`（100 MHzなら約33.33 Mbeat/s）となる。これは測定ケースのRTL換算値であり、物理実装のクロック目標ではない。

## 段別サイクル分解

性能を一つの終端値だけで比較しないため、engineの状態遷移とMAC内部busyを段別に計測した。`control`〜`wait_output`は重複しないengine状態の合計で、`mac_busy`は次のissueの読出しと重なるため別掲している。

| 段 | 観測定義／作業 | nostall | stress | 主な量 |
|---|---|---:|---:|---|
| control/start | start受理からLOAD遷移 | 1 cycle (1.41%) | 1 cycle (1.23%) | 1 transaction |
| load/prefetch | `STATE_LOAD`、入力受理とSRAM書込み | 20 (28.17%) | 30 (37.04%) | 18 beat、72 word、288 B |
| window read | `STATE_READ`、6 unique sampleのbank読出し発行 | 15 (21.13%) | 15 (18.52%) | 15 issue、90 word、360 B |
| capture/multicast | `STATE_CAPTURE`、6 word捕捉→4 lane×3 tapへ同報 | 15 (21.13%) | 15 (18.52%) | 15 capture |
| MAC submit | `STATE_SUBMIT`、MACへのissue受理 | 15 (21.13%) | 15 (18.52%) | 15 issue |
| MAC compute | `mac_busy`（上記状態と重複） | 45 | 45 | 15 issue×3 tap |
| output wait | `STATE_WAIT_OUTPUT`、出力FIFO排出待ち | 5 (7.04%) | 5 (6.17%) | 15 output、stress stall 8 |
| **transaction合計** | `done-start` | **71** | **81** | — |

`stress`で増えた10 cycleは入力valid間隔によるLOAD滞在であり、出力backpressure 8 cycleはFIFOに吸収された。window形成・multicastは専用の追加cycleではなく、capture後の組合せ経路である。段別カウンタの機械可読値は[`rtl-performance-report-20260829.json`](rtl-performance-report-20260829.json)の各`measurement.stage`に保存した。

## 仕様値・派生指標

100 MHzは`manufacturing/baseline.json`のprototype clock targetからの換算基準であり、post-route sign-off周波数ではない。

| 指標 | 100 MHz換算値 | 根拠／状態 |
|---|---:|---|
| input AXI stream | 1.6 GB/s | 128 bit/beat、理論値 |
| output AXI stream | 1.6 GB/s | 128 bit/beat、理論値 |
| SRAM read | 2.4 GB/s | 6 read/cycle × 32 bit、仕様値 |
| SRAM prefetch write | 1.6 GB/s | 4 write/cycle × 32 bit、仕様値 |
| SRAM read+write | 4.0 GB/s | 上記の合計、仕様値 |
| MAC-4相当 | 3.2 GFLOP/s | 4 lane/3 cycle、8 real FLOP/complex MACのRTL換算 |
| STENCIL-4相当 | 9.6 GFLOP/s | 4 lane/cycleの提案ピーク、未実装 |

今回の17x3 tileでは、全体の有効lane結果は51個で、100 MHz換算のtransaction時間は`nostall` 710 ns（51/71=0.718 lane結果/cycle）、`stress` 810 ns（51/81=0.630 lane結果/cycle）だった。前者の定常値はREQ-PERF-002の4-lane/3-cycle条件に一致するが、REQ-PERF-001の全corner 100 MHzは未検証である。

比較用の`N=6`／`M=16` bank案は、read 8×32 bit=3.2 GB/s、write 6×32 bit=2.4 GB/s、合計5.6 GB/s（100 MHz換算）、理想lane比1.5倍と見積もれる。ただしこれは提案値であり、RTL・formal・物理測定は未実施である。

## 指標別まとめ（実測／試算／未検証）

`実測`はRTLまたは保存済みphysical runから直接得た値、`試算`はその実測cycle数や固定仕様を周波数・電力へ換算した値、`未検証`は比較対象または実装がまだない値である。

### ① 性能

| 指標 | nostall | stress | 区分 |
|---|---:|---:|---|
| outputs/s（output beat、100 MHz換算） | 21.127 Mbeat/s | 18.519 Mbeat/s | 試算（15 beat / 71・81 cycle） |
| 有効lane結果/s（100 MHz換算） | 71.831 Mresult/s | 62.963 Mresult/s | 試算（51 result / transaction） |
| start→first output | 28 cycle / 280 ns | 39 cycle / 390 ns | 実測RTL＋100 MHz換算 |
| end-to-end（start→done） | 71 cycle / 710 ns | 81 cycle / 810 ns | 実測RTL＋100 MHz換算 |
| steady II | 3.0000 cycle/beat | 2.9286 cycle/beat* | 実測RTL |
| output stall率 | 0.00% | 9.88%（8/81） | 実測RTL |
| input stall率 | 0.00% | 0.00% | 実測RTL（FIFO満杯条件は未網羅） |
| CPU/GPU比 | — | — | 未実測（同一kernelの比較ベンチマークなし） |

`*` stressのIIは15 beatの有限窓でFIFO吸収を含む観測値で、無限定常系の保証ではない。MAC-4の定常4 lane/3 cycleは満たすが、100 MHz全cornerは未検証である。

### ② メモリ

| 指標 | 値 | 区分 |
|---|---:|---|
| 論理read → unique read | 12 → 6 sample/issue | 実測構成値 |
| 重複読出し削減率（定常） | **50.0%** | 実測構成値 |
| 17x3有限tileの削減率（tail込み） | 153 → 90 sample read = **41.18%** | 試算（partial laneで固定6 read） |
| SRAM read/write/合計帯域（100 MHz換算） | 2.4 / 1.6 / **4.0 GB/s** | 仕様値の換算 |
| transaction内有効output帯域（valid bytes、100 MHz換算） | 287.3 / 251.9 MB/s | 試算（nostall / stress） |
| transaction内output stream帯域（16-byte beat、100 MHz換算） | 338.0 / 296.3 MB/s | 試算（nostall / stress） |
| SRAM read/write/合計 bytes per valid lane result | 7.059 / 5.647 / **12.706 B/result** | 試算（tile実測beat数） |
| bank conflict率 | **0**（36 scheduler state、統合RTLとも衝突なし） | formal＋RTL実測 |

### ③ コスト

| 指標 | 値 | 区分／注意 |
|---|---:|---|
| die / core面積 | 16.000 / 15.6708 mm² | physical run実測値 |
| placed instance面積 | 8.41586 mm² | physical run実測値 |
| SRAM macro面積 | 6.82892 mm²（24 macro） | physical run実測値 |
| standard-cell面積 | 1.58693 mm²（348,678 cell） | physical run実測値 |
| SRAM容量 | 48 KiB（24×2 KiB、A/B合計） | macro構成値 |
| 追加面積Δ | — | 比較用baselineがないため未算出 |
| power（internal / switching / leakage） | 7.938 / 2.644 / 0.852 mW | OpenROAD estimate、nominal TT、run clock 4 MHz |
| power total | **11.434 mW** | 同上。SAIF/workload sign-offではない |
| energy / valid lane result | 3.98 / 4.54 nJ/result | 試算（4 MHz制約×RTL 71/81 cycle） |
| performance / W | 251.3 / 220.3 Mresult/s/W | 試算（4 MHz制約と上記powerを対応） |
| performance / mm² | 0.1796 / 0.1574 Mresult/s/mm² | 試算（die 16 mm²、4 MHz換算） |

面積・電力の根拠はローカル保存した `sky130-klayout-streamout-hold1/state_out.json`（SHA-256 `527921b5a51fa3e1c907080de7cb5676722f1d4ec095e049a48108b305f3973e`）であり、要約は[物理検証レポート](PHYSICAL-VERIFICATION-REPORT.md)に固定した。面積は「追加分」ではなくこの派生全体の配置結果で、ベースラインとの差分はまだ取っていない。

### ④ 統合

| 指標 | 結果 | 区分 |
|---|---|---|
| 起動→最初の結果 | 28 / 39 cycle（nostall / stress） | 実測RTL |
| 同期 | 単一clock、performance TBでreset後収束 | 実測RTL；CDC未検証 |
| DMA | core外AXI境界のみ、external DMA wrapperなし | 未実装 |
| input FIFO occupancy | 最大1/16 = 6.25%（両条件） | 実測RTL |
| output FIFO occupancy | 最大1/16 = 6.25% / 2/16 = 12.5% | 実測RTL（nostall / stress） |
| CPU/GPU fallback率 | — | fallback経路未定義のため未検証 |

### ⑤ 品質・再現性

| 指標 | 結果 | 区分 |
|---|---|---|
| 数値誤差 | 17x3 tileの51 lane結果でbit mismatch 0、error 0 | 実測RTL |
| 決定性 | 固定vector／固定LFSR seed／固定containerで再生可能 | 実測条件；独立二重実行比較は未実施 |
| RTL/formal回帰 | 24/24 checks PASS、Python unit 36件 | 実測 |
| STA corner数 | 9 corner定義（setupは0 violation、holdは違反あり） | physical run実測 |
| 再現コマンド | 本レポート「再現コマンドと証跡」のdigest固定Docker command | 実測証跡 |

未検証として残るのは、CPU/GPU比較、外部DMA/NoC、gate/SDF、qualified SRAM、100 MHz全corner、workload-annotated power、baseline差分面積、実機fallback率である。

## 境界

今回の`stress`では出力FIFOがバックプレッシャを吸収し、入力handshake stallは0だった。外部DMA、任意サイズ長時間トラフィック、CDC、gate/SDF、qualified SRAM、全corner STA、電力、`M=16` bank／3D拡張は別検証項目である。`M=16` bank案と3Dツリー案はこの測定結果に含めず、実装時に独立したRTL・formal・物理再検証を行う。
