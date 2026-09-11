# PCAT-286 AT Bus and CPU–Chipset Contract

**Document:** `docs/AT_BUS_CPU_CHIPSET_SPEC.md`
**Version:** 1.0 draft engineering specification
**Status:** A0–A4 implementation slice delivered; A5+ and hardware validation pending
**Scope:** CPU wrapper, 80286-compatible motherboard bus, arbitration and minimum PC/AT chipset boundary
**Consumer:** `PCAT-286_MiSTer`
**CPU provider:** `SPK286`

This document defines the contract between the standalone SPK286 CPU and a
progressively developed PC/AT machine. It is deliberately separate from the
SPK286 architectural specification and from individual peripheral
implementations. The purpose is to prevent an XT-derived bridge, a CPU bus
owner and an AT chipset from silently acquiring overlapping responsibilities.

The current implementation delivery covers the A0–A4 normalized CPU-facing
contract, the standalone `spk286_at_bus_bridge`, the AT memory-range decoder,
ownership arbiter, dual-PIC/NMI interrupt boundaries and the functional
DMA/refresh/PIT boundaries. The active MiSTer machine remains the documented
`XT_COMPAT` profile; keyboard, RTC, storage/video, AT BIOS and hardware
integration remain later milestones and are not implied by this A4 slice.

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT** and **MAY** are
normative. A statement that is not yet validated on hardware is marked as a
design requirement or a functional target, not as a historical timing claim.

## 1. Goals and non-goals

### 1.1 Goals

The implementation shall provide a reusable machine boundary that can:

1. run the SPK286 CPU from its architectural reset vector;
2. expose the complete 24-bit 80286 physical address space to the chipset;
3. preserve 16-bit data and byte-lane semantics, including odd-address words;
4. support memory, I/O, code-fetch and interrupt-acknowledge cycles;
5. arbitrate CPU, DMA, refresh and loader ownership without duplicating effects;
6. deliver cascaded AT PIC interrupts with the correct two-acknowledge sequence;
7. keep READY, LOCK and HOLD/HLDA dependencies observable and testable;
8. allow the same machine to validate real-mode DOS and later protected-mode
   software without changing the CPU–chipset contract;
9. provide deterministic simulation traces suitable for debugging and
   comparison with a physical PC/AT;
10. support a conservative first FPGA implementation before historical timing
    refinement.

### 1.2 Non-goals of this document

This document does not:

- implement or redefine SPK286 instruction semantics;
- implement Protected Mode, descriptor caches or task switching inside the
  motherboard project;
- add paging, 386 control-register semantics or 32-bit bus behaviour;
- claim cycle-exact 80286 electrical timing before physical validation;
- replace the existing EGA, audio or storage implementations without a
  separately reviewed device contract;
- permit firmware changes to conceal an invalid CPU, bus or chipset result.

Protected Mode remains an upstream SPK286 workstream. The machine contract
defined here must remain valid when the CPU begins issuing protected-mode
addresses and protected-mode interrupt frames.

## 2. Relationship to existing specifications

The following documents remain authoritative for their respective boundaries:

- [SPK286 architecture specification](D:/GitHub/SPK286/SPK286_SPEC.md) — CPU
  state, instruction semantics, exceptions and native BIU contract;
- [SPK286 native bus boundary](D:/GitHub/SPK286/docs/BUS_INTERFACE.md) — current
  normalized signals, READY ownership, lanes and logical word completion;
- [PCAT-286 integration specification](../PCAT_286_MISTER_SPEC.md) — machine
  milestones, provenance and MiSTer delivery rules;
- the selected PCXT/KFPC-XT source snapshot — reusable device behaviour and
  existing EGA/storage/audio implementation details.

When this document conflicts with an actual accepted SPK286 interface, the
accepted CPU source and its bus contract win. The adapter shall be changed and
the conflict recorded; the CPU shall not be made XT-specific to simplify the
adapter.

## 2.1 External reference sources and evidence policy

The implementation shall follow the SPK286 source-and-evidence discipline:
functional behaviour is specified first, each ownership boundary is explicit,
and tests are written before a feature is considered delivered. External
projects are references for structure and compatibility investigation; they are
not architectural authority and their source code shall not be copied without
an explicit license review.

The reference hierarchy for this document is:

1. Intel/IBM primary manuals and schematics for the 80286 local bus, 82288/
   82289-style control and arbitration, READY, HOLD/HLDA, LOCK, INTA and the
   PC/AT device map;
2. independently captured physical 80286/PC/AT traces;
3. project-owned tests and deterministic bus/device models;
4. 86Box's IBM AT/286 machine and chipset models for software-visible machine
   behaviour and cross-checks;
