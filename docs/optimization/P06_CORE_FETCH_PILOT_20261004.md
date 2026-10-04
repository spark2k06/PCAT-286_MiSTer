# P06 M4 — retained CODE/fetch timing in the private full CPU

Status: **directed acceptance complete, 2026-10-04**. Production CPU/QIP,
MAX RBF and frozen M3 files are unchanged. This qualifies the private 6 MHz
register/CODE path, not a complete historical CPU or profile.

## Connection and reference

`build_p06_fetch_cpu.py` extends the pinned M3 selection. Normalized physical
READY captures into the **existing fetch response slot** on any fabric edge.
Logical issue uses the shared 6 MHz boundary; publication waits for Ts/Tc and
board-ready eligibility. Exact-Tc capture has a same-edge metadata/data bypass.
Earlier data survives poisoned bus values. Late capture extends Tc and records
an implementation deadline miss separately from external waits.

No extra packet buffer, CPU, PLL or queue capacity is added. Full CPU fixtures
use zero extra CODE waits; component fixtures cover 0/1/2. Data/INTA/HOLD/LOCK
have explicit scope guards; their historical sequencing is still unqualified.

The [Intel-derived contract](P06_TIMING_CONTRACT_20261003.md) specifies two
processor clocks for Ts/Tc, word fetch except odd/limit bytes, and six prefetch
bytes including reservations. Native 86Box's simplified aggregate model has a
16-byte ceiling. Initial development uses 86Box with these differences declared;
later physical evidence reviews calibration without blocking development now.

## Capacity and tests

Admission forecasts the resulting queue count after publication/consumption
before reserving another word. A fill from four to six cannot reserve a fourth
word. This historical rule is private; production MAX stays unchanged. An odd
first fetch contributes one byte followed by words, stopping at five bytes if
none are consumed. Warm fixtures fill the actual queue before EU dispatch
through existing controller-error suppression; no queue state is forced.

| Experiment | Accepted result |
| --- | --- |
| Real fetch + six-byte queue | 297 scenarios, identical Icarus/Verilator edge traces |
| READY matrix | Waits 0/1/2 × aligned/odd × offsets 0..45, exact Tc, late capture |
| Lifecycle/capacity | Full/resume, backpressure, four redirect phases, reset after retention, segment-limit byte, real-mode wrap |
| Captures outside CPU boundaries | 2,206 in the component run |
| Full CPU warm register/immediate | 208 cases, exact 2/3-clock minima and independent architectural oracle |
| Full CPU cold fetch | 208 correct results; 16 extensions waiting for required bytes |
| Deliberately late physical dependency | 13 cases |
| Pause/error/redirect/reset/NMI | 65 cases |
| Unsupported opcode/form/protected mode | Seven explicit stops |
| Injected HOLD/LOCK/data/INTA demands | 52 stops; no HLDA/data/ACK traffic or commit |
| Dependent ADD stream | Four instructions; two-clock EU duration, one extra dispatch clock |
| Original versus private MAX | 208 per-edge traces identical, both simulators |
| Existing MAX units | Register 78, immediate 184, policy 63 checks, fetch 32 checks plus lifecycle/limits |
| MAX fetch sequential proof | 170 equivalence cells proven by Yosys |
| Negative timing control | Early raw publication fails the independent oracle |

Cold dependency extensions are not added to instruction-table budgets or
labelled board waits. Warm and cold cases retain the same architectural oracle;
only warm cases certify exact EU minima with all required bytes available. NMI
preserves completed IP and stops before untimed entry; event timing stays open.

## Resources

| Isolated fetch, generic Yosys mapping | Register bits | Cells |
| --- | ---: | ---: |
| Original | 98 | 508 |
| Private MAX | 98 | 508 |
| Private timed CODE | 102 | 603 |
| Timed delta | +4 | +95 |

The two-bit logical state maps to four FFs in this flow. Response storage is
reused. MAX gate types differ slightly after alias renaming, but aggregate
storage/cells match and sequential equivalence is proven. These are **not ALMs,
whole-CPU overhead, fit or STA**. Admission/scope logic and future data/event/IU
policy require separate accounting and complete Quartus measurement before
adoption. M3's isolated shared clock/register control stays 22 bits / 284 cells;
it is not a complete FPGA delta either. No fit or total regression ran for M4.

## Evidence and next work

[Frozen evidence](../evidence/p06-core-fetch-20261004/README.md) contains logs,
vectors, private sources, generic netlists and paired edge traces. Its auditor
reconstructs CPU/benches and verifies source/artifact hashes, outcomes and
production guards. The unchanged M3 audit also passes (120 artifacts).

Two test-adapter issues were corrected without changing the RTL oracle: settle
inputs before observing READY, and gate queue fill during consumer refusal.
Next are the P06-IU01 dispatch/lookahead study, data/odd-word/I/O/INTA and ownership
timing, wrapper/instruction/event/PM coverage, speed profiles and machine
integration. Native 86Box comparison, physical calibration, complete FPGA cost
and P21 setup/hold retain their declared separate acceptance scopes.
