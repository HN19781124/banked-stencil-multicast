# Precision Clock / Timer

既存の `banked-stencil-multicast` コアを、時刻基準・タイマー用途へ転用する応用例です。

## 目的

- 閉じた同報経路で共通の基準tickを配布する。
- 各laneの既知の配線遅延を補正値として扱う。
- クロック数だけに依存しない時間差計測の可能性を、再現可能なモデルとRTLで確認する。

## 境界

ここは応用例です。既存コアのRTLを変更せず、接続条件・遅延モデル・校正方法を別に検証します。
現段階では提案であり、実チップの精度や衛星用途の成立を主張しません。

## 検証予定

1. 基準tickと各配線遅延の参照モデル
2. 遅延差・ジッタ・校正誤差の境界テスト
3. 同じ条件を再生するRTLテスト
4. 実測・試算・未検証項目を分けた記録

## 現在の実装

`reference/clock_model.py` に、整数fs単位の基準tick、lane別の配線遅延、既知tickからの校正、補正後の共通時刻、tick間隔、deadlineを実装しています。
これは時間関係を固定する参照モデルであり、fs精度や実チップのクロック精度を意味しません。

```text
python -B -m unittest discover -s applications/precision-clock/tests -v
```
