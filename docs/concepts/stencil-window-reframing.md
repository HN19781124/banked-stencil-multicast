# ステンシル窓の再定式化

## Sliding-window buffer から unique-sample multicast へ

> This is a conceptual explanation of the representation used by the
> repository's measured `N=4` baseline. It is not a new verification result
> and does not claim that every stencil implementation can eliminate line or
> plane buffers.

ステンシル計算は、画像処理、物理シミュレーション、数値計算、AI向け
アクセラレータなどで繰り返し現れる基本操作です。各出力要素が周囲の
小さな入力窓に依存するため、計算式は単純でも、データの表現方法が
メモリ構成と配線量を大きく左右します。

この文書では、窓を「スライドするバッファ」として保持する見方と、窓を
「重複を除いたユニークサンプルの集合」として扱う見方を比較します。
後者では、論理的な重複要求を一度の読み出しとmulticastに分離できます。

## 1. 4-lane／3-tapの例

4つの隣接レーンが3-tap窓を同時に要求すると、論理上の要求は12個です。

| Lane | 入力窓 |
|---|---|
| 0 | `{s0, s1, s2}` |
| 1 | `{s1, s2, s3}` |
| 2 | `{s2, s3, s4}` |
| 3 | `{s3, s4, s5}` |

しかし、集合として必要なのは次の6サンプルだけです。

$$
U = \{s_0,s_1,s_2,s_3,s_4,s_5\},\qquad
|U| = N+T-1 = 4+3-1 = 6
$$

したがって、12個の論理tap要求をそのまま12回の物理読み出しにする必要は
ありません。6サンプルを一度ずつ読み出し、消費するレーンへ分岐すれば、
重複の扱いを読み出し側から配線側へ移せます。

## 2. 従来の見方：窓をスライディングバッファとして保持する

窓をバッファとして扱う実装では、次の状態を維持する必要があります。

- 次の窓へ進むたびに、入力要素をシフトまたは再配置する。
- 隣接窓に現れる同じ入力要素を、複数の要求として扱う。
- 2Dではline buffer、3Dではplane bufferなど、保持する状態を増やす。
- 同じcycleに要求が集中すると、multi-port SRAMや複雑なbank scheduleで
  衝突を回避する。

line bufferやmulti-port構成が常に不適切という意味ではありません。ここで
問題にしているのは、窓の重複をデータ移動と個別読出しとして表現すると、
重複、移動、bank競合が別々の付加コストとして現れる点です。

## 3. 再定式化：窓をユニークサンプル集合として扱う

隣接する`N`レーンと`T` tapの連続窓では、ユニークサンプル数は

$$
U=N+T-1
$$

です。提案するデータ面では、次の順序で処理します。

1. サンプルをSRAMセル間でシフトせず、banked SRAMへ静的に配置する。
2. そのcycleに必要な`U`個のユニークサンプルを各1回読み出す。
3. SRAM出力をmulticast配線で、サンプルを消費する複数レーンへ分岐する。
4. レーン側でそれぞれのtap窓を再構成して演算する。

現行の`N=4`／`T=3` baselineでは、12個の論理要求を6 readに圧縮し、
6本のデータを4レーンへ配送します。「データ移動ゼロ」はSRAMセル間の
シフト／再配置を行わないという意味であり、SRAM読み出しと配線上の
信号伝搬がなくなるという意味ではありません。

## 4. 表現の違い

```mermaid
flowchart LR
    Q["N=4, T=3 の隣接窓<br/>W0={s0,s1,s2}<br/>W1={s1,s2,s3}<br/>W2={s2,s3,s4}<br/>W3={s3,s4,s5}<br/>論理要求 N×T=12"]:::neutral

    Q -->|窓をバッファとして保持| C0
    Q -->|窓をユニーク集合へ再定式化| R

    subgraph CONV["従来：sliding-window buffer"]
        direction TB
        C0["sliding / line / plane buffer<br/>次元が増えるほど状態が増加"]:::old
        C0 --> C1["シフト・再配置<br/>余分なデータ移動"]:::old
        C1 --> C2["重複読出し<br/>同じ入力を複数回要求"]:::old
        C2 --> C3["bank conflict回避<br/>multi-port／複雑なschedule"]:::old
        C3 --> C4["各laneへ供給"]:::old
    end

    R["表現の変更<br/>window = unique samples + fan-out"]:::pivot --> U0

    subgraph PROP["提案：unique-sample multicast"]
        direction TB
        U0["U={s0,s1,s2,s3,s4,s5}<br/>U=N+T-1=6"]:::new
        U0 --> U1["静的banked SRAM<br/>single-port<br/>各sampleを1回読出し<br/>セル間シフトなし"]:::new
        U1 --> U2["multicast配線<br/>必要なlaneへ直接分岐"]:::new
        U2 --> U3["Lane 0…3<br/>各3 tapを受信"]:::new
        U3 --> U4["y0 y1 y2 y3"]:::new
        U1 -.-> U5["静的bank式＋phase<br/>R_t ∩ W_t = ∅を事前検査"]:::proof
    end

    OUT["12 logical requests → 6 unique reads<br/>重複・移動・衝突を構造的に切り分ける"]:::result
    U0 --> OUT

    classDef neutral fill:#f8fafc,stroke:#64748b,stroke-width:1px;
    classDef old fill:#fff1f2,stroke:#e11d48,stroke-width:1px;
    classDef pivot fill:#f3e8ff,stroke:#9333ea,stroke-width:1px;
    classDef new fill:#eff6ff,stroke:#2563eb,stroke-width:1px;
    classDef proof fill:#fef3c7,stroke:#d97706,stroke-width:1px;
    classDef result fill:#ecfdf5,stroke:#059669,stroke-width:1px;
```