5. MiSTer FPGA cores such as ao486 and z486 for synthesis, SDRAM, boot-ROM,
   top-level and verification patterns;
6. the existing PCXT-EGA_MiSTer implementation for reusable EGA, storage,
   audio and MiSTer integration, with its XT assumptions explicitly isolated.

The following sources are specifically admitted for review:

- [Intel 80286 Hardware Reference Manual](https://www.dosdays.co.uk/media/intel/210760-002_80286_Hardware_Reference_Manual_1987.pdf)
  and the [Bitsavers 80286 documentation index](https://www.bitsavers.org/components/intel/80286/).
  These are the primary references for local-bus phases, bus relinquish,
  READY/hold behaviour and the 82288/82289 system boundary.
- [86Box source](https://github.com/86Box/86Box), especially the IBM 286
  machine entry [`src/machine/m_at_286.c`](https://github.com/86Box/86Box/blob/master/src/machine/m_at_286.c),
  common AT setup and the separate [`src/chipset`](https://github.com/86Box/86Box/tree/master/src/chipset)
  and device directories.  86Box is used to compare machine topology, port
  decode, IRQ/DMA wiring and software-visible quirks, not to override Intel
  bus semantics.
- [ao486_MiSTer](https://github.com/MiSTer-devel/ao486_MiSTer), including its
  [`rtl`](https://github.com/MiSTer-devel/ao486_MiSTer/tree/master/rtl),
  [`sim`](https://github.com/MiSTer-devel/ao486_MiSTer/tree/master/sim) and
  top-level [`ao486.sv`](https://github.com/MiSTer-devel/ao486_MiSTer/blob/master/ao486.sv).
  It is a reference for MiSTer top-level separation, memory/boot integration
  and test organization; it is not a 286 architectural reference.
- [z486_MiSTer](https://github.com/nand2mario/z486_MiSTer), especially its
  [`src`](https://github.com/nand2mario/z486_MiSTer/tree/main/src),
  [`tests`](https://github.com/nand2mario/z486_MiSTer/tree/main/tests),
  [`verilator`](https://github.com/nand2mario/z486_MiSTer/tree/main/verilator)
  and MiSTer top-level.  It is a reference for a newer CPU/machine split,
  repeatable build profiles and software-driven verification, not for 286
  bus or protection semantics.
- [PCXT-EGA_MiSTer](https://github.com/MiSTer-devel/PCXT-EGA_MiSTer), which is
  the current local machine baseline. Its existing bus-arbiter and DMA timing
  assumptions must be audited before reuse; an XT-compatible result is not
  automatically an AT-compatible result.

At implementation start, record the exact commit, file hash, license status
and interpretation used for every external source. Do not use a moving `main`
branch as an unrecorded dependency.

## 2.2 SPK286-style development method

The work shall use the same development shape as SPK286:

1. write the architectural/transaction contract before RTL;
2. assign every state and side effect to one owner;
3. build small pure units with directed tests before integrating them;
4. make accepted/completed/canceled transactions explicit;
5. preserve real dependencies in every performance mode;
6. keep functional semantics separate from historical timing;
7. validate with the smallest focused test first, then lint, affected
   integration tests, dual-simulator smoke and synthesis sanity;
8. record unresolved hardware evidence as an open decision instead of encoding
   a guessed constant;
9. never weaken an expected result or add a test-specific path to make a ROM,
   BIOS or game progress;
10. deliver each phase with reproducible sources, commands, traces and hashes.

Each new bus or device feature should therefore have four artefacts:

- a section in this document or a linked decision record;
- an RTL owner with a typed request/completion boundary;
- a focused unit or subsystem test with side-effect counters;
- an integration trace proving that the machine-level owner is correct.

## 3. Target machine profile

The target is a 16-bit 80286 PC/AT-class machine with:

- a 24-bit physical address bus, supporting up to 16 MiB without paging;
- a 16-bit data path with A0/BHE byte selection;
- an AT-style cascaded interrupt controller;
- AT-style DMA and refresh ownership;
- PIT, keyboard controller, RTC/CMOS, video and mass-storage devices;
- a BIOS and option-ROM map compatible with the selected machine profile;
- a MiSTer implementation whose external SDRAM/HPS access is treated as a
  motherboard bus participant, not as a privileged second memory system.

The initial FPGA implementation MAY reuse device RTL from the XT-derived
baseline. Reuse is acceptable only when the device's address, interrupt, DMA,
bus-width and timing assumptions are recorded. Existing XT peripherals are not
evidence that the resulting machine is AT-compatible.

The CPU MUST retain its full 24-bit address in internal state and traces. Any
XT-compatible address projection is a machine-profile adapter policy and MUST
NOT be implemented by changing SPK286 segment arithmetic or its reset state.

The first genuine AT compatibility target shall be named explicitly (the
recommended baseline is the IBM AT 286 profile), rather than silently mixing
the IBM AT and IBM XT Model 286 behaviours. 86Box documents those as distinct
80286 machine profiles, with different onboard-memory assumptions and BIOS
expectations. An `XT_COMPAT` profile may continue to exist for bring-up, but it
must not be reported as the final AT machine.

## 4. Ownership model

Every request and side effect has exactly one owner.

| Area | Sole owner | Responsibility |
| --- | --- | --- |
| Instruction execution | SPK286 | Registers, FLAGS, segmentation, exceptions, prefetch and retirement |
| CPU physical request | SPK286 BIU | Address, cycle class, direction, lanes, payload, READY completion |
| CPU wrapper | Machine adapter | Safe tie-offs, clock/reset boundary, debug exposure and source provenance |
| CPU-to-chipset translation | AT bus bridge | Snapshot, lane conversion, command strobes and completion |
| Bus arbitration | AT arbiter | CPU/DMA/refresh/loader ownership, HOLD/HLDA and LOCK exclusion |
| Memory/device decode | Chipset | Address map, read data, write side effects and unmapped policy |
| Interrupt priority/vector | PIC | IRQ latching, cascade, masking, priority and INTA vector |
| DMA sequencing | DMA controller | DREQ/DACK, address/count, memory and I/O beat order |
| Refresh | Refresh controller/DMA | Refresh requests and retention timing |
| ROM/HPS loading | Startup loader | Reset-held image loading before runtime ownership |

The bridge MUST NOT inspect instruction opcodes, expected signatures or CPU
register values. The chipset MUST NOT infer a completed transfer from an idle
READY level. The CPU MUST NOT directly perform peripheral side effects.

There MUST be one physical bus owner at a time. A device-side queue is allowed
only if its acceptance, ordering, reset and side-effect policy are explicit.

## 5. Clock, reset and clock-domain contract

### 5.1 Preferred clocking

The first implementation SHOULD use one synchronous clock for SPK286, the
bridge, arbitration and the functional chipset model. Legacy bus phases may be
represented by clock-enable states rather than by creating unrelated clocks.

If separate clocks are required, the crossing MUST use one of:

- a bundled request/response handshake that retains address, direction, lanes,
  payload and cycle class together; or
- an asynchronous FIFO with complete transaction records and explicit reset
  sequencing.

Synchronizing address, data and control bits independently is forbidden.

### 5.2 Reset sequence

Reset shall proceed in this order:

1. hold the CPU and runtime bus bridge inactive;
2. reset arbitration, device state, pending responses and CDC storage;
3. initialize memory/ROM images and option-ROM contents;
4. release the startup loader only after all images report ready;
5. release the CPU reset and allow the first architectural fetch;
6. release runtime DMA, refresh and HPS access according to the arbiter policy.

The CPU's first physical fetch MUST remain `FFFFF0` with the SPK286 reset
segment-cache semantics. A system ROM alias belongs in the chipset decode, not
in a CPU reset-vector workaround.

Reset MAY discard unaccepted requests. It MUST NOT replay an already accepted
device write or read side effect. Resetting the CPU and resetting the bridge
must clear incompatible retained responses together.

### 5.3 Pause and execution enable

`execute_enable` is an architectural CPU control input, not a general-purpose
clock gate. The machine MUST NOT use it as a bus divider or assume that it
freezes prefetch, accepted bus cycles or device state. A user-visible pause
must be implemented at a defined machine boundary and tested separately.

## 6. CPU-facing normalized contract

The bridge shall consume the current SPK286 top-level interface. The following
signals are normative at the CPU side:

| Signal | Direction | Contract |
| --- | --- | --- |
| `clk` | input | Synchronous CPU/bridge clock |
| `reset` | input | Active-high synchronous CPU reset |
| `ready` | input | Completes the currently owned CPU physical request |
| `data_in[15:0]` | input | Read data sampled on the completion edge |
| `execute_enable` | input | Allows architectural execution; not a clock enable |
| `intr` | input | Synchronized level-sensitive maskable interrupt request |
| `nmi` | input | Synchronized NMI event input; edge qualification belongs to CPU semantics |
| `hold_request` | input | Requests bus ownership at a legal CPU boundary |
| `address[23:0]` | output | Physical address held for the owned request |
| `data_out[15:0]` | output | Write payload positioned on active lanes |
| `data_oe` | output | Indicates CPU write drive; zero for reads/fetches |
| `bus_valid` | output | A CPU physical request is active |
| `bus_write` | output | Active request is a write |
| `bus_bhe_n` | output | Active-low upper-byte enable |
| `bus_status[3:0]` | output | Normalized cycle class |
| `bus_lock` | output | CPU atomic ownership interval |
| `hlda` | output | CPU has granted external bus ownership |
| `halted` | output | Architectural HLT state; not a failed request |
| `shutdown` | output | CPU shutdown indication; must remain observable |

Debug outputs MAY be captured by the overlay and trace recorder. Debug inputs
that can alter architectural state MUST be tied to documented safe values in a
production wrapper.

The normalized interface is intentionally not a direct claim about the
electrical 80286 pin cycle. The bridge is responsible for producing the
machine-side phases and strobes.

## 7. Request, retention and completion rules

### 7.1 Ownership and READY

For every CPU request:

1. the bridge detects a new request only when `bus_valid` is asserted while no
   previous CPU request is owned;
2. it snapshots address, status, direction, lanes and write payload exactly
   once;
3. it holds the snapshot unchanged through all downstream waits;
4. it performs each required byte beat exactly once;
5. it asserts CPU `ready` only after the complete logical physical request is
   complete and read data is valid;
6. it releases ownership only after the CPU has observed that completion.

`ready=1` while `bus_valid=0` has no effect. Consecutive CPU requests MAY keep
`bus_valid` high and MAY repeat the same address/data; a falling edge is not a
  request delimiter.

The bridge MUST NOT acknowledge a request merely because a device's READY line
is idle-high. Device selection, command phase and completion must already be
established.

### 7.2 Normalized cycle classes

The current SPK286 status values map as follows:

| `bus_status` | Class | Machine action |
| ---: | --- | --- |
| `0x0` | Interrupt acknowledge | Run one PIC acknowledge beat; two CPU requests form one interrupt sequence |
| `0x5` | Memory read | Decode memory/device read and return lane-positioned data |
| `0x6` | Memory write | Commit selected byte lanes exactly once |
| `0x9` | I/O read | Decode the 16-bit I/O address and return data |
| `0xA` | I/O write | Commit the selected I/O side effect exactly once |
| `0xD` | Code fetch | Read instruction bytes through the memory/ROM map |
| `0xF` | Passive/no request | No transaction; do not manufacture a cycle |
| `0x4` | Halt/shutdown indication | Diagnostic indication only when `bus_valid=0`; not a READY-qualified transfer |

The bridge MUST decode the complete four-bit status. Truncating `0xD` to three
bits would incorrectly turn a code fetch into a memory read.

### 7.3 Byte lanes and words

For each physical transfer:

| Address A0 | `bus_bhe_n` | Active lane | Meaning |
| ---: | ---: | --- | --- |
| 0 | 1 | `D7:0` | Even byte |
| 1 | 0 | `D15:8` | Odd byte |
| 0 | 0 | `D7:0` and `D15:8` | Aligned word |
| 1 | 1 | none | Protocol error; no fabricated access |

An aligned word may be serviced by one native 16-bit memory beat only if the
chipset and memory path explicitly support both lanes. An 8-bit device path
MUST serialize it as address `N` low byte followed by `N+1` high byte. An odd
word remains two ordered physical transfers owned by the same logical request;
HOLD, DMA and refresh MUST NOT interrupt between them.

The bridge shall not split a single-lane SPK286 physical transfer again. The
inactive data lane is ignored. Device write side effects occur only for active
lanes.

### 7.4 I/O address and word boundary

I/O addresses are 16-bit architectural values. For an odd word at port `FFFF`,
the second physical beat uses the 17-bit incremented path (`010000`) at the CPU
boundary, preserving the SPK286 contract. The chipset's port decode MAY alias
or ignore the high carry only if that policy is explicit and tested.

## 8. AT bus bridge

### 8.1 Functional bridge state machine

The first bridge shall use an explicit transaction FSM. A permitted abstract
state set is:

```text
IDLE
  -> SNAPSHOT_CPU
  -> DECODE_CYCLE
  -> ADDRESS_PHASE
  -> COMMAND_PHASE
  -> WAIT_READY (repeat while downstream not ready)
  -> COMPLETE_BEAT
  -> NEXT_BEAT (for a serialized word)
  -> COMPLETE_CPU
  -> IDLE
```

The implementation may use different state names, but it MUST expose equivalent
observable boundaries. `WAIT_READY` holds address, direction, lane, data and
cycle class. A command strobe MUST not repeat merely because READY is delayed.

### 8.2 Machine-side signals

The bridge-to-chipset interface shall contain, directly or through an
equivalent typed record:

- cycle class: memory read/write, I/O read/write, code fetch, INTA;
- physical address and active byte lanes;
- write data and data-drive enable;
- request valid/accepted/completed;
- read data and read-data-valid;
- READY/wait control;
- `LOCK` ownership;
- bus owner identity (CPU, DMA, refresh or loader);
- reset and error status.

The address, lanes and cycle class MUST be available to the decoder before a
side-effecting command is accepted. A combinational status-to-strobe shortcut
without ownership and completion state is not sufficient.

### 8.3 AT maximum-mode compatibility

The bridge SHOULD be structured so that a later pin-level implementation can
map it to the 80286 maximum-mode status and 82288/82289-style command and
arbitration devices. The initial MiSTer implementation may use an internal
normalized command record, provided that:

- memory and I/O command polarity is documented;
- address latch and data-transceiver ownership are explicit;
- T1/T2/T3/Tw/T4-like phases can be observed in simulation;
- READY insertion does not change the request identity;
- no historical Ts/Tc timing claim is made until measured.

The functional bridge must not be coupled to an 8088-only multiplexed
20-bit/8-bit bus. An XT compatibility adapter may be retained as a separate
profile, never as the definition of the AT contract.

### 8.4 Native 80286 signal mapping target

The long-term native mapping shall preserve the distinctions present in the
80286 hardware reference even if the first FPGA bridge represents them as a
typed internal record:

| Native function | Contractual meaning | FPGA treatment |
| --- | --- | --- |
| `A23..A0` | Latched physical address | Retain all 24 bits; do not apply an XT mask in SPK286 |
| `D15..D0` | Bidirectional data bus | Drive only during accepted writes; sample only on completed reads |
| `BHE` and `A0` | Upper/lower byte selection | Preserve as lane metadata through every wait |
| `S1/S0`, `M/IO`, `COD/INTA` | CPU cycle/status classification | Decode into the normalized class without lossy truncation |
| `LOCK` | Atomic bus ownership | Feed arbiter exclusion and trace it for the complete interval |
| `HOLD` / `HLDA` | External-master bus exchange | No master drives the bus before HLDA; no CPU resumes before the grant is released |
| `READY` plus any asynchronous/advanced-ready input | Cycle completion and wait insertion | Convert to one accepted completion edge; retain request identity |
| `ALE`, `DEN`, `DT/R`, `MRDC`, `MWTC`, `IORC`, `IOWC`, `INTA` | 82288-style latch, transceiver and command controls | Generate from the bridge FSM or an equivalent command block |
| `PEREQ` / `PEACK` | Optional 80287 handshake | Reserve the boundary; keep absent-coprocessor behaviour deterministic |

The exact pin names and polarity shall be checked against the selected Intel
80286/82288/82289 documentation before a pin-level implementation. A functional
MiSTer bridge may collapse `ALE`/`DEN`/`DT/R` into an internal accepted-beat
record, but it must still expose the same address, direction, lane and
completion ordering to the chipset model. An 82288-style command generator and
an 82289-style arbiter are therefore architectural reference boundaries, not
requirements to instantiate obsolete discrete chips literally.

## 9. Arbitration and bus ownership

### 9.1 Owners

The arbiter recognises at least these owners:

1. CPU;
2. DMA master;
3. refresh controller;
4. startup ROM/HPS loader;
5. optional debug/diagnostic master, disabled in production acceptance tests.

Only one owner may drive address, command and data strobes. Devices may return
read data only to the owner whose request selected them.

### 9.2 CPU HOLD/HLDA

`hold_request` is accepted only at a legal CPU boundary. The arbiter MUST NOT
grant HOLD:

- while a physical beat is waiting for READY;
- between the two halves of a retained odd word;
- while `bus_lock` is active;
- during the protected INTA/first-frame-word lock chain;
- while an accepted response still belongs to the CPU.

After the final owned transfer drains, SPK286 asserts `hlda`. The arbiter then
owns the physical bus and may grant DMA or refresh. New CPU requests remain
blocked until the grant is released.

If the selected CPU wrapper uses an equivalent grant protocol instead of
direct external HOLD pins, the equivalence must be documented and tested at the
same boundaries.

### 9.3 LOCK

`bus_lock` is an exclusion guarantee, not a hint. The arbiter must retain the
CPU owner through every locked transfer and must not start DMA, refresh or
loader traffic inside the interval. The INTA sequence and the first complete
interrupt-frame word retain their documented lock relationship. LOCK must be
released on normal completion, reset and a canceled acknowledgement without
leaving a stale grant.

## 10. Interrupt contract

### 10.1 Cascaded PIC

The target AT machine contains a master and a slave 8259-compatible PIC:

- master command/data ports: `20h/21h`;
- slave command/data ports: `A0h/A1h`;
- slave cascade input on master IRQ2;
- default BIOS vector bases commonly `08h` and `70h`, but software-programmed
  bases are authoritative;
- IRQ priority, masking, edge/level mode, IRR/ISR/IMR and EOI semantics belong
  to the PIC implementation.

The final vector is never hard-coded in the CPU bridge. The PIC supplies it on
the second INTA data beat.

### 10.2 INTR and INTA

The machine shall:

1. synchronize PIC `INT` to the CPU clock domain;
2. present it as the level-sensitive SPK286 `intr` input;
3. preserve the request until the PIC accepts or the source withdraws it;
4. service two independently READY-qualified CPU INTA transactions;
5. return the vector only on the second transaction's `D7:0`;
6. preserve LOCK through the acknowledged sequence and the first complete
   frame push;
7. deliver no fabricated data on the first acknowledge.

The bridge MUST NOT acknowledge the PIC merely because `intr` is high. The
actual INTA command and acceptance edge perform the PIC acknowledge side effect.

### 10.3 NMI

NMI sources include parity/channel-check and other explicitly modelled AT
events. The port `70h` NMI mask policy belongs to the RTC/CMOS/NMI glue. An
initial profile may tie NMI low, but that is a declared limitation, not a
verified AT implementation. NMI event synchronization and edge qualification
remain CPU responsibilities after the input crosses the machine boundary.

## 11. DMA, refresh and memory ownership

### 11.1 DMA target

The target machine models an 8237-compatible pair:

- DMA1 channels 0–3 for 8-bit transfers;
- DMA2 channels 4–7 for 16-bit transfers;
- channel 4 as the cascade link;
- page registers extending the 16-bit channel address;
- request/acknowledge, terminal count, masking, mode and priority state;
- memory-to-I/O and I/O-to-memory direction with one side effect per beat.

The exact MiSTer implementation may reuse an existing DMA block, but its
channel widths, page handling, address increment/decrement and terminal-count
behaviour must be recorded before it is called AT-compatible.

### 11.2 HRQ/HLDA and grant policy

DMA asserts a bus request to the arbiter. The arbiter asks the CPU for HOLD,
waits for `hlda`, then transfers ownership. DMA MUST NOT assume that an idle
CPU bus or READY-high level is an implicit grant.

The DMA owner must preserve address, direction, lane and device selection
through READY waits. A DMA transfer may not overlap CPU LOCK or split a retained
CPU word.

### 11.3 Refresh

Refresh requests are a separate bus owner or an explicitly documented DMA
channel policy. Refresh must not steal a CPU cycle without an accepted grant.
The refresh cadence is a functional retention requirement first; historical
cycle frequency is a later timing-profile task.

### 11.4 Startup loader and HPS access

The loader may own memory while the CPU is held in reset. Once runtime begins,
loader/debug traffic must use the same arbitration contract as any external
master. It must not wait for HLDA from a CPU that is intentionally held in
reset, and it must not replay a write that was already accepted by memory.

## 12. Address and I/O map

The exact map is a machine profile and must be generated from one authoritative
decode table. The following is the target PC/AT baseline; existing EGA/XT
aliases must be listed as explicit compatibility extensions.

### 12.1 Memory map

| Range | Target use | Required policy |
| --- | --- | --- |
| `000000h–09FFFFh` | Conventional RAM | Read/write; parity policy explicit |
| `0A0000h–0BFFFFh` | EGA/VGA video aperture | Device-selected lane and latch semantics |
| `0C0000h–0EFFFFh` | Option ROMs, adapters and reserved holes | Decode table with ROM write protection |
| `0F0000h–0FFFFFh` | System BIOS | Read-only after image load |
| `100000h–FFFFFFh` | Extended RAM and/or mapped devices | Full 24-bit decode; no paging implied |

An address hole must have deterministic read and write behaviour. Word
transactions crossing a device boundary are two independently decoded byte
beats unless the device explicitly supports a native word operation.

### 12.2 Core I/O map

| Ports | Device/function |
| --- | --- |
| `0000h–000Fh` | DMA1 |
| `0020h–0021h` | Master PIC |
| `0040h–0043h` | PIT channels and control |
| `0060h` / `0064h` | 8042 data / command-status |
| `0070h–0071h` | RTC index/data and NMI mask |
| `0080h–008Fh` | DMA page and diagnostic latch policy |
| `00A0h–00A1h` | Slave PIC |
| `00C0h–00DFh` | DMA2 |
| `00F0h–00FFh` | 80287/AT coprocessor interface or defined unmapped policy |
| `01F0h–01F7h` | Primary ATA channel, if enabled |
| `03F0h–03F7h` | Floppy controller |
| `03B0h–03DFh` | Video/EGA registers |
| `03F8h–03FFh` | COM1 and related serial registers |
| `02F8h–02FFh` | COM2 and related serial registers |
| `0378h–037Fh` | LPT1 and related parallel registers |

Unimplemented devices must return a documented deterministic value and must
not consume a DMA request or interrupt. Aliases and OSD-selected devices must
be represented by the same decode table used in simulation and synthesis.

## 13. Device-side transaction contract

Every device adapter shall expose or internally implement:

- `select` derived solely from cycle class and address;
- read/write direction;
- active byte lanes;
- request acceptance;
- READY/completion;
- read data valid;
- side-effect counter for verification;
- reset state and pending-request cancellation policy.

A device MUST perform a write once, at the acceptance edge defined by its
contract. A read with side effects (PIC acknowledge, keyboard FIFO pop, ATA
status/data, floppy data) must consume exactly once, even if READY is stretched
or the CPU is paused.

Device responses must not remain visible to a later request. The bridge shall
tag or retain response ownership until the originating transfer completes.

## 14. Clock-independent timing policy

The machine shall separate three concerns:

1. **functional dependency:** READY, response availability, arbitration,
   command completion and required serialization;
2. **machine bus scheduling:** device phases, refresh cadence and arbitration;
3. **historical timing:** measured 80286 Ts/Tc/Ti and peripheral timings.

Accurate/Fast/Max CPU profiles MUST NOT bypass functional dependencies. Max
mode may remove compatibility delays but cannot skip READY, DMA grants, PIC
acknowledgements, locked intervals or required device response ordering.

The first AT profile shall run at one conservative, measured operating point.
OSD speed controls that cannot be mapped to the new contract MUST be disabled
or clearly labelled experimental; legacy MCL86 counters are not automatically
SPK286 timing controls.

## 15. Verification strategy

Tests are part of this specification. Each test must identify the owner,
accepted transaction edge, expected side effect count and final state.

### 15.1 CPU/bridge unit tests

At minimum, test:

- status-to-cycle conversion, including full four-bit `0xD` code fetch;
- address, A0/BHE and data-lane selection for all byte/word alignments;
- odd words and device-boundary crossings;
- stable metadata through arbitrary READY waits;
- repeated identical back-to-back requests;
- read response retention and no stale-response reuse;
- writes exactly once under pause, reset and redirect;
- INTA two-beat ordering and vector placement;
- LOCK and HOLD exclusion;
- DMA grant only after HLDA and transaction drain;
- reset-held ROM loading and runtime loader arbitration;
- unmapped, ROM-protected and device-alias policies.

### 15.2 Chipset unit tests

Create independent tests for:

- master/slave PIC priority, masking, cascade, EOI, spurious IRQ and vector;
- two-acknowledge INTA timing with READY waits;
- DMA address/count/page, direction, masking, cascade and terminal count;
- refresh ownership and retention under CPU contention;
- PIT mode/count and IRQ0 cadence;
- 8042 command/data/status, keyboard IRQ1 and reset output policy;
- RTC/CMOS index/data, NMI mask and IRQ8;
- memory/option-ROM/video decode and write protection;
- floppy/ATA request completion and DMA side effects.

### 15.3 Integration tests

The machine test ladder is:

1. reset vector and BIOS ROM fetch;
2. project-owned diagnostic ROM with exact signature;
3. memory and I/O byte/word tests;
4. PIC programming, IRQ0/IRQ1/IRQ8 and two-INTA delivery;
5. DMA floppy-like transfer with CPU contention and refresh;
6. keyboard input and timer-driven software;
7. DOS boot and file access;
8. CheckIt real-mode tests and protected-mode entry once SPK286 supports it;
9. AT BIOS POST, option ROMs and representative software;
10. repeated reset, pause, HPS load and board runs.

The diagnostic ROM must not inject CPU state or use expected results to drive
device responses. Production BIOS success is valuable evidence but is not a
substitute for deterministic bus and chipset tests.

### 15.4 Assertions and trace records

Simulation shall assert that:

- at most one bus owner drives a command in any cycle;
- address/status/direction/lanes remain stable while a request waits;
- no side effect occurs without an accepted request;
- every accepted request has exactly one completion or documented reset abort;
- CPU LOCK excludes DMA/refresh/loader;
- HOLD never splits an odd word or INTA lock chain;
- a second INTA beat is the only vector source;
- an accepted write is not replayed after reset or redirect.

Trace records should include timestamp, owner, cycle class, physical address,
A0/BHE, direction, payload, READY waits, selected device, completion edge,
PIC/DMA state and CPU debug snapshot. The trace format must be stable enough
to compare simulation, MiSTer captures and future hardware captures.

## 16. Implementation milestones

### A0 — Contract freeze

- Record exact SPK286 revision and port list.
- Freeze the transaction record and status mapping.
- Freeze reset, lane, READY, LOCK and HOLD rules.
- Add bridge assertions and a source/provenance manifest.

**Acceptance:** CPU boundary tests pass and no signal has dual ownership.

### A1 — CPU wrapper and functional AT bridge

- Instantiate SPK286 without debug state injection.
- Implement request retention, status conversion, lane handling and response
  assembly.
- Keep an optional XT compatibility profile separate from the AT profile.

**Acceptance:** reset-to-ROM and memory/I/O bridge suites pass in both
simulation engines.

### A2 — AT memory and arbitration

- Implement the 24-bit map, ROM protection and extended-RAM path.
- Implement CPU/DMA/refresh/loader arbitration and HOLD/HLDA.

**Acceptance:** contention, reset, READY, odd-word and LOCK tests pass without
duplicated side effects.

### A3 — Interrupt subsystem

- Add cascaded PICs, IRQ routing, INTA and NMI mask/source policy.

**Acceptance:** programmed PIC tests and hardware-like two-INTA traces pass.

### A4 — DMA, refresh and timer

- Add DMA1/DMA2, page registers, cascade and refresh.
- Add PIT and IRQ0.

**Acceptance:** floppy-like DMA transfers, refresh contention and timer tests
pass with no CPU bus corruption.

**Implementation status:** Delivered as a standalone functional boundary in
`spk286_at_dma.sv`, `spk286_at_refresh.sv` and `spk286_at_pit.sv`. The
Icarus/Verilator `A4_DMA_REFRESH_PIT_TEST_PASS` suite covers a two-beat DMA1
transfer with page addressing and terminal count, refresh priority under
contention and PIT channel 0/IRQ0. DMA2 word-page refinements and top-level
device wiring remain later work.

### A5 — Keyboard, RTC and storage/video integration

- Add 8042, RTC/CMOS, floppy/ATA and the selected video adapters under the same
  decode and interrupt ownership rules.

**Acceptance:** DOS boot and representative device software run with traces.

### A6 — Full protected-mode machine validation

- Consume the completed SPK286 Protected Mode implementation.
- Exercise CheckIt's real-mode setup, far transition, descriptors, gates and
  protected-mode exception paths.

**Acceptance:** dedicated protected-mode tests and representative software
  complete without modifying the CPU/chipset contract.

### A7 — FPGA and board evidence

- Build with reproducible Quartus inputs and constraints.
- Record fit, timing, resource use, image hash and board results separately.

**Acceptance:** the documented machine profile runs the diagnostic ladder on
  hardware; unsupported AT features remain listed rather than implied.

## 17. Open decisions that must be resolved before RTL freeze

1. Exact Cyclone V clock plan and whether CPU/chipset share one domain.
2. Whether the first AT memory path is native 16-bit SDRAM or a serialized
   8-bit compatibility path.
3. Exact AT ROM/option-ROM and A20 decode policy.
4. Reuse versus replacement of the KFPC-XT bus controller and arbiter.
5. Physical versus normalized modelling of 82288/82289 command/arbitration
   phases.
6. IRQ routing for EGA, AdLib, Sound Blaster, serial, floppy, ATA and RTC.
7. DMA channel assignments and device request/acknowledge polarity.
8. 80287 socket behaviour: absent, deterministic no-coprocessor profile or
   future device model.
9. HPS/SDRAM access ownership during reset, OSD pause and runtime.
10. Which historical timing measurements are required for the first Accurate
    profile and which remain functional-only.

Every decision shall be recorded in the machine repository before it becomes a
shared RTL assumption. Ambiguous hardware evidence must remain visible as an
open item; it must not be resolved by a test-specific constant.

## 18. Definition of done

The AT bus and CPU–chipset contract is complete for a release when:

- the exact CPU and bridge interfaces are documented and lint-clean;
- memory, I/O, code-fetch and INTA transfers have one tested owner;
- READY waits, lanes, odd words, LOCK, HOLD/HLDA and reset are verified;
- dual PIC, DMA/refresh and loader arbitration are independently tested;
- the authoritative memory/I/O decode table is shared by simulation and RTL;
- no device side effect is duplicated or lost under stalls, pause or reset;
- a diagnostic ROM reaches a deterministic signature from native reset;
- DOS and representative devices run through the same bridge;
- FPGA fit/timing and board evidence are reported separately;
- remaining XT compatibility, Protected Mode and timing limitations are stated
  explicitly.

This definition does not claim a complete IBM-compatible PC/AT until the
protected-mode CPU work, AT BIOS behaviour and required device compatibility
have each passed their own acceptance gates.
