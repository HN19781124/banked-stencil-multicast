# 数値演算仕様

## 1. 表現

入力sampleとcoefficientは各32 bitで、`[15:0]`を実部、`[31:16]`を虚部とする。各成分はIEEE 754 binary16で、sign 1 bit、exponent 5 bit、fraction 10 bitとする。内部accumulatorと中間結果はIEEE 754 binary32を使用する。

## 2. 演算順序

lane `j`、tap `k`の入力を `x[j+k] = xr + i*xi`、係数を `c[k] = cr + i*ci` とする。結果は次式である。

```text
real = sum(k=0..2) (xr[j+k] * cr[k] - xi[j+k] * ci[k])
imag = sum(k=0..2) (xr[j+k] * ci[k] + xi[j+k] * cr[k])
```

bit-exact性のため、各成分は次のbinary32 FMA列で評価する。`fma(a,b,c)`は積と加算の間で丸めず、binary32へ1回だけ丸める。

```text
r = +0.0f
i = +0.0f
for k = 0, 1, 2:
    r = fma(fp32(xr[k]), fp32(cr[k]), r)
    r = fma(-fp32(xi[k]), fp32(ci[k]), r)
    i = fma(fp32(xr[k]), fp32(ci[k]), i)
    i = fma(fp32(xi[k]), fp32(cr[k]), i)
out.real = fp16_rne(r)
out.imag = fp16_rne(i)
```

lane間で演算順序を変更してはならない。area最適化で演算器を共有しても、この順序とtransaction tagを維持する。

## 3. 丸め・例外

- rounding modeは全段`roundTiesToEven`固定。
- binary16 subnormalはbinary32へ正確に変換し、flush-to-zeroしない。
- overflowは符号付きinfinityへ丸め、OFとNXを立てる。
- tinyかつinexactな最終結果はUFとNXを立てる。tininess判定はrounding後とする。
- signaling NaN入力、`infinity * zero`、符号の異なるinfinity加算はNVを立てる。
- NaN出力bit patternは符号0のcanonical quiet NaN、binary16 `0x7e00`に統一する。
- exact zeroの符号はIEEE 754 RNE規則に従う。全入力が`+0`の場合は`+0`。
- DZは本演算に除算がないため常に0。

laneごとの`NV/OF/UF/NX`をoutput sidebandへ付加し、transaction内の全laneをORした値をsticky CSRへ保持する。sticky bitはwrite-one-to-clearとする。

## 4. 係数

3個のcomplex coefficientは全4 laneで共有する。coefficient registerはidle時だけ更新可能で、busy中のwriteはSLVERRとerror statusを生成する。START受理時にshadow registerからactive registerへatomic commitする。

## 5. 最低限のdirected vector

| ID | input / coefficient | 期待値 |
|---|---|---|
| NUM-V001 | 全入力`1+0i`、全係数`1+0i` | 全lane `3+0i` |
| NUM-V002 | 全入力`0+1i`、全係数`0+1i` | 全lane `-3+0i` |
| NUM-V003 | impulse input、中央係数のみ`1+0i` | 中央sampleのlane別転送 |
| NUM-V004 | `+0/-0`の全組合せ | IEEE signed-zero規則 |
| NUM-V005 | min/max subnormal、min normal、max finite | bit-exact reference一致 |
| NUM-V006 | quiet/signaling NaN、±infinity | canonical NaNとflag一致 |
| NUM-V007 | half-way rounding pattern | ties-to-even一致 |
| NUM-V008 | overflow/underflow境界 | resultとOF/UF/NX一致 |

random検証はreference modelでbinary16全分類を重み付き生成し、最低100万transactionを実行する。
