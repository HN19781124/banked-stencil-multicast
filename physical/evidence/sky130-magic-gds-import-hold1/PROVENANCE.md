# Execution provenance

> Historical commands below preserve the exact completed run. Absolute
> `namiki` paths identify that frozen workspace; replace them with the current
> worktree path when reproducing the flow.

Date: 2026-08-29 (JST)  
Host: WSL2 `Ubuntu-24.04`, commands launched from PowerShell.

## Container and tool versions

The physical and container verification runs used the OpenLane 2.3.10 image
tag. The local image was resolved before the runs to the immutable digest below;
the tag is retained in the recorded commands because that is the invocation
captured by the run logs.

```text
Image tag:    ghcr.io/efabless/openlane2:2.3.10
Image digest: ghcr.io/efabless/openlane2@sha256:37c3bd4ea0534a276cb2deb88d601044857bad2807b9bc5b36efe9d02c62624e
Inspect:      wsl -d Ubuntu-24.04 -- docker image inspect ghcr.io/efabless/openlane2:2.3.10 --format "{{.Id}}|{{json .RepoDigests}}"
Inspect out:  sha256:37c3bd4ea0534a276cb2deb88d601044857bad2807b9bc5b36efe9d02c62624e|["ghcr.io/efabless/openlane2@sha256:37c3bd4ea0534a276cb2deb88d601044857bad2807b9bc5b36efe9d02c62624e"]
Inspect exit: 0
```

| Tool | Version | Evidence |
|---|---|---|
| OpenLane | 2.3.10 | container command and `openlane --version` |
| Magic | 8.3 revision 489 | successful GDS/DRC/extraction logs |
| Netgen | 1.5.278 | successful LVS log first line |
| Yosys | 0.46, git `e97731b9dda91fa5fa53ed87df7c34163ba59a41` | container verification report |
| Icarus Verilog | 12.0 stable | container verification report |
| Python | 3.11.9 | container verification report |

Version queries in the container were `openlane --version`, `yosys --version`,
and `iverilog -V`; Magic and Netgen versions are taken from their successful
step-log headers.

The normal physical PDK is `sky130A`, open_pdks commit
`0fe599b2afb6708d281543108caf8310912f54af` (Magic reports version
`1.0.493-0-g0fe599b`). The GDS-only sidecar comes from open_pdks commit
`9ca6f00b4360922e095033945f36198060b65086`, version `1.0.529`; its source
SHA-256 is `60214b3a16e445830782cdaa012a1d8869a3638da34e9b02ed94ace88648f8ae`,
and the materialized `sky130A-GDS.tech` SHA-256 is
`5298e51d55b993a7d59aa491f3318d4f5f3026f46c244f89e624a23b16223fe`.

## Commands and exit codes

The following are the commands captured for the completed checks. Every
OpenLane container was started with `--rm`; therefore Docker's post-removal
`State.ExitCode` is not available. For those steps, exit code `0` is recorded
from the completed `state_out.json` and terminal completion marker (`DONE`,
`exttospice finished`, or `LVS Done`).

### Sidecar materialization

```text
wsl -d Ubuntu-24.04 -- python3 '/mnt/c/Users/namiki/Documents/neumann bottleneck2/tools/prepare_magic_gds_tech.py'
```

Exit code: **0**. Manifest:
`.cache/open_pdks_gds/9ca6f00b4360922e095033945f36198060b65086/manifest.json`
(SHA-256 `575d698f6cbf9d110269fc0fb4ef19290893691c27f5b009c520d1391d1b4901`).

### RTL, formal, and generic synthesis

```text
wsl -d Ubuntu-24.04 -- docker run --rm --name nb2-verify-container -v '/mnt/c/Users/namiki/Documents/neumann bottleneck2:/work' -w /work ghcr.io/efabless/openlane2:2.3.10 python3 -u tools/verify.py --require-rtl --report build/verification-report-container-20260829.json
```

Exit code: **0**. The report is **24/24 PASS**, every recorded subprocess
`returncode` is `0`, and its SHA-256 is
`c1570ccc0bd1c8a467b78f3037bdb52252705181a7005e7a7620cbc3f775a1e5`.

The same regression was rerun with the immutable digest (exit code **0**):

```text
wsl -d Ubuntu-24.04 -- docker run --rm --name nb2-verify-container-digest -v '/mnt/c/Users/namiki/Documents/neumann bottleneck2:/work' -w /work ghcr.io/efabless/openlane2@sha256:37c3bd4ea0534a276cb2deb88d601044857bad2807b9bc5b36efe9d02c62624e python3 -u tools/verify.py --require-rtl --report build/verification-report-container-digest-20260829.json
```

