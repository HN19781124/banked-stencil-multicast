# ASIC 参考比较：line-buffer 与 banked multicast

[日本語（正本）](asic-linebuffer-comparison.md) ／ [English](asic-linebuffer-comparison.en.md) ／ 简体中文

本文是将相同的 `N=4` lane、`M=36` bank 候选、3x3 stencil 和 4-byte 复数
sample 放入 ASIC 时的 reference-only 模型。这里固定 `N` 表示 lane 数，`M`
表示物理 SRAM bank 数。两条路径使用相同的输入、计算和输出契约，但
仓库尚无 line-buffer RTL、统一 PDK 的布局布线或 technology-calibrated
功耗，因此活动计数不是绝对功耗测量。

## 比较契约

~~~mermaid
flowchart LR
    IN[共同输入 tile<br/>complex sample] --> LB[line-buffer<br/>3-row SRAM + window registers]
    IN --> BM[banked multicast<br/>N=4 / M=36-bank 候选]
    LB --> LMAC[共同四 lane 复数 MAC]
    BM --> BMAC[共同四 lane 复数 MAC]
    LMAC --> OUT[共同输出 FIFO／stream]
    BMAC --> OUT
    PDK[相同 ASIC PDK／SRAM／clock／voltage／activity] -.-> LB
    PDK -.-> BM
~~~

两条路径必须使用相同 tile、系数、FP16 与复数 MAC 规则、ready/valid
轨迹、Halo、输出检查、clock、voltage 和 temperature。比较 single-port
情况时，line-buffer 也必须受相同的有效端口预算限制；true-dual-port
情况必须同时报告两条路径的端口数和功耗。

比较中故意给 line-buffer 一个无 stall、无 backpressure 的上限模型，而
banked 路径保留 SRAM load、unique-read、multicast 和 bank schedule 成本。
这是保守比较，不是性能保证。实际 line-buffer 可能因 SRAM/BRAM 端口
冲突、line/row fill、tail/Halo 边界或下游 backpressure 而阻塞。

下表数值是在无 stall 前提下得到的 reference 上限，不包含 line-buffer
可能发生的 stall，也不是 ASIC timing。若使用 load/compute overlap 或
多次 pass，banked 路径还必须同时预留 active 与 prefetch A/B buffer 以及
Halo 容量；其容量、保持功耗和配线成本不会自动出现在计数器中。

## 1024x1024 reference 计数

| 指标 | line-buffer | banked multicast | 解释 |
|---|---:|---:|---|
| 输出 sample | 1,048,576 | 1,048,576 | 相同输入和计算 |
| Storage reads | 2,097,152（2.000/output） | 4,718,592（4.500/output） | reference 计数，无 stall 上限 |
| Storage writes | 1,054,728（1.006/output） | 1,054,728（1.006/output） | 共同 input-stream 保持 |
| Storage access 合计 | 3,151,880（3.006/output） | 5,773,320（5.506/output） | 读写简单相加 |
| Logical window values | 9,437,184（9.000/output） | 9,437,184（9.000/output） | 共同 MAC 输入 |
| Multicast deliveries | 0 | 9,437,184（9.000/output） | banked 固定 fan-out 计数 |
| Core cycles | 262,145 | 262,145 | preload、无 stall reference |
| End-to-end cycles | 263,683 | 525,827（load 串行） | 无 stall 上限；banked overlap 上限 263,682 |

匹配的输出 digest 和完整计数保存在
[ASIC JSON 证据](../../physical/evidence/asic-dataflow-reference-1024.json)，
可由[比较脚本](../../tools/compare_asic_dataflows.py)复现。

## 功耗边界

在两条路径使用相同 ASIC PDK、SRAM macro view、clock/activity、voltage
和物理实现之前，绝对功耗仍未知。与技术无关的符号项为：

    E_LB = R_LB*e_sram_read + W_LB*e_sram_write
          + S_LB*e_window_shift + C*e_common
    E_BM = R_BM*e_sram_read + W_BM*e_sram_write
          + F_BM*e_multicast_fanout + C*e_common

S_LB 表示 window-register 移动，F_BM 表示 multicast fan-out。现有
11.434 mW 的 `N=4`／`M=12` SKY130 探索是独立的 banked ASIC 锚点，不是本 2D
比较的数值。

本文是简体中文伴随概要；详细技术正本仍为日文文件。
