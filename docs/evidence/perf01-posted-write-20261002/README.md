# PERF01 one-entry posted-write evidence

The [P18 review](../../optimization/P18_ONE_ENTRY_POSTED_WRITES_20261002.md)
describes the retained write, cache coherence, physical drain and ordering
fences. This first receipt covers a private prototype, not production adoption.

`prototype/` contains the frozen source identities and private transformation,
all eight physical-data kernel logs and signatures, compiled-source guards,
495-check physical/bridge/arbiter test, 145-check composed-cache test and its
generated top, strict module lint, and matched 86Box build identities. CPU
objects, CPU options, capacities and controller timing are unchanged. The
complete DOS measurements are separate and are not yet claimed here.

The isolated mapping retains every payload output but disconnects diagnostic
counters. The enabled block estimates 51 ALMs, 59 registers and no RAM. This
is not a fitted whole-project delta, and the disabled-block comparison still
contains a new layer absent from P17. First mapping attempts rejected report
column names after successful control synthesis; their errors remain recorded.
No architectural expectation or RTL was waived to obtain the final results.

The initial directed launcher resolved `$PWD` before changing directory and
wrote to `D:/GitHub/directed-baseline` and `D:/GitHub/directed-candidate`. These
outputs were left intact; byte copies and hashes are retained in the private
experiment and inventory. All declared private input/source guards pass.

`prototype/retained-files.json` hashes this completed receipt. It excludes live
DOS images, ongoing output and binary/object build products. Historical receipts
will not be rewritten to cover later measurement/promotion groups.

`promotion/` retains the full private candidate, exact changed-source hashes,
common/divided real-CPU machine checks, dual-simulator bridge checks and Quartus
analysis/elaboration (0 errors, no fitter/RBF). The initial divided-clock
observer failure and corrected sampling-edge fixture are preserved separately.
Production has not yet adopted this candidate.

`integer-partial/` retains two stable read-only formatter observations (6138
control, 6906 posted), owned executable/PID/start identities and unchanged
disk/profiler inputs. Guest completion and math output remain pending.

`refresh/` retains eight matched physical-data AT refresh/HOLD controls, their
generated fixture, exact production requester/arbiter and source identities.
All signatures, retired work and physical stores match. See [P19](../../optimization/P19_AT_REFRESH_PLATFORM_ATTRIBUTION_20261002.md).
These groups each have independent byte inventories; `prototype/` is unchanged.

`pit-correction/` retains the P19 candidate, real PIT and composed CPU checks,
original fixture failures and corrected fixtures. Its own byte inventory keeps
these additions separate from the original fixed 32-clock attribution.

`complete-checknum/` retains the completed 6138 / 113.6K versus 6906 / 121.6K
P18 comparison and its configuration, initial CMOS and build identities.
Each guest has RC0/ALL_DONE. Host exit timeouts and SIGTERM are explicitly
recorded. This group supersedes partial-score status, preserving the original
`integer-partial/` observations unchanged.

`refresh-checknum-partial/` retains the matched 6138 -> 5666 first integer
observation, exact old requester/arbiter, generated top and identical-binary
identities. The 5666 matches P17 MiSTer. The guest math/exit tests still run;
this group makes no completed-suite or corrected-policy speed claim.

`refresh-checknum-complete/` retains the completed same-binary 6138 / 113.6K
control and 5666 / 106.7K old-requester measurements. Both guests have
RC0/ALL_DONE; CPU objects/options and initial disk/CMOS/configuration match.
The old-requester result reproduces both P17 MiSTer numbers exactly. The
explicit host teardown classification does not replace guest completion.

## Reproduction

`combined-rbf/` retains the verified P18/P19 bitstream identity, frozen build
manifest, fitted resource summaries and detailed timing/path reports. The
4,091,384-byte RBF is exported under `build/perf01-posted-pit-rbf-20261002`.
Hardware acceptance and 50 MHz setup closure remain pending. A full CPU and
PCAT regression was subsequently requested and is recorded separately.

Use the prototype checkpoint's production P17 sources, before adoption, with
Ubuntu WSL, Verilator, NASM and the existing Quartus container:

```text
python3 tools/perf01/prepare_posted_write.py --output build/fresh-posting
```

Run each arm's `scripts/test_checkit_directed.sh` with an **absolute**
`PCAT_BUILD_DIR`, `PCAT_CODE_BUFFER_LINES=512` and `PCAT_PROFILE=1`. Then run
`review_posted_write.py` against the experiment. `test_posted_write.sh` and
`test_posted_cache.py` take the experiment and a new absolute result directory.
`map_posted_write.py` takes a new result directory and runs isolated mapping.

Build each frozen arm's `tools/perf01/build_86box_memory_probe.py` against the
existing unchanged CPU objects, then run the common launcher using fresh arm
names and the same reference image/CMOS. Complete guest receipts and strict
input/profiler/CPU-object comparison are required before using DOS scores.
