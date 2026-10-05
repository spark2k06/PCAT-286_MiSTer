# Protected Mode PM5a — Fixed 80286 TSS image service

Status: implemented as an isolated PM5 foundation increment. This slice does
not claim that the live decoder or far-transfer paths perform task switching.
It establishes and verifies the transaction owner that the integrated PM5
task-switch path will use.

## Fixed 80286 layout

The service uses the 22-word 80286 TSS and rejects a candidate whose complete
minimum image is not covered by a descriptor limit of at least `002Bh`.

| Offset | Field |
| ---: | --- |
| `00h` | backlink selector |
| `02h/04h` | SP0 / SS0 |
| `06h/08h` | SP1 / SS1 |
| `0Ah/0Ch` | SP2 / SS2 |
| `0Eh` | IP |
| `10h` | FLAGS |
| `12h–20h` | AX, CX, DX, BX, SP, BP, SI, DI |
| `22h/24h/26h/28h` | ES, CS, SS, DS selectors |
| `2Ah` | LDT selector |

The named offsets are held in `spk286_tss_pkg`; no 386 TSS fields or paging
state are represented.

## Transaction contract

`spk286_tss_service` owns one ordered word/byte transaction at a time. A
transaction remains asserted until `memory_done`; no TSS phase advances on a
READY stall. Nested CALL/task-gate entry performs, in order:

1. save the outgoing IP, FLAGS, eight general registers, four segment
   selectors and LDTR;
2. write the old TR selector to the target backlink word;
3. set the target TSS descriptor busy bit; and
4. read the complete architectural target image.

Direct JMP additionally clears the outgoing descriptor busy bit. A task-return
request clears the current busy bit and reads the linked target image without
rewriting the target backlink. The service exposes the loaded image and the
busy TR candidate through a single commit pulse.

Validation of the target descriptor class, selector privilege, linked-task
rules, target segment descriptors and hidden-cache construction belongs to the
next PM5 integration slices. This boundary prevents a stalled bus response
from partially committing CPU state.

## Verification

`sim/unit/spk286_tss_service_tb.sv` passes 13 Icarus checks with deliberate
transaction handshakes. It verifies the complete outgoing image, backlink,
busy-byte update, loaded target fields, nested `NT` flag candidate, TR
candidate and pre-transaction `#TS` rejection for a short TSS.
