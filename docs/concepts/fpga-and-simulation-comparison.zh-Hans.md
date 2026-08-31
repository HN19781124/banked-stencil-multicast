# FPGA 适用性与仿真边界

[日本語（正本）](fpga-and-simulation-comparison.md) ／ [English](fpga-and-simulation-comparison.en.md) ／ 简体中文

本文是说明性伴随资料，说明将已测量的 N=4 基线映射到 FPGA 时可以检查
哪些内容，以及哪些量适合在相同条件下比较。它不是新的测量结果，也不
属于 v0.3.0 的硬件 sign-off。

## FPGA 可观察的量

现有 RTL 包含同步 single-port SRAM 行为、FIFO、multicast、复数 MAC 和
AXI 侧接口。固定目标器件和工具流程后，可以从相同 RTL 得到以下量：

~~~mermaid
flowchart LR
    HOST["CPU／主机"] --> CTRL["AXI-Lite／控制面"]
    STREAM["AXI-Stream 输入"] --> ENGINE["N=4 engine RTL"]
    CTRL --> ENGINE
    ENGINE --> OUT["AXI-Stream 输出"]
    ENGINE --> MAP{"FPGA 实现"}
    MAP --> BRAM["BRAM／URAM／M20K"]
    MAP --> DSP["DSP 或 LUT 复数 MAC"]
    MAP --> ROUTE["配线／fan-out／时序"]
    BRAM --> REPORT["资源／Fmax／功耗估算"]
    DSP --> REPORT
    ROUTE --> REPORT
~~~

| 量 | FPGA 可得到的结果 | 当前状态 |
|---|---|---|
| 逻辑移植 | compile、复位、ready/valid、输出一致 | RTL 已检查；未做 vendor run |
| 存储推理 | block-RAM 数量、宽度／深度、读写规则 | 依赖器件和推理设置 |
| 计算资源 | DSP、LUT、FF、乘法器推理 | 依赖器件 |
| 时序 | 实现后的 Fmax 与 setup/hold slack | 未测量 |
| 吞吐 | 将 RTL cycle 间隔换算为实际 clock | 实际 clock 未测量 |
| 功耗 | vendor estimator 或板级／器件测量 | 未测量 |
| 外部存储 | DDR／DMA burst、延迟、backpressure | DMA wrapper 未实现 |

FPGA 的 Fmax 或功耗估算不能直接外推到 SKY130 silicon、量产 qualification
或其他 FPGA 系列。反过来，某个 FPGA 映射失败也不能单独否定使用不同
SRAM、DSP 和配线资源的 ASIC macro。

## 同条件仿真契约

详细比较契约见 [FPGA line-buffer 比较](fpga-linebuffer-comparison.zh-Hans.md)。
两条路径必须使用相同 input tile、系数、复数 reference 算术、输出检查、
Halo 和 ready/valid 轨迹。line-buffer 模型给出无 stall、无 backpressure
的上限，而 banked 路径保留 SRAM load、unique-read、multicast 和
bank schedule 成本。

无 stall 是比较边界，不保证实际 line-buffer 永不阻塞。BRAM/SRL 端口
冲突、line/row fill、tail/Halo 处理和下游 backpressure 都可能引入
blocking 或 stall。为 overlap 或多次 pass 预留的 A/B buffer 与 Halo
容量也是实际资源，必须单独报告。

~~~mermaid
flowchart TD
    V["相同 vector／系数／tile"]
    V --> A["unique read + multicast"]
    V --> B["lane 局部 window read"]
    V --> C["shift／line buffer"]
    V --> D["register exchange"]
    A --> M["cycle／access／stall／正确性比较"]
    B --> M
    C --> M
    D --> M
~~~

最低指标包括 first-output latency、steady output interval、每 cycle 的
lane 结果数、logical／unique read、write、bank conflict、multicast
fan-out、FIFO occupancy、stall cycle、边界 bubble，以及 bit-exact 输出
和 sideband。仿真器 wall-clock 时间不是硬件速度；先比较 cycle，再用
FPGA post-route Fmax 换算时间。

## 公开边界

- 已公开基线是 N=4、M=12：reference、RTL、formal、generic synthesis
  和探索性 physical evidence。
- Vendor synthesis、place-and-route、实板测量、外部 DDR 以及 line-buffer
  RTL 都是独立的后续评估物。
- 大规模 replay 可用以下命令复现：
  python tools/compare_2d_dataflows.py --width 1024 --height 1024
- 新增比较模型时必须保持输入契约，不能覆盖基线数值。

本文是简体中文伴随概要；详细技术正本仍为日文文件。
