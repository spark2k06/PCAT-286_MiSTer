# P18/P19 active-option full regression

Date: 2026-10-02. Status: **execution completed with open checks; aggregate
acceptance is not claimed**. The run is
`build/full-regression-posted-pit-active-20261002`.
Original failures and identified successful replays are retained separately.

## Terminal result

The frozen full run started at **20:32:08** and finished at **22:20:50**
Europe/Madrid, taking **1 h 48 min 42 s**. All lanes completed; no frozen input
changed and no check was interrupted to report completion.

| Lane | Original PASS | Original FAIL | Total |
| --- | ---: | ---: | ---: |
| Production CPU | 123 | 24 | 147 |
| CPU audits | 20 | 5 | 25 |
| PCAT/platform | 60 | 19 | 79 |
| Total | **203** | **48** | **251** |

Of the 48 initial failures, **37 have separately retained successful replays**
after verification-package, manifest, fixture-contract or input-supply repairs.
The other **11 entry points remain unaccepted**: four historical compiler-fixture
checks, one MRBIOS restart, one source-bound P05 proof, four missing Landmark
ROM workloads and one deliberately disabled historical CheckIT counterfactual.
The raw result remains **FAIL**; it is not overwritten by the successful replays.
No production CPU/chipset correction is inferred from those verification repairs.

The final synthesis gate, failure-propagation checks and MCL86 checks pass.
MCL86 runs 24 toolchain tests, matches the original **4096/4096 words**, and
preserves both 4096-word round trips. Its separate rewrite differs in 431
words, as explicitly reported by that research check; it is not the production
SPK286 microcode image.

## Scope and source identity

The user requested the complete regression and subsequently limited CPU
configuration to the enabled options. Every CPU compile uses
P01/P02/P05/P06/P07 from `config.tcl`; no disabled-option reference arm remains
running. Internal timing-policy matrices and memory/native-width controls
retain their existing functional checks with those macros enabled.

The original run freezes HEAD `976e8a00d454e4c5ea220117060ea96b11ea0123`
and 1257 input files, including the then-pending verification repairs. The
physical corpus revision is recorded in `inputs.json` and in each identity
report. Production RTL, microcode source/generated image, configuration and
constraints retain their original byte hashes through the repairs and replays.
No RBF, CPU or chipset implementation is changed by this regression work.

The historical Git-baseline code-buffer equivalence experiment is excluded
from this functional run; production capacity/coherence checks execute.
The explicit CPU-options-off bus-latency experiment is also excluded to honor
the requested active-only scope. Other registered shell entry points execute,
including diagnostics whose unavailable inputs are reported as coverage gaps.

## Completed evidence

- Required physical cohort: **1,386,996 passed**, failed 0, 307 opcode files,
  no unexpected omissions. The one exact incomplete E7 capture remains
  **NOT EVALUABLE**; three revoked records remain excluded by their existing
  policy. This does not change their publication or architectural-release status.
- Supplemental SALC/ESC physical families: **6,000 passed**, failed 0.
  Total evaluable physical cases passed: **1,392,996**.
- All **20 CPU mutation families** complete after separately retained source
  manifest and exact functional-assertion receipt repairs. Compile errors and
  arbitrary failures are never accepted as functional mutant rejection.
- The corpus/parser/comparator audit cross-checks **1,398,000 raw records**
  against the upstream parser, rejects **1,925 negative probes**, and accepts
  **320 positive controls** against the same production executable.
- Generated microcode consistency, the microcode audit and strict CPU lint pass.
- The composed posted-write/PIT CPU diagnostics pass with common and divided
  clocks: **14 accepted stores / 14 physically drained stores** per run.
  A20 aliases, ROM write blocking, IRQ/IRET and original signatures remain checked.
- Phoenix protected-mode reset and floppy POST tests pass after supplying the
  exact locally available ROM bytes, whose identities are retained separately.
- SDRAM admission/phase tests pass both simulators at the common phase and
  3 ns chip advance, with **90 checks** per run. Early write launch, retained
  payload, byte masks, burst order, refresh and reset-before-pin-command checks
  remain required. The updated test checks the implemented launch contract.
- The native-width memory workload preserves retired instructions, all data
  traffic/stores, GPRs, FLAGS, CS/IP and initialized full-memory signature
  `8ddb7025`. Speculative code-read counts may differ; negative controls reject
  every required architectural field change. The eight-part code-buffer
  integration entry point completes with the corrected comparator.
- XTIDE and code-capacity entry points pass after restoring omitted modules
  in their manifests. The capacity experiment completes **32 variants / 128 runs**.
- The active-profile stack-offset check passes with both simulators after
  supplying its already committed, source-bound proof omitted by the original
  snapshot. The subsequent runner preserves this proof when freezing inputs.

All **129 banks in the original CPU registry are covered successfully**.
Twenty-three were registered
but missing from the vendor test package. Their exact upstream test bytes
were tested against the frozen PCAT CPU with both simulators, then restored
in commit `7533270`. The additional independent event-arbitration bank passes
both simulators and rejects the owed-TF-priority mutation without relying on
an instruction fetch fault that real-mode wrapping correctly avoids.
The repaired current registry additionally includes the independent event
arbitration bank, making 130 banks; its separate successful receipt is retained.
The existing full expand-down matrix runs in Icarus with 2183 checks and
2,998,872 READY stalls; its explicit historical Verilator-skip policy is retained.

