# クロック／リセット／電源／DFT仕様

## 1. Clock

初回基準は`core_clk` 1本、100 MHz、duty 45–55%とする。内部PLL、分周clock、logic generated clockは禁止する。clock gatingはtechnology ICG cellだけを用い、RTLの論理AND/ORでclockを生成しない。

clock gate enableは同期化し、scan/test modeでは強制openできること。CTS前にclock-gating checkを実行し、post-routeでgated branchを含むsetup/hold、pulse width、skewをsign-offする。

## 2. Reset

`core_reset_n`は非同期assert、各clock domainで2-flop同期deassertとする。reset解除後は最低2 cycle待ってreadyをassertする。

reset値:

- AXI valid: 0
- input ready: FIFO初期化後1
- status: IDLE=1、BUSY/DONE/ERROR=0
- coefficient shadow/active: +0.0
- FIFO pointers/count: 0
- FP sticky、IRQ、error code: 0
- SRAM content: undefined。使用前にDMA loadまたはMBISTを必須とする。

soft resetはtransaction中に要求された場合、安全点までdrainしてからstate/FIFO/flagsを初期化する。hard resetは進行中transactionを破棄できるが、外部protocolへvalidを残さない。

## 3. CDC / RDC

core baselineはsingle clock domainである。AXI wrapperが別clockの場合はvendor-independent async FIFOを境界に置き、pointer Gray encoding、2-flop synchronizer、reset release orderingをformal CDC/RDCで検証する。multi-bit controlを個別synchronizerで渡してはならない。

CDC waiverは構造、理由、source/destination clock、検証evidence、ownerを記録する。

## 4. Power

初回基準はsingle 1.8 V core domain、power gatingなし、state retentionなし。公開PDK試作ではPDK/libraryが指定するnominal voltageをauthorityとする。

clock gating対象:

- MAC pipeline
- operand/result register
- scheduler/address generator（idle時）
- CSR以外のcontrol datapath

SRAM sleep modeは選定macroが提供する場合のみ使用し、wake-up latencyをcontrollerへparameter化する。clock-gated状態でもAXI-Lite CSR、interrupt、wake requestは動作する。

power intentをUPFで管理する場合、初回は単一domain宣言とsupply mappingのみとし、isolation/retention cellは挿入しない。

## 5. DFT architecture

### Scan

- all scannable flopをbalanceされた複数chainへ分割
- async reset synchronizer first stage、analog hard macro、SRAM arrayは除外可能
- chain countはpackage pinとtester制約で決定
- scan clock 10–25 MHzを初期値とする
- `test_mode`でICG bypass、reset制御、X source maskを行う

ATPG target:

- stuck-at fault coverage >= 99%
- transition fault coverage >= 95%
- unresolved Xとuntestable faultを分類し、waiver承認を受ける

### SRAM MBIST

`M=12` bankを独立に選択し、March C-相当またはmacro supplier承認algorithmで次を検出する。

- stuck-at
- address decoder
- transition
- read disturb
- coupling

MBIST中はfunctional accessを遮断し、終了時にpass/fail、最初のbank/address、signatureをCSRへ保存する。初回基準はredundancy repairを持たない。

### Boundary scan / package test

pad ringを含むchip integrationではIEEE 1149.1 boundary scan、IDCODE、BYPASS、SAMPLE/PRELOAD、EXTESTを実装する。IP block単体ではscan/test/MBIST portをtop-levelへ引き出し、SoC DFT controllerとの接続表を引渡す。

## 6. DFT sign-off artifacts

- scan architecture report、chain map、scan DEF
- ATPG pattern、fault coverage、untestable/aborted list
- MBIST algorithm、pattern、simulation log、failure dictionary
- gate-level scan shift/capture simulation
- tester timing set、pin map、expected signature
- DFT DRC reportとwaiver register
