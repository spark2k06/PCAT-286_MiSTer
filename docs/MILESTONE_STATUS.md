# Integration milestone status

Recorded on 2026-09-10 for branch `codex/spk286-xt-integration`.

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
