# 文書の言語運用方針

## 正本と派生文書

- README.md と docs/*.md の番号付き仕様は、日本語の技術正本とする。
- README.en.md／README.zh-Hans.md は、正本から展開する公開概要とする。
- 数値、要求ID、コマンド、ファイル名、検証境界は、正本と派生文書で一致させる。
- 完全翻訳でない文書は、タイトルやリンクで「概要」「日本語正本」と明記し、翻訳済みであるかのように扱わない。

## 更新手順

1. まず日本語正本へ仕様・証跡・制約を追加する。
2. 英語・简体中文の概要、図、検証境界表へ同じ変更を反映する。
3. 数値を変更した場合は、機械可読JSONとリンク先を確認する。
4. 言語別リンク、CITATION.cff、ライセンス範囲を確認する。

この構成は翻訳の重複管理を避け、仕様の意味と数値を一か所で保守するためのものです。

## 対応範囲

| 層 | 日本語 | English | 简体中文 |
|---|---|---|---|
| 公開入口 | README.md | README.en.md | README.zh-Hans.md |
| 詳細仕様 | docs/*.md | docs/README.en.mdから正本へ案内 | docs/README.zh-Hans.mdから正本へ案内 |
| 概念説明 | docs/concepts/*.md | .en.mdがある資料 | .zh-Hans.mdがある資料 |
| 検証結果 | VALIDATION.md／evidence | VALIDATION.en.md | VALIDATION.zh-Hans.md |
