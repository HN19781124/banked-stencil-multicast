# Filament integration (optional preparation)

This directory is an optional timing-contract layer for the measured
`N=4`/`M=12` data path. It is not part of the v0.2.0 verified baseline, does
not replace the existing SystemVerilog/Python/Yosys flow, and does not claim
that the coprocessor has a fixed end-to-end latency under backpressure or
external-DRAM waits.

## What is prepared

- [`n4_multicast.fil`](n4_multicast.fil) declares the existing combinational
  `rtl/stencil_multicast.sv` module as a one-cycle Filament component.
- The `main` component is a small wrapper for checking that the six unique
  samples are available before the twelve lane/tap outputs are consumed.
- The file deliberately stops at the regular multicast boundary. AXI/FIFO
  handshakes, SRAM macros, bank-conflict proofs, FP16 arithmetic, DMA/DRAM,
  and physical timing remain in the existing verification flow.

Filament's availability intervals and event delays are useful for checking
pipeline composition and initiation interval. Its `extern` declarations are
contracts for black-box SystemVerilog modules; they do not independently
prove the implementation, so the existing RTL simulation and formal checks
remain authoritative.

## Optional local check

The current upstream snapshot used for this preparation is pinned to
`3c17db5ce85c354dd3da0af57f3adcb59bb295ac`.

```powershell
$FilamentRoot = 'C:\src\filament'
git clone https://github.com/cucapra/filament.git $FilamentRoot
git -C $FilamentRoot checkout 3c17db5ce85c354dd3da0af57f3adcb59bb295ac
cargo run --manifest-path "$FilamentRoot\Cargo.toml" -p filament -- `
  "$PWD\filament\n4_multicast.fil"
```

The command is intentionally optional and is not added to
`tools/verify.py` or the required CI job. A later integration change should
record the generated Verilog, compiler output, and a cycle-trace comparison
against `rtl/tb_banked_stencil_path.sv` before changing verification status.

## Next safe step

After the N=4 contract compiles and matches the existing trace, add separate
contracts for the registered MAC boundary and then parameterize `N`/`T`.
N=6 and N=16 remain outlook/estimate targets until their own RTL, formal,
backpressure, and physical evidence exists.
