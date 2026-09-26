# Machine integration decisions

## D-AT-001 — First AT bridge boundary

**Date:** 2026-09-10  
**Status:** Accepted for the A0/A1 implementation slice

The current production machine remains the existing `XT_COMPAT` profile and
continues to use `spk286_xt_bridge`. The AT work starts with a separate
`spk286_at_bus_bridge` rather than widening or silently changing the XT path.
This keeps the existing diagnostic machine reproducible while establishing the
24-bit/16-bit CPU-to-chipset contract required by the AT specification.

The AT bridge emits one normalized CPU-owner transaction record with the full
four-bit cycle class, 24-bit physical address, A0/BHE, explicit byte enables,
lane-positioned write data, direction, LOCK and explicit command acceptance
and READY completion edges. DMA, refresh, loader and device decode are not
owners of this module; they will consume the same typed boundary in later A2+
work.

## D-AT-002 — Acceptance and completion handshake

**Date:** 2026-09-10  
**Status:** Accepted for the A0/A1 implementation slice

`at_accept` is the sole command-acceptance edge. `at_ready` is ignored until
that edge has occurred and is only a completion when the selected read also
asserts `at_read_data_valid`. The bridge holds the complete request record
unchanged through `at_ready` waits and reports one `at_completed` edge per
physical byte beat. This separates decoder/command acceptance from downstream
device completion and prevents idle READY or stale read data from becoming a
transfer.

An aligned word is serialized as low byte at address N followed by high byte
at N+1. An odd single-lane SPK286 physical transfer is retained as one beat;
the bridge never splits it again. Reset clears the retained request and does
not replay a command that was already accepted before reset.

## D-AT-003 — Clock and profile policy

**Date:** 2026-09-10  
**Status:** Accepted for the A0/A1 implementation slice

The first normalized AT bridge is synchronous to the shared machine clock and
does not claim historical 80286 Ts/Tc/Ti timing. A future separate-clock
chipset must transfer the entire request record through a bundled handshake or
FIFO; individual address, lane and control bits may not be synchronized
independently. AT memory decode, cascaded PIC/DMA, refresh and A20 policy remain
open A2+ decisions and are not implied by this bridge.

## D-AT-004 — First AT memory decode profile

**Date:** 2026-09-11
**Status:** Accepted for the A2 implementation slice

The first decoder retains the complete 24-bit physical address and classifies
memory/code requests into conventional RAM (`000000h–09FFFFh`), video aperture
(`0A0000h–0BFFFFh`), option/reserved region (`0C0000h–0EFFFFh`), system BIOS
(`0F0000h–0FFFFFh`) and extended RAM (`100000h–15FFFFh`). This is the initial
1 MiB machine profile: 640 KiB below the video hole and 384 KiB remapped above
1 MiB. CPU reads above `15FFFFh`, apart from the reset-vector BIOS alias, are
completed by the unmapped-memory sink with `FFh`. I/O and INTA never
select the memory path. Conventional, video and extended RAM writes are
allowed; option-region and BIOS writes are reported as ROM-protected. Presence
of individual option ROMs and reserved-hole side effects remains a later
chipset decision.

## D-AT-005 — First AT ownership policy

**Date:** 2026-09-11
**Status:** Accepted for the A2 implementation slice

The first arbiter uses fixed priority loader, refresh, then DMA. Runtime
external owners assert CPU HOLD and are granted only after CPU HLDA, bridge
drain, no pending response and no LOCK/INTA/retained odd-word interval. Once
latched, an external owner remains selected until `external_done`, even if its
request line withdraws. A loader explicitly marked as reset-held owns the bus
without waiting for HLDA and does not assert CPU HOLD. This is a functional
ownership policy, not an historical 82289 timing claim.

## Source selections

The consumed CPU snapshot is the imported `vendor/spk286` indexed tree at
`9d3a69eb0e9d7bed32a9a8672a3ce8b464865101`, with the integration repository at
`320d7acfa9ccd7f7f852c87ed823aec82332c0ee`. The source manifest and the
selected PCXT baseline are recorded in `docs/SOURCE_PROVENANCE.md`; no external
repository is a runtime build dependency.

## D-AT-006 — Cascaded PIC implementation boundary

**Date:** 2026-09-11
**Status:** Accepted for the A3 implementation slice

The AT interrupt boundary reuses the imported `KF8259` state machines rather
than introducing a second production PIC implementation. The wrapper maps the
master to `20h/21h`, the slave to `A0h/A1h`, wires slave IRQ8-15 through master
IRQ2 and exposes only the second accepted INTA beat as read data. The master's
cascade ID is registered between accepted INTA transactions so the normalized
handshake is deterministic without changing the imported device logic.

The active machine remains the separate XT-derived path. The A3 tests are
standalone device-boundary evidence and do not claim AT BIOS or board support.

## D-AT-007 — NMI mask and source policy

**Date:** 2026-09-11
**Status:** Accepted for the A3 implementation slice

