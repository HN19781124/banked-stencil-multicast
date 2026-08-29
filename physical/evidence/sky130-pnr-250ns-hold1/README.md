# sky130-pnr-250ns-hold1 evidence

- Run tag: `sky130-pnr-250ns-hold1`
- Source run: frozen local OpenLane workspace (raw directory not versioned)
- Compact record: this summary, the top-level physical report, hashes, and provenance
- Result: OpenROAD P&R, routing DRC, post-PNR STA, and IRDrop completed. The flow stopped at `Magic.StreamOut` because the vendor SRAM GDS contains layer/datatype records unsupported by the installed Magic view.

## Frozen metrics

- Die: 4000 x 4000 um; 24 SRAM macros; 348,678 standard cells; utilization 0.54.
- Routing DRC: 0; critical disconnected pins: 0 (8 non-critical top-level pins).
- Setup WNS/TNS: 0 / 0 ns; hold WNS/TNS: -1.36 / -849.97 ns.
- Antenna: 49 nets, 59 pins after repair.
- IRDrop worst case: VPWR 0.000328 V (0.02%); VGND 0.000209 V (0.01%).

## SHA-256 spot checks

```text
8cc606fe122ee4bd39a2ddee18476c9043661f598e982e070afeaae049bb009e  physical-run/flow.log
d7a47eae396d56be00225f50d7d9308937fec4255b21bea4bc4c4dfc6c67dbb4  physical-run/error.log
afca9ac83b1dcf240e2b03c2163920b094d3b5e610af6131163945b500f35c0c  physical-run/19-openroad-irdropreport/state_out.json
```

Previous runs remain in the local recovery archive and are not part of the
public repository.

## Archive

- Full artifact ZIP: local-only recovery archive
- Contents: 1,096 files; current run artifacts plus preserved previous-run logs/reports.
- ZIP SHA-256: `CD1B4F1B6EF47B203A3B5A197C7492B9A41F4E179726BCA3D7AF1D97B7812810`
- The ZIP is intentionally excluded because of size and third-party artifact
  redistribution constraints.
