# SRAM／ストリーミング／DMA契約

## 1. SRAM organization

初回基準は12 bank、各1024 word、word幅32 bit、single-port synchronous SRAM、read latency 1 cycleとする。論理buffer A/Bは同一bank群の異なるdepth範囲へ配置する。

```text
bank 0..11:
  address   0..511  : buffer A
  address 512..1023 : buffer B
```

初期容量はpadded width 48、最大128行を各bufferへ格納できる。別寸法を製品要件とする場合、bank depthとmacro選定を再baselineする。

## 2. Mapping

```text
B_b(x,y) = (x + 2*y + phi_b) mod 12
phi_A = 0
phi_B = 6
A_b(x,y) = base_b + y*(Wp/12) + floor(x/12)
```

`x`は左Haloを0とした非負の物理座標である。`Wp`は12の倍数で、right Halo、無効lane、bank alignment paddingを含む。`(bank,address)`はtile内で一意でなければならない。

## 3. Row / Halo policy

- hostまたはDMA wrapperが左1、右1以上のHaloを物理rowへ含める。
- logical output widthを4へ切り上げた領域までsampleを供給し、最後の6-sample windowがrow範囲外へ出ないようpaddingする。
- padding値はapplicationが定義する。zero、clamp、mirrorの生成はcore外部で行う。
- 最終issueの無効laneはlane maskで抑止するが、SRAM read自体は6 sample固定とする。
- row切替ではread/writeが同一local `y`でない場合にtransition bubbleを挿入する。dynamic phase補償は将来extensionであり、初回製品には含めない。

## 4. Steady-state access

有効issue `t`ではactive bufferから`x=4t..4t+5`をreadし、opposite bufferへ`x=4t..4t+3`をwriteする。6 readと4 writeのbank集合は分離し、2 bankをidleとする。

request発行前に次をassertする。

```text
unique(read_banks) == 6
unique(write_banks) == 4
intersection(read_banks, write_banks) == empty
all(address < 1024)
```

違反時はmemory enableを全てdeassertし、`ERROR_CODE=4`をlatchedする。

## 5. FIFO sizing

初期値はinput FIFO 16 beat、output FIFO 16 beatとする。各beatは128-bit dataとsidebandを保持する。最終depthはpost-layout clock ratio、DMA burst、consumer stall simulationから決定する。

最低検証scenario:

- input 1 beat供給後に最大15 cycle gap
- output `ready=0`を1、2、15、16、17、255 cycle継続
- input/outputを独立random backpressure
- row境界直前・最終issue・reset直前のstall
- FIFO almost-full/almost-empty同時遷移

overflow/underflowは通常運転で発生してはならず、formal assertionを置く。

## 6. DMA wrapper contract

DMAはcoreの外側に置き、memory-mapped AXI4とAXI4-Streamを変換する。最低仕様は次のとおり。

- 128-bit AXI4 data、INCR burst、最大16 beat
- 4 KiB boundaryを跨がない
- source/destination addressは16-byte aligned
- programmed row strideをsupport
- outstanding read/write数はintegration targetに合わせparameter化
- AXI errorを停止・drain・CSR errorへ変換
- descriptor ownership bitとcompletion statusをatomicに更新

coreはAXI orderingやDRAM latencyを直接扱わない。DMA verificationはprotocol VIP、random wait-state、SLVERR/DECERR injection、burst分断、descriptor wrapを含む。

## 7. SRAM macro acceptance

macro vendorまたはcompilerから以下を同一releaseで受領する。

- functional Verilog model
- timing/power liberty for all sign-off corners
- LEF abstract、GDS/OASIS、CDL/SPICE
- datasheet、read/write timing、setup/hold、minimum pulse width
- BIST/repair interface specification
- pin capacitance、power-up state、sleep behavior
- license、redistribution条件、checksum manifest

macro modelとsilicon behaviorの不一致はtapeout blockerとする。
