# P06 provisional timing components

CPU-only timing components staged in PCAT for directed development. They are
not selected by the production QIP and introduce no OSD/config option. Keep
them separate from the existing functional engine until the stated milestone
contracts and instruction/board coverage are validated. This directory is
not a second CPU implementation.

`p06_clock.sv` emits 6 MHz processor boundaries and 12 MHz phase events from
the common 50 MHz clock. Its static MAX form has no state or historical delay.
Sample enables on the rising fabric edge; never use them as generated clocks.

`p06_bus_cycle.sv` is a one-beat packet reference for Ts/Tc, physical capture,
retained logical replies and cancel/drain. It carries opaque CPU-owned class
and LOCK metadata but does not implement odd-word/HOLD arbitration or a
posted-write buffer. Its packet interface is not the CPU's level-held bus.
Reuse existing retention when integrating; do not stack the reference slots
on top of existing BIU/fetch/bridge slots. MAX is a static wire bypass whose
endpoint must provide the original command/response ownership contract.

`p06_instruction_duration.sv` accepts already-decoded, explicitly qualified
forms. It starts its minimum duration in parallel with functional work and
permits retirement only at a CPU boundary with functional completion and
dependencies available. It owns no architectural result storage or execution
semantics. Actual read-wait events extend the table budget; write/fetch waits
remain dependencies. The bounded fixture reports malformed waits and budget
overflow; elapsed time saturates. This is not enough to certify complete
instruction timing, bus issue phases, branch refill or interrupt boundaries.
The static MAX form bypasses duration and metadata without state.

See [the contract](../../docs/optimization/P06_TIMING_CONTRACT_20261003.md)
and [implementation progress](../../docs/optimization/P06_PILOT_PROGRESS_20261003.md).
Run the relevant stage from WSL/Linux with a fresh output directory:

```sh
python3 scripts/run_p06_pilot.py --stage clock --output build/p06-clock-repeat
python3 scripts/run_p06_pilot.py --stage bus --output build/p06-bus-repeat
python3 scripts/run_p06_pilot.py --stage duration --output build/p06-duration-repeat
python3 scripts/run_p06_pilot.py --stage fixture --output build/p06-coupled-repeat
```

The runner checks lint, Icarus/Verilator, a failing mutation and generic
Yosys synthesis. Generic cells/register bits are not Quartus ALMs or STA.
The coupled stage mocks a functional caller, issues data at instruction start,
and uses an abstract backend. That issue milestone is an unvalidated fixture
assumption, not an Intel-qualified phase. It does not execute SPK286 or DOS.
Its generic synthesis measures the named duration component, not a full CPU.

## Private full-CPU register connection (M3)

`p06_register_connection.svh` is inserted by the hash-guarded private builder
into one selected copy of the existing CPU sources under an ignored build
directory. It gates actual retained register execution/commit and publishes
the saved instruction IP while active; it does not add another result buffer.
The production QIP does not include it. Use:

```sh
python3 scripts/run_p06_timed_register.py --output build/p06-register-repeat
```

The full CPU register subset passes 2/3-clock minima at virtual 6 MHz, late
dependencies, lifecycle and scope stops in both simulators. MAX traces remain
identical. The exact connection's cost fixture maps to 22 register bits /
284 generic cells, or zero in MAX, not an FPGA resource/timing estimate.
The repeated ADD stream exposes an additional dispatch clock in P06-IU01.
See the [M3 report](../../docs/optimization/P06_CORE_REGISTER_PILOT_20261004.md)
for evidence and remaining historical BIU/IU/event/physical acceptance.
