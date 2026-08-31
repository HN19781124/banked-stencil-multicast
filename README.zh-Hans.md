# 固定延迟型 1D 流式复数数据流协处理器

[日本語](README.md) · [English](README.en.md) · 简体中文

[![DOI: all versions](https://zenodo.org/badge/DOI/10.5281/zenodo.22155033.svg)](https://doi.org/10.5281/zenodo.22155033)

> 面向无冲突流式 stencil 的防御性公开与可执行参考设计：采用单端口 banked SRAM、重叠读取消除、固定 multicast 配送和 ping-pong 缓冲。

本仓库记录面向规则复数局部 stencil 工作负载的**可编程流式协处理器展望**。已测量的 N=4 数据通路与尚未实现的扩展、控制面候选明确分开。

## 状态与范围

- **已测量基线：** N=4 lanes、T=3 taps、M=12 个 single-port SRAM bank；每次 issue 读取 6 个 unique sample，并提供 reference／RTL／formal 证据和探索性 SKY130 physical run。
- **版本：** v0.3.0 是 immutable content freeze，不代表 tapeout、量产、热验证或性能 sign-off。
- **固定延迟：** 仅指规则 in-SRAM streaming 区间内的确定性延迟；不包含外部 DRAM 等待、backpressure、prologue／epilogue 和未实现的 ROMBASIC 层。
- **展望：** N=6 为一次估算，N=16 为数学推导目标，均不是已测量实现。

## 控制面与数据面

控制面描述执行计划；数据面将 sample 静态映射到 SRAM bank，并把每个 unique sample multicast 到使用它的 lane。

~~~mermaid
flowchart LR
    subgraph CTRL["控制／指令面"]
        CPU["CPU／主机"]
        ROM["ROMBASIC 宏指令展开层<br/>（未来、未实现）"]
        CFG["descriptor／CSR<br/>固定计划"]
        CPU --> ROM --> CFG
    end

    subgraph DATA["数据面"]
        IN["输入流／DMA边界"] --> SRAM["静态 SRAM<br/>12 bank／single-port"]
        SRAM --> UNIQUE["unique samples"]
        UNIQUE --> MCAST["固定 multicast 网络"]
        MCAST --> MAC["复数 MAC lanes<br/>N=4 基线"]
        MAC --> OUT["输出 FIFO／下一阶段"]
    end

    CFG -. "窗口／长度／启动条件" .-> SRAM
    CFG -. "指令序列／系数／valid" .-> MAC
~~~

这里的 ROMBASIC 不是通用 BASIC 解释器，而是未来的控制层候选，可展开 WINDOW／BROADCAST／MAC／STREAM 宏指令。它不属于已测量基线。

## 为什么适合规则的大规模数据

对于相邻 lanes 和连续的 T-tap stencil，N*T 个逻辑引用只包含 U=N+T-1 个 unique sample。设计只读取每个 unique sample 一次，不在 SRAM cell 之间移动 sample，并将其 multicast 给所有使用 lane。静态 bank 映射和 compile-time 计划使读写 bank 集合的互斥性可以在执行前检查。

数据面不把 window 生成、shift、写回或再次读取作为必需步骤。并行结果可以作为定义明确的 beat stream 定量交给 output FIFO。这是对稳态操作数和 cell 间移动的结构性削减，不是速度保证；SRAM、multicast 和 FIFO 成本仍然明确保留。

与 line-buffer 路径的比较采用保守条件：line-buffer 模型使用无 stall、无 backpressure 的上限，而 banked 路径保留 SRAM load、unique-read、multicast 和 bank schedule 成本。实际 line-buffer 可能因 SRAM／BRAM／SRL 端口冲突、line／row fill、tail／Halo 边界或下游 backpressure 而发生 blocking／stall。因此比较证据中的 cycle 和 access 数值带有“reference 上限”注释，不是硬件保证。

## 证据边界

| 分类 | 已包含的证据 | 不作出的主张 |
|---|---|---|
| 已验证 | N=4／M=12 reference／RTL／formal、64 个 Python tests、2D 输出 digest 一致、输入 load 的 bank-uniqueness assertion、复数 MAC vectors、FIFO／CSR／MBIST、4 MHz SKY130 探索性 run | N=6／N=12／N=16 的实现性能、全 corner timing、量产 sign-off |
| 一次估算 | N-way 容量／带宽／重叠削减／endpoint／理想 MAC 数值；受约束的 N=16 候选 | 实际配线延迟、实测功耗、实测面积、qualified SRAM 裕量 |
| 未验证 | 参数化 N-way RTL／formal、direct 与 pyramidal multicast 对比、外部 DMA／NoC、gate-level、实板测试、休止 bank 的热／功耗效果 | 产品保证或唯一最优解 |

## 特定空间用途目标（未评估）

一个候选评估场景是：在解调和解码之前，对低轨卫星接收的复数 I/Q（或等价复数 sample）执行规则局部滤波、相关或均衡预处理。光学捕获与跟踪、调制解调器选择、FEC／解码、飞行控制、推进、载人安全、深空通信和整星 qualification 不在范围内。已测量的 N=4 基线和 18-bank 1R1W 候选都没有 flight、辐射或热真空 qualification。双端口存储器可以放宽 access-slot 约束，但不会自动解决 SRAM 辐射特性或散热问题。

| 评估项目 | 该场景的检查项 | 当前状态 |
|---|---|---|
| 辐射 | TID、SEU／SET／SEL、SRAM bit upset、ECC／parity、scrub 周期 | 未评估 |
| 热真空 | 结温、传导路径、热循环、休止 bank 效果 | 没有热／功耗模型 |
| 功耗与带宽 | 同时读／写、峰值功耗、idle／gating、W/sample | 仅有端口模型 |
| 通信质量 | BER／FER、EVM、同步捕获、link margin、packet loss、处理延迟 | 通信／链路模型未评估 |
| 确定性 | 规则区间固定延迟、backpressure、DRAM 等待、fault／reset 恢复 | 仅有逻辑条件 |
| 故障容忍与降级路径 | 双端口 macro／bank／lane 故障、告警封离、N=4 fallback、串行化、重试、safe halt | 路径与切换条件未定义 |
| 物理环境 | 振动、冲击、封装、EMI／EMC、配线和电源裕量 | 未评估 |
| Sign-off | PVT STA、IR／EM、gate-level、辐射与热真空试验、目标 qualification | 不属于本仓库范围 |

~~~mermaid
flowchart LR
    C[18-bank 1R1W 候选<br/>复数 I/Q 预处理] --> R[辐射]
    C --> T[热真空与功耗]
    C --> L[BER / EVM / 同步 / link margin]
    C --> D[确定性与故障恢复]
    C --> P[振动 / EMI / 物理 sign-off]
    C --> F{故障或约束}
    F --> B[降级到 N=4 / 串行化<br/>或 safe halt]
    R --> Q[目标 qualification<br/>未执行]
    T --> Q
    L --> Q
    D --> Q
    P --> Q
    B --> Q
~~~

## 可复现检查

~~~shell
python tools/verify.py
python tools/verify.py --bootstrap --require-rtl
python tools/compare_2d_dataflows.py --width 1024 --height 1024 --report build/2d-dataflow-comparison-1024.json
python tools/compare_asic_dataflows.py --width 1024 --height 1024 --report build/asic-dataflow-comparison.json
~~~

机器可读报告会保留数值结果的前提，包括 line-buffer 无 stall 上限的范围。编号规格、接口、物理设计说明和附录请参阅日文正本。

## 相关文档

- [Stencil 窗口重新表述（简体中文）](docs/concepts/stencil-window-reframing.zh-Hans.md) ／ [English](docs/concepts/stencil-window-reframing.en.md) ／ [日本語](docs/concepts/stencil-window-reframing.md)
- [FPGA 比较契约](docs/concepts/fpga-and-simulation-comparison.zh-Hans.md) ／ [日本語](docs/concepts/fpga-and-simulation-comparison.md) ／ [English](docs/concepts/fpga-and-simulation-comparison.en.md)
- [FPGA line-buffer 比较](docs/concepts/fpga-linebuffer-comparison.zh-Hans.md) ／ [日本語](docs/concepts/fpga-linebuffer-comparison.md) ／ [English](docs/concepts/fpga-linebuffer-comparison.en.md)
- [ASIC 参考比较](docs/concepts/asic-linebuffer-comparison.zh-Hans.md) ／ [日本語](docs/concepts/asic-linebuffer-comparison.md) ／ [English](docs/concepts/asic-linebuffer-comparison.en.md)
- [功耗与数据移动参考](docs/concepts/energy-measurement-references.zh-Hans.md) ／ [日本語](docs/concepts/energy-measurement-references.md) ／ [English](docs/concepts/energy-measurement-references.en.md)
- [ROMBASIC／GPU 集成展望](docs/concepts/rombasic-gpu-integration.zh-Hans.md) ／ [日本語](docs/concepts/rombasic-gpu-integration.md) ／ [English](docs/concepts/rombasic-gpu-integration.en.md)
- [设计空间探索](docs/13-design-space-exploration.md)
- [资料索引](docs/README.zh-Hans.md)
- [验证记录（简体中文）](VALIDATION.zh-Hans.md) ／ [日本語](VALIDATION.md) ／ [English](VALIDATION.en.md)

README.md 与 docs/ 下的编号文件是详细规格的日文正本。本文件是独立的简体中文概要，不增加任何实现主张。
