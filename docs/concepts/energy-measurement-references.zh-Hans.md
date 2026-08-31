# 功耗与数据移动比较的外部参考

[日本語（正本）](energy-measurement-references.md) ／ [English](energy-measurement-references.en.md) ／ 简体中文

本文将“减少窗口移动和重复传输可能改善能效”这一设计假设，与公开的
测量方法并列说明。下列资料都不是本设计的直接比较；现有 RTL 也没有
功耗实测结果。

## 近期主要参考

| 资料 | 范围 | 在本仓库中的用法 |
|---|---|---|
| [TyTraCL: Optimising Stencil Code on FPGAs by Trading Data Movement for Compute using Compiler Rewrite Rules](https://doi.org/10.1007/s10766-025-00809-z)（2025） | Intel Arria 10 板级功耗（含 DRAM）由 fpgainfo 测量；报告减少中间 buffer 后的能效改善 | FPGA 功耗边界的先例；不是 line-buffer 直接比较 |
| [Exploring Efficient FPGA Acceleration of High-Order 3D Iterative Stencil Loops on Large Data Grids](https://doi.org/10.1007/s13369-025-10919-y)（2025） | 25-point 3D stencil 与 A100 以 W/GB/s 比较，包含空间／时间 blocking | stencil 功耗指标的例子；不移植其绝对数值 |
| [FlexNPU: a dataflow-aware flexible deep learning accelerator for energy-efficient edge devices](https://doi.org/10.3389/fhpcp.2025.1570210)（2025） | Intel 7 nm test chip 与 synthesis，分离 MAC、存储／移动和控制功耗，并评估 SRAM 到 PE 的 multicast 与 double buffering | 分开报告移动与计算计数的先例；结果面向 DNN，不是 stencil |
| [HiEval: A scheduling performance estimation approach for spatial accelerators via hierarchical abstraction](https://doi.org/10.1016/j.sysarc.2024.103079)（2024） | 以分层性能／能量模型评估 placement、peer forwarding 和 parent multicast | 物理测量前统一 read/write/forward/multicast 计数的参考 |

背景资料包括 [Eyeriss](https://doi.org/10.1109/ISCA.2016.40)（2016，
比较 dataflow 与 local-storage reuse）以及 [Horowitz, Computing's Energy
Problem](https://doi.org/10.1109/ISSCC.2014.6757323)（2014，给出 45 nm
下计算、SRAM、DRAM 的数量级比较）。两者都不是本仓库工艺校准的数值。

## 公平测量的条件

1. 固定 FPGA 型号、speed grade、电压、温度、tool 版本、seed、约束、
   bit width 和 clock。
2. 使用相同密集 tile、系数、Halo、ready/valid 轨迹和输出检查；不得只
   在一侧计入预处理。
3. 分离 idle、static、clock、BRAM/SRAM、DSP/MAC、routing 和 I/O；可能
   时同时报告 active 减 idle 以及每个输出的能量。
4. 将板级功耗与器件估算分开。说明是否包含 DRAM、测量窗口、采样周期和
   热稳定条件。
5. 只有在输出、toggle activity、Fmax 和功耗条件匹配后，才记录方式优势。

当前证据范围止于 1024 x 1024 的输出一致以及 cycle/access 计数。功耗
尚未测量。

## 附录：单元复制的一次模型

4 MHz SKY130 探索性 run 为一个 `N=4、M=12` 单元提供 11.434 mW 锚点。
有意采用理想模型 P(n) = n x (10.582 + 0.852) mW，其中 shared logic、
额外配线、外部带宽和单元间 backpressure 均为零。因此两个单元的
22.868 mW 只是一次外推，不是功耗实测、热裕量或制造 sign-off。

| 交通条件 | units | 功耗（mW） | 理想吞吐（Mresult/s） | 能量（nJ/result） | 性能/W（Mresult/s/W） |
|---|---:|---:|---:|---:|---:|
| nostall | 1 | 11.434 | 2.873 | 3.979 | 251.3 |
| nostall | 2 | 22.868 | 5.746 | 3.979 | 251.3 |
| stress | 1 | 11.434 | 2.519 | 4.540 | 220.3 |
| stress | 2 | 22.868 | 5.037 | 4.540 | 220.3 |

复现命令：

~~~shell
python tools/estimate_power_scaling.py --units 1,2 --report physical/evidence/power-scaling-estimate-20260831.json
~~~

该模型不表示复制 single-port 单元即可无条件运行。必须重新检查各
单元的 read/write bank 集合、输入分割、DMA/FIFO 竞争和外部带宽。
`M=18` bank・1R1W register-exchange 是独立候选。

本文是简体中文伴随概要；详细技术正本仍为日文文件。