That digest-pinned report is also **24/24 PASS** with zero nonzero
subprocess return codes; SHA-256:
`48a456c9fbccc60d1fa4ba571675f1d64cf740154c7446819f366927c9fbbd6d`.

### Magic GDS-only import

```text
magic -dnull -noconsole -rcfile /dev/null \
  -T '/mnt/c/Users/namiki/Documents/neumann bottleneck2/.cache/open_pdks_gds/9ca6f00b4360922e095033945f36198060b65086/sky130A-GDS.tech' <<'EOF'
gds readonly true
gds read {/mnt/c/Users/namiki/Documents/neumann bottleneck2/.cache/sky130_sram_macros/sky130_sram_2kbyte_1rw1r_32x512_8/sky130_sram_2kbyte_1rw1r_32x512_8.gds}
load sky130_sram_2kbyte_1rw1r_32x512_8
puts stdout "TOP_OK"
quit -noprompt
EOF
```

Exit code: **0** (`TOP_OK`). Transcript:
`.cache/physical-validation/magic-gds-import/magic-gds-import-read2.log`
(SHA-256 `976c5f96aa8a08b87daa8651177d3b315d90c05b8cbfd29884e643024afc0846`).

### Normal-tech Magic DRC

```text
docker run --rm --name magic-normal-drc -v /home/namiki:/home/namiki ghcr.io/efabless/openlane2:2.3.10 python3 -m openlane.steps run --id Magic.DRC --config /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-magic-drc-hold1/config.json --state-in /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-magic-drc-hold1/state_in.json --output /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-magic-drc-hold1/output4 --manual-pdk --pdk-root /home/namiki/.volare/volare/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af --pdk sky130A --scl sky130_fd_sc_hd --condensed --hide-progress-bar
```

Exit code: **0** (runtime `00:24:56.686`; `DRC Checking DONE`). Report
SHA-256: `56aa487196fba9d01925e8234338408b60317626f02d9ea98372253f9e85b6cd`.

### Normal-tech Magic extraction

```text
docker run --rm --name magic-normal-extract -v /home/namiki:/home/namiki ghcr.io/efabless/openlane2:2.3.10 python3 -m openlane.steps run --id Magic.SpiceExtraction --config /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-magic-extract-hold1/config.json --state-in /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-magic-extract-hold1/state_in.json --output /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-magic-extract-hold1/output --manual-pdk --pdk-root /home/namiki/.volare/volare/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af --pdk sky130A --scl sky130_fd_sc_hd --condensed --hide-progress-bar
```

Exit code: **0** (runtime `00:23:32.037`; `exttospice finished`). SPICE
SHA-256: `7b0f4431504716dd84745039f3e4e896cc8fed244f38f12db8b7ea5ae1282312`;
feedback XML SHA-256:
`a79cb5c200444a60c02ae2bc848aa10c432b6f8e108ba35fe43c8f5b672e7130`.

### Normal-tech Netgen LVS

```text
docker run --rm --name netgen-lvs-hold1 -v /home/namiki:/home/namiki ghcr.io/efabless/openlane2:2.3.10 python3 -m openlane.steps run --id Netgen.LVS --config /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-netgen-lvs-hold1/config.json --state-in /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-magic-extract-hold1/output/state_out.json --output /home/namiki/neumann-bottleneck2-physical/physical/runs/sky130-netgen-lvs-hold1/output --manual-pdk --pdk-root /home/namiki/.volare/volare/sky130/versions/0fe599b2afb6708d281543108caf8310912f54af --pdk sky130A --scl sky130_fd_sc_hd --condensed --hide-progress-bar
```

Exit code: **0** (runtime `00:07:06.138`; `Final result: Circuits match uniquely.`
and `LVS Done.`). Netgen report SHA-256:
`80be3a7fdd1f99283677f89efc0546d2490c353c4233b3e5169922ed3c1f761a`;
JSON report SHA-256:
`5755290a86286af609bd12608eeb0058419e1686c9a22d3a23ed8066e64f1f5b`.

The normal `sky130A.tech` remains mandatory for DRC, extraction, and LVS.
`sky130A-GDS.tech` is only the mask-layer import/handoff view; no installed PDK
file was edited and no OpenROAD P&R rerun was triggered by the sidecar import.
