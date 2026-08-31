# Verification and Physical-Design Dossier

[日本語（正本）](README.md) · English · [简体中文](README.zh-Hans.md)

This directory contains the requirements, interface contracts, verification
boundaries, and physical-design evidence for the banked-stencil data path.
The Japanese numbered files remain the detailed technical source of truth;
this page provides an English navigation layer without silently changing
numbers or claims.

## Language policy

See [the language policy](languages/LANGUAGE-POLICY.en.md). Add a new
specification to the Japanese source first, then update the English and
Simplified Chinese overviews and their links.

## Numbered specification

| ID | English scope | Japanese source |
|---|---|---|
| 01 | Product requirements and acceptance targets | [01-product-requirements.md](01-product-requirements.md) |
| 02 | Complex binary16/binary32 numerical rules | [02-numerical-specification.md](02-numerical-specification.md) |
| 03 | Architecture, pipeline, AXI interfaces, CSR, and errors | [03-architecture-and-interfaces.md](03-architecture-and-interfaces.md) |
| 04 | SRAM mapping, streaming, Halo, FIFO, DMA, and macro acceptance | [04-memory-streaming-and-dma.md](04-memory-streaming-and-dma.md) |
| 05 | Clock, reset, power, CDC, scan, and SRAM MBIST | [05-clock-reset-power-dft.md](05-clock-reset-power-dft.md) |
| 06 | Physical-design constraints, floorplan, timing, power integrity, and DRC/LVS | [06-physical-design.md](06-physical-design.md) |
| 07 | Verification levels, formal properties, coverage, and sign-off gates | [07-verification-and-signoff.md](07-verification-and-signoff.md) |
| 08 | Manufacturing handoff, package input, and silicon test planning | [08-manufacturing-handoff.md](08-manufacturing-handoff.md) |
| 09 | Risk register and closure rules | [09-risk-register.md](09-risk-register.md) |
| 10 | Requirement traceability matrix | [10-traceability-matrix.md](10-traceability-matrix.md) |
| 11 | Git, tags, releases, CI, and publication procedure | [11-release-and-git.md](11-release-and-git.md) |
| 12 | Magic technology selection and GDS handoff | [12-magic-tech-selection.md](12-magic-tech-selection.md) |
| 13 | Design-space exploration and N=16 verification candidate | [13-design-space-exploration.md](13-design-space-exploration.md) |

## Concept and comparison notes

- [Stencil-window reframing (English)](concepts/stencil-window-reframing.en.md) ／ [简体中文](concepts/stencil-window-reframing.zh-Hans.md) ／ [日本語](concepts/stencil-window-reframing.md)
- [ROMBASIC／GPU integration outlook](concepts/rombasic-gpu-integration.en.md) ／ [日本語](concepts/rombasic-gpu-integration.md) ／ [简体中文](concepts/rombasic-gpu-integration.zh-Hans.md)
- [FPGA comparison contract](concepts/fpga-and-simulation-comparison.en.md) ／ [日本語](concepts/fpga-and-simulation-comparison.md) ／ [简体中文](concepts/fpga-and-simulation-comparison.zh-Hans.md)
- [FPGA line-buffer comparison](concepts/fpga-linebuffer-comparison.en.md) ／ [日本語](concepts/fpga-linebuffer-comparison.md) ／ [简体中文](concepts/fpga-linebuffer-comparison.zh-Hans.md)
- [ASIC reference comparison](concepts/asic-linebuffer-comparison.en.md) ／ [日本語](concepts/asic-linebuffer-comparison.md) ／ [简体中文](concepts/asic-linebuffer-comparison.zh-Hans.md)
- [Energy and data-movement references](concepts/energy-measurement-references.en.md) ／ [日本語](concepts/energy-measurement-references.md) ／ [简体中文](concepts/energy-measurement-references.zh-Hans.md)

The comparison reports explicitly label the no-stall line-buffer model as an
upper bound. Real line-buffer implementations may block on port conflicts,
fill/boundary handling, or downstream backpressure.

## Evidence and reproducibility

- [English validation summary](../VALIDATION.en.md) ／ [简体中文](../VALIDATION.zh-Hans.md) ／ [日本語](../VALIDATION.md)
- [RTL performance report](../physical/evidence/RTL-PERFORMANCE-REPORT.md)
- [2D dataflow evidence](../physical/evidence/2d-dataflow-comparison-1024.json)
- [ASIC activity evidence](../physical/evidence/asic-dataflow-reference-1024.json)
- [Physical execution provenance](../physical/evidence/sky130-magic-gds-import-hold1/PROVENANCE.md)

These links describe reproducible evidence, not a tapeout or production
qualification.
