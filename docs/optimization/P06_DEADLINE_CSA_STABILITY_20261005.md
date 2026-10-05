# P06 deadline arithmetic and palette hold work

## Candidate

The prior fit has −10.992 ns global setup, −10.658 ns CPU setup and −0.110 ns
global hold at physical 50 MHz. Its critical CPU path crosses execution budget
arithmetic, saturation, comparison and register-write selection. The hold
violation is a video-clock palette MLAB write-address path.

Compress the execution lane's three addends with XOR/majority carry-save
logic, followed by one carry-propagating sum. Keep the full sum instead of
placing a saturation mux on the budget-to-deadline cone. A saturated elapsed
value directly satisfies the saturated deadline. For elapsed in 0..1023,
`elapsed >= min(1023, total)` equals `elapsed == 1023 || elapsed >= total`.
There is no new state or cycle. Admission accounting and public budget telemetry
retain their existing saturation and values.

The palette's logic is unchanged. Add a 0.700 ns minimum-delay requirement
from its write-index registers to the synchronous MLAB address registers,
allowing the fitter to route for hold. Existing single-cycle setup requirements
remain. There is no new false path, multicycle path, PLL or profile divisor.
Optional VGA configurations omit the scope; a present write index with missing
address endpoints is an error. Actual fitted collection counts must be checked.

The [Quartus LCELL documentation](https://resources.altera.com/quartushelp/17.1/hdl/prim/prim_file_lcell.htm)
discourages using logic cells as intentional delay elements because their delay
varies with process, voltage and temperature. This candidate uses timing-driven
routing requirements and four-corner STA rather than a fixed manual cell delay.

## Directed qualification

| Gate | Result |
| --- | --- |
| Symbolic actual metadata expressions | PASS |
| Scheduler state and every public output | Induction PASS against frozen production |
| Wrong opcode negative control | Rejected with counterexample |
| Unchanged scheduler / handoff / replay units, both simulators | 54 / 398 / 246 checks PASS |
| Existing five controller mutations | All rejected; only implementation anchors adapted |
| Strict helper and generated full-CPU lint | PASS |
| Full CPU handoff, all eight profiles, both simulators | PASS |
| Exact comparison with prior directed CPU receipt | Every case, clock, event, fault, cancellation, HOLD and MAX raw-stream digest identical |
| Generic schedule synthesis | 525 → 530 cells; 37 retained bits unchanged |

The formal scheduler contract is the separately proved equality of admission
and execution metadata during a body. Other inputs remain arbitrary; reset and
initial-state assumptions retain their prior explicit scope. Production
instruction minima, workloads, assertions and expected clock values are unchanged.
Generic counts are not Cyclone V ALM estimates. Full regression remains
**USER_DEFERRED**. Portable raw CPU and generated CPU/event RTL bytes are unchanged;
the generation receipt records the new included scheduler hash.

The [sealed functional packet](../evidence/p06-deadline-csa-20261005/manifest.json)
contains complete proofs, fixtures, units, negative controls, integration logs,
source snapshots and baseline comparison. Its SDC snapshot is a preliminary
constraint draft; register query names were subsequently corrected from report
entity-qualified display names to actual instance names. The fit's frozen source
and final constraint identity must bind the implemented scope. No fitted result
or hold improvement is claimed by this functional packet.

## Physical validation

Run a fresh all-features seed-1 fit at the existing 50 MHz, with Adlib/OPL2
enabled. Measure actual ALMs, registers, memory, global/CPU setup and hold,
recovery/removal and SDRAM margins. Check that the palette scope binds and that
minimum-delay routing produces positive hold without worsening a setup path.
Retain RBF/SOF and reports, seal fitted inputs/results, then remove owned compiler
databases and simulator objects. Stop only owned discarded Docker jobs.

## Completed fit and independent hold check

The all-features seed-1 compile completed in 31:12; its four-corner detailed
STA took 5:20. The fit binds all 1,376 frozen inputs at `3cd8501`, the actual
compiled 1024-word M10K image and the directed qualification sources. The only
compile-generated source update is BUILD_DATE. The added palette minimum-route
collection binds 8 sources and 288 endpoints. Other SDC/QSF/QIP/QPF/TCL inputs
and all functionality settings retain their preceding identities.

| Measurement | Prior execution-deadline fit | CSA fit |
| --- | ---: | ---: |
| Global setup minimum | −10.992 ns | −10.412 ns |
| CPU setup minimum | −10.658 ns | −10.359 ns |
| Hold under original SDC | −0.110 ns | +0.041 ns |
| CPU hold minimum | +0.094 ns | +0.121 ns |
| Equivalent ALMs | 31,600 | 31,234 |
| Actual physical placed ALMs | 36,866 | 36,638 |
| Registers | 38,166 | 38,203 |
| M10K / DSP / PLL | 416 / 39 / 3 | 416 / 39 / 3 |

Physical placement occupies 87.42% of the device, 228 fewer ALMs. Fitted
register count includes physical optimization; no retained scheduler state
was added. SDRAM input setup/hold minima are +5.185 / +5.000 ns, and output
setup/hold minima are +4.312 / +0.098 ns. Recovery/removal are +3.111 / +0.190 ns.

The fitted 0.700 ns extra palette requirement has −0.082 ns hold slack at the
fast −40 C corner. That path has 0.684 ns data delay and 0.006 ns clock skew;
it fails the voluntary margin. An independent four-corner STA run overlays
the exact preceding SDC on the same completed fitted netlist. It reports
positive real hold in all four corners, with global minimum +0.041 ns.
RBF/SOF and all recorded fitted artifacts were checked unchanged before and
after the overlay. No actual hold path was waived or excluded.

For subsequent fits, select a 0.500 ns extra minimum-route requirement. This
still tightens the original 0 ns clock relationship; it does not change setup,
clocks or false/multicycle exceptions. Its physical acceptance remains to be
measured in a fresh fit. The original 0.700 ns result and its failure remain
recorded. Setup remains open; the next candidates address live event selection
and metadata arithmetic. There is no whole-design timing closure claim.

The [sealed fit packet](../evidence/p06-deadline-csa-fit-20261005/manifest.json)
preserves effective source bytes, both complete STA runs, original reports,
resource/hierarchy accounting, source bindings and launch commands. Owned
compiler databases and duplicate sources are removed after byte verification;
RBF/SOF, reports and prior candidates remain available.

RBF: `build/p06-deadline-csa-allfeatures-20261005-v1/work/output_files/PCAT-286.rbf`

Full regression remains **USER_DEFERRED** and hardware testing is **NOT_RUN**.
