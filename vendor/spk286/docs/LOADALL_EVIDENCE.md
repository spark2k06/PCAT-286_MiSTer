# 80286 LOADALL evidence and current implementation contract

Status: **implemented functional slice; milestone not closed**  
Review date: 2026-09-16  
Target: Intel 80286 real/protected-mode semantics, with no 80386 behavior

This report records the evidence used for the current SPK286 implementation.
It separates primary documentation, physical-test availability, emulator
references, and project implementation choices. Agreement with an emulator is
not treated as proof of 80286 silicon behavior.

## Sources and provenance

| Source | Revision/hash | Use and confidence |
| --- | --- | --- |
| Intel, *80286 and 80287 Programmer's Reference Manual*, 210498-005 (1987), [archived PDF](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf) | Local ignored copy `build/references/intel-286-programmer.pdf`; SHA-256 `ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460` | Primary authority for documented 80286 exception 6, saved `CS:IP`, no error code, restartability, and 286 scope. High confidence. |
| Intel, *Undocumented iAPX 286 Test Instruction*, [archived PDF](https://docs.pcjs.org/manuals/intel/80286/80286_LOADALL.pdf) and [HTML transcription](https://www.pcjs.org/documents/manuals/intel/80286/loadall/) | Local ignored copy `build/references/intel-286-loadall.pdf`; SHA-256 `5c5a128ea7d5500c62f75efb24d1bac7ac392bb4f2fa21dce9a0277ac9d8e13d` | Primary-era evidence for `LOADALL`, the fixed physical image, hidden caches, and privilege rules. High confidence for the layout; medium confidence where the note is internally inconsistent or lacks silicon revision metadata. |
| SingleStepTests/80286, [repository](https://github.com/SingleStepTests/80286) | Pinned local checkout `.cache/phase7-clean-corpus-275`, commit `37c73caf53dcd22d3dd369ff09305d13d117a4fe`; README SHA-256 `75ffa0f36e49d2ce09c22cb2871a051176b419cb985b4a968ee586099cc9b285` | Independent hardware-derived 286 real-mode corpus. Its README explicitly says `0F 05` is not included and reserves unreal-mode tests for a future set. It is therefore an evidence gap, not a LOADALL oracle. |
| 86Box, [repository](https://github.com/86Box/86Box) | Local checkout `D:\GitHub\86Box_dev`, commit `de4a54c96fbdb9b3a233703646f354e7b2f2b8ff`, dirty only because of unrelated `src/disk/hdc_xtide.c`; reviewed files: `x86_ops_misc.h` SHA-256 `7cca59f327985989ef2b3ca5e530dfea2ee0d012261e6d4023bf9bf69b28e441`, `386_ops.h` SHA-256 `a4b1a63b67bfc7c96963f92e404989d8525e56fd7f222e2a98e059d4a02d9527` | Bounded source-function and opcode-table reference. It maps 80286 `0F 05` to `opLOADALL`, `0F 04`/`0F 07` and holes to `ILLEGAL`, and keeps `64h`–`67h` invalid in its 286 table. No source was copied. |
| PCem, [repository](https://github.com/sarah-walker-pcem/pcem) | Local checkout `D:\GitHub\pcem`, commit `3a9b8b704b81c77a4e072e27448766b8056b585a`, clean; reviewed files: `x86_ops_misc.h` SHA-256 `eb4ef7e813c0b872ff2dd9d20600fda573c4acaebba6d23ec7a7982e813176ae`, `386_ops.h` SHA-256 `d7ce794fff24a029a291422ec7c5824f8636a4155ea192fdffe0b62703c101d5` | Second bounded source-function and opcode-table reference. It independently agrees with 86Box on the tested 286 LOADALL cases; its agreement remains emulator evidence, not silicon proof. No source was copied. |

The Intel note has an opcode-reference inconsistency: its text uses both
`0F04H` and `0F05H`. The 80286 opcode table in 86Box selects `0F 05` for
LOADALL, while the pinned SingleStepTests corpus excludes that opcode from its
current real-mode vector set. SPK286 therefore records `0F 05` as the selected
target, while retaining `0F 04` as invalid pending direct silicon evidence.

## Page-level observations

- The Intel 80286/80287 Programmer's Reference Manual, section 9.6.1
  (printed pages 9-10), defines invalid-opcode interrupt 6 as an execution-time
  exception: prefetch alone does not raise it, the saved `CS:IP` identifies the
  offending instruction (or its leading prefixes), and no error code is pushed.
- The Intel LOADALL note (pp. 1 and 3) describes the fixed physical `000800h`
  image, its 51-word layout and hidden-cache records. The note's separate
  opcode references are retained verbatim as a provenance issue rather than
  silently normalized.
- The pinned SingleStepTests 80286 README documents the hardware-derived
  real-mode corpus and explicitly leaves `0F 05`/unreal-mode coverage for a
  future set. No LOADALL vector is therefore claimed from that corpus.

## Image layout adopted by the current slice

The Intel note describes a 102-byte image at physical address `000800h`.
SPK286 reads it as 51 little-endian words; the following table uses byte
offsets relative to `000800h`.

| Offset | Size | Field |
| ---: | ---: | --- |
| `00` | 6 | Reserved/unused |
| `06` | 2 | MSW |
| `08` | 8 | Reserved/unused |
| `10` | 2 | TR selector |
| `12` | 2 | FLAGS |
| `14` | 2 | IP |
| `16` | 2 | LDT selector |
| `18` | 2 | DS selector |
| `1A` | 2 | SS selector |
| `1C` | 2 | CS selector |
| `1E` | 2 | ES selector |
| `20` | 16 | DI, SI, BP, SP, BX, DX, CX, AX |
| `30` | 6 | ES hidden cache |
| `36` | 6 | CS hidden cache |
| `3C` | 6 | SS hidden cache |
| `42` | 6 | DS hidden cache |
| `48` | 6 | GDTR: base low word, base high/reserved word, limit |
| `4E` | 6 | LDT hidden cache |
| `54` | 6 | IDTR: base low word, base high/reserved word, limit |
| `5A` | 6 | TSS hidden cache |

Each six-byte hidden cache record is represented as two bytes of base low,
one byte of base high, one byte of access rights, and two bytes of limit. In
the little-endian word stream, the base-high byte is the low byte of the
middle word and the access byte is its high byte. The current RTL retains only
80286-width state: 24-bit base, 16-bit limit, and 8-bit access; it does not add
386 granularity, default-size or 32-bit fields.

The access byte's present/valid bit is staged as bit 7. The segment class,
DPL, selector RPL and table indicator are derived into the same state boundary
used by protected-mode translation. LDT and TSS cache records use the
dedicated system-cache classes; their exact type validation remains a later
evidence gate.

## Implemented behavior and explicit choices

The current functional slice does the following:

- decodes `0F 05` to a dedicated microcode entry and leaves `0F 04`, `0F 07`,
  and other 286 `0F` holes on the invalid-opcode path;
- issues 51 word reads through the existing top-level memory/BIU boundary at
  physical `000800h`, with the address and response held through READY waits;
- stages all image words and commits GPRs, IP, FLAGS, MSW, system registers,
  selectors and hidden caches on one architectural clock edge;
- rejects protected-mode execution for non-zero CPL with `#GP(0)` and rejects
  a LOADALL image that attempts to clear PE while already in protected mode;
- demonstrates real-mode hidden-cache translation with an instruction fetch
  above 1 MiB and a DS-based data read above 1 MiB.

The control-path integration also drives finite READY waits, injects reset
after LOADALL has begun, asserts HOLD during the LOADALL traffic, and raises a
synchronous NMI edge during the image read. The test verifies that the bus
transaction metadata remains stable during READY waits, reset clears the
partial transaction and restarts the image at `000800h`, HLDA suppresses new
bus cycles without changing the transaction count, and no event completes
before the atomic image commit. The NMI edge remains pending after commit;
ordinary NMI/INTR entry and acknowledgement behavior remains covered by the
existing event-lifecycle bank.

The current CPU-only top-level interface has `ready`,
`hold_request`/`hlda`, reset and interrupt inputs, but no bus-error or
transaction-abort input. This milestone therefore makes no bus-abort/error
claim for LOADALL. Modeling one by forcing `ready` or reusing the development
`cancel_data` path would conflate distinct external conditions; a native
bus-error contract and evidence belong to a separate bus-interface change.

The atomic staging and the local protected-mode checks are SPK286 design
choices until physical traces establish a different fault/partial-commit
sequence. A cancellation or reset discards the staged image. Bus-cycle count
and historical clock timing are intentionally not claimed from the Intel note:
the note itself contains an inconsistent count (195 clocks/51 bus cycles in
one passage versus 190 clocks without waits in another).

## Verification receipt

The dedicated checks currently pass as follows:

| Check | Result |
| --- | --- |
| `python3 -m unittest discover -s tests -p 'test_microcode*.py'` | 90 tests passed |
| `bash ./scripts/test_units.sh both spk286_decoder` | 263 opcode checks passed |
| `bash ./scripts/test_units.sh both spk286_loadall_service` | 186 image/privilege/atomicity checks passed, including FLAGS publication, READY withholding and reset restart, protected CPL=0, privilege rejection and cancellation |
| `bash ./scripts/test_units.sh both spk286_loadall_integration` | Atomic 102-byte commit and post-LOADALL `>1 MiB` hidden-cache access passed; READY stability, reset restart, HOLD/HLDA suppression and NMI deferral passed; 131 bus transactions in the stalled model |
| `bash ./scripts/test_units.sh both spk286_loadall_protected` | Top-level CPL=1 `LOADALL` `#GP(0)` event delivery passed with the saved `FLAGS`, `CS`, `IP` and zero error word |
| `bash ./scripts/test_units.sh both spk286_segments` | 262,202 checks passed |
| `bash ./scripts/test_units.sh both spk286_execution` | Ordinary execution and unsupported-diagnostic regression passed |
| `bash ./scripts/test_units.sh both spk286_microcode_execution` | 5,380 checks passed |
| `bash ./scripts/test_units.sh both spk286_microcode_rom` | 316 semantic/range checks passed |
| `bash ./scripts/lint.sh` | Passed |
| `bash ./scripts/synth_check.sh` | Passed; Yosys hierarchy includes `spk286_loadall_service` |

The complete point-4 validation receipt, including the WSL execution boundary
and the repository-state limitation in the broad Python discovery run, is in
[LOADALL_VALIDATION_RECEIPT_20260916.md](LOADALL_VALIDATION_RECEIPT_20260916.md).

The current SingleStep corpus has no LOADALL vectors, so no SingleStep LOADALL
claim is made. The focused integration is a project-owned directed test, not a
replacement for the reserved unreal-mode hardware suite.

The bounded 86Box/PCem functional differential is recorded in
[LOADALL_EMULATOR_DIFFERENTIAL_20260916.md](LOADALL_EMULATOR_DIFFERENTIAL_20260916.md).
Both references agree on the tested state/read outcomes and expose two
differences from the current SPK286 contract: reserved FLAGS normalization and
protected-mode LOADALL images that clear PE. Those differences remain evidence
questions; neither emulator is treated as the adjudicating authority.

For physical follow-up, the repository now includes a self-contained DOS probe
under [research/loadall_probe](../research/loadall_probe/). The hand-off binary
is `research/loadall_probe/release/LOADALL.COM`; it tests `0F 04`, `0F 05`,
reserved FLAGS and, when A20 plus extended RAM are available, a hidden DS base
at `100000h`. It remains in real mode, writes to the screen only, installs
temporary `#UD/#GP` handlers, and restores the image scratch area at physical
`000800h` before returning to DOS. The phase lines identify the last sensitive
operation if the CPU hangs; the binary SHA-256 is recorded in
`research/loadall_probe/release/LOADALL.COM.manifest.json`. Its output is
physical evidence for the tested CPU/revision, not a universal 80286 oracle.
The probe intentionally does not execute `STR`/`SLDT` in real mode: Intel's
80286 manual specifies `Interrupt 6` for both there, so clean-DOS `TR`/`LDTR`
are recorded as zero rather than risking an unhandled exception.

## Remaining evidence gates

The milestone remains open until the following are independently resolved:

1. a target Intel/Harris/AMD 80286 stepping is selected;
2. direct silicon or a published hardware-derived unreal-mode suite confirms
   opcode spelling, cache validity/type semantics and all image corner cases;
3. protected-mode CPL=0 success is tested through the complete event-delivery
   path, and silicon-specific non-zero-CPL frame behavior is independently
   confirmed;
4. Functional coverage now includes READY waits, reset restart, HOLD/HLDA
   suppression and NMI deferral. Exact silicon timing remains open, and no
   bus-abort/error behavior is claimed because the current CPU-only interface
   exposes no bus-error input;
5. a bounded logical-read/state differential against 86Box and PCem is now
   recorded, including the two observed disagreements with the current SPK286
   contract; full-machine timing and silicon differential evidence remain open;
6. `STOREALL`, ICE/test forms and 80386 `LOADALLD` remain separate work and are
   not silently added to this milestone.
