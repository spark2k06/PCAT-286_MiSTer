# Fixed-source verification adapter repairs — 2026-10-05

P05 and stack-offset adapters previously refused the current source because
they depended on a retired opt-in block or a whole-file October 2 hash.
The repairs preserve the original independent contracts and expected values.
Production RTL, clocks, cycles, fixtures and architectural behavior are unchanged.

- P05: actual raw/timed fault/cache/offset cones, 324 unconstrained binary
  boundary bits; independent 34-bit range primitive; eight genuine SAT mutants
  rejected. The original expression retains SHA256
  `520e5e444252f3a5d871afd339a7d43ebdf867a9d5df1686b1bc30a4b257908f`.
- Stack: actual four-assignment raw/timed cones versus the checked original
  archived `offset_old` module; all 101 binary inputs, simultaneous selects,
  allocation-valid choices and 16-bit wraps; eight SAT mutants rejected.
- Both strict CPU lint logs are empty. All 12 original directed bank runs pass
  with identical Icarus/Verilator expected result lines: call-stack precheck
  (9 checks), protected outer event (6 checks, 499 READY stalls), call-gate
  accessed (420 checks / 144 cases). The old base/pcat labels both use the
  fixed active CPU implementation.

The archive contains exact proof sources/logs/receipts, compiled input sources,
original result lines and binary identities, independent review, and the
unexecuted full-regression preparation plan. Every byte was verified by archive
readback. No proprietary ROM, full corpus or compiler object is packaged.
The archive's inventory provides SHA256 and size for every retained input.

These are cone contracts and directed checks, not a full CPU/machine equivalence
proof, a complete regression, historical hardware certification or timing
signoff. The full regression waits for positive setup/hold at all four corners.
The raw prior full-regression failures are not overwritten by these repairs.
