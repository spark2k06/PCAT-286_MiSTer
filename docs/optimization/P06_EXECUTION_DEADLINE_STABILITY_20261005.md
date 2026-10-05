# P06 execution deadline timing work — 2026-10-05

## Critical-path hypothesis

The registered-head fit still has −16.044 ns worst setup at the existing
physical 50 MHz. Its worst path traverses prefetch data, opcode decoding,
metadata classification and arithmetic, deadline comparison, EU exception
selection, and microsequencer admission. There are 31 logic levels.

The original metadata lane selects the next decoded head before a body starts
and the retained instruction context during execution. Physically, this puts
admission decoding on the retirement/REP permission cone, even though a body
deadline is never needed for the admission case.

Add a parallel combinational metadata lane using only the retained execution
opcode/entry, with the same event context, operands, outcome/count, prefixes,
REP policy and READ qualification. Use it for the deadline comparison. Preserve
the original admission metadata for captured state, elapsed accounting and
scheduled-clock telemetry. No register or virtual-clock stage is inserted.
No instruction minimum, divisor, PLL, dependency, timing constraint, event
priority or raw CPU behavior is changed.

## Verification

| Gate | Result |
| --- | --- |
| Existing scheduler, handoff and replay units, each simulator | 54 / 398 / 246 checks PASS |
| Existing five negative controller mutations | All rejected; adapted only implementation anchors |
| Strict helper and generated full-CPU lint | PASS |
| Symbolic metadata lane equality | PASS using expressions extracted from the actual generator |
| Scheduler state and every public output | Induction PASS under the proved lane contract |
| Wrong next-head opcode in execution lane | Rejected with counterexample |
| Full CPU handoff, all eight profiles | 777 cases in each simulator PASS |
| Exact prior directed receipt comparison | All results, clocks, budgets, frames, faults, cancellations, HOLD and MAX public-stream digest unchanged |
| Directed compatibility: execution, prefixes, events, REP memory/I/O zero-count | 15 Icarus + 15 Verilator records at MAX/6/25 PASS; five MAX raw CPU pairs exact |
| Generic synthesis | Scheduler 383 → 525 generic cells; 37 retained register bits unchanged |

The lane theorem holds for arbitrary context inputs whenever `body_active` is
true. The caller's original `candidate_body` expression then excludes the
next-head opcode. Qualification, clock budget and READ policy match exactly.
The scheduler proof equates its 37 retained bits and every public output after
zero initialization and reset at step one. Outside a body, the two metadata
inputs may differ freely. These assumptions are explicit and discharged by
the actual-context theorem, not treated as unverified timing exceptions.

The first formal adapter attempt omitted Yosys `-set-assumes`; independent
arbitrary lane values then produced an expected mismatch. That failed record
is retained. The corrected run applies the separately proved contract without
changing the production implementation or expected outputs.

The two existing scheduler benches only wire the additional lane inputs to
their original stimulus. Architectural assertions, instruction kernels and
expected clock values are unchanged. The ordinary timing policy module and
raw CPU sources retain their earlier validated hashes. The full compatibility
regression remains **USER_DEFERRED**.

## Cost, fit and evidence

Generic cell counts are not FPGA ALM estimates. Duplicated combinational
classification may increase ALMs; Quartus must measure actual sharing,
placement, setup and hold before judging this tradeoff. No new registers,
memory, DSP or clock hardware are requested by the implementation.

The [sealed packet](../evidence/p06-execution-deadline-20261005/manifest.json)
retains exact tested sources, fixtures, logs, proof scripts, counterexamples,
receipts and baseline comparisons. Simulator objects are excluded and removed
after byte verification. Verified implementation commit: `99c4934`.

A fresh all-features 50 MHz compile started at 2026-10-05 10:56:40 UTC in
`build/p06-execution-deadline-allfeatures-20261005-v1`, from 1,375 frozen input
files. Compilation succeeded in 28 min 05 s; detailed four-corner STA took
3 min 35 s. The complete flow finished at 11:28:28 UTC, 31 min 48 s after
launch. Adlib/OPL2 and every other feature remain enabled.