## Checks that prevent aggregate acceptance

### MRBIOS restart: unresolved integration failure

With MR BIOS 1.65 supplied, the keyboard-driven restart fixture completes its
first Ctrl-Alt-Delete and re-enters POST. On the second fixture invocation,
keyboard byte 38h times out with IRQ1 pending and CS:IP in low RAM. The raw
failure, POST sequence and registers are retained. The old 32-clock AT refresh
requester reproduces the same failure class with the active CPU unchanged;
the P19 PIT correction is therefore not necessary to reproduce it.

This BIOS bank does not instantiate the P18 posted-write block from
`PCAT-286.sv`. Its separate composed posted-write diagnostics must not be
confused with this failure. The fixture installs its RAM program directly in
the pin-model array and redirects the running CPU while preserving chipset
and caches. A passive program-span monitor found no stale code read there.
An attempted physical-loader control allowed the CPU to run during fixture
installation and failed before the intended check; it is **not a valid
corrective control** and is retained as an unsuccessful diagnostic attempt.

No CPU, cache or fixture cause is established yet. Reduce and capture the
IRQ/vector/stack sequence, compare against a coherently installed fixture,
and only then select an implementation area. Do not weaken the restart count,
keyboard checks or architectural assertions to turn this bank green.

### Historical compiler fixtures: verification version debt

The Python suite reports three failures and five errors. Some checks name
obsolete LOADALL/SALC source filenames, one required phase-9 fixture is absent,
and literal historical encodings disagree with the current LOADALL/CARRY_FILL8
catalog ordering. The immediate/register canonical-source checks encounter
the same historical SALC/LOADALL collision. The root immediate/register/LOADALL
scripts stop at those Python checks; their executable CPU banks are covered
independently by the complete registered-bank run and the additional LOADALL
replay. This executable coverage does not make the scripts themselves PASS.

Current microcode generation and its independent audit pass. Migrate these
fixtures with explicit format/catalog provenance or a versioned historical
decoder. Do not regenerate expected historical literals blindly from the
candidate compiler, which would destroy their independent regression value.

### P05 source-bound SAT harness: obsolete extraction scope

The original pre-P05 expression remains identical to its frozen contract,
but the candidate now uses the parallel cache/range helper network. The old
proof correctly refuses its changed identifier set instead of treating those
helper outputs as free ports. Extend source extraction to the actual helper
network and its selection bindings, retain the frozen arithmetic reference,
and require a genuine boundary counterexample from the negative control.
Directed CPU coverage is not a substitute for this open proof check.

### Supersoft Landmark: missing exact ROM inputs

Four CMOS/DMA/floppy/peripheral entry points require AT 5170 images absent
from the available input package. The available SKIP_PM_V2 image is a different
artifact and is not silently substituted for the required older/full images.
These four workload gates are **not executed**, rather than passed.

### Old IDEAL_OWNER counterfactual: disabled experiment

The old CheckIT attribution script requests IDEAL_OWNER modes 1 through 6,
which the current benchmark explicitly rejects after the posted-write model
change. Its ordinary physical kernels run and pass before that rejection.
The historical counterfactual remains unavailable; no rate from it is counted
as candidate acceptance. Reintroducing such a model requires its own validated
ordering/drain semantics.

## Relationship to the protected-mode backlog

These findings do not establish a new protected-mode CPU failure or reopen a
closed H story. Missing banks, stale compiler fixtures and proof extraction
are verification repairs. The MRBIOS restart needs a reduced architectural or
motherboard transaction case before attribution to an H finding is justified.
H02 (partial), H05, H17, the remaining H19 matrix and H20 retain their separately
recorded scopes in the global protected-mode review.

## User performance observation and later work

The user supplies CHECKNUM **6906 / 121.6K**, matching the completed combined
86Box platform model exactly. The independent CheckIT screen reports
**6765 / 121.6K**. On 2026-10-03 the user confirms the delivered RBF; this
attribution does not imply independently observing its loaded hash or passing
the still-open regression checks. The same-CPU immediate-memory reference is
**7709 / 133.3K**: current CHECKNUM reaches **89.58% / 91.22%**, requiring
another **11.63% / 9.62%** rate increase to equal it. Native 86Box's separate
286 model, **8287 / 144.9K**, remains a later comparison.

The combined bitstream remains byte-identical to the delivered artifact.
Its 50 MHz setup closure is still deferred as requested; regression simulations
and benchmark improvement do not replace timing analysis or broaden the
user's hardware observation into OS/game acceptance for this particular RBF.

The completed receipt preserves all original results, exact failed-stage
classifications, replay identities and an archive of the executed logs. The
later snapshot repair includes the already committed stack-offset proof;
prepare-only mode freezes it without launching a second complete regression.
The archive retains the earlier runner bytes actually used by this run.

Retained evidence: [completed receipt](../evidence/full-regression-posted-pit-active-20261002/completed/receipt.json),
[active regression receipts](../evidence/full-regression-posted-pit-active-20261002/README.md)
and [combined candidate](P18_P19_COMBINED_RBF_20261002.md).
