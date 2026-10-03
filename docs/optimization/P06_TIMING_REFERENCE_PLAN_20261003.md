# P06-M1: timing reference and first 6 MHz profile

Status: measurement/specification milestone, 2026-10-03. Historical profiles
and their precision remain **unvalidated**. This plan introduces no CPU, OSD,
clock or T-state implementation. It complements [P06](P06_CPU_SPEED_PROFILES.md)
and the [P12 reference contract](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md).
The native 86Box reference portion is complete; see the
[P06-M1 native results](P06_NATIVE_REFERENCE_RESULTS_20261003.md). Physical
6/12 MHz measurements remain `NOT_MEASURED`, so the historical/physical M1
scope is still open.

## 1. Current boundary and intended product

PCAT currently uses one functional SPK286 implementation, with CPU, bridge and
SDRAM service on the common physical 50 MHz clock. `execute_enable=1` selects
native execution. The machine requests internal policy 0; SPK286 policies 0 and
2 currently share the dependency-driven schedule. There is no historical
speed selector or whole-CPU virtual-tick protocol in this interface.

Retain accelerated execution without added historical delays, and later offer
optional historical T-states with the 86Box Intel-family speed entries:
6, 8, 10, 12.5, 16, 20, 25 MHz, plus MAX. MAX denotes the fastest accepted
implementation under its actual clock/resource constraints. Historical policy
must preserve work, architectural results, READY, ordering and device clocks.
The meaning of a selected speed with historical timing disabled must be fixed
before OSD/RTL; it cannot be inferred from current CheckIT MHz estimates.

The physical collaborator's 12 MHz CPU setting is a separate reference. Native
86Box's entry labelled `12` sets 12,500,000 Hz. Keep both numbers in result
metadata; do not silently treat them as measurements at the same frequency.

## 2. Reference evidence to freeze

| Evidence | Identified source/boundary | Required result before historical RTL |
| --- | --- | --- |
| Current implementation | `config.tcl`, `PCAT-286.sv`, `rtl/spk286_integration/spk286_machine_cpu.sv`, `vendor/spk286/rtl/spk286{,_biu,_timing_policy,_timing_trace}.sv` | Source hashes, physical clocks, public acceptance/completion events; identify advance/capture interface still to be designed |
| CPU instruction timing | Intel 80286 instruction timing tables; primary reference catalogue in `vendor/spk286/docs/PROTECTED_MODE_GLOBAL_REVIEW_20260929.md` | Exact manual revision/pages, units and operand/branch/prefetch conditions for R0/B0/M0; extraction remains pending |
| CPU/bus and board timing | Qualified Intel hardware timing documentation and the selected board's IBM/other manufacturer reference | CPU-clock definition, EU/BIU overlap, READY/waits, ISA/device cadence and reference buffering; identification/extraction pending |
| Native 86Box | Separate `86box_dev` checkout: `src/cpu/cpu_table.c`, `src/cpu/cpu.c`, instruction handlers and prefetch implementation | Native raw runs at 6 and 12.5 MHz accepted; frozen executable/CPU/config/result evidence in [the native results](P06_NATIVE_REFERENCE_RESULTS_20261003.md). Historical timing calibration remains open |
| Physical 286 | Collaborator's same PC at nominal 6 and 12 MHz | CPU/stepping if available, board/BIOS, speed-switch method, RAM/waits/cache and raw DOS output; measurements pending |
| SPK286 / MiSTer | Current accelerated CPU and PCAT integration | Functional signatures and identified measurement environment; useful contrast, not a historical cycle oracle |

In local native 86Box, without cache overrides, `cpu_waitstates=0` means automatic
memory-table selection.
It does not remove instruction `CLOCK_CYCLES` or prefetch timing. The Intel
table assigns memory read/write costs of 2 cycles at 6 MHz and 3 cycles at the
`12`/12.5 MHz entry. These are emulator settings, not measured physical READY
waveforms. Record overrides and cache policy rather than describing the default
as a CPU with all T-states removed.

## 3. First DOS measurement: T286REF.COM