| Metric | Registered-head baseline | Execution-deadline fit | Delta |
| --- | ---: | ---: | ---: |
| Worst global setup | −16.044 ns | −10.992 ns | +5.052 ns |
| Worst CPU setup | −16.044 ns | −10.658 ns | +5.386 ns |
| Worst global hold | +0.055 ns | −0.110 ns | −0.165 ns |
| Worst CPU hold | +0.120 ns | +0.094 ns | −0.026 ns |
| Worst global recovery | +1.981 ns | +2.429 ns | +0.448 ns |
| Worst global removal | +0.160 ns | +0.187 ns | +0.027 ns |
| Equivalent ALMs | 31,108 | 31,600 | +492 |
| Physical ALMs used in final placement | 36,490 | 36,866 | +376 |
| Physical placed device occupancy | 87.068% | 87.965% | +0.897 percentage points |
| Total registers | 38,127 | 38,166 | +39 |
| Block memory bits | 3,301,019 | 3,301,019 | 0 |
| M10K | 416 | 416 | 0 |
| DSP / PLL | 39 / 3 | 39 / 3 | 0 / 0 |

Physical ALM totals come from the Fitter's global final-placement count.
Hierarchy attribution instead reports 36,489.0 and 36,865.5; those fractional
attributions are not the whole-device physical count. The inclusive CPU
hierarchy changes from 7,357.3 to 7,670.1 equivalent ALMs, 8,156.3 to 8,475.4
placed ALM attribution, and 5,492 to 5,519 registers. Mapping and duplication
alter fitted register counts although the scheduler still retains the same
37 architectural bits and adds no pipeline stage.

## Remaining timing paths

Setup improved, but **this candidate does not close at 50 MHz**. The worst
global setup path starts at BIOS ROM-availability `missing_ega_sync[1]` and
ends at CPU `gpr_q[63]`: 30 logic levels, 30.310 ns data delay, −10.992 ns slack
at the slow −40°C corner. The worst CPU-only path starts at `operand.blocked`
and reaches the same register: 28 levels, 29.966 ns data delay, −10.658 ns.
Its chain crosses event dispatch, execution metadata, deadline arithmetic,
stack/range checks, operand completion and register-write selection. The
prefetch-head metadata cone is no longer the reported worst path.

Global hold is now negative in the EGA/VGA palette's green distributed RAM:
`vga_dac_io.write_index[3]` to the DAC RAM address register, −0.110 ns at the
slow −40°C corner. This is a zero-logic-level path with 0.309 ns data delay
and +0.419 ns clock skew. CPU hold remains positive at +0.094 ns. The palette
violation needs correction; it has not been waived or made a false path.

Reported SDRAM input setup/hold minima are +5.181 / +4.986 ns, and output
setup/hold minima are +5.316 / +0.073 ns. These constrained external paths
remain positive. Other setup violations remain in CPU integration, memory,
cache, SDRAM ownership and video. Inherited platform timing-check limitations
are unchanged; bounded top-N reports are not a total path census.

The measured setup benefit costs 376 additional physical ALMs, with unchanged
memory, DSP and PLL usage. It is useful progress towards timing closure, not
a demonstration of complete hardware stability. No PLL, SDRAM clock relation,
profile divisor, minimum instruction time or SDC exception was changed.

## Fitted artifact and cleanup

The [sealed fit packet](../evidence/p06-execution-deadline-fit-20261005/manifest.json)
retains all effective input files, original reports, measured comparisons and
source bindings. Every directed CPU/generator proof input matches the fitted
source, and every baseline SDC, QSF, QIP, QPF and TCL hash is unchanged. The
sole declared compile-generated input update is BUILD_DATE in `build_id.v`.

RBF: `build/p06-execution-deadline-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`

SHA-256: `4c02e8dac4b7026ae938bdf8c70637f2aaf80cc99545a3fc1dd8e081fae2bddd`

Size: 4,105,836 bytes. Hardware testing is **NOT_RUN**. Directed cycle
equivalence gives no expected profile or benchmark change; the preceding RBF
remains available for consistent ongoing hardware/profile measurements.

After checking the sealed packet against every archived byte and confirming
the directed processes had completed, five owned test directories and the
collector were removed: 1,300,998,280 logical bytes. After the completed fit,
all 1,568 archived members and original bytes were verified again. The owned
compiler databases, duplicate frozen source tree and fit collector were then
removed. RBF/SOF, compact reports, root metadata, timing reports and predecessor
artifacts were retained; the new RBF hash was verified after cleanup. No Docker
container remained active.

The [cleanup receipt](../evidence/p06-execution-deadline-fit-20261005/cleanup.json)
records the exact removed paths. This fit's removed byte total is unavailable:
CIM denied the free-space query after deletion and before the accounting could
be saved. The cleanup itself completed and was checked separately. Native
DriveInfo subsequently measured approximately 25.21 GiB free on C: and
149.98 GiB on D:. No unmeasured freed-byte total is claimed.
