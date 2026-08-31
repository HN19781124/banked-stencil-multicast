# Physical implementation evidence

This directory contains the reproducible inputs and compact evidence needed to
review the exploratory SKY130 implementation. It intentionally excludes PDKs,
vendor macro binaries, generated GDS/DEF/ODB files, raw run directories, and
the 9.17 GB local recovery archive.

## Included

- `config.json`, `constraints.sdc`, `pin_order.cfg`: pinned OpenLane inputs
- `run_openlane.sh`: flow entry point
- `src/`, `sim/`: SRAM black-box and simulation views
- `evidence/PHYSICAL-VERIFICATION-REPORT.md`: physical result and limitations
- `evidence/RTL-PERFORMANCE-REPORT.md`: cycle-accurate performance evidence
- `evidence/GPU-COMPARISON-REPORT.md`: dated roofline comparison, not a benchmark
- `evidence/sky130-magic-gds-import-hold1/PROVENANCE.md`: tool and command provenance

## Boundary

The saved run completed OpenROAD placement, CTS, routing, setup analysis, and
IR-drop analysis at a 250 ns constraint. Hold and antenna violations remain;
Magic/KLayout and SRAM-internal checks are not complete. The result is evidence
of routability and a reproducible physical experiment, not tapeout sign-off.

The published baseline notation is `N=4` lanes and `M=12` physical SRAM
banks; larger `N`/`M` values are separate estimates or future candidates.

Raw artifacts remain local because of size and third-party redistribution
constraints. Their hashes are retained in the evidence reports.
