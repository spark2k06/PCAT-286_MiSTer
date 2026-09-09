# SPK286 Phase 1 Handoff

Date: 2026-09-05
Branch: `codex/phase1-architectural-state`
Verified Phase 0 parent: `c021070` (`codex/phase0-bootstrap`)

## Outcome and scope

The architectural foundation requested for this Phase 1 session is implemented
and verified. This advances the prerequisites of RM1 in
`SPK286_REALMODE_MVP.md`; it does not complete RM1 or the real-mode MVP.

- Eight 16-bit GPRs and all eight byte aliases, two independent read ports,
  one byte/word write port, deterministic reset and observation.
- 16-bit architectural IP and masked FLAGS storage, including space for
  IOPL/NT, without an arithmetic flag generator or instruction policy.
- CS/DS/SS/ES visible selectors and independent hidden 24-bit bases, 16-bit
  limits and 8-bit normalized access state.
- Intel-defined reset values in this scope: CS=F000, base=FF0000, IP=FFF0,
  FLAGS=0002; DS/SS/ES selectors/bases zero; all four segment limits FFFF.
- Ordinary real-mode reloads, including same-selector CS reload, and cached
  base-plus-offset addressing with carry through A20. No PC/AT A20 logic.
- Integrated first fetch at FFFFF0, sequential fetch requests, one response
  slot, READY waits, odd/even byte lanes, response backpressure and coordinated
  near/far restart. Stale outstanding reads drain and are discarded.
- Independent architectural IP and fetch cursor. Fetch cursor exhaustion is
  retained beyond FFFF, preventing silent wrap into offset zero.
- A small state-vector bridge through the existing data reader and Verilator
  executable, using normal datapath commits and a synthetic memory response.

No instructions execute. No ALU, decoder, interrupts, exceptions, protected
mode, descriptor loading, LOADALL or microcode engine has been added.

## Modules and interfaces

| File | Responsibility |
| --- | --- |
| `rtl/spk286_registers.sv` | GPR/byte storage, IP, masked FLAGS |
| `rtl/spk286_segments.sv` | Visible/hidden segment state and address formation |
| `rtl/spk286_fetch.sv` | One outstanding code read, response slot, restart/drain |
| `rtl/spk286.sv` | Integration and controller-transaction consistency checks |

The execution-facing controls are temporarily top-level composition ports;
they will be driven internally by the instruction controller. They are not
architectural instructions or debug-only state injection. A CS reload requires
a redirect and IP write; a redirect requires an IP write. Malformed controls
assert `control_error` and suppress the state transaction, without pretending
to generate an x86 exception. Read-only debug vectors expose the actual state.

See [STATE_INTERFACE.md](STATE_INTERFACE.md), [BUS_INTERFACE.md](BUS_INTERFACE.md)
and [ARCHITECTURE.md](ARCHITECTURE.md). Microcode ownership remains as specified
in `SPK286_MICROCODE_FORMAT.md`; no packed microinstruction format was frozen.

## Tests and exact results

The received Phase 0 regression passed before edits: both reset smokes, four
Python reader tests and Yosys with zero structural problems.

Every functional commit passed lint, affected tests, both simulator smokes and
the complete then-current regression. Final validation used a previously absent
build directory, rebuilding every executable from source:

```bash
SPK286_BUILD_DIR="$PWD/build/phase1-final" make regression
SPK286_BUILD_DIR="$PWD/build/phase1-final" make verify-failure waveform data-smoke
```

Both commands returned status 0. The ordinary `make regression` path also
passed after each milestone.

| Check | Final result |
| --- | --- |
| Verilator `--Wall` lint | PASS, integrated top and all three component modules |
| `spk286_registers_tb` | PASS in Verilator and Icarus: 200 counted register/flag checks plus reset/commit cases |
| `spk286_segments_tb` | PASS in both: 262,202 counted cache/address checks, including 262,144 paragraph loads |
| `spk286_fetch_tb` | PASS in both: 26 counted bus/response checks plus wait/backpressure/cancellation/limit cases |
| `spk286_core_tb` | PASS in both: 7 counted bus checks plus integrated state/redirect/error/reset cases |
| Original reset smoke | PASS in the C++ Verilator harness and Icarus; FFFFF0 first fetch preserved |
| Python `unittest` | 8 tests PASS: 4 existing reader tests and 4 state-adapter tests |
| State vectors | 4 initialization/first-fetch cases PASS in Verilator (original fixture + 3 directed cases) |
| Yosys | PASS for integrated hierarchy and every component; `check -assert`, 0 problems in all four runs |
| Negative failure path | PASS; both simulators returned nonzero for an intentionally wrong fetch address |
| Waveform | PASS; `build/phase1-final/traces/reset_verilator.vcd` generated |
| Data ingestion smoke | PASS; 1 fixture parsed/selected, execution deferred |
| Git diff whitespace checks | PASS |

The counted checks are testbench progress counters, not instruction counts or
complete assertion totals. Additional explicit checks are described in the
table. No RTL or C++ warnings were reported in the positive final regression.
No warning suppression was added; the old Verilator build's `--Wno-fatal` was
removed, and structural checks now use `check -assert`.

