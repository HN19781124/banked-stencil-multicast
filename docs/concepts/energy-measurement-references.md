# 電力・データ移動の比較に使う外部資料

[English](energy-measurement-references.en.md) · [简体中文](energy-measurement-references.zh-Hans.md) · 日本語（正本）

この資料は、本リポジトリの「窓の移動・重複転送を減らすと電力面で有利になり得る」という設計仮説を、既存研究の測定方法と切り分けて扱うための参考文献である。いずれも本方式の直接比較や、現行RTLの電力実測を意味しない。

## 新しい一次資料

| 資料 | 実験・分析の範囲 | 本リポジトリでの使い方 |
|---|---|---|
| [TyTraCL: Optimising Stencil Code on FPGAs by Trading Data Movement for Compute using Compiler Rewrite Rules](https://doi.org/10.1007/s10766-025-00809-z)（2025） | Intel Arria 10上でFPGAボード（DRAMを含む）の電力を`fpgainfo`で測定し、手動最適化FPGA実装とのenergy efficiencyを比較。中間buffer削減による30%改善を報告 | FPGAでの電力測定境界と、BRAM／DRAM削減を性能・電力へ換算する方法の先行例。ラインバッファ対本方式の直接比較ではない |
| [Exploring Efficient FPGA Acceleration of High-Order 3D Iterative Stencil Loops on Large Data Grids](https://doi.org/10.1007/s13369-025-10919-y)（2025） | 8次・25点3D stencilをFPGAで実装し、A100との比較を`W/GB/s`で報告。空間／時間blockingと外部帯域の影響を評価 | stencil固有の電力効率指標の例。ただしデバイス、精度、測定範囲が異なるため数値の横移植はしない |
| [FlexNPU: a dataflow-aware flexible deep learning accelerator for energy-efficient edge devices](https://doi.org/10.3389/fhpcp.2025.1570210)（2025） | Intel 7 nm test chipと合成結果で、MAC、データstorage／movement、control等の電力内訳を分離。schedule-awareなSRAM→PE multicastとdouble bufferingを評価 | data movementと演算を別カウンタで報告する構成の参考。DNN向けであり、stencilの電力結果ではない |
| [HiEval: A scheduling performance estimation approach for spatial accelerators via hierarchical abstraction](https://doi.org/10.1016/j.sysarc.2024.103079)（2024） | data placement、peer forwarding、parent multicastを含む通信パターンを、階層的な性能・energy cost modelで評価 | 実測前にread／write／forward／multicast回数を揃えるためのモデル設計の参考。物理電力の実測資料ではない |

## 背景としての基準資料

- [Eyeriss: A Spatial Architecture for Energy-Efficient Dataflow for Convolutional Neural Networks](https://doi.org/10.1109/ISCA.2016.40)（2016）は、同じ面積・並列度・技術条件でdataflowを比較し、local storage reuseとmulticastを含むデータ移動の差を分析する。
- [Horowitz, Computing's Energy Problem](https://doi.org/10.1109/ISSCC.2014.6757323)（2014）は、演算、SRAM、DRAMのエネルギーを比較する45 nm基準である。絶対値を現行プロセスへ移植せず、階層間の桁差を説明する基準として使う。

## 公平な測定へ落とす条件

外部資料の数値を本方式へ転記せず、次の条件を固定した同一FPGA比較を別途行う。

1. FPGA型番、speed grade、電圧、温度、tool version、seed、制約、bit width、clockを固定する。
2. 同じ密な入力tile、係数、Halo、`ready/valid`列、出力検査を使い、方式ごとの前処理を片側だけに含めない。
3. idle、static、clock、BRAM／SRAM、DSP／MAC、routing／I/Oを分け、可能なら`P_active - P_idle`と`energy/output sample`を併記する。
4. ボード電力とデバイス内推定電力を混ぜず、DRAMを含むか、測定窓、サンプル周期、温度安定条件を明記する。
5. 本方式の優位は、出力一致を満たした上で、データ移動量、toggle、Fmax、電力を同じ実装条件で比較できた場合に限って記載する。

現状は、1024×1024 referenceの出力一致とcycle／アクセス数までが完了範囲であり、電力は未測定である。

## 付録：ユニット複製の一次電力モデル

現行の`N=4`／12-bank baselineに対して、SKY130探索runのOpenROAD見積（4 MHz、nominal TT、合計11.434 mW）を1ユニットのアンカーとして、同じclockとtransaction率が独立に保たれる場合の複製コストを機械的に計算できるようにした。既定モデルは`P(n)=n*(10.582+0.852) mW`で、shared logic、追加配線、外部帯域、ユニット間backpressureはゼロとしている。したがって2ユニットの22.868 mWは理想的な一次外挿であり、実電力・熱余裕・製造sign-offではない。

| 交通条件 | units | power（mW） | ideal throughput（Mresult/s） | energy（nJ/result） | performance/W（Mresult/s/W） |
|---|---:|---:|---:|---:|---:|
| nostall | 1 | 11.434 | 2.873 | 3.979 | 251.3 |
| nostall | 2 | 22.868 | 5.746 | 3.979 | 251.3 |
| stress | 1 | 11.434 | 2.519 | 4.540 | 220.3 |
| stress | 2 | 22.868 | 5.037 | 4.540 | 220.3 |

再現コマンドは次のとおり。実際の電源／熱予算を持つ場合は`--power-budget-mw`、追加配線を見込む場合は`--interconnect-mw-per-extra-unit`、共有回路を見込む場合は`--shared-static-mw`／`--shared-dynamic-mw`を明示する。

```shell
python tools/estimate_power_scaling.py \
  --units 1,2 \
  --report physical/evidence/power-scaling-estimate-20260831.json
```

このモデルは現行のsingle-port設計を2重化すれば無条件に動くことを意味しない。各ユニットのread／write bank集合、入力分割、DMA／FIFO競合、外部帯域を再検査する必要がある。18-bank 1R1W register-exchangeは、single-port baselineとは別の候補である。
