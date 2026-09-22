# Immediate register execution at 50 MHz — 2026-09-22

This increment imports the validated SPK286 immediate ALU/TEST and MOV schedule
on top of PCAT commit `0636d85eedbed3d41e1834904e6543880b996d3a`. It retains the
50 MHz CPU clock, NO_DEBUG, P01/P02/P05/P06, the existing SDRAM code buffer and
the 16 MiB memory-map fixes. No clock or memory-interface constraint is changed.

The upstream source is commit `8525236558a0e7067f442be6d48d6530edcabd23` on
`codex/immediate-execution-optimization`, based on
`bab0f67d44c4afda414d583a6948df213453e452`. Its complete regression,
309,998 affected SingleStep cases, mutation checks and synthesis sanity passed
before import. The downstream import receipt records the upstream commit and
exact imported file hashes, including the downstream compiler adaptations.

## Import

The two modified CPU RTL files are identical to the validated upstream files.
Nine format-23 controls capture the immediate and register operand together;
the existing register execution stage commits GPR/FLAGS and retires on the next
enabled clock. READY, instruction-byte availability, cancellation and event
boundaries remain dependencies. Memory forms retain their complete original
sequence. This is an implementation optimization, not a historical timing claim.

The downstream compiler and frozen contracts retain `CARRY_FILL8=171` and
`LOADALL=172`. Generated artifacts are rebuilt by the downstream compiler.
The new independent fixture applies nine literal changes to the frozen
downstream format-22 image, preserving entries, labels and all other words.
Unrelated upstream protected-mode and timing-policy development is not imported.

The broader Python check also found eight stale mutation anchors inherited in
the vendored verification tools. Current upstream corrections identify the
intended expression precisely; the scalar audit additionally distinguishes the
register FLAGS path. I/O and scalar auditors compile packages before users.
Architectural expectations and mutation rejection requirements are preserved.

