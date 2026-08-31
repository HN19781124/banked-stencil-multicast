# 验证摘要

[日本語（正本）](VALIDATION.md) · [English](VALIDATION.en.md) · 简体中文

本摘要按照初始 bank-scheduler 公开内容复现外围功能和物理流程检查。本文
统一使用 `N` 表示 lane 数、`M` 表示物理 SRAM bank 数；“12-bank／4-lane”
表示 `N=4、M=12`。每个 PASS 只适用于表中注明的边界；制造 sign-off 以
[docs/07-verification-and-signoff.md](docs/07-verification-and-signoff.md) 为准。

| 项目 | 方法 | 状态 |
|---|---|---|
| 行边界、Halo、部分 lane | 宽度 1–257、每个 issue、两种 buffer 方向的 reference model | 完成 |
| 跨行同时访问 | 验证所有 row pair 的 reference phase compensation；初始产品固定插入 transition bubble | reference 完成／controller 未实现 |
| SRAM 读延迟与 multicast RTL | 12 个同步 single-port SRAM 模型和 6-to-4x3 multicast 的 cycle 精确仿真 | 完成 |
| 复数 MAC 与 FP16 规则 | bit-exact reference、256-vector RTL、product RTL | RTL 完成／未运行 gate-level |
| 输入 load 与 FIFO 安全 | 在 STATE_LOAD FIFO 边界用 simulation-only bank assertion 检查，验证 occupancy／underflow／overflow，并确认接收 18 个 input beat | baseline RTL 完成；外部 DMA／CDC 不在范围 |
| 2D 数据流比较 | 相同密集复数 tile、3x3 stencil、输出 digest、cycle／带宽指标；1024x1024 digest 一致 | reference 完成；未运行 FPGA RTL／P&R（[证据](physical/evidence/2d-dataflow-comparison-1024.json)） |
| ASIC 参考比较 | 相同输入的 line-buffer／banked-multicast 活动计数器和 technology-calibrated 功耗边界 | 仅 reference；无绝对功耗、line-buffer RTL 或 P&R（[证据](physical/evidence/asic-dataflow-reference-1024.json)） |
| DMA 与 backpressure | FIFO／engine／product 随机路径 | 部分完成；外部 DMA wrapper 未实现 |
| 基线 engine 性能 | 17x3 tile、无 stall／固定 LFSR backpressure、Icarus RTL | 完成（[报告](physical/evidence/RTL-PERFORMANCE-REPORT.md)）；未评估物理频率 |
| 分阶段性能 | control／load／window read／capture-multicast／MAC／output 的 cycle 测量 | 完成（[报告](physical/evidence/RTL-PERFORMANCE-REPORT.md#段別サイクル分解)） |
| GPU 比较 | 对 3-tap 复数 FP16 进行阶段对应，并根据公开内存带宽计算 roofline | 规格比较完成；未运行 GPU（[报告](physical/evidence/GPU-COMPARISON-REPORT.md)） |
| N-way 设计空间估算 | 一次带宽、容量、multicast endpoint 和理想 MAC 扫描 | 完成；选择 N=16 作为下一 RTL 候选，物理性能未验证 |
| 单元复制功耗估算 | 以 4 MHz OpenROAD 锚点计算 1／2 单元理想线性缩放 | 估算完成（[报告](physical/evidence/power-scaling-estimate-20260831.json)）；实际功耗／热裕量未验证 |
| Halo 交换与 NoC multicast | 初始基线止于 AXI 边界；NoC 属于未来扩展 | 不在范围 |
| STA、布局布线、fan-out、功耗 | 固定 SKY130A 探索性 run，250 ns（4 MHz），使用 OpenROAD／Magic／Netgen | 已运行；sign-off 未完成 |

Hold／antenna 违规、GDS／SRAM 内部 sign-off 缺口及保留证据的确切范围，
固定在[物理验证报告](physical/evidence/PHYSICAL-VERIFICATION-REPORT.md)中。
