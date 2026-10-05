# P06 compressed instruction metadata budgets

The execution deadline originally follows consecutive additions of instruction
base, effective-address correction, prefix allowance and REP iteration clocks.
REP also subtracts two clocks after a wide addition because its setup already
includes one prefix. This leaves another long combinational cone after the
separate event selection improvement in `c38898c`.

Factor the nonnegative prefix allowance first. A repeated string uses
`2 * max(prefix_count - 1, 0)`; an ordinary instruction uses `2 * prefix_count`,
and event delivery has no ordinary prefix allowance. Select instruction/REP
base and EA/iteration addends, compress the three operands using XOR/majority,
then perform one carry-propagating sum and the unchanged 1023-clock clamp.
The function is shared by admission and execution metadata. Event selection
remains after the ordinary execution budget. There is no new state or cycle.

## Qualification

| Gate | Result |
| --- | --- |
| Actual new function versus actual old admission arithmetic from `c38898c` | All symbolic inputs proved equal; no lifecycle assumption |
| Zero-prefix underflow / omitted EA negative controls | Both rejected with counterexamples |
| Actual admission/execution expressions during a body | Symbolic equality PASS |
| Scheduler state and all public outputs | Induction PASS against frozen production |
| Wrong execution opcode negative control | Rejected |
| Strict full generated CPU lint | PASS |
| Scheduler and full TOP prefix oracles, both simulators | PASS |
| Full CPU handoff, all eight profiles, both simulators | PASS |
| Exact prior directed results | Entire list identical, including cycles, budgets, events, faults, cancellation, HOLD and full MAX public stream |

The new arithmetic proof pins and extracts the old generator's actual code;
it does not replace the old expression with a rewritten expectation. The
existing context/scheduler proof retains its explicit initial-state/reset and
metadata-lane equality contract. The arithmetic proof discharges the additional
change to admission values. Instruction table minima, speed divisors, stimuli
and expected cycles remain unchanged. Full regression is **USER_DEFERRED**;
hardware testing is **NOT_RUN**.

Isolated generic execution-metadata mapping changes from 1,179 to 1,155 cells,
with zero registers in both versions. The scheduler remains 530 generic cells
and 37 retained bits. These are not fitted Cyclone V ALM counts or nanosecond
predictions. Physical acceptance requires a fresh all-features fit at the same
50 MHz and four-corner setup/hold analysis.

The [sealed qualification packet](../evidence/p06-budget-compressor-20261005/manifest.json)
preserves original/current sources, generated CPU, actual-expression proofs,
negative controls, unchanged directed fixtures, full logs and baseline/cost
comparisons. Every archived member was verified against its original bytes
before deleting owned simulator objects. The recorded SDC is the then-current
0.700 ns palette routing requirement; any subsequent constraint adjustment must
be explicitly bound and measured by its fit packet.

## Completed physical measurement

All-features seed-1 compile at frozen `fbda3ba` completed in 35:33. The
[sealed fit packet](../evidence/p06-budget-compressor-fit-20261005/manifest.json)
binds all 1,377 frozen inputs, the actual compiled M10K image, qualification
receipts and both complete four-corner STA runs.

| Measurement | Event selection | Budget compressor |
| --- | ---: | ---: |
| Global / CPU setup minimum | -6.989 ns | -7.300 ns |
| Global hold under original SDC | +0.009 ns | +0.082 ns |
| CPU hold minimum | +0.118 ns | +0.115 ns |
| Equivalent ALMs | 31,563 | 31,110 |
| Physical placed ALMs | 36,757 | 36,610 |
| Registers | 38,218 | 38,204 |
| M10K / DSP / PLL | 416 / 39 / 3 | 416 / 39 / 3 |

Physical placement is 87.35%, 147 ALMs fewer than the event-selection fit.
Setup is 0.311 ns worse, so event selection remains the best measured setup
candidate. The arithmetic version provides a resource reduction and is the
base for the independently verified REP-permission correction; its own fit
does not establish timing closure.

The extra 0.500 ns palette route requirement reports -0.055 ns hold slack.
With the original SDC, the same fitted netlist has positive global hold in
every corner, minimum +0.082 ns. Recorded fitter files and RBF/SOF were verified
unchanged across that independent STA check. Recovery/removal minima are
+2.879/+0.218 ns. Original constraints and the added voluntary route guard
are reported separately; no existing setup, clock or hold requirement was
waived.

The archive was read back byte for byte before deleting 317,280,461 logical
bytes of owned compiler temporaries. RBF/SOF and reports remain available.
Full regression remains **USER_DEFERRED**; hardware is **NOT_RUN**.

RBF: `build/p06-budget-compressor-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`
