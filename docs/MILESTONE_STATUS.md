# Integration milestone status

Recorded on 2026-09-11 for branch `codex/spk286-xt-integration`.

| Milestone | Status | Evidence |
| --- | --- | --- |
| I0 — Baseline and provenance | Complete | Pinned PCXT and SPK286 manifests, preserved sources and import verification |
| I1 — CPU packaging and wrapper | Complete | Complete SPK286, BIU and generated microcode; elaboration and generation checks pass |
| I2 — XT bus adapter | Complete | Icarus and Verilator bridge suites pass, including seven deliberate mutation detections |
| I3 — Reset-to-program execution | Complete | Project diagnostic runs from native `FFFFF0`, passes exact signatures and transaction counts |
| I4 — Machine events and ROM loading | Complete | PIC/INTA, ownership, ROM loading, monitor and inherited focused regressions pass |
| I5 — MiSTer FPGA candidate | Qualified delivery | Quartus compile, fit and assembler pass; RBF is delivered and all new 50 MHz paths close timing. Inherited video/HPS/SDIO setup groups prevent strict whole-project timing sign-off |
| I6 — Board diagnostic validation | Pending | Loading procedure and observations are defined; exploratory runs used an earlier candidate, while the exact final RBF still requires the diagnostic acceptance run |

Production BIOS work B0-B2 was not started and is not an acceptance gate for
these milestones. See `BIOS_BACKLOG.md`.

The current deliverable is therefore a simulation-validated and FPGA-built
candidate, not a physically validated PC/AT-compatible machine. The initial
profile remains an XT-derived machine with SPK286 in Real Mode.

## AT contract implementation progress

| Milestone | Status | Evidence |
| --- | --- | --- |
| A0 — Contract freeze | Complete | `docs/DECISIONS.md` records the CPU snapshot, shared-clock policy, ownership boundary and handshake decisions |
| A1 — Functional AT bridge | Complete | `rtl/spk286_integration/spk286_at_bus_bridge.sv` and the Icarus/Verilator `A1_AT_BRIDGE_TEST_PASS` suite validate 24-bit metadata, lanes, READY, LOCK, INTA-class requests and reset cancellation |
| A2 — Memory and arbitration slice | Complete | `spk286_at_memory_decode.sv` and `spk286_at_arbiter.sv` pass Icarus/Verilator tests for the 24-bit profile map, ROM protection, HOLD/HLDA, LOCK, odd-word/response exclusion and reset-held loader ownership |
| A3 — Interrupt subsystem | Complete | Dual KF8259 boundary, IRQ2 cascade, programmed masks/vectors, two-INTA delivery and NMI mask/source tests pass; active top remains XT-derived |
| A4 — DMA, refresh and timer | Complete | Functional DMA1/DMA2 boundary, page/count/mode/terminal-count state, refresh owner and PIT/IRQ0 pass Icarus and Verilator integration tests; active top remains XT-derived |
| A5 — AT device boundary and routing | SDRAM/loader ownership boundary simulation-ready; acceptance pending | Device/router slice, `spk286_at_machine`, `spk286_at_mister_memory_port` and `spk286_at_mister_sdram_owner` pass focused Icarus/Verilator checks and the event ROM boundary test through a behavioral SDRAM-pin model; top-level profile selection, HPS ROM-sequencer wiring, media/video attachment and DOS acceptance remain pending. See `docs/AT_A5_HANDOFF.md`, `docs/AT_A5_SYSTEM_HANDOFF.md` and `docs/AT_MISTER_MEMORY_HANDOFF.md` |
| A6+ — Protected mode, AT system and board evidence | Not started | Protected-mode validation, AT BIOS, DOS/representative-device traces and hardware validation remain pending; no AT compatibility claim is made |
