# 製造引渡しパッケージ

## 1. Tapeout directory

最終archiveは次の構造とし、全fileをmanifestへ列挙する。

```text
tapeout/<baseline>/<run-id>/
  manifest.sha256
  README.txt
  rtl/
  constraints/
  netlist/
  layout/
  timing/
  power/
  verification/
  dft/
  macros/
  package/
  test/
  licenses/
  logs/
```

## 2. Mandatory deliverables

### Design

- frozen RTL and generated-source manifest
- synthesis and LEC netlist
- SDC、UPF（使用時）、floorplan/PDN/CTS configuration
- final DEF/ODB、GDS or OASIS、abstract LEF
- SPEF、SDF、extracted netlist
- top-level port/pin list and hierarchy manifest

### Verification / sign-off

- regression report and coverage database
- lint、CDC、RDC、formal、LEC reports
- all-corner STA summary and unconstrained-path report
- DRC/LVS/ERC/antenna/fill reports
- static/dynamic IR、EM、power reports
- waiver register with approvals

### DFT / test

- scan chain map、ATPG patterns、coverage report
- MBIST pattern/algorithm、expected signatures
- JTAG/boundary-scan BSDL when chip-level
- tester vector format、timing set、pin map
- wafer sort、package final test、bring-up procedures

### Supply chain / legal

- PDK/tool/macro/IP version and checksum
- all licenses、notices、redistribution restrictions
- foundry submission form and accepted rule-deck version
- package drawing、bonding diagram、assembly limits
- export/control and product compliance review where applicable

## 3. Foundry questions before submission

1. accepted PDK and sign-off deck revision
2. accepted GDS/OASIS format, layer map, units, top-cell name
3. seal ring、scribe、logo、wafer map requirements
4. density/fill responsibility and final fill deck
5. antenna/ESD/latch-up/reliability limits
6. SRAM hard macro qualification and allowed redistribution
7. MPW/full-mask schedule、reticle limit、die count
8. package/assembly vendor handoff boundary
9. encrypted IP/data transfer method and checksum procedure
10. resubmission/ECO deadline and change-control procedure

## 4. Package / board input

chip-level productizationでは次をfreezeする。

- package type、body size、ball/pin count、thermal resistance
- core/IO supply rails、decoupling、power sequence
- clock source、reset、JTAG、boot/test strap
- high-speed/analog pin constraints if added
- ESD class and IO drive/load
- pin escape、PCB stack-up、test points
- maximum junction temperature and thermal solution

IP block単体のreleaseでは上記をintegration requirementとして引渡し、未定のまま「製品tapeout ready」と呼ばない。

## 5. Silicon test plan

### Wafer sort

- ID/JTAG connectivity
- scan stuck-at/transition patterns
- SRAM MBIST all banks
- clock/reset/CSR smoke
- reduced-speed functional stencil vectors
- leakage and basic supply current limits

### Packaged device

- full functional regression subset
- frequency sweep and voltage margin
- interface timing and backpressure
- power modes and thermal steady state
- FP corner vectors and long-run data integrity

### Characterization

- PVT frequency/voltage/power matrix
- SRAM retention/read/write margin
- multicast path max toggle and simultaneous switching
- output accuracy distribution against reference
- aging/reliability plan required by product class

## 6. Tapeout authorization

次の役割が同一baseline、commit、physical run ID、manifest hashへ署名する。

| role | responsibility |
|---|---|
| design owner | RTL/spec/ECO closure |
| verification owner | regression/coverage/formal closure |
| physical owner | STA/IR/EM/DRC/LVS closure |
| DFT owner | scan/ATPG/MBIST/test closure |
| product owner | requirements/package/test/business acceptance |
| foundry interface | submission rule/data acceptance |

署名後のbit変更は、新baseline、再sign-off、再署名を要求する。
