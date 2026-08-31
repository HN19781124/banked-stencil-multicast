# GPU同条件比較レポート

本書は、基準`N=4`／`M=12`／`T=3` RTL性能と、公開GPU仕様から計算した帯域rooflineを同一カーネル条件で比較する補助資料である。GPU実機は本環境に存在しないため、ここでのGPU値はベンチマーク結果ではなく理論上限である。

## 比較条件

- カーネル: 複素FP16の3-tapステンシル
- 1 complex sample: 32 bit（実部FP16＋虚部FP16）
- 1 output: 3 complex MAC = 24 real FLOP
- 4 output issue: unique read 6 sample、write 4 output
- 重複除去後のデータ移動: `(6 + 4) × 4 byte / 4 output = 10 byte/output`
- 算術強度: `I = 24 FLOP/output / 10 byte/output = 2.4 FLOP/byte`

GPU側の帯域上限は次式で計算する。

```text
P_bw = memory_bandwidth × I
result_bw = P_bw / 24 FLOP/output
```

この上限は、全GPUメモリ帯域をこのカーネルだけで使い切る仮定である。GPUの命令供給、occupancy、cache／shared-memory再利用、kernel launch、境界処理、他ワークロードとの競合は含めない。

## RTL基準

根拠は[`RTL-PERFORMANCE-REPORT.md`](RTL-PERFORMANCE-REPORT.md)である。

| 構成 | 条件 | 性能 |
|---|---|---:|
| MAC-4 | 100 MHz換算、4 lane／3 cycle | 3.2 GFLOP/s、定常133.3 Mresult/s |
| STENCIL-4相当 | 100 MHz換算、4 lane／cycle、未実装ピーク | 9.6 GFLOP/s、定常400 Mresult/s相当 |
| 現行physical run | 4 MHz換算、MAC-4相当 | 0.128 GFLOP/s、定常5.33 Mresult/s相当 |

有限の17×3 tile（51 valid lane results）では、RTLレポートの実測値は`nostall=51/71×100 MHz=71.831 Mresult/s`、`stress=51/81×100 MHz=62.963 Mresult/s`である。これは立ち上がり・tail・backpressureを含むtransaction値であり、定常値とは区別する。

## 公開GPU仕様からの計算

