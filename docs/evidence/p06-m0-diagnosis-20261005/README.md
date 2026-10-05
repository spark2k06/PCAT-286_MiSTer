# M0 diagnosis evidence and replay

`manifest.json` binds the accepted source-frozen experiment, raw traces,
fixtures, results and failed/ineffective harness attempts. It contains 699
artifacts and a 369-member deduplicated source archive. `current/` contains
the complete 366-file view; `previous/` contains the three CPU overrides.
Both full source views are hash-bound by `diagnosis/source-binding.json`.

## Restore and prepare recipes

Run with Python 3.10 or newer in Linux/WSL. The default operation only
restores inputs, verifies hashes and writes recipes. A fresh output directory
is required. Existing repository files and original absolute build paths
are not used as production inputs.

```sh
python3 scripts/replay_p06_m0_archive.py \
  --archive docs/evidence/p06-m0-diagnosis-20261005 \
  --output /tmp/p06-m0-replay
```

For a copied evidence packet outside this repository, the identical standalone
helper is preserved as `portable-replay/replay-helper.py.gz`:

```sh
gzip -dc portable-replay/replay-helper.py.gz > /tmp/replay_p06_m0_archive.py
python3 /tmp/replay_p06_m0_archive.py --archive "$PWD" --output /tmp/p06-m0-replay
```

`replay.json` records all eight build recipes and 144 accepted runs: 24 exact
diagnosis runs, 58 natural epoch runs and 62 legal NOP-prelude runs. The helper
rehashes the complete current/previous source views, rebases every source and
generated-bench operand, sets the restored source root as the working directory,
and relocates object, executable, image, trace and log paths. Compile flags,
operand order, bench bytes, workload images and scalar run arguments are
preserved. It does not regenerate microcode or assemble a new workload.

Adding `--execute` explicitly compiles and runs the prepared experiment using
Verilator, make and a C++ compiler from PATH. Execution compares the archived
fabric-clock and instruction counts; bench assertions check work, GPR, flags,
stack and memory. Compilation has a 600-second process-group limit and each
simulation a 90-second limit. Full rerun traces can be large; remove that new
output directory after retaining any required results.

The sealed `portable-replay/replay.json.gz` was prepared at a different source
root and records `executed: false`. It establishes input restoration and recipe
rebasing, not another simulation pass. `contracts.json` summarizes the path-only
compile changes and preserved run scalars. `verification.json` and
`portable-manifest.json` bind these supplements to the core manifest.

## Analyze the archived raw traces

The following commands read gzip traces directly and write only new summaries.
Run from the repository root or preserve the canonical analyzer scripts with
their original names. Completed copies of the analyzer sources are also in the
packet as `diagnosis/analysis-runner.py.gz` and `epoch8/analysis-runner.py.gz`.

```sh
python3 scripts/analyze_p06_m0_diagnosis.py \
  --input docs/evidence/p06-m0-diagnosis-20261005/diagnosis \
  --output /tmp/p06-m0-analysis.json
python3 scripts/analyze_p06_m0_phase.py \
  --input docs/evidence/p06-m0-diagnosis-20261005/epoch8 \
  --output /tmp/p06-m0-epoch-analysis.json
python3 scripts/analyze_p06_m0_phase.py \
  --input docs/evidence/p06-m0-diagnosis-20261005/prelude8 \
  --output /tmp/p06-m0-prelude-analysis.json
```

All three archived analyses reproduced byte-identical summaries after the old
owned `/tmp` compilation directories were observed absent. The hashes are in
`archived-analysis-verification.json`. This analysis reproduction requires no
CPU compilation, original binaries or original uncompressed traces.

## Measurement limits

The report is `docs/optimization/P06_M0_PHASE_DIAGNOSIS_20261005.md`.
The composed PCAT fixture reproduces the 6 MHz penalty at +5.85%; immediate
RAM gives identical timings. The bounded 8 MHz epoch/prelude controls do not
reproduce the hardware +2.67% result. DOS/PIT prehistory, arbitrary warmed
machine state and AT refresh are outside this experiment. No production RTL
fix or CPU regression result is claimed by this packet.
