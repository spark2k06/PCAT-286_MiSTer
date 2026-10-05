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
