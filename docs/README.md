# 検証・物理実装参考資料

本ディレクトリは、12-bankスケジューラからend-to-end参照RTL、物理実装の探索までを追試できるよう、設計入力、検証条件、未完項目を分離して管理する。製造を意図するものではなく、実施可能性と検証境界を明確にするための参考資料である。

## 基準

- 製品基準ID: `NB2-SMA-01-MB1`
- 基準ファイル: `manufacturing/baseline.json`
- 現在状態: `pre-tapeout`
- 公開PDK用途: 再現可能な試作・設計検証
- 商用製造: foundry-qualified PDKへの再ターゲットとfoundry sign-offが必須

## 資料

1. [製品要求仕様](01-product-requirements.md)
2. [数値演算仕様](02-numerical-specification.md)
3. [アーキテクチャ／インターフェース](03-architecture-and-interfaces.md)
4. [SRAM／ストリーミング／DMA契約](04-memory-streaming-and-dma.md)
5. [クロック／リセット／電源／DFT](05-clock-reset-power-dft.md)
6. [物理設計基準](06-physical-design.md)
7. [検証・サインオフ計画](07-verification-and-signoff.md)
8. [製造引渡しパッケージ](08-manufacturing-handoff.md)
9. [リスク登録簿](09-risk-register.md)
10. [要求トレーサビリティ](10-traceability-matrix.md)
11. [Git／リリース手順](11-release-and-git.md)
12. [Magic tech選択・GDS受渡し手順](12-magic-tech-selection.md)
13. [設計空間試算とN=16検証候補](13-design-space-exploration.md)

実行済みSKY130 runのコンテナdigest、ツール版、実行コマンド、終了コードは
[physical execution provenance](../physical/evidence/sky130-magic-gds-import-hold1/PROVENANCE.md)を参照する。
基準engineのRTL性能測定は[RTL性能レポート](../physical/evidence/RTL-PERFORMANCE-REPORT.md)に固定する。

## 参考付録

- [ROMBASIC／GPU統合案](concepts/rombasic-gpu-integration.md) — baseline外の将来候補
- [設計空間試算](13-design-space-exploration.md) — 制約付きN-way候補選定とN=16検証ゲート
- [物理実装の再現入口](../physical/README.md)

## 完了の定義

「資料完成」は、要求ID、設計境界、検証方法、合否基準、未解決リスク、製造引渡し物が相互参照できる状態を指す。「tapeout ready」は別判定であり、`07-verification-and-signoff.md`の全必須gateがPASSし、foundry・package・testの各担当が署名した時点に限る。
