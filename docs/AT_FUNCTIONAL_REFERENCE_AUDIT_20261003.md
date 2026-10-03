# AT motherboard behavior compared with manufacturer documentation and 86Box

Date: 2026-10-03. PCAT source baseline: `ed0a67e`. Local 86Box reference:
`D:/GitHub/86Box_dev`, HEAD `fa3343da5b551bc937114c1e3ab3a8e16aed9e79`.
Status: **static review and future acceptance specifications**.

The user requests a search for overlooked AT motherboard behavior, using
official references and 86Box. Seven concrete source discrepancies are
recorded below, including the previously pending PIC special mask issue.
These are compatibility candidates. No new guest reproduction, benchmark,
simulation, synthesis or functional correction was performed in this review.

The review concentrates on DMA, PIC, PIT, RTC, port 61h and their integration.
It does not certify every peripheral or reopen a CPU protected-mode H story.
Source identities and downloaded manual identities are retained in the
[audit manifest](evidence/at-functional-audit-20261003/manifest.json).

## Fast operation and optional historical timing

The user's intended product has a fast mode without imposed historical
T-states, followed by optional T-states and speed profiles. The current
functional bridge already states that it does not model historical Ts/Tc or
the physical 82288/82289. The existing CPU optimization macros do not supply
the future historical timing mode. See [P12](optimization/P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md).
The [existing SPK286 timing draft](../vendor/spk286/SPK286_TIMING_MODEL.md)
already separates real dependencies from optional compatibility delays.

