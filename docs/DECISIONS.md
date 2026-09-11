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
(`0F0000h–0FFFFFh`) and extended RAM (`100000h–FFFFFFh`). I/O and INTA never
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