The canonical deliverable is
`build/p06-timing-reference-20261003/T286REF.COM`, with reproducible sources and
build instructions in `SW/CPUTIME`. It has passed the required initial runs with
**ORIGINAL native 286 in 86Box**, at 6 MHz and at its `12`/12.5 MHz entry:
both host and guest returned RC0, and the frozen strict parser accepted all
42 samples and six summaries per profile. See [the native results](P06_NATIVE_REFERENCE_RESULTS_20261003.md).
This completes the native-program check before the physical collaborator.
Physical measurements remain `NOT_MEASURED`. Use the same executable and fixture
at physical 6 and 12 MHz; record each setting without assuming an exact 2:1 time ratio.

| Case | Purpose | Required observation |
| --- | --- | --- |
| R0 | Register-only deterministic loop | Known instruction bytes, iteration count, result signature and elapsed raw timer samples |
| B0 | Branch/prefetch deterministic loop | Taken/not-taken pattern, code alignment/placement, signature and raw samples; no claim of pure EU cost |
| M0 | Aligned conventional-RAM loop | Address/alignment, fixed RAM access work, signature, board memory policy and raw samples |

For each case keep seven repetitions, paired gross and measurement-baseline
samples, all raw values, minimum/median and spread. Keep gross values even when
reporting a net estimate; subtraction does not prove that prefetch, I/O overhead
or interrupt interference are identical. Printing, DOS services and result
formatting stay outside the measured region. Preserve and restore caller state.

Read PIT0 through the 8254 read-back interface without reprogramming PIT/PIC or
changing system timer frequency. Record observed mode/status, raw counter
delta and the clock/reload assumptions used for any normalization. A counter
latch does **not** reveal the reload divisor: a standard BIOS divisor of 65536
must be labelled an assumption supported by the identified environment, not an
observed value. Mode 2/3 normalization must account for their different counter
sequences and prove an unambiguous measurement window. Reject incompatible
mode/BCD, ambiguous wraps or unqualified timer assumptions for normalized
timing; retain raw output and a reason. Do not convert those samples into MHz
or CPU cycles. Physical oscillator tolerance remains part of the uncertainty.

The initial program is a bounded elapsed-time reference, not a pin capture or a
complete instruction-cycle oracle. Timer qualification, functional correctness
and historical-profile acceptance are separate results. Exact result fields,
accepted timer conditions and any unsupported environment belong in its README.

## 4. M1 acceptance before RTL

M1 requires the frozen manifest, executable/source hashes, case bytes and exact
work/signatures; reproducible native-286 runs at both 86Box entries; explicit
timer qualification and raw repetitions; and a review of each missing reference
item above. The native execution and strict raw CSV acceptance are complete;
the timer remains `NOT_CALIBRATED`, not a calibrated cycle reference. Obtain the
physical 6/12 MHz pair before treating hardware timing as validated. Missing
physical results are `NOT_MEASURED`, never PASS. Historical-profile acceptance
and the physical/reference portion of M1 remain open.

Explain disagreements through discriminating cases and reference assumptions.
Do not change work, time bases or expected signatures to make clocks/benchmarks
agree. A passing DOS program authorizes the next small design proposal; it does
not certify SPK286 as historically timed or all profiles as interchangeable.

## 5. First profile proposal after M1

Start with a **6 MHz** historical candidate and the qualified R0/B0/M0 Real Mode
families. Before RTL, define observable EU/BIU milestones, prefetch overlap,
READY and ownership rules, buffer visibility, and capture/retention of physical
responses between virtual ticks. Expand instruction/event/PM coverage separately;
do not publish the partial pilot as a complete or pin-exact 6 MHz CPU.

Use one shared, small policy/tick generator on the existing 50 MHz domain.
No new PLL/domain, duplicate CPU, larger cache or queue is proposed. Accepted
responses must still be captured/drained at physical clock boundaries. Separate
reference-permitted external waits from implementation `deadline_miss`; CPU
throttling cannot stop PIT/RTC or mask internal deadline failures.

Every physical 50 MHz path still has a **20 ns STA budget**, including under a
6 MHz virtual profile. Virtual ticks alone justify no multicycle exceptions.
Before adoption, report equivalent/placed ALMs, FF, M10K and worst setup/hold
before/after under identical constraints and scope, including MAX behavior.
Resource cost is unmeasured, not zero; the baseline receipt must identify the
latest accepted RBF/source set rather than an older fit. Agree the measured cost
and validation scope before accepting the first implementation.
