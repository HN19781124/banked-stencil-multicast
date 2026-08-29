# Manufacturing baseline

`baseline.json` is the machine-readable configuration authority for the first manufacturing-reference block. Human-readable requirements and sign-off rules live under `docs/`.

The open SKY130 target is for reproducible prototype implementation and design validation. A commercial product tapeout requires a foundry-qualified production PDK, qualified SRAM/compiler deliverables, package rules, and foundry sign-off.

No field in `baseline.json` may change after layout freeze without an ECO record, repeated verification, and a new baseline identifier.
