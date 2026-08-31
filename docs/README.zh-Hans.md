# 验证与物理实现资料

[日本語（正本）](README.md) · [English](README.en.md) · 简体中文

本目录收录 banked-stencil 数据通路的需求、接口契约、验证边界和物理设计
证据。本文统一使用 `N` 表示 lane 数、`M` 表示物理 SRAM bank 数；“12-bank／
4-lane”始终指 `N=4、M=12`。编号文件的详细技术正本仍为日文；本页提供
简体中文导航，不改变任何数值或主张。

## 语言维护方针

参阅[语言维护方针](languages/LANGUAGE-POLICY.zh-Hans.md)。新规格先写入日文
正本，再同步到英文和简体中文概要及链接。

## 编号规格

| ID | 中文范围 | 日文正本 |
|---|---|---|
| 01 | 产品需求与验收目标 | [01-product-requirements.md](01-product-requirements.md) |
| 02 | 复数 binary16／binary32 数值规则 | [02-numerical-specification.md](02-numerical-specification.md) |
| 03 | 架构、流水线、AXI 接口、CSR 与错误 | [03-architecture-and-interfaces.md](03-architecture-and-interfaces.md) |
| 04 | SRAM 映射、流式传输、Halo、FIFO、DMA 与宏接受条件 | [04-memory-streaming-and-dma.md](04-memory-streaming-and-dma.md) |
| 05 | 时钟、复位、电源、CDC、scan 与 SRAM MBIST | [05-clock-reset-power-dft.md](05-clock-reset-power-dft.md) |
| 06 | 物理设计约束、floorplan、时序、电源完整性和 DRC/LVS | [06-physical-design.md](06-physical-design.md) |
| 07 | 验证级别、formal 属性、覆盖率与 sign-off gate | [07-verification-and-signoff.md](07-verification-and-signoff.md) |
| 08 | 制造交付、封装输入与硅测试计划 | [08-manufacturing-handoff.md](08-manufacturing-handoff.md) |
| 09 | 风险登记与关闭规则 | [09-risk-register.md](09-risk-register.md) |
| 10 | 需求可追溯矩阵 | [10-traceability-matrix.md](10-traceability-matrix.md) |
| 11 | Git、标签、release、CI 与公开流程 | [11-release-and-git.md](11-release-and-git.md) |
| 12 | Magic technology 选择与 GDS 交付 | [12-magic-tech-selection.md](12-magic-tech-selection.md) |
| 13 | 设计空间探索与 N=16 验证候选 | [13-design-space-exploration.md](13-design-space-exploration.md) |

## 概念与比较资料

- [Stencil 窗口重新表述（简体中文）](concepts/stencil-window-reframing.zh-Hans.md) ／ [English](concepts/stencil-window-reframing.en.md) ／ [日本語](concepts/stencil-window-reframing.md)
- [ROMBASIC／GPU 集成展望](concepts/rombasic-gpu-integration.zh-Hans.md) ／ [日本語](concepts/rombasic-gpu-integration.md) ／ [English](concepts/rombasic-gpu-integration.en.md)
- [FPGA 比较契约](concepts/fpga-and-simulation-comparison.zh-Hans.md) ／ [日本語](concepts/fpga-and-simulation-comparison.md) ／ [English](concepts/fpga-and-simulation-comparison.en.md)
- [FPGA line-buffer 比较](concepts/fpga-linebuffer-comparison.zh-Hans.md) ／ [日本語](concepts/fpga-linebuffer-comparison.md) ／ [English](concepts/fpga-linebuffer-comparison.en.md)
- [ASIC 参考比较](concepts/asic-linebuffer-comparison.zh-Hans.md) ／ [日本語](concepts/asic-linebuffer-comparison.md) ／ [English](concepts/asic-linebuffer-comparison.en.md)
- [功耗与数据移动参考](concepts/energy-measurement-references.zh-Hans.md) ／ [日本語](concepts/energy-measurement-references.md) ／ [English](concepts/energy-measurement-references.en.md)

比较报告明确把无 stall 的 line-buffer 模型标为上限。实际 line-buffer 可能因
端口冲突、填充／边界处理或下游 backpressure 而发生阻塞。

## 证据与复现

- [English validation summary](../VALIDATION.en.md) ／ [简体中文](../VALIDATION.zh-Hans.md) ／ [日本語](../VALIDATION.md)
- [RTL 性能报告](../physical/evidence/RTL-PERFORMANCE-REPORT.md)
- [2D 数据流证据](../physical/evidence/2d-dataflow-comparison-1024.json)
- [ASIC 活动证据](../physical/evidence/asic-dataflow-reference-1024.json)
- [物理执行 provenance](../physical/evidence/sky130-magic-gds-import-hold1/PROVENANCE.md)

这些链接描述的是可复现证据，不是 tapeout 或量产 qualification。
