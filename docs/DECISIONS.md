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

## Source selections

The consumed CPU snapshot is the imported `vendor/spk286` indexed tree at
`9d3a69eb0e9d7bed32a9a8672a3ce8b464865101`, with the integration repository at
`320d7acfa9ccd7f7f852c87ed823aec82332c0ee`. The source manifest and the
selected PCXT baseline are recorded in `docs/SOURCE_PROVENANCE.md`; no external
repository is a runtime build dependency.
