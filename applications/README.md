# Applications

[English](README.en.md) · 日本語 · [简体中文](README.zh-Hans.md)

このディレクトリは、既存の `banked-stencil-multicast` コアを異なる用途へ転用する応用ノートのローカルスナップショットです。
公開用の正本は、DOI単位を分けられる独立した3つの派生repoに置きます。

| 応用例 | 独立repo（正本） | このrepoのスナップショット | 現在の段階 |
|---|---|---|---|
| Precision Clock / Timer | [banked-precision-clock-multicast](https://github.com/HN19781124/banked-precision-clock-multicast) | [`precision-clock`](precision-clock/README.md) | 参照モデル＋テスト |
| Systolic Array | [banked-systolic-multicast](https://github.com/HN19781124/banked-systolic-multicast) | [`systolic-array`](systolic-array/README.md) | 参照モデル＋テスト |
| TDOA Sensor Array | [banked-tdoa-multicast](https://github.com/HN19781124/banked-tdoa-multicast) | [`tdoa-sensor`](tdoa-sensor/README.md) | 参照モデル＋テスト |

各応用は、既存コアのRTLを変更せず、参照モデル・境界条件・再現手順を先に定義します。
実測、試算、未検証の主張は混ぜません。

3応用の固定ケースは [`evidence/three-application-performance.json`](evidence/three-application-performance.json) に保存し、`applications/generate_performance_report.py --check` で再計算結果を照合します。独立repoを先に更新し、このスナップショットは対応関係の確認用に保ちます。
