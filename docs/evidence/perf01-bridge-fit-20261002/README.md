# PERF01 bridge response: fitted timing evidence, 2026-10-02

Status: **MEASURED_TIMING_FAIL**. Quartus compiled the candidate successfully,
but the completed four-corner analysis has negative setup slack. This candidate
does not meet the previous positive-setup/positive-hold 50 MHz acceptance.

## Measured timing

All numbers are ns. `summary.json` parses the retained raw reports;
`completion-audit.json` rechecks the actual reports, source identities,
constraints, fitted ROM image and required coverage.

| Model | Global setup | Global hold | CPU setup | CPU hold | SDRAM output setup | SDRAM output hold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7_slow_1100mv_100c | -0.557 | +0.189 | -0.557 | +0.251 | +5.349 | +3.035 |
| 7_slow_1100mv_-40c | -0.301 | +0.084 | -0.301 | +0.243 | +6.259 | +2.380 |
| MIN_fast_1100mv_100c | +2.302 | +0.133 | +8.668 | +0.133 | +9.363 | +0.880 |
| MIN_fast_1100mv_-40c | +2.612 | +0.087 | +10.403 | +0.116 | +11.003 | +0.208 |

The scope remains constrained FPGA fabric and the declared conditional W9825
SDRAM flight/device budget. It does not certify inherited platform I/O/HPS
hard blocks or unmeasured board flight times. No timing exception or relaxed
device budget is introduced to turn this result into a pass.

## Source and functional binding

The actual fit is `build/perf01-bridge-response-fit-20261002`. The frozen
`manifest.json`, original working-tree record, compilation logs and compiled
configuration identify it. `compiled-config/build_id.v` is the actual generated
build-date file; the original manifest remains intact, and the completion audit
records any specifically permitted date regeneration.

The integration binding checks the entire trusted cycle-validation source set
against the fitted workspace, allowing only the AT bridge to differ in this
run. CPU proofs, configuration, firmware and harness inputs remain bound to
their prior evidence. The actual M10K image and its independent contract are
retained under `compiled-rom/`, with the original compiled-image receipt.

Directed functional tests, the guarded eight-pair workload comparison, parser
controls and complete workload logs are in the separately committed
[functional bundle](../perf01-bridge-response-20261002/README.md). The guarded
comparison is also retained here, with a byte-identical hash checked during
packaging. The [warm-reset evidence](../perf01-reset-fixture-20261002/README.md)
is separately retained. `references.json` pins those bundle inventories.
This fit is not a full CPU regression.

User hardware benchmark observations are recorded in the separate
[hardware bundle](../perf01-bridge-hardware-20261002/README.md). They do not
establish all-corner timing closure. `hardware: NOT_RUN` in the automated audit
describes execution by that tool; it does not negate the separate user report.

## Bitstreams

No bitstream is duplicated into this evidence bundle.

- Candidate: [build/perf01-bridge-candidate-20261002/PCAT-286.rbf](../../../build/perf01-bridge-candidate-20261002/PCAT-286.rbf),
  4,097,400 bytes, SHA-256 `3cbcbaaba667c48c4ef28c45f484c61563cee660e9fd21e8267a77cd013a3b7e`.
  Its timing result is **MEASURED_TIMING_FAIL**.
- Previous fallback: [build/50mhz-closed-20261002/PCAT-286.rbf](../../../build/50mhz-closed-20261002/PCAT-286.rbf),
  4,076,700 bytes, SHA-256 `22b6ee1e7384d9db43c8b241b5fdc6ca75e6e48c4d6847a5dae153f7964ea34b`.
  That earlier selection has positive all-corner timing under its documented
  scope; this failed candidate does not replace that evidence.

`bitstreams.sha256` retains both original candidate RBF/SOF identities from the
fit directory. Packaging separately verified the ready-to-copy candidate RBF
against that fit, and hashed the fallback without modifying either binary.

## Archive integrity and retained artifacts

- `timing-reports.zip` contains **166 raw timing files**, preserving
  every relative filename and complete byte content. Its manifest lists sizes
  and hashes, and the complete inventory equals `summary.json.report_hashes`.
- `quartus-reports.zip` contains the five original map/fit/STA/flow/assembler
  reports. Small fit/map/STA summaries remain readable under `quartus/`.
- Each archive member was read back and compared byte-for-byte with its
  original source file, then checked by SHA-256 and ZIP CRC. The manifests
  record that verification; no report was reconstructed from a summary.
- `critical-paths/` keeps global, CPU and bridge-to-CPU setup/hold reports from
  every corner directly readable. These are identical copies of ZIP members.
- `compile.log`, `project-check.log`, `profile-check.log`, `profile.log` and
  `timing.log` are complete original run logs, not selected success lines.
- `profile/` retains compiled-source manifests, actual performance macros and
  the source-verification result. The functional bundle contains the individual
  workload logs; the comparison records their hashes.
- `provenance.json` records every copied file's original path, size and hash;
  `files.sha256` covers the whole bundle except itself.

Quartus databases, generated objects/C++, RBF/SOF binaries and unrelated build
artifacts are excluded. Negative setup results remain visible in the original
reports and audit; hardware observations and simulation success do not waive
them.
