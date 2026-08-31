# Documentation language policy

## Canonical and derived documents

- README.md and the numbered files under docs/ are the Japanese technical source of truth.
- README.en.md and README.zh-Hans.md are public overviews derived from that source.
- Numbers, requirement IDs, commands, file names, and evidence boundaries must remain identical across languages.
- A document that is not a full translation must be labelled as an overview or as a link to the Japanese canonical document.

## Update workflow

1. Add specifications, evidence, and constraints to the Japanese source first.
2. Propagate the same change to the English and Simplified Chinese overviews, diagrams, and evidence tables.
3. When numbers change, check the machine-readable JSON reports and their links.
4. Check language links, CITATION.cff, and documentation-license coverage.

This structure avoids maintaining three independent copies of the detailed specification while keeping public language entry points separate.

## Coverage

| Layer | Japanese | English | Simplified Chinese |
|---|---|---|---|
| Public entry | README.md | README.en.md | README.zh-Hans.md |
| Detailed specification | docs/*.md | docs/README.en.md routes to the canonical files | docs/README.zh-Hans.md routes to the canonical files |
| Concept notes | docs/concepts/*.md | Files with the .en.md suffix | Files with the .zh-Hans.md suffix |
| Validation results | VALIDATION.md／evidence | VALIDATION.en.md | VALIDATION.zh-Hans.md |
