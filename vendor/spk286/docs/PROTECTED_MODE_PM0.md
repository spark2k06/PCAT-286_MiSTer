# Protected Mode PM0 — State and Descriptor Foundation

Status: implemented as an independent, non-executing foundation slice.

This document records the contract and evidence for PM0. The new services are
not connected to the instruction decoder, microcode, fetch path or event entry
yet. The existing Real-Mode segment service therefore remains unchanged and
continues to own the live CPU state.

## Scope completed

- `spk286_protected_state` stores the 16-bit 80286 MSW, GDTR, IDTR, LDTR and TR
  visible fields and their PM0 hidden-cache fields.
- Four PM0 segment-cache candidates can be committed atomically with their
  selector, base, limit, access byte, class, present, mode, DPL, table-origin
  and RPL metadata.
- `spk286_selector` decomposes index/TI/RPL and checks the complete eight-byte
  descriptor range before a bus request. The end calculation is 21 bits.
- `spk286_descriptor` assembles and validates an eight-byte 80286 descriptor
  into a typed candidate. It does not commit architectural state or issue bus
  cycles.
- No 386 paging, granularity, default-size, long-mode, CR0 or 32-bit TSS state
  exists in this slice.

## Descriptor layout and reserved policy

The parser consumes the descriptor as little-endian bytes, with byte 0 in
`raw_descriptor[7:0]`:

| Bytes | Field | Width | PM0 policy |
| --- | --- | ---: | --- |
| 0–1 | limit | 16 | retained verbatim |
| 2–3 | base low | 16 | retained verbatim |
| 4 | base high | 8 | retained verbatim |
| 5 | access rights | 8 | decoded below |
| 6–7 | reserved | 16 | must be zero |

For a segment descriptor, access byte bits are `P`, `DPL`, `S`, `E`,
`C/ED`, `R/W` and `A` at bits 7 through 0. `S=1,E=1` is code,
`S=1,E=0,C/ED=1` is expand-down data, and `S=1,E=0,C/ED=0` is ordinary
data. For system descriptors, PM0 recognizes only the 80286 classes:

| `S` | type | Class |
| ---: | ---: | --- |
| 0 | 1 | available 80286 TSS |
| 0 | 2 | LDT |
| 0 | 3 | busy 80286 TSS |
| 0 | 4 | 80286 call gate |
| 0 | 5 | 80286 task gate |
| 0 | 6 | 80286 interrupt gate |
| 0 | 7 | 80286 trap gate |
| 0 | other | invalid/reserved |

Gate byte 4 is reserved except for the five-bit call-gate parameter count.
Bytes 6–7 remain reserved for every class. A not-present but otherwise
well-formed descriptor remains typed and returns `present=0`; the later
segment/event service decides whether that becomes #NP, #TS or another fault.

## Selector and table contract

| Field | Source |
| --- | --- |
| index | selector bits 15:3 |
| TI | selector bit 2; 0=GDT, 1=current LDT |
| RPL | selector bits 1:0 |
| null | index equals zero AND TI=0; RPL is ignored (`0000h`-`0003h` only) |
| descriptor end | `index * 8 + 7`, evaluated without truncation |
| table valid | descriptor end `<=` table limit and selector is non-null |
| physical address | 24-bit table base plus `index * 8`; carry is observable in PM0 |

The null selector is reported separately from table-limit failure. PM0 does
not permit it as a descriptor candidate. A later operation-specific service
will apply the distinct DS/ES, CS and SS null-selector rules.

