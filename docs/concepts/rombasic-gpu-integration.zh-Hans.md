# ROMBASIC 与 GPU 集成展望

[日本語（正本）](rombasic-gpu-integration.md) ／ [English](rombasic-gpu-integration.en.md) ／ 简体中文

> 本文是未来集成参考，不属于已测量的 12-bank/4-lane 基线、v0.3.0
> sign-off，也不是性能保证。

## 为什么采用 BASIC 风格的控制描述

这里使用 BASIC 作为紧凑的顺序 reference 与控制记法，并不是把 BASIC
解释器当作高速数据通路。它的循环、赋值、分支和 fallback 行为提供
CPU 侧 golden path，规则数组／窗口操作可从此委托给 stream engine。

- 保留顺序语义，用于 reference、异常和不支持操作。
- 控制面可描述 buffer、系数、范围和启动条件，不必在每个 sample 上插入分支。
- 循环体可展开到 instruction-memory stream，而不是逐元素解释。

## ROMBASIC 宏指令展开层

此处将 ROMBASIC 定义为 ROMBASIC macro-instruction expansion layer（宏
指令展开层）。它可以把 WINDOW、BROADCAST、MAC、STREAM_IN、STREAM_OUT
和 WAIT 展开为 descriptor 或 instruction sequence，同时让分支与异常
回到 CPU fallback。该层尚未实现，也不计入当前 N=4 测量。

~~~basic
FOR x = 0 TO W - 1 STEP 4
  y = STENCIL3(WINDOW(x), COEFF)
  STREAM_OUT y
NEXT x
~~~

~~~mermaid
flowchart LR
    SRC["BASIC source"]
    CPU["CPU process／runtime"]
    REF["顺序 reference 路径"]
    ROM["ROMBASIC 展开<br/>loop／window／stream ops"]
    IMEM["instruction memory<br/>execution stream"]
    ACC["ASIC／GPU stream 层"]
    SRAM["banked SRAM／shared memory"]
    OUT["stream 输出"]
    SRC --> REF
    SRC --> ROM
    CPU -->|"program／buffer／parameters"| ROM
    ROM --> IMEM
    IMEM --> ACC
    SRAM <--> ACC
    ACC --> OUT
    ACC -. 不支持分支／异常 .-> REF
    REF -. verification／fallback .-> CPU
~~~

目标分层如下：

| 层 | 作用 |
|---|---|
| BASIC 顺序路径 | reference 语义、分支、异常、fallback |
| ROMBASIC 展开 | loop、window、multicast 和 stream 描述 |
| ASIC/GPU 执行层 | 并行执行展开后的 stream |

## GPU 集成契约

集成时可把多个 1D unit 接入现有 GPU 执行层，而不是新建 GPU 编程
API。本仓库固定顺序语义、抽象 WINDOW/BROADCAST/MAC/stream 行为、
buffer／系数 descriptor 以及 start/completion/error 同步。GPU 实现自行
选择 command format、driver、lane/warp 映射、occupancy、cache/shared
memory 路径和 DMA。

以下三层只是架构参考点：

| 层级 | 可能映射 | 主要问题 |
|---|---|---|
| 旗舰 | 每个 SM/CU cluster 放置多个 unit，连接 HBM 或大容量 shared memory | 带宽与复制上限 |
| 中端 | 每个 cluster 放置一个到数个 unit，共享 dispatch/local SRAM | 有效吞吐与面积的平衡 |
| 入门 | 共享一个 unit，或使用小型 CPU/GPU buffer | 最小成立配置与启动开销 |

设 unit 数为 U、每 unit 输出率为 R、每输出操作量为 O、clock 为 f，
理想计算上限为 P_peak = U x R x O x f。有效性能还必须包含内存带宽、
命令供给、occupancy 和 stall。

对同一示例 kernel（complex FP16、3 tap、24 FLOP/output、重叠消除后
10 byte/output），算术强度为 2.4 FLOP/byte。以下是 2026-08-29 的
GeForce 带宽快照；它们不是本 RTL 的测量结果：

| 层级 | 代表 GPU | 带宽 | 带宽 roofline | MAC-4 比 | STENCIL-4 比 |
|---|---|---:|---:|---:|---:|
| 旗舰 | RTX 5090 | 1.792 TB/s | 4.30 TFLOP/s | 约 1,344x | 约 448x |
| 中端 | RTX 5070 | 672 GB/s | 1.61 TFLOP/s | 约 504x | 约 168x |
| 入门 | RTX 5060 | 448 GB/s | 1.08 TFLOP/s | 约 336x | 约 112x |

因此比较对象不是替换整块 GPU，而是减少 global memory 重复读取、向
shared/local buffer 提供规则 stream 的前端或辅助层。只有在同一 kernel
中测量 data movement、有效带宽、功耗和启动开销后，才能讨论集成收益。

## 探索性附录

Self-attention redistribution、纵向／横向／递归反馈以及任意 N-way
扩展仅作为想法保留。它们需要明确的 exchange、reduction、softmax、
时序、fan-out、SRAM 容量和功耗验证；不表示一 cycle 完成或收敛。

本文是简体中文伴随概要；详细技术正本仍为日文文件。
