# PERF01 SDRAM response evaluation evidence

This directory records the private owner-only experiment described in
[P09](../../optimization/P09_SDRAM_RESPONSE_EVALUATION_20261002.md).
The candidate is not selected for production and has no synthesis/timing or
hardware acceptance.

## Retained records

- `profile-comparison.json`: all eight baseline/candidate pairs, signatures,
  counters, per-class latencies and the individual workload-log hashes.
- `validation-summary.json`: all seven stage outcomes, executed commands,
  environments, timestamps and original full-log hashes. All are PASS.
- `private-sources.json`: hashes of all 1,195 files in each independent source
  copy, with only the owner different. Both complete source guards pass.
- `source-hashes.txt`: the owner file SHA-256 values.
- `baseline/frozen-manifest.json`: the parent's frozen project provenance.
- `baseline/config.tcl`: the actual reference configuration.
- `baseline/*-p03-*.log` and `candidate/*-p03-*.log`: all sixteen complete
  workload logs, copied byte-for-byte.
- `baseline/compiled-sources.sha256` and `candidate/compiled-sources.sha256`:
  actual workload inputs. Their `sources-verified.log` companions pass.
- `candidate/profile-run.log`: the candidate profile runner's complete stdout,
  retained under this name from original `profile.log`.
- `directed/{capture,entry,owner,ram-buffer-pipeline,code-buffer,memory-port}.log`:
  complete stage logs, with bytes matching the validation receipt.
- `directed/capture-skew-{0,1}.log`: the two deliberate invalid-read failures
  used as timing-model sensitivity controls.
- `directed/entry-*` and `directed/ram-buffer-*`: lint results and relevant
  source manifests/verification logs. A zero-byte lint log means no diagnostics.
- `reproduction/owner-direct-response.patch`: the single-owner change, using
  normal `a/rtl/...` and `b/rtl/...` paths for application to a private reference.
- `reproduction/run_private_validation.py` and `compare_profiles.py`: the exact
  scripts used for source isolation, directed runs, guards and comparisons.
  Their original private local paths remain explicit; they are execution
  receipts rather than portable project entry points.
- `files.sha256`: archive inventory. Paths are relative to this directory.

## Paths and reproduction

Receipt paths beginning `/mnt/d/GitHub/PCAT-286_MiSTer/build/` describe the actual
run locations, not required destinations for these archived files. Stage logs
retain their original names under `directed/`; original `profile.log` is the
archived `candidate/profile-run.log`. Individual workload logs retain their
names under their respective variant directories.

To repeat the isolated experiment, first reproduce the reference sources from
the recorded project revision/working-tree snapshot and verify their hashes.
Use an independent copy for the candidate and apply only the retained owner
patch there. The patch contains no changes to the bridge, controller, buffers,
CPU, firmware, tests or configuration. Git normalizes text line endings in
the patch; the source manifests record the exact bytes of the original run.

The physical capture runner supports `AT_SDRAM_OWNER_SOURCE`. The workload
runner supports `PCAT_SOURCE_ROOT` and `PCAT_BUILD_DIR`. Other directed runners
derive the source root from their script location, so invoke copies inside the
private source tree. `test_at_sdram_entry.sh` requires a new output directory.
Keep baseline and candidate outputs separate and compare complete architectural
signatures plus retirement/write counts, not benchmark time alone.

No archived log is evidence of FPGA timing closure, hardware acceptance or a
complete CPU regression. The buffer/pipeline and memory-port tests use their
existing abstract backends; physical tests are identified explicitly in P09.
