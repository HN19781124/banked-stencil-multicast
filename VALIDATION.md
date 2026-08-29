# 周辺検証

初期開示の中核スケジューラを基準として、周辺機能と物理実装を段階的に追試した。各PASSは表に記載した境界だけに適用し、製造sign-offの合否条件は[`docs/07-verification-and-signoff.md`](docs/07-verification-and-signoff.md)をauthorityとする。

| 項目 | 検証方法 | 状態 |
|---|---|---|
| 行端・Halo・部分レーン | 全幅1〜257、全issue、両bufferの参照モデル | 完了 |
| 異なる行の同時アクセス | 全row pairのreference補償を検証。初回製品はtransition bubble固定 | reference完了／controller未実装 |
| SRAM read latency・multicast統合RTL | 12個の同期1-port SRAMモデルと6→4×3同報のcycle精度simulation | 完了 |
| 複素MAC・FP16数値規則 | bit-exact参照モデル、256-vector RTL、product RTL | 完了（RTL）／gate未実施 |
| DMA・バックプレッシャ | FIFO/engine/product randomized path | 一部完了（外部DMA wrapper未実装） |
| 基準engine性能 | 17x3 tile、無ストール／固定LFSR backpressure、Icarus RTL | 完了（[指標レポート](physical/evidence/RTL-PERFORMANCE-REPORT.md)、3 cycle/output beat、物理周波数未評価） |
| 段別性能分解 | control／load／window read／capture-multicast／MAC／outputをcycle単位で計測 | 完了（[RTL段別証跡](physical/evidence/RTL-PERFORMANCE-REPORT.md#段別サイクル分解)） |
| GPU同条件比較 | 3-tap複素FP16を段別に対応付け、公開メモリ帯域からroofline計算 | 完了（[比較レポート](physical/evidence/GPU-COMPARISON-REPORT.md)、GPU実測は未実施） |
| N-way設計空間試算 | 一次帯域・容量・multicast endpoint・理想MACの候補掃引 | 完了（N=16を次のRTL検証候補に選定、物理性能は未検証） |
| Halo交換・NoC multicast | 初回baselineはAXI境界まで。NoCは将来extension | 対象外 |
| STA・配置配線・fan-out・電力 | SKY130A試作基準、現行run 250 ns (4 MHz)、OpenROAD/Magic/Netgenの固定run | 実行済み／sign-off未完 |

物理runのhold／antenna違反、GDS／SRAM内部sign-off未完、および保存証跡の範囲は[物理検証レポート](physical/evidence/PHYSICAL-VERIFICATION-REPORT.md)に固定する。
