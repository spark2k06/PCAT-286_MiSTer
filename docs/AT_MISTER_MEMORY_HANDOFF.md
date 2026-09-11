# AT MiSTer memory handoff

**Date:** 2026-09-11
**Status:** Intermediate attachment boundary ready; physical backend pending
**Branch:** `codex/spk286-xt-integration`

## Boundary delivered

`rtl/spk286_integration/spk286_at_mister_memory_port.sv` is the production
adapter between the normalized AT machine and a future MiSTer SDRAM/HPS owner.
It exposes one abstract 16-bit backend transaction port and three initiator
sides:

- CPU memory/code fetch, including cycle class and byte enables;
- DMA memory beats;
- refresh ownership.

The adapter selects one owner at a time with the documented priority CPU,
refresh, DMA. It accepts a command once, keeps address, data and lanes stable
until completion, requires explicit read-data-valid for reads, and returns
independent ready/data handshakes to the initiator. An overlap is retained as
a sticky protocol diagnostic instead of silently allowing two owners.

Byte lane convention is unchanged: lane 0 is the low byte, lane 1 is the high
byte, and refresh uses both lanes. This keeps the normalized AT contract
independent of whether the eventual backend is KFSDRAM, an HPS-mediated
buffer, or another MiSTer memory owner.

## Evidence

Unit boundary test:

```text
bash scripts/test_at_mister_memory_port.sh
```

Pass marker from both Icarus and Verilator:

```text
AT_MISTER_MEMORY_PORT_TEST_PASS
```

The composed CPU event-ROM test also passes through the adapter:

```text
bash -lc "AT_SYSTEM_MAX_CYCLES=200000 bash scripts/test_at_machine_boundary.sh"
```

Observed result:

```text
AT_SYSTEM_BOUNDARY_PASS memory_beats=211 io_writes=12 irq0=1 refresh=30 port80=4
AT_MACHINE_BOUNDARY_TEST_PASS
```

## Remaining physical connection

This adapter is not yet a board-ready memory implementation. The active
`PCAT-286.sv` top level still instantiates `CHIPSET_SPK286`, whose legacy XT
path owns the existing SDRAM controller and device wiring internally. The
next top-level step is therefore an explicit AT profile/backend connection,
with an intentional decision about SDRAM ownership and the media/video
owners; a direct unreviewed tie into the legacy bus would create two memory
owners.

No RBF was generated or flashed by this step. Board acceptance remains
pending physical keyboard, storage, video, DOS and timing evidence.