86Box is the project's principal code reference for future profiles. It is
not the sole implementation available: [MAME's 286 code](https://github.com/mamedev/mame/blob/master/src/devices/cpu/i86/i286.cpp)
also has cycle tables, with explicit doubts about some entries. Instruction
cost tables alone do not establish exact bus sequencing. Manufacturer
documentation defines the proposed timing contract, and measurements of a
real 286 can resolve remaining uncertainty when available.
The user has access through collaborators running DOS programs at 6 and 12 MHz,
including both speeds on the same PC, rather than a local instrumented 286.
P12 records a future program-based timing measurement plan and its limits.

Reducing actual bridge or SDRAM stalls, improving coherent buffers and
overlapping independent work are legitimate fast-mode improvements. Functional
register behavior, DMA data, ordering, interrupt semantics and independently
clocked peripheral time must still be correct in that mode. Exact historical
numbers of bus states belong to the later timing contract.

Do not adjust PIT/RTC time, benchmark work, returned results or reference clock
labels to obtain a target score. Retain physical SDRAM refresh and required
completion/coherence fences. Removing a real hardware wait requires a design
that can provide the correct data or retain the operation at that point.

The same-SPK286 immediate-memory result, 7709 / 133.3K, is a comparison under
that service model. It is not a required score for FPGA hardware. The accepted
combined hardware CHECKNUM observation is 6906 / 121.6K. Its agreement with the
corresponding PCAT platform model is useful attribution, not proof of an exact
historical AT. The native 86Box 286 also has a separate CPU timing model.

Subsequent user scope clarification sets ordinary speed profiles through
25 MHz plus Maximum, with limited additional FPGA cost. Current throughput
exceeds the retained 25 MHz control, so further performance hardware is parked.
Maximum will depend on validated physical timings and the resource budget.
Preserve the current common 50 MHz CPU/bridge/memory relationship as the first
choice, seeking timing improvements with neutral or small measured area cost.
Other frequencies require a complete clock-domain and SDRAM evaluation. See the
[current P12 specification](optimization/P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md#performance-target-and-fpga-resource-budget).

In the retained PERF01 evidence, improvements come from memory service and
the corrected PIT-driven AT refresh cadence; no score manipulation is
identified by this review. Buffers, posting and extra overlap are fast-mode
design choices, not evidence that a stock IBM 5170 contained those mechanisms.
The former fixed 32-clock AT refresh stimulus was a real fidelity discrepancy,
already corrected by P19. This conclusion is limited to the inspected sources
and retained evidence; it is not aggregate regression acceptance.

## Findings and proposed order

IDs here identify motherboard work, independently of CPU H stories and PERF01
experiment numbers. All seven remain **unreproduced in a new directed case**.
The order favors small, observable register cases before ownership changes.

| ID | Finding | Status in this review | Proposed sequence |
| --- | --- | --- | --- |
| ATF01 | DMA address and count after terminal transfer | New source contradiction | First bounded register case |
| ATF02 | RTC SET does not clear UIE | New source contradiction | First bounded register case |
| ATF03 | PIC special mask command and IMR semantics | Existing pending finding reconfirmed | Focused production PIC case |
| ATF04 | RTC UIP and update window are absent | New source contradiction | After RTC register case |
| ATF05 | DMA single and block request lifetime | New source contradiction | After terminal-state case |
| ATF06 | DMA controller cascade is bypassed | New source contradiction | After request-mode cases |
| ATF07 | Speaker output also requires GATE2 high | New source contradiction | Independent small audio case |

No measured performance gain or FPGA resource cost is assigned to these items.
A correct result may increase or decrease throughput; that alone cannot decide
whether a functional correction is appropriate.

## ATF01 DMA state after the terminal transfer

**Manufacturer requirement.** Address advances after every transfer; a count
of zero rolls to FFFFh at TC. Autoinitialization instead restores the base
values. See [Intel 8237A, printed page 7](https://www.pcjs.org/documents/datasheets/intel/INTEL_8237A_DMA.pdf).

**PCAT.** `spk286_at_dma.sv:360` enters its terminal branch at count zero.
Without autoinit it sets the mask, leaving both current registers unchanged.
Increment/decrement and count subtraction exist only in the nonterminal branch
at lines 372-380. Register reads expose those retained values at lines 257-263.

**86Box.** `src/dma.c:1751`, in `dma_channel_write`, decrements the count after
advancing the address. `dma_channel_advance:1559` also retains the underflow
unless autoinit restores the base. Check decrementing word writes separately
because of ATREF01 below.

**Proposed case.** Count=0, one beat, then read back count and address in both
directions. Add byte/word channels, page wrap, TC acknowledgment and autoinit
controls. The existing DMA register bench checks transfer addresses and TC
status but does not read these two registers after TC; it is not acceptance
for this property.

## ATF02 RTC SET clears the update interrupt enable

**Manufacturer requirement.** A rising SET bit clears UIE. See
[Motorola MC146818A, printed page 15](https://www.ardent-tool.com/datasheets/Motorola_MC146818A_alt.pdf).

**PCAT.** `spk286_at_rtc_cmos.sv:701` stores the requested B byte without this
side effect. Clock update is inhibited by SET at line 518, but UIE remains set.

**86Box.** `src/nvr_at.c:612-620`, `nvr_reg_write`, explicitly clears UIE on
SET's 0-to-1 transition and clears its UIP status.

**Proposed case.** Write B=12h, then B=92h and read B; require 82h. Verify the
existing periodic flag/enable path and resume updates by clearing SET. This
small case should precede the larger update-window work.

## ATF03 PIC special mask command and IMR semantics

**Manufacturer requirement.** ESMM authorizes that OCW3 to change SMM; OCW1
still writes IMR. In SMM, masked ISR levels cease blocking other requests.
See [Intel 8259A, printed pages 13 and 16](https://www.pcjs.org/documents/datasheets/intel/INTEL_8259A_PIC.pdf).

**PCAT.** `KF8259_Control_Logic.sv:449-462` stores SMM even with ESMM=0.
OCW1 at lines 372-388 uses stored ESMM to select ordinary versus a separate
special mask. This contradicts the command permission and persistent IMR
behavior already described in the [pending PIC record](HARDWARE_FOLLOWUPS_20260930.md#1-pic-special-mask-mode-pending-functional-review).

**86Box.** `src/pic.c:530` writes IMR; line 567 gates SMM changes on OCW3
bit 6. Priority resolution at line 338 uses the current IMR and SMM together.

**Proposed case.** Enter with 68h; change/read IMR; issue 0Ah/0Bh without
losing SMM; leave with 48h. Include masked ISR priority, EOI and cascade.
Run the production KF8259: `test_a3_interrupts.sh` uses a portable behavioral
PIC for Icarus execution, with a production compile check and production
Verilator execution. Agreement with that substitute is not an independent
execution of production logic in both simulators.

This remains motherboard work. The retained OS/2 observation did not capture
an ESMM command and does not implicate ATF03 in the already resolved EGA fault.

## ATF04 RTC UIP and the clock update window

**Manufacturer requirement.** UIP announces the update. At the AT's 32.768 kHz
time base, the warning precedes the 1984 us update by 244 us; UF marks its end.
See [Motorola MC146818A, printed pages 14-15](https://www.ardent-tool.com/datasheets/Motorola_MC146818A_alt.pdf).

**PCAT.** `spk286_at_rtc_cmos.sv:603` hardwires UIP=0. At lines 750-755,
calendar update, UF and alarm matching happen on one `second_tick`, with no
busy interval. An atomic calendar update does not supply the advertised UIP
event to software that waits for it.

**86Box.** `src/nvr_at.c:548`, `timer_tick`, sets UIP and schedules 244 us.
`timer_update:459` schedules another 1984 us before UF/UIP completion;
`nvr_read:728-729` exposes the live UIP bit. This is an explicit timed model.

**Proposed case.** Poll A across one second and observe 0-to-1-to-0; correlate
UF and IRQ8 with update completion. Include a rollover, SET during update,
C-read acknowledgment and periodic interrupts during SET. Define deterministic
read behavior during the busy window rather than accidentally returning a
mixture of calendar values. No CPU T-state option is required to make UIP
observable; RTC time is its own device contract.

## ATF05 DMA request lifetime in single and block modes

**Manufacturer requirement.** Single mode releases and reacquires service
when DREQ stays active. Block mode continues after its initial DACK until
TC/EOP; demand mode suspends on inactive DREQ. See
[Intel 8237A, printed page 5](https://www.pcjs.org/documents/datasheets/intel/INTEL_8237A_DMA.pdf).

**PCAT.** `spk286_at_dma.sv:383` sets `single_block_q`, which lines 241-243
clear only after external DREQ goes low. A held request therefore cannot get a
second single transfer. Block mode has no latched service request: after each
completion, line 138 selects from current DREQ/software requests again.
`spk286_at_arbiter.sv` also completes ownership one physical beat at a time.

**86Box.** `src/dma.c:135`, `dma_block_transfer`, loops over software-requested
work. Device callbacks service DMA without a pin-level HRQ/HLDA/DACK model.
This reference cannot establish exact CPU-bus release intervals.

**Proposed case.** Held-DREQ single transfers, block DREQ withdrawn after
first DACK, and demand pause/resume; compare transfer/state traces. Preserve
LOCK protection and accepted-store draining. Fast mode needs correct request
lifetime; the precise historical bus-state spacing belongs to P12.

## ATF06 DMA cascade and hierarchical selection

**Manufacturer requirement.** The AT routes controller 1 through controller 2
channel 4. See [IBM 5170 Technical Reference March 1986, printed pages 1-9 to 1-10](https://www.minuszerodegrees.net/manuals/IBM/IBM_5170_Technical_Reference_MAR86.pdf)
and [Intel 8237A cascade operation, printed page 6](https://www.pcjs.org/documents/datasheets/intel/INTEL_8237A_DMA.pdf).

**PCAT.** `spk286_at_dma.sv:138-157` selects the lowest requested channel
globally, excluding 4. Disabling controller 2 masks only channels 4-7. Low
channels do not depend on channel 4 mask/mode or controller 2 enable. The
`cascade_request` output is connected at `spk286_at_machine.sv:1093` but has no
use that gates low-controller bus ownership. The command handler at line 344
also retains only the controller-disable bit, without rotating-priority state.

**86Box.** `src/dma.c:1600-1611` and `1693-1704` check the selected channel's
own controller and mask. They do not establish a full master-channel cascade
gate. Use 86Box for register/data comparison, not as proof of this topology.

**Proposed case.** Mask or disable the master cascade and verify low-channel
service suppression; restore it without changing address/count. Add simultaneous
low/high requests and programmed rotation. This requires an ownership design,
not merely suppressing channel 4's own data beat. Existing address tests
exercise low channels after master clear without programming cascade, so their
setup would need correction while preserving their data assertions.

## ATF07 Speaker data with GATE2 low

**Manufacturer requirement.** The speaker driver ANDs OUT2 with port 61h
bit 1; bit 0 separately controls GATE2. See
[IBM 5170, printed page 1-23](https://www.minuszerodegrees.net/manuals/IBM/IBM_5170_Technical_Reference_MAR86.pdf).
Modes 2/3 drive OUT high when GATE is low; see
[Intel 82C54, printed page 11](https://www.pcjs.org/documents/datasheets/intel/INTEL_82C54_TIMER.pdf).

**PCAT.** `spk286_at_machine.sv:1116-1117` requires speaker enable AND GATE2
for both active and level signals. `PCAT-286.sv:1908` suppresses audio while
inactive. This blocks direct bit-1 audio with GATE2 low, even when OUT2 is high.

**86Box.** `src/port_6x.c:68-72` separates these controls.
`src/sound/snd_speaker.c:71-75` retains speaker-data output without the gate.
Its audio filtering is separate from the digital pin behavior.

**Proposed case.** Initialize mode 3, lower GATE2, and toggle bit 1; verify
the digital speaker waveform before audio filtering. Retain ordinary tone
and mode-0/PWM controls. Potential affected software is direct speaker audio;
this is not an identified cause of the CPU benchmark difference.

## ATREF01 A local 86Box word DMA discrepancy

In `src/dma.c:1729-1736`, the ordinary AT word-write decrement branch subtracts
two bytes in its `else`, then subtracts two again unconditionally. With PS/2
and advanced DMA disabled, source inspection therefore predicts a four-byte
stride. PCAT's nonterminal address step is one word, consistent with IBM's
word-address wiring. This possible local-reference defect has not been
reproduced here. Do not copy it into PCAT or use that branch as the sole oracle.
Use an independent address trace for a future decrement case.

## Coverage and questions retained for later work

| Area inspected | Result and remaining boundary |
| --- | --- |
| PIT and refresh | Production wraps KF8253 with 8254 read-back enabled and all six mode branches. P19 uses OUT1, with separate physical SDRAM AUTO REFRESH. Older descriptions of a three-mode PIT are stale. Exact mode edge/BCD cases remain a directed timing inventory. |
| RTC | ATF02/04 are specific discrepancies. Divider-reset phase, the first update after reset release, DSE and non-010 DV settings need separate investigation; do not infer correctness from matching periodic rates alone. |
| PIC | ATF03 is reconfirmed. SFNM, specific/nonspecific EOI and spurious cascade combinations need a manufacturer-led trace inventory. IRQ7 fallback is present; it was not classified as missing. |
| DMA | ATF01/05/06. Byte lanes and word page wiring exist. External EOP, other command bits and complete per-mode ownership are not certified by this register review. |
| Port 61h and NMI | Speaker issue is ATF07. Active machine NMI uses its integrated, mask-qualified source latch at lines 1331-1333; conclusions about an older standalone NMI adapter cannot be applied to this path. |
| 8042 and reset | Functional command/reply and A20/reset paths exist. Reset is deliberately normalized to a CPU request pulse. Complete command coverage, held-reset electrical behavior and input-port board straps require their own AT firmware cases. |
| Memory and bridge | RAM, ROM aliases, EMS mapping, byte/word transactions and ownership fences are present. Historical Ts/Tc/ISA-slot cadence is declared timing debt. The reduced 86Box benchmark adapter omits parts of motherboard/device arbitration. |
| EGA and remaining peripherals | The accepted OS/2 EGA correction remains accepted. Disk controllers, serial/parallel ports and sound-card timing were not comprehensively audited here; VGA+ is outside this task. |

The completed [active-profile regression](optimization/P18_P19_FULL_REGRESSION_20261002.md)
retains MRBIOS restart and verification/input gaps. None of these source
findings is established as their cause. No new full regression is started.

## Recommended next work

Retain the accepted performance improvements. First reproduce ATF01 and ATF02
through guest-visible register cases, then implement and commit each confirmed
correction separately. ATF03 and the independent speaker case can follow with
production logic and exact digital expectations. DMA ownership and timed RTC
updates require a written transition contract before integration.

Benchmark only a change with a demonstrated hardware mechanism, unchanged
work and correct independent time bases. Agreement with 86Box is evidence
when its relevant mechanism is modeled; an ideal service assumption or a
shared omission cannot prescribe MiSTer behavior. The read-service/cache
experiments remain retained proposals, subordinate to this functional review.