The complete vendored regression exposed older test adapters that had not
followed existing protected-task, LOADALL and operand timing ports. The operand
service/byte banks now use the current upstream connections and assertions;
two legacy banks use explicit matching array/value widths. The invalid-opcode
bank's former assertion that LOADALL was unimplemented is replaced by supported
LOADALL dispatch, while retaining all three #UD cases. The existing LOADALL
integration/protected banks check image loading and architectural completion.
The event lifecycle bank uses the upstream IRET response-stage offset, accounting
for the existing validation microstep; all 468 scenarios remain enabled.
The legacy SMSW integration test expected a zero MSW after reset; it now checks
the Intel-defined `FFF0h` value already implemented by the CPU, without masking
reserved bits ([Intel 1987 Programmer's Reference Manual, section 10.4](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf)).

The I/O auditor's pristine 11,520-case string bank completed successfully in
61.25 seconds when rerun after its 60-second wall timeout. A configurable
`--simulation-timeout` retains the default of 60 seconds; this loaded build uses
180 seconds. Functional cycle bounds and all mutation assertions are unchanged.

## Directed full-machine comparison

These synthetic firmware runs use the physical SDRAM model and the same
production macros as the prior bus-latency build. They do not execute DOS
CheckIt. Historical baseline logs are verified against the previous committed
receipt. All eight workload/profile pairs preserve GPR/FLAGS, a hash of complete
backing memory, retired instructions and write counts.

| Workload, production code buffer | Previous clocks | New clocks | Throughput gain |
| --- | ---: | ---: | ---: |
| Integer mix | 1,151,471 | 1,140,987 | +0.92% |
| Fixed-point mix | 961,554 | 950,487 | +1.16% |
| Working set | 1,087,135 | 1,064,066 | +2.17% |
| Dhrystone 2.1 fixture | 1,270,699 | 1,246,833 | +1.91% |

The [comparison receipt](immediate_execution_50mhz_comparison.json) contains all
profiles and log hashes.

## Reported hardware result

The user tested the new named RBF on 2026-09-22 and supplied a CheckIt screenshot:

| CheckIt metric | Previous bus-latency RBF | Immediate optimization RBF | Change |
| --- | ---: | ---: | ---: |
| Dhrystones | 3,400 | 3,400 | 0.0% |
| Whetstones | 67.1K | 69.8K | +4.0% |
| CheckIt CPU frequency estimate | 34.87 MHz | 34.89 MHz | Diagnostic estimate |

Both FPGA configurations retain the physical 50 MHz CPU clock. This single
reported comparison shows an improvement in the software math benchmark and
no observable Dhrystone gain. It is not a repeated-run average or historical
timing calibration. The screenshot's CPU frequency estimate is not CLK2's
configured frequency.

## Verification

The 97 compiler tests, generated consistency check, independent ROM audit and
strict CPU lint pass. All 270 vendored Python tests pass after the auditor fixes.
`scripts/test_at_immediate_execution.sh` passes its six banks in Icarus and
Verilator, including 184 immediate lifecycle cases, 26 throughput profiles,
the prior register path and protected LOADALL.

The full-machine diagnostic passes in both simulators: 107 memory beats,
12 I/O writes, 32 IRQ0 observations, 27 refresh observations and four port-80
writes. The physical SDRAM LOADALL/XMS fixture passes three LOADALL operations,
32 extended-memory copy bytes, A20 aliasing and byte lanes at 50 MHz.

The scalar mutation audit rejects all eight mutants. The I/O mutation audit
passes all three pristine banks and rejects all 19 mutants with the documented
180-second host timeout. The complete `bash scripts/test.sh` regression finishes
with `TEST PASS` and exit status 0: all 71 configured RTL banks in both simulators,
CPU reset smoke in both simulators, 270 Python tests, state vectors and four
SingleStep smoke groups (970 selected cases, zero failures). The compiler's
97 tests and independent ROM audit also pass within that complete run.

## Fitted artifact and timing

Quartus 17.0.2 completed a clean full compilation in 35 minutes 38 seconds;
the additional four-corner timing report completed in 2 minutes 19 seconds.
The frozen workspace has no reused database or output bitstream. Its inventory
confirms `no_debug=1 observers=0`, `FPGA_CLK2_50 period=20.000`, and the four
production performance macros. All 342 production inputs still match the
snapshot after the verification-only adapter repairs.

The new [PCAT-286_IMMEDIATE_OPT_50MHz.RBF](../../output_files/PCAT-286_IMMEDIATE_OPT_50MHz.RBF)
is 4,055,240 bytes. SHA-256:
`7933a45cacc778b75b2426c4b06cffa0cb583ee2077846e9e5876ba6c2205d4a`.
The copied binary matches the newly generated artifact. Previous RBFs are
preserved. JSON and SHA-256 sidecars link the artifact to the frozen sources,
import receipt and successful regression log. Resource use is
27,827 / 41,910 ALMs (66%), 34,260 registers,
3,152,832 / 5,662,720 RAM bits (56%), 395 / 553 RAM blocks (71%),
38 / 112 DSP blocks (34%) and three PLLs.

| Timing corner | CLK2 Fmax (MHz) | CPU setup slack (ns) | CPU hold slack (ns) | Global setup slack (ns) | Global hold slack (ns) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Slow, 1100 mV, 100 C | 41.14 | -4.306 | 0.252 | -19.648 | -1.062 |
| Slow, 1100 mV, -40 C | 41.07 | -4.351 | 0.244 | -20.093 | -1.134 |
| Fast, 1100 mV, 100 C | 76.75 | 6.971 | 0.134 | -10.008 | -0.330 |
| Fast, 1100 mV, -40 C | 91.19 | 9.034 | 0.118 | -8.383 | -0.407 |

**The build does not close timing at 50 MHz.** Slow/100 C CPU setup changes
from -4.648 ns in the bus-latency build to -4.306 ns, and CLK2 Fmax from
40.57 to 41.14 MHz. Placement and routing changed, so these measurements do not
establish a causal improvement for every path. CPU/bridge setup remains positive
in all four corners. Slow/100 C memory-port setup is -4.331 ns, SDRAM-owner
setup -8.147 ns and SDRAM-output setup -5.413 ns; their worst paths start at
`sysmem|init_reset_n`. Global failures include video and HDMI crossings.
No timing exception was added to hide these paths. CLK2 Fmax is not a claim
that the complete machine closes at that frequency.

Full compile and timing logs remain in
`build/at-no-debug/20260922-immediate-50mhz/`. Functional simulation and a
generated bitstream do not establish hardware timing closure, historical cycle
accuracy, or Windows 3.1 boot compatibility.

## Reproduction

```sh
bash scripts/test_at_immediate_execution.sh
bash scripts/test_at_machine_boundary.sh
bash scripts/test_at_loadall_xms.sh
PCAT_PROFILE=1 bash scripts/test_checkit_directed.sh
bash scripts/build_at_no_debug.sh build/at-no-debug/NEW_RUN_DIRECTORY
```

Local validation logs are retained under ignored `build/immediate-import/`.
The fresh Quartus workspace is
`build/at-no-debug/20260922-immediate-50mhz/work/`.
