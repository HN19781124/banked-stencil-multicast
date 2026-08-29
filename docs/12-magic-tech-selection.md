# Magic tech file selection

Magic uses two different SKY130 technology files for two different jobs.  This
distinction is easy to miss and is the source of the vendor-SRAM import failure
seen in the physical run.

| File | Purpose | Connectivity / extraction |
|---|---|---|
| `sky130A.tech` | normal generated-layer view used for electrical interpretation, DRC, LVS, and extraction | supported |
| `sky130A-GDS.tech` | exact GDS mask-layer view used for vendor-GDS handoff and mask-layer checks | intentionally not supported |

The GDS-only file must be selected explicitly with an absolute path:

```text
magic -dnull -noconsole -rcfile /dev/null \
  -T "$PDK_ROOT/sky130A/libs.tech/magic/sky130A-GDS.tech"
```

## Pinned workaround for the 2024 PDK

The physical baseline keeps the standard SKY130A PDK at open_pdks commit
`0fe599b2afb6708d281543108caf8310912f54af`.  That revision's GDS tech file
does not define every purpose layer emitted by the pinned OpenRAM SRAM view.
Use a sidecar GDS tech generated from open_pdks commit
`9ca6f00b4360922e095033945f36198060b65086` (version 1.0.529), and verify its
manifest before use:

```text
wsl -d Ubuntu-24.04 -- python3 tools/prepare_magic_gds_tech.py
```

The helper records the source and generated SHA-256 values under
`.cache/open_pdks_gds/<commit>/manifest.json`; it does not modify the installed
PDK.  The exact mappings include `33/42` (CP1MDROP), `33/43` (CP1MADD),
`22/21` (CNTMADD), `22/22` (CFOMDROP), and `235/0` (BOUND2).
The pinned source is the `fossi-foundation/open-pdks` `sky130gds.tech` file;
the commit and SHA-256 are authoritative, not the moving `main` branch.

## Verification order

1. Read the unchanged vendor GDS with the pinned GDS-only tech and record that
   the purpose-layer records are accepted.  This step does not prove
   connectivity or sign-off.
2. Run DRC/LVS and extraction with the unchanged normal `sky130A.tech` and the
   pinned PDK/library views.  Keep the two logs and their input hashes
   separate.
3. Re-run OpenROAD only when the PDK/library/LEF/routing rules change.  A
   sidecar GDS-tech change alone does not change placement, routing, timing, or
   power data.

Never absorb these purpose layers into `locali`, `abuttment`, or another
electrical layer, and never edit the installed PDK in place; either can hide a
real DRC/LVS problem.
