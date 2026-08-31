# FPGA 比较：line-buffer 与 banked multicast

[日本語（正本）](fpga-linebuffer-comparison.md) ／ [English](fpga-linebuffer-comparison.en.md) ／ 简体中文

本文定义相同 3-tap、4-lane 工作负载在 FPGA 上的公平 reference 比较。
两条路径使用密集的 4-byte 复数 sample 网格和 2D reference 模型；尚未
在特定器件上完成布局布线，因此不宣称 FPGA 实现结果。

## 两条数据路径

~~~mermaid
flowchart LR
    IN["相同 AXI-Stream 输入<br/>4-byte 复数 sample"] --> LB
    IN --> BM
    subgraph LB["line-buffer 路径"]
        LB0["BRAM／SRL 行与窗口存储"]
        LB1["shift／window update"]
        LB2["四 lane MAC"]
        LB0 --> LB1 --> LB2
    end
    subgraph BM["banked multicast 路径"]
        BM0["静态 bank 配置<br/>12-bank 基线"]
        BM1["6 个 unique read"]
        BM2["固定 multicast"]
        BM3["四 lane MAC"]
        BM0 --> BM1 --> BM2 --> BM3
    end
    LB2 --> OUT["相同 AXI-Stream 输出"]
    BM3 --> OUT
~~~

两条路径共用 input FIFO、output FIFO、系数、FP16 adapter 规则、Halo、
边界策略和 ready/valid 轨迹。1D 基线为 N=4、T=3、M=12；2D reference
候选使用 18 个 unique read 和 M=36，但它不是 RTL 或 FPGA 测量。

## 输入与实现契约

两条路径都接收相同的密集 row-major W x H 网格。不得把预展开的 window
数组作为某一侧隐藏的预处理。最低输入包括同 seed 的 impulse、ramp 和
有限随机数据，并保持系数、padding、有效输出坐标和 sideband 相同。

| 条件 | 固定内容 |
|---|---|
| 器件 | FPGA 型号、speed grade、BRAM/DSP/SRL 资源 |
| 工具 | vendor synthesis/P&R 版本、seed、retiming |
| clock | 相同 clock 约束和 I/O 延迟假设 |
| 工作负载 | N=4、T=3、4-byte 复数 sample、相同 tile/Halo/系数 |
| 存储 | 相同有效 single-port 或相同 true-dual-port 预算 |
| MAC | 相同 DSP 推理许可；不能混用 LUT 与 DSP case |
| 检查 | bit-exact 输出、lane mask、TLAST、复位、stall 保持 |

比较故意把 line-buffer 置于无 stall、无 backpressure 的优化上限模型，
把 SRAM load、unique-read、multicast 和 bank schedule 成本保留在 banked
一侧，因此是对本方案不利的保守比较。真实 line-buffer 可能因 BRAM/SRL
端口冲突、line/row fill、tail/Halo 边界或下游 backpressure 而阻塞或
stall。为 overlap 或多次 pass 预留的 A/B buffer 与 Halo 也必须计入
BRAM/SRL 容量、保持功耗和配线。

## 指标与解读

测量 first-output latency、steady output interval、有效 lane 吞吐、每
cycle 输入字节、logical/unique read、write、BRAM 端口使用、LUT/FF/
BRAM/SRL/DSP 资源、post-route Fmax、fan-out、FIFO occupancy、stall cycle
和相同 activity 下的功耗。仿真比较 cycle；只有 post-route Fmax 才能
换算 FPGA 时间。

下面的 reference replay 输出 digest 一致且 core 输出率相同。它是无
stall 上限，不包含 Fmax、实际时间或 line-buffer 可能发生的 stall。

## 1024 x 1024 reference replay

输入 digest：
92f25b9ca748fe02a4d7d14a7fc0df7d36507f6af090dc1f25f175414de39ba9

| 指标 | line-buffer | banked multicast |
|---|---:|---:|
| 输出 beat | 262,144 | 262,144 |
| End-to-end cycle | 263,683 | 525,827（load 串行） |
| preload 后 core cycle | 262,145 | 262,145 |
| load/compute overlap 上限 | — | 263,682 |

overlap 行是模型上限，不是已实现的调度。这里故意列出串行 load，
使 banked 路径的加载成本保持可见。完整条件和计数见
[2D JSON 证据](../../physical/evidence/2d-dataflow-comparison-1024.json)。

## 当前状态

已完成：banked N=4 reference、RTL、formal 检查，以及共同 2D 输出
digest/cycle 基线。未完成：line-buffer RTL、vendor P&R、实板测量和
统一 FPGA 结果。因此不宣称 FPGA 速度、面积或功耗优势。

本文是简体中文伴随概要；详细技术正本仍为日文文件。