LDT entry zero (`0004h`-`0007h`) is non-null and remains subject to the normal
table, type, presence and privilege checks. This corrects the original PM0
index-only definition. Evidence: Intel, *80286 (B-2/B-3) Information Sheet*,
21 November 1984, page 4, "Loading Null Selector Values Into DS or ES Registers",
Background ([scan](https://docs.pcjs.org/manuals/intel/80286/80286_B2_B3_Errata-1984-11-21.pdf)).

The executable privilege contract is reserved for PM2. Its input truth table
is fixed here so later tests consume the same fields rather than recomputing
them:

| Operation | Required PM2 predicates before commit |
| --- | --- |
| data load | non-null, in-table, present, data or readable-code, `max(CPL,RPL) <= DPL` |
| writable data use | present, writable data, `max(CPL,RPL) <= DPL` |
| stack load | present writable data, `DPL=CPL`, `RPL=CPL` |
| non-conforming code transfer | target/gate checks plus target privilege relation |
| conforming code transfer | conforming-code relation; CPL unchanged |

These predicates are not silently applied by the PM0 parser.

## PM0 state and reset policy

The Intel iAPX 286 Programmer's Reference Manual 210498-005, section 10.4,
page 10-6 (PDF page 281), records `MSW=FFF0h`, `IDTR.base=0` and
`IDTR.limit=03FFh` after reset. PM0 uses those values. The same source's
section 10.3 and Figure 10-1/10-2 define the 24-bit table bases, 16-bit limits
and hidden LDTR/TR caches.

GDTR reset contents are not used before an explicit table load, so PM0 gives
the uninitialized GDTR fields a deterministic zero baseline. LDTR and TR are
invalid with selector zero until a validated candidate is committed. The four
segment-cache slices preserve the current project reset shape (ES, CS, SS, DS
order; CS=`F000h`, base=`FF0000h`, limit=`FFFFh`, real-mode access=`93h`).

The 80286 Hardware Reference Manual 210760-002, table 3-6, is recorded in
`docs/SOURCE_NOTES.md` as a conflicting IDTR-reset source that reports a
different limit. PM0 does not use IDTR for event delivery, so this remains a
named evidence item rather than an execution guess. It must be resolved before
PM3 protected event closure.

## TSS preparation contract (not implemented in PM0)

The fixed 80286 TSS is 22 words (minimum limit `2Bh`/size 2Ch). The named
offset table below is reserved for the PM5 task service; no 386 fields are
permitted.

| Offset | Field |
| ---: | --- |
| 00h | backlink selector |
| 02h/04h | SP0 / SS0 |
| 06h/08h | SP1 / SS1 |
| 0Ah/0Ch | SP2 / SS2 |
| 0Eh | IP |
| 10h | FLAGS |
| 12h–20h | AX, CX, DX, BX, SP, BP, SI, DI |
| 22h/24h/26h/28h | ES, CS, SS, DS selectors |
| 2Ah | LDT selector |

Evidence: Intel 210498-005, section 8.1, Figure 8-1 and the task-state
description. The table is a contract for a future named TSS service, not a
claim that task switching is implemented.

## System-instruction preparation matrix

The exact PM1 forms were recorded by PM0 before decoder work. PM1a implements
the six bounded `0F 01` forms, PM1b implements the visible-selector stores,
and PM1c/PM1d/PM1e implement the bounded descriptor-backed `LLDT/LTR`,
`VERR/VERW` and `LAR/LSL` operations listed
below. Privilege-sensitive selector inspection remains deferred. See
[PROTECTED_MODE_PM1.md](PROTECTED_MODE_PM1.md) for the live contract.

| Form | Encoding family | Status |
| --- | --- | --- |
| SLDT/STR | `0F 00 /0..1` | PM1b implemented |
| LLDT/LTR | `0F 00 /2..3` | PM1c implemented |
| VERR/VERW | `0F 00 /4..5` | PM1d implemented |
| SGDT/SIDT/LGDT/LIDT/SMSW/LMSW | `0F 01 /0..4,/6` | PM1a implemented |
| LAR | `0F 02 /r` | PM1e implemented |
| LSL | `0F 03 /r` | PM1e implemented |
| CLTS | `0F 06` | PM1g implemented; focused Real/CPL0/CPL1 evidence |
| ARPL | `63 /r` | PM1f implemented; focused register/memory/Real-Mode evidence |

The PM0 change itself decoded no system instruction. The current PM1a/PM1b/PM1c/PM1d/PM1e/PM1f/PM1g
slices connect these sixteen forms through the normal decoder, generated microcode,
executor, descriptor parser, operand path and BIU/READY transaction boundary.

## Verification

Focused tests, run from the repository root:

```text
bash scripts/test_units.sh iverilog spk286_protected_foundation
bash scripts/test_units.sh verilator spk286_protected_foundation
```

The test covers null/first/last selectors, GDT/LDT decomposition, exact and
overflowing limits, 24-bit base carry, code/data/expand-down/system classes,
reserved encodings, not-present typing, reset state, one-way PE state and
atomic GDTR/IDTR/LDTR/TR/segment-cache commits. The 2026-09-13 correction adds
all 65,536 selector values plus the LDT-entry-zero/GDT-null distinction and
exact/short descriptor boundaries for every RPL: 65,571 checks in each simulator.

PM0 does not claim descriptor bus transactions, protected instruction fetch,
privilege faults, event entry, system instructions or task switching. Those
belong to PM1–PM5 and must be added behind the tested service boundaries.