メモリ帯域は2026-08-29に取得した[NVIDIA公式GeForce比較表](https://www.nvidia.com/en-us/geforce/graphics-cards/compare/?section=compare-20)を使用した。

| 層 | 代表GPU | 公称メモリ帯域 | 同条件の`P_bw` | `result_bw` | MAC-4比 | STENCIL-4比 |
|---|---|---:|---:|---:|---:|---:|
| フラグシップ | RTX 5090 | 1.792 TB/s | 4.3008 TFLOP/s | 179.2 Gresult/s | 約1,344倍 | 約448倍 |
| ミドル | RTX 5070 | 672 GB/s | 1.6128 TFLOP/s | 67.2 Gresult/s | 約504倍 | 約168倍 |
| エントリ | RTX 5060 | 448 GB/s | 1.0752 TFLOP/s | 44.8 Gresult/s | 約336倍 | 約112倍 |

データセンター上限の参考として、NVIDIA Rubin GPUの公表値（予備仕様）22 TB/sを同じ式へ入れると、`P_bw=52.8 TFLOP/s`、`result_bw=2.2 Tresult/s`となる（[公式仕様](https://www.nvidia.com/en-eu/data-center/vera-rubin-nvl72/)）。これは三層表とは別セグメントの参考値である。

## 段別比較

GPU全体の一つの数字に潰さず、同じ4-output issueを次の段へ分解して比較する。RTLの`control`〜`output wait`はtransactionの実測cycle、`mac_busy`は読出しと重なる演算時間である。GPUにはASICのような固定prefetch SRAM段がないため、対応するglobal load、warp内window形成、MAC、global storeを測定する。

| 段 | `N=4`／`M=12` RTL（nostall / stress） | GPU側の対応 | 比較する値 |
|---|---|---|---|
| load/prefetch | 20 / 30 cycle、18 beat受理、72 word (288 B) 書込み | coalesced global load（unique sample 6個／issue） | byte/output、load latency、cache hit率 |
| window read | 15 / 15 cycle、90 word (360 B) | global/shared-memory read | 実効read GB/s、warp stall |
| capture/multicast | 15 / 15 cycle、6 sample→4×3 tapへ同報 | shared-memoryまたはshuffleによるwindow形成 | 命令数、同期、再利用率 |
| MAC | 45 / 45 `mac_busy` cycle、15 issue×3 tap | 3 complex MAC／4 output | 実効FLOP/s、occupancy |
| output/wait | 5 / 5 cycle、15 beat (240 B)、stress stall 8 | coalesced global store（4 output／issue） | store GB/s、end-to-end latency |

GPUの帯域だけで切った段別上限も併記する。`unique-read`は6 B/output、`store`は4 B/output、両方を合算した値は前表の10 B/outputである。

| GPU | unique-read上限 | store上限 | read+store上限 |
|---|---:|---:|---:|
| RTX 5090 | 298.7 Gresult/s | 448.0 Gresult/s | 179.2 Gresult/s |
| RTX 5070 | 112.0 Gresult/s | 168.0 Gresult/s | 67.2 Gresult/s |
| RTX 5060 | 74.7 Gresult/s | 112.0 Gresult/s | 44.8 Gresult/s |

これらはGPU実測値ではなく、各段が公称メモリ帯域を単独または合算で使い切るrooflineである。実機比較では同じtileを使い、段別kernel timing、global/shared transaction、warp stall、転送・launch時間を取得してから全体値を出す。

## GPUの比較単位（SM／warp）

GPUの「1コア」は本提案の1Dユニットと直接対応しない。RTX Blackwellでは、SMが複数warpを同時に実行し、CUDA coreはそのSM内のlane演算器である。したがって、実行単位の比較はCUDA core 1個ではなく、SM／CUまたはSM内のactive warp群を基準にする。RTX 5090は170 SM、RTX 5070は48 SMで、いずれも128 CUDA core／SMと[NVIDIAのアーキテクチャ資料](https://images.nvidia.com/aem-dam/Solutions/geforce/blackwell/nvidia-rtx-blackwell-gpu-architecture.pdf)に記載されている。RTX 5060の30 SMは、公式の3,840 CUDA coreを128 core／SMで割った推定値である。

メモリ帯域がSMへ均等に分配されるという仮定で、同じ`I=2.4 FLOP/byte`を1 SMへ割り当てると次の目安になる。実際の帯域分配、warpスケジューリング、cache／shared-memory再利用は均等ではないため、これは比較単位を揃えるための計算値である。

| GPU | SM数 | CUDA core／SM | 仮想帯域／SM | 帯域roofline／SM | MAC-4比 | STENCIL-4比 |
|---|---:|---:|---:|---:|---:|---:|
| RTX 5090 | 170 | 128 | 10.54 GB/s | 25.30 GFLOP/s | 約7.9倍 | 約2.6倍 |
| RTX 5070 | 48 | 128 | 14.00 GB/s | 33.60 GFLOP/s | 約10.5倍 | 約3.5倍 |
| RTX 5060* | 30 | 128 | 14.93 GB/s | 35.84 GFLOP/s | 約11.2倍 | 約3.7倍 |

`*` RTX 5060のSM数はCUDA core数／128からの推定。1Dユニットを1 SMへ割り当てるのか、1 warpまたは複数warpへ分割するのかで、実効性能と必要な命令・同期方式は変わる。したがって、GPU統合時の実測比較は「1 CUDA core対1 ASIC」ではなく、同じ入力・出力・境界処理を含む1 SM／warp群対1Dユニット群で行う。

## 解釈と限界

1. 上表はGPU全体と、SKY130上の小規模RTLブロックを比較した帯域上限であり、同じ面積・電力・製造条件の比較ではない。
2. この処理強度ではGPUの公称演算TOPSよりメモリ帯域が先に上限となるが、実効値はGPU実装とデータ配置で下がる。
3. したがって、本提案の主張はGPU全体の生GFLOP/sを上回ることではない。GPU前段で窓生成、重複読出し除去、同報、局所バッファ化を行い、`byte/output`、実効帯域、energy/result、起動・同期時間を改善できるかを評価対象とする。
4. GPU実測比を確定するには、同じ3-tap複素FP16カーネル、同じ入力・出力形式、同じ境界処理、転送とkernel launchを含む実機ベンチマークが必要である。現時点では未実施である。

## 再現性

- RTL基準: [`RTL-PERFORMANCE-REPORT.md`](RTL-PERFORMANCE-REPORT.md)
- 計算条件: 本書「比較条件」
- GPU仕様取得日: 2026-08-29
- GPU実測環境: 未導入