Logs and reports remain ignored and reproducible:

- `build/phase1-final-regression.log`
- `build/phase1-final-extra.log`
- `build/phase1-final/reports/yosys_*.log`
- `build/phase1-final/state-vectors/<source-stem>/`: input streams,
  expected/actual JSON snapshots and driver stderr

Simulator coverage: WSL Verilator 5.020 and Icarus/VVP 12.0. Python 3.12.3 and
Yosys 0.33 remain the Phase 0 tools. No toolchain installation or infrastructure
redesign was needed. The state adapter itself uses the C++ Verilator driver;
the underlying RTL has independent Icarus coverage.

## Synthesis and hardware status

The final Yosys process/optimization/structural result reports 152 generic RTLIL
cells across the hierarchy, 0 remaining processes and 0 memories. These are
not Cyclone V ALMs or mapped flip-flop/resource counts. The 20 `$sdff`/`$sdffe`
cells are vector cells, not 20 physical state bits.

Quartus compilation, ALM/RAM/DSP utilization, Fmax and physical FPGA validation
were not run. Phase 0 has no small Quartus project to reuse, so creating one
would expand this CPU-foundation milestone. MiSTer/PCAT integration remains
outside the standalone CPU and outside the fast loop.

## Evidence and decisions

- D-007: explicit datapath storage, x86 register encoding, masked FLAGS and
  separation from instruction control.
- D-008: 286-sized hidden cache fields, ordinary real-mode reload contract,
  canonical access representation and 24-bit physical address formation.
- D-009: architectural commit versus fetch progress, response backpressure,
  coordinated restart and the normalized bus contract.

See [DECISIONS.md](DECISIONS.md) and [SOURCE_NOTES.md](SOURCE_NOTES.md) for Intel
manual/page references. Intel's hardware reset table was visually inspected.
Appendix C explicitly resolves the programmer manual's misleading 20-bit
real-mode shorthand: the CPU adds a 16-bit offset to a 24-bit cached base.
No external RTL, microcode or implementation fragments were reused.

One real simulator disagreement was reproduced and fixed: Icarus kept an
initial read stale when a function accessed GPR state through an implicit
outer reference. Passing that state explicitly to the function fixed the
dependency in both simulators. Expected architectural results were unchanged.

## Known limitations and unresolved questions

- GPR zero reset is a deterministic SPK286 choice; the consulted Intel reset
  tables do not guarantee GPR values. It is not a physical reset signature.
- Access byte 93 is a documented normalized internal representation. Exact
  LOADALL/STOREALL cache images, including accessed bits and unusual cache
  reload cases, still need physical evidence before those features are added.
- FLAGS keeps defined storage fields and reserved reset positions. POPF/IRET,
  real-mode IOPL/NT update restrictions, privilege masks and arithmetic/undefined
  flag behavior are not implemented or certified by these storage tests.
- The fetch response slot is not the six-byte prefetch queue. There is no
  instruction consumption, retirement, execution, memory write or exception
  result yet. Fetch stops at its cached limit; future consumption must trigger
  the appropriate architectural fault when needed.
- No native Ts/Tc/Ti or reset-delay timing, HOLD/HLDA arbitration, LOCK operation,
  interrupt acknowledgement or data/prefetch bus arbitration is implemented.
- MSW, GDTR/IDTR, LDTR/TR and other system state remain unimplemented. Intel's
  reset sources disagree on IDTR limit (FFFF versus 03FF) and reset timing;
  resolve those with errata/physical evidence before implementing them.
- The external SingleStep corpus is not configured or checked out. Physical
  instruction tests executed: 0. Functional/memory/bus/cycle instruction pass
  rates are therefore not applicable. State-vector success is not reported as
  instruction success, and no corpus cases were excluded to hide RTL failures.

## Branch and commits

| Commit | Verified milestone |
| --- | --- |
| `7a31a08` | Add 80286 architectural register storage and directed tests |
| `98c07de` | Add 80286 segment caches and real-mode address formation |
| `380b47f` | Integrate architectural state with restartable 24-bit code fetch |
| `f8676c1` | Verify datapath initialization and fetch from state vectors |
| This handoff commit | Record clean final validation and continuation boundary |

Phase 0 history and main are unchanged. The Phase 1 branch is intended to be
pushed to `origin` after this handoff commit; no merge or history rewrite is
authorized or performed. The session's final Git check records push completion.

## Next recommended implementation step

Continue RM1 with the six-byte prefetch queue and its consumer interface on top
of the verified fetch service. First add directed tests for byte order, refill
capacity, consumer stalls, flush while data is buffered/in flight and segment
end handling. Keep instruction-start IP distinct from prefetched bytes and
the fetch cursor so later faults can report the correct saved IP.

Then build the smallest decoder and project-owned DSL/compiler/microsequencer
path needed for `MOV r16, imm16` (B8-BF) and explicit instruction completion.
That provides the first real instruction execution through the existing GPR
commit port without requiring ModR/M memory operations or a complete ALU.
Extend the state adapter to execute and compare those instructions, including
the corpus's terminating HALT/IP convention, before expanding to broader MOV
and effective-address forms. Do not mark MOV or RM1 complete on fetch tests.
