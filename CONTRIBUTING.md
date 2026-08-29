# Contributing

Changes must preserve the completed scheduler behavior unless an explicit new baseline is approved.

1. Link each behavioral change to one or more `REQ-*` identifiers.
2. Add or update automated tests before changing status in the traceability matrix.
3. Run `python tools/verify.py --bootstrap --require-rtl`.
4. Record PDK, macro, tool, interface, numerical, or timing changes as an ECO in the pull request.
5. Do not commit PDKs, restricted macro views, credentials, build directories, or generated GDS without redistribution approval.

Security, safety, license, numerical-corner, data-loss, reset, and clock issues must be called out explicitly in review.
