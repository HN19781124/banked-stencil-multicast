# 設計空間試算と次の検証候補

この資料は、`N` レーン／`T` tap の候補を同じ前提で比較し、次にRTLへ持ち込む構成を再現可能に選ぶためのものです。試算は一次モデルであり、配置配線後の周波数、電力、面積、SRAM macro sign-offを保証しません。

## 1. 実行方法

```shell
python tools/explore_design_space.py \
  --json build/design-space-report.json \
  --csv build/design-space-report.csv
```

`--lanes 4,6,8,12,16,24,32`、`--taps`、`--clock-mhz`、`--depth-words`で候補と前提を変更できます。選定条件も`--max-capacity-kib`、`--max-endpoints`、`--min-reduction`で明示的に変更できます。

## 2. モデルと前提

隣接する`N`レーンが連続する`T` tap窓を処理する場合、重複排除後の読み出し数を`U`とすると、対称ping-pong単一ポートbank familyは次式です。

$$
U=N+T-1,\qquad M=2U
$$

buffer phaseは`0`と`U`、読み出しは`U`語、反対bufferへの先読み書き込みは`N`語とします。したがって`M-(U+N)=T-1` bankが各cycleでidleになります。`depth-words`はA/Bを合わせた1物理bankあたりの論理深さです。現在の2 KiB（512×32 bit）macroをA/Bで使う基準は、合計1024 word/bank、48 KiB（12 bank）に対応します。

`T=3`ではidle bankが常に2つ残ります。これは均熱、clock gating、power gatingの候補領域として利用できますが、温度分布・リーク・動的電力への効果はこの一次試算では測定していません。

一次モデルの指標は次のとおりです。

- duplicate reduction: `1-U/(N*T)`
- on-chip帯域: `read=U*sample_bytes*f`、`write=N*sample_bytes*f`
- 容量: `M*depth_words*sample_bytes`
- serialized MAC: 1 tap MAC／lane／cycle、`N*8*f` FLOP/s
- unrolled MAC: `T` tap MAC／lane／cycle、`N*T*8*f` FLOP/s
- multicast endpoint: `N*T`（各laneのtap入力ポート）

complex MACは、複素乗算4乗算＋加算と累積加算を合わせた8 real FLOPとして数えます。`serialized`は現在のMAC-4型、`unrolled`は各laneにT tap分の演算器を置く理想上限です。

## 3. デフォルト掃引結果

デフォルトは`N=1..32`、`T=3`、complex FP16の4 byte/sample、100 MHz、1024 word/bankです。選定用の設計 envelopeは、基準の3倍に相当する`capacity <= 144 KiB`、直接接続時の`multicast endpoints <= 48`、重複削減率`>= 60%`としました。これは法則から自動的に決まる唯一の最適値ではなく、比較可能な予算を固定するための公開した仮定です。下表は代表行で、全候補はJSON／CSVに保存されます。

| N | U | M | 削減率 | 容量 KiB | read GB/s | 合計 GB/s | serialized GFLOP/s | unrolled GFLOP/s | endpoints | 判定 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 4 | 6 | 12 | 50.0% | 48 | 2.4 | 4.0 | 3.2 | 9.6 | 12 | — |
| 6 | 8 | 16 | 55.6% | 64 | 3.2 | 5.6 | 4.8 | 14.4 | 18 | — |
| 8 | 10 | 20 | 58.3% | 80 | 4.0 | 7.2 | 6.4 | 19.2 | 24 | — |
| 12 | 14 | 28 | 61.1% | 112 | 5.6 | 10.4 | 9.6 | 28.8 | 36 | feasible |
| **16** | **18** | **36** | **62.5%** | **144** | **7.2** | **13.6** | **12.8** | **38.4** | **48** | **selected** |
| 24 | 26 | 52 | 63.9% | 208 | 10.4 | 20.0 | 19.2 | 57.6 | 72 | over envelope |
| 32 | 34 | 68 | 64.7% | 272 | 13.6 | 26.4 | 25.6 | 76.8 | 96 | over envelope |

この envelopeでの理論上の選択は**N=16、T=3、36 bank、18 unique read、16 write、48 multicast endpoint**です。`unrolled`ピークは100 MHz換算38.4 GFLOP/s、現在のMAC-4型の`serialized`換算は12.8 GFLOP/sです。直接配線なら48 endpoint、二分木ならlane-clusterの深さ目安は4段です。これは配線遅延を見積もった値ではありません。機械可読な候補定義は[`manufacturing/candidate-n16.json`](../manufacturing/candidate-n16.json)に固定します。

基準N=4のRTL性能レポートにあるread 2.4 GB/s、write 1.6 GB/s、合計4.0 GB/sおよびserialized 3.2 GFLOP/sは、この一次モデルと一致します。一致はモデルの校正であって、N=16の物理性能を保証するものではありません。

## 4. N=16を尖った候補として検証へ進める理由

N=16は、削減率60%を超えながら、容量144 KiBと48 endpointの境界に収まる最大候補です。N=24以降は理想スループットが増える一方、bank数、配線endpoint、SRAM容量が同時に増え、現在の4-lane physical runからの外挿が大きくなります。したがって、N=16を「最終最適」と断定せず、予算境界上の尖った検証ターゲットとして固定します。

### 検証ゲート

1. **Reference／schedule** — `scalable_cycle_plan(16, 3)`について両ping-pong方向、複数行、長いcycle列を検証し、`R_t`と`W_t`の集合が常に互いに素であることを確認する。
2. **Parameterized RTL** — `N=16`、`T=3`、`M=36`、read 18、write 16、phase差18をパラメータ化し、1-port SRAMの同一cycle read/writeを実装する。
3. **Multicast equivalence** — `s_0..s_17`から各laneの`(s_j,s_{j+1},s_{j+2})`を生成し、16本等の直接配線とbuffered pyramidの両トポロジーで値・宛先・validを一致させる。pyramidにレジスタを入れた場合の追加latencyも測る。
4. **Performance／backpressure** — serialized MACの`16/3 output/cycle`とunrolled MACの`16 output/cycle`を別ケースで測定し、input/output FIFOのstall、tail、行切替bubbleを記録する。
5. **Formal／synthesis** — bank conflict、bank/address一意性、multicast宛先欠落、FIFO overflow、reset復帰をSAT／assertion／generic synthesisで確認する。
6. **Physical exploration** — 36 bankと直接配線／pyramidを同一制約で配置配線し、wire length、fan-out、buffer数、timing、電力、macro面積を比較する。hold／antenna／qualified SRAMが閉じるまでは探索結果であり、製造sign-offではない。

各ゲートは基準N=4の結果を上書きせず、`N=16`専用のRTL、formal、性能、physical証跡として保存します。制約を変更した場合は、同じスクリプトで選定と検証計画を再生成できます。