図の要点は、ステンシル式そのものを変更することではありません。同じ
入力窓を、(a)重複を含むバッファ状態として移動させるか、(b)ユニークな
サンプルの集合として一度だけ読み出し、fan-outするかという表現の違いです。

## 5. これまでに確認した課題

ここでいう「課題」は、ステンシル計算が不可能という意味ではなく、
窓をバッファとして実装したときに設計・検証コストとして現れたものです。
解消済みの範囲と、まだ残っている課題を分けて記載します。

| 課題 | リポジトリで確認した状態 | 現在の扱い |
|---|---|---|
| 重複窓の読出し | `N=4`／`T=3`では論理12要求に対しunique readは6。有限17x3 tileではtailを含めて153→90 read | unique-sample化とmulticastで定常部を圧縮。tail／境界は別扱い |
| バッファのシフト／再配置 | sliding／line／plane bufferでは、窓を進めるたびに状態移動が必要 | 静的SRAM配置を採用。セル間シフトをしないことを主張 |
| single-port bank競合 | `N=4`の36周期状態と統合RTLでread/write conflict 0を確認 | `N=4`のreference／RTL／formal範囲で対処済み。大きな`N`は未検証 |
| 行端・Halo・部分lane | 全幅1〜257のreferenceで確認。外部controller側はtransition bubble固定で、部分lane maskが必要 | `N=4`のreference／RTL範囲で実装。異なる行のcontrollerは未完 |
| backpressure／外部DMA | stress RTLではoutput stall 8 cycleを観測。外部DMA wrapperと任意長トラフィックは未実装 | 固定遅延は規則区間・nostall前提に限定 |
| 配線・物理タイミング | SKY130探索runは4 MHz制約。hold WNS `-1.36 ns`、antenna 49 nets／59 pins、SRAM GDS stream-out停止を記録 | 探索的physical evidenceのみ。100 MHz sign-offやSRAM内部sign-offは未完 |
| スケール時のfan-out／容量 | `N=6`は一次試算、`N=16`は前提付き数学的導出。直接配線とpyramidの比較は未実施 | レーン数ごとにRTL、formal、P&Rを独立検証 |

根拠は[検証範囲表](../../VALIDATION.md)、[RTL性能レポート](../../physical/evidence/RTL-PERFORMANCE-REPORT.md)、
[物理検証レポート](../../physical/evidence/PHYSICAL-VERIFICATION-REPORT.md)に固定しています。

## 6. 何が変わり、何が残るか

| 論点 | unique-sample multicastで変わる点 | 残る検証課題 |
|---|---|---|
| 窓の重複 | `N*T`要求を`U=N+T-1` readへまとめる | 不連続窓や境界窓では別スケジュールが必要 |
| データ移動 | SRAMセル間のシフト／再配置を避ける | DMA、FIFO、行切替、Halo投入は残る |
| bank競合 | 静的bank式とphaseで集合を事前検査する | 異なる行、可変アドレス、書戻しは個別検証が必要 |
| 配線 | 一度読んだ値を複数laneで共有する | fan-out、配線遅延、バッファ段数、電力は残る |
| 外部メモリ | 規則区間で読み出し回数と中間書戻しを抑える余地 | DRAM待ち、backpressure、帯域隠蔽はシステム条件依存 |

2D／3Dへの拡張でも、line／plane bufferが物理的に必ず不要になると主張
するものではありません。タイル内の静的配置と階層型multicastで、移動と
重複読出しをどこまで減らせるかを、次元ごとに独立して検証する必要があります。

## 7. このリポジトリでの位置づけ

- `N=4`／`M=12`の無衝突スケジューラ、RTL、formal、generic synthesisは
  [README](../../README.md)と[VALIDATION.md](../../VALIDATION.md)に記載した現行baselineです。
- `N=6`は一次試算、`N=16`は`U=18`・`M=36`・phase差18の前提付き数学的
  導出であり、16-lane RTLや実チップの実測ではありません。
- この文書は上記の数値を新たに保証するものではなく、なぜ重複窓を
  unique sampleへ再定式化するのかを説明するための補助文書です。
- 固定遅延は、backpressure、外部DRAM待ち、prologue／epilogueを除く
  規則区間の決定性レイテンシとして扱います。

## English summary

Stencil operators are simple mathematically, but a sliding-window
representation turns overlap into repeated reads, buffer shifts, and bank
conflicts. For `N` adjacent lanes and a contiguous `T`-tap window, the union
contains only `U=N+T-1` unique samples. The proposed data path keeps those
samples statically placed in single-port banked SRAM, reads each sample once,
and multicasts the SRAM outputs to the consuming lanes. This changes the
representation of the data path; it does not remove physical fan-out, timing,
power, boundary handling, DRAM waits, or backpressure. The repository's
measured scope is the `N=4`／`M=12` baseline; larger `N` values remain estimates
or mathematical outlooks until independently verified.
