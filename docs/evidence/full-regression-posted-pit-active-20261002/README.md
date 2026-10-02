# Active-options regression evidence

The complete run is retained under
`build/full-regression-posted-pit-active-20261002`. It freezes the PCAT sources
and uses only P01/P02/P05/P06/P07 enabled from `config.tcl`. Initial failures
and later replays are separate records; no initial result is overwritten.
The initial package receipt was recorded while the run was still executing.
The full run has subsequently completed; its terminal result is retained below.

## Completed run

`completed/receipt.json` records **COMPLETED_WITH_OPEN_CHECKS**, with the raw
result still **FAIL**. All 251 stages finish: 203 original PASS and 48 original
FAIL. Of those failures, 37 have individually verified successful replays and
11 entry points remain unaccepted. Original failures are never rewritten.

All 129 original CPU banks are covered successfully, including 23 restored
banks tested against the unchanged CPU in both simulators. The additional
event-arbitration bank also passes. There are **1,392,996 evaluable physical
cases passed**, zero failures and zero unexpected omissions. The exact one E7
incomplete capture remains NOT EVALUABLE under the existing policy.

Open checks comprise the unresolved MRBIOS keyboard-restart failure, historical
compiler fixtures, an obsolete source-extraction proof harness, four absent
Landmark ROM workloads and the disabled old CheckIT counterfactual. No new
protected-mode CPU defect or aggregate hardware acceptance is established.

`completed/logs.zip` preserves all original stage logs, replay logs and receipts,
diagnostic attempts and the frozen runner bytes actually executed. Its entries
are byte-verified against `completed/archive-inventory.json`; source identity,
raw summary and physical-case summary are also retained separately.
No proprietary BIOS ROM binary is included. See the
[full report](../../optimization/P18_P19_FULL_REGRESSION_20261002.md).

## Restored verification package

`restored-unit-package.json` records 23 upstream unit banks missing from the
vendored package despite registration in `scripts/test_units.sh`. Every bank
passed Verilator and Icarus against the frozen PCAT CPU and generated microcode
with active options. The receipt identifies upstream revision, exact test
bytes, unchanged CPU hashes, commands and original log hashes. The validated
test files are restored under `vendor/spk286/sim/unit`; existing files and
architectural assertions are preserved. No production RTL is changed.

The full suite also finds historical compiler fixtures and diagnostic-script
issues. The package restoration is a verified coverage repair, not an overall
regression PASS or hardware acceptance. Those results are recorded separately
in the completed receipt and report.

## Completed verification repairs

`verification-repairs/receipt.json` retains the original and corrected logs
for all 20 CPU mutation families, the canonical source-manifest tests, event
arbitration, architectural memory-work comparison, SDRAM admission/phase checks,
XTIDE and code-capacity manifests, and active-profile stack-offset validation.
The RTL, generated microcode and configuration byte hashes remain unchanged.

The event arbitration bank independently rejects the owed-TF-priority mutant
without depending on a real-mode instruction fetch that wraps correctly at
FFFFh. Unary, segment and ESC mutants remain rejected by exact functional
assertions that now execute before the old expected messages; compile failures
and arbitrary nonzero exits are not accepted as functional rejection.

The memory workload retains all data traffic, retired work, GPRs, FLAGS, CS/IP
and a complete initialized memory signature. Only speculative code-read counts
may vary with the native prefetch path. Dedicated negative controls reject
changes to each architectural field or to the required physical-store count.

The SDRAM bank now explicitly requires writes to enter KFSDRAM on the accepting
edge, while reads/refresh retain their entry stage. It still corrupts upstream
payload after acceptance, checks all read data/byte writes/burst order, and
asserts reset before registered pin commands cannot leak a write. Both
simulators pass 90 checks at the common phase and at a 3 ns chip advance.

The stack-offset replay supplies the already committed proof omitted by the
runner's initial snapshot, verifies its source/artifact hashes and runs only
the requested active profile with both simulators. These successful repairs
do not waive the separate unresolved MRBIOS restart or compiler-fixture checks.

## SingleStep comparator controls

`singlestep-probes/` retains the completed corpus/parser/comparator audit and
the earlier rejected repair attempt separately. The audit cross-checks all
1,398,000 source records against the upstream parser and rejects **1,925**
fault probes with **320** successful positive controls against the unchanged
production executable. Counts here are derived from actual `FAULT_PROBE`
records, including the additional #UD-vector positive control.

The original negative fixture replaced only the first byte with 0Fh and
expected an unsupported latch from early development. Supported 286 system
forms and architectural #UD delivery make that fixture stale. The corrected
probe uses a complete reserved escape and supplies the four #UD vector bytes,
then requires an architectural completion mismatch against the original MOV
expectation. The unchanged MOV with the same added vector must first pass.
No physical-corpus expected state, CPU RTL or comparator assertion changes.