Port `70h` bit 7 is the NMI mask. Reset starts masked; parity, channel-check
and explicitly supplied external events are ORed at the boundary and edge
qualified to one synchronous NMI pulse per asserted source. This is a
functional source policy, not a claim about every board-specific parity or
channel-check generator. Separate-clock synchronization and additional AT
event sources remain later integration work.

## D-AT-008 — Functional DMA pair and transfer profile

**Date:** 2026-09-11
**Status:** Accepted for the A4 implementation slice

The A4 boundary uses a repository-owned functional DMA pair rather than
mutating the imported XT-oriented `KF8237`. It exposes DMA1 channels 0–3 as
byte transfers, DMA2 channels 4–7 as word transfers, page registers, channel
4 cascade state, request/acknowledge, masking, mode, address/count flip-flops,
auto-init and terminal count. A transfer retains address, direction and lanes
until the endpoint accepts and completes exactly one beat.

The first DMA2 profile emits an even physical address with both lanes active.
This is an explicit functional boundary, not a cycle-accurate claim about all
8237 word-page and device wiring variants. Device-specific request polarity,
full word-address page semantics and top-level storage wiring remain open for
A5/A7.

## D-AT-009 — Refresh and PIT boundary

**Date:** 2026-09-11
**Status:** Accepted for the A4 implementation slice

Refresh is a separate external bus owner and outranks DMA in the first fixed
arbiter priority. Its cadence is parameterized for deterministic simulation;
the refresh row and completion are visible at the normalized boundary. The
PIT boundary owns ports `40h–43h`, supports the functional counter modes
needed by the first timer path and emits a synchronous one-cycle IRQ0 pulse.
`counter_clock` is treated as a sampled tick enable; clock-domain crossing and
historical PIT frequency selection are later top-level decisions.

## D-AT-010 — A5 device routing and interrupt assignments

**Date:** 2026-09-11
**Status:** Accepted for the A5 functional boundary

The A5 CPU-facing device map is owned by one router so a request cannot be
accepted by both a legacy alias and an AT device. The first functional IRQ
assignments are IRQ1 for the 8042, IRQ6 for floppy, IRQ8 for RTC/CMOS and
IRQ14 for primary ATA. Floppy-like DMA uses channel 2; video has no new IRQ
source in this slice. Unmapped I/O returns `FFh` on its addressed byte lane
and does not create DMA or interrupt activity.

The router exposes normalized device boundaries and can be connected to the
existing AT bridge/PIC/DMA contracts, but it does not silently replace the
active XT top. Physical PS/2 decoding, real media backends, complete EGA/VGA
VRAM semantics and DOS boot evidence remain required before A5 system
acceptance.

## D-AT-011 — RTC management and initial CMOS memory profile

**Date:** 2026-09-12
**Status:** Accepted for the AT MiSTer profile

The AT RTC consumes the same `hps_ext` management window as ao486 and z486:
addresses `F400h–F47Fh` update the corresponding MC146818 register. This makes
the MiSTer host date and time visible through ports `70h/71h` without adding a
second clock source or an AT-specific HPS protocol. The RTC advances the full
calendar after import and implements BCD/binary and 12/24-hour representation,
Gregorian month/leap-year transitions, SET freeze, alarm/update/periodic
status-C flags and IRQ8 clear-on-read behavior.

CMOS starts with base memory `0280h` (640 KiB), extended memory `0180h`
(384 KiB) in both standard field pairs, and no memory above 16 MiB. HPS writes
cannot replace those profile defaults. CPU access retains normal CMOS-RAM
semantics, including temporary write/read/restore patterns used by hardware
diagnostics. The standard checksum over bytes `10h–2Dh` is maintained
incrementally, while checksum bytes `2Eh/2Fh` also remain directly writable as
required by the IBM AT programming model.

## D-AT-012 — Selectable 1–16 MiB RAM profiles

**Date:** 2026-09-21
**Status:** Implemented in the PCAT-286 MiSTer profile

The Hardware OSD selects nominal installed-RAM profiles of 4, 8, 16, 1 or
2 MiB, in that order. The 4 MiB option is the default (`000` in status bits
`74:72`), with 3,456 KiB of extended memory above the fixed 640 KiB
conventional base. The 1 MiB profile remains selectable and provides the
original 384 KiB of extended memory. The applied profile extends the physical
RAM decode up to its selected limit. Following the 86Box 16-bit-bus AT map, the
16 MiB selection exposes extended RAM through `FDFFFFh`, reserves
`FE0000h–FEFFFFh`, and maps `FF0000h–FFFFFFh` to the 64 KiB system-BIOS alias.
CMOS reports 15,232 KiB of extended RAM (`3B80h`), so the BIOS sees 15,872 KiB
including conventional memory. CMOS fields and their checksum follow the
applied profile.

EMS retains its private 2 MiB page backing at SDRAM addresses 2–4 MiB. CPU and
DMA accesses at physical addresses 2 MiB and above are translated by +2 MiB in
the SDRAM backend, keeping that EMS store disjoint from expanded RAM without
changing addresses visible to the CPU.
