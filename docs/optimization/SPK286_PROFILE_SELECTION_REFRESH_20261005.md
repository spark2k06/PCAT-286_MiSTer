# Current standalone profile selection maintenance

The standalone SPK286 generator's source pins predated accepted instruction-
length and encoding-metadata updates. Its current selection is refreshed in
upstream commit `c9239dc3f02c2cef03d36a7cd2b22301affe7795`, then mirrored
completely into PCAT. Both historical baseline/READY-chain contracts remain
byte-identical. A separately dated selected contract pins the eight accepted
source changes; arbitrary further source changes still fail its guards.

The existing focused checker passes against the installed upstream sources:
deterministic generation and installed identity, strict full-CPU lint,
45 schedule checks and eight full-top prefix cases in both simulators,
reset/fetch checks in both modes, and 43,878 metadata cases per simulator.
Seven additional source/contract/output mutants are rejected. CPU, microcode,
timing tables/policy, checkers and expected results are unchanged by this
maintenance. It is not a complete-regression or hardware PASS.

[Sealed upstream evidence mirrored in PCAT](../../vendor/spk286/docs/evidence/profile-selection-refresh-20261005/manifest.json)
is read back before 341,149,735 bytes of owned private/applied compiler
outputs are removed from the two repositories. The
[cleanup receipt](../evidence/spk-profile-selection-maintenance-20261005/cleanup.json)
records the exact targets and free-space observations.

The active `p06-null-segment-allfeatures-20261005-v1` fit remains frozen at
PCAT `3d1fd8d`, upstream `3001de7`, with 2,062 inputs and its own canonical
vendor ledger. This maintenance changes no RTL consumed by that fit.
All five PCAT-owned timing-overlay files are retained byte-identically.
The full regression is authorized once the selected candidate closes timing.
