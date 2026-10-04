# READY chaining: broad functional regression evidence

The real `make regression` completed in the third attempt. Every functional
simulation and vector generator ran again. Validated previous Verilator
unit compilations were reused; this is not a full fresh Verilator build.

- `v1` remains FAILED: historical microcode fixtures produced three failures
  and five errors before RTL tests. The separate microcode-repair packet
  records their explicit migration and the preserved negative checks.
- `v2` remains FAILED: architecture comparisons passed through the adjust
  bank, whose radix-byte starvation coverage assertion then failed.
- `adjust-focused` contains the exact source before/after/diff. Only CODE
  READY latency was strengthened by sixteen cycles. All 8184 cases,
  architectural expected values, timeout and coverage assertion remain.
- `starvation-preflight` contains the unchanged stack/far/muldiv full
  dual banks, source receipts and their original generated vectors.
- `v3` contains the successful fresh execution log, source/corpus receipts,
  exact compile-cache implementation, controls, command/source proofs and
  per-hit receipts. Historical compile logs are explicitly labelled.
- `compiled-source` preserves every tracked input of the tested snapshot
  compressed with its original SHA. Corpus hashes refer to the original
  external corpus; the existing smoke policy is recorded in the log.

`v3/postrun-derived` also preserves generated runtime ROM HEX files,
manifests, trace CSV, all 97 SST binary batches/identities/reports and
Yosys reports. These are hashed after execution, not
presented as pre-existing inputs with fabricated before hashes. Their
generators/source and fresh invocation logs remain independently bound.

Existing script policy runs the full protected expand-down matrix only
in Icarus. All 130 Icarus and 129 Verilator unit banks are independently
counted in the final review. Simulator/state smoke, Python/compiler tests,
four SingleStep smoke groups and Yosys synthesis sanity follow the banks.
The scope excludes a complete external corpus, physical/PCAT OS testing,
STA and Quartus fit.

`archive-manifest.json` binds every stored artifact and its uncompressed
SHA. The archive verification helper rechecks those hashes and all live
compiled inputs. Exact absolute build paths remain in original receipts
as provenance; a replay can restore the snapshot and run normal make
regression with fresh compilation. v1 did not originally record its
runner SHA; its runner is preserved with a new archive hash, while its
original source/log hashes and FAILED status remain unchanged.
