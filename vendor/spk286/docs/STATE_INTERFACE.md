# Architectural State Contract

Current Phase 7 integration uses ordered microcode formats 15/16/17 (100 entries,
612 words), shared CPU owners and the D-037 functional acceptance contract.
See [PHASE7_FUNCTIONAL_POLICY.md](PHASE7_FUNCTIONAL_POLICY.md),
[PHASE7_MEMORY_STRINGS.md](PHASE7_MEMORY_STRINGS.md), [PHASE7_IO.md](PHASE7_IO.md)
and [PHASE7_EMULATOR_REFERENCE.md](PHASE7_EMULATOR_REFERENCE.md). Earlier
increment counts and pending inventories below are historical snapshots.

The 2026-09-09 [independent closure review](PHASE7_CLOSURE_20260909.md) found no
demonstrated state-owner defect in the preserved combined candidate. Its added
REP INS lifecycle cases check changing accepted input samples and complete
architectural state. The corrections change verification/build files only;
pending candidate strings/I/O are not delivered production interfaces.

## Register storage

`spk286_registers` is a synthesizable datapath storage block. All writes are
synchronous to `clk`; active-high synchronous `reset` has priority. Reads are
combinational, including after a write edge, with no asynchronous write bypass.

| Encoding | Word | Byte |
| --- | --- | --- |
| 0 | AX | AL |
| 1 | CX | CL |
| 2 | DX | DL |
| 3 | BX | BL |
| 4 | SP | AH |
| 5 | BP | CH |
| 6 | SI | DH |
| 7 | DI | BH |

Each read port has an independent index and byte-mode bit. Byte reads are
zero-extended. Byte writes use `write_data[7:0]` and preserve the other half.
All three-bit encodings are valid. `gpr_state[index*16 +: 16]` exposes exactly
the same word state used by the datapath; no simulation-specific copy exists.

IP accepts an absolute 16-bit commit value. Sequential advancement, instruction
length accounting and control transfers belong to the instruction
controller. The storage block does not infer them from GPR or bus activity.

FLAGS writes update only `flags_write_mask & 16'h7FD5`. Other bits hold.
The reset representation of reserved bits is preserved. The controller must
provide a mask appropriate to the instruction and operating mode; this block
does not implement POPF, IRET, arithmetic flag generation or privilege policy.

The three write enables are independent. A future execution controller may
commit a GPR result and FLAGS on one edge, or suppress both on a fault. Tests
drive these normal datapath interfaces; no hierarchical force/deposit is used.

## Segment storage and address formation

`spk286_segments` has one synchronous ordinary-real-mode reload port and one
combinational read/address port. Index 0/1/2/3 means ES/CS/SS/DS. Every index is
valid; selector zero is a valid real-mode paragraph, not a protected-mode null
selector. Consumers must not use a selector as a substitute for its cached base.

The observation vectors use `index * width +: width`: selectors/limits have
width 16, bases 24, access fields 8. They expose the real stored values.

Reset values are CS=F000/base FF0000, other selectors/bases zero, every limit
FFFF and canonical access 93 (see D-008 for the normalization boundary).
`load_en` replaces one selector and its ordinary real-mode cache on the edge;
reset overrides it. Reads observe the new state after that edge. Code-segment
loads must be coordinated with IP and fetch invalidation by the controller;
this module alone does not implement far control transfers.

`physical_address` is cached base plus a 16-bit offset. It is a byte address
on a 24-bit path and retains carry into A20. This combinational output does not
authorize a memory transaction or validate the entire width of an operand.

## Integrated execution and fetch boundary

`spk286` exposes these datapath ports under `gpr_*`, `ip_*`, `flags_*` and
`segment_*`. The GPR/IP/FLAGS ports are setup controls when `execute_enable=0`;
when enabled, decode/microcode own those writes. Word MOV also owns its write
width independently of the external setup byte selector. Segment/redirect
ports remain development composition controls. All enables must be driven
explicitly, including in the reset smoke harness.

- A normal `ip_write_en` commit changes architectural IP only.
- `redirect && ip_write_en` also flushes/restarts fetch at `ip_write_data`.
- A CS load must occur with that redirect/IP transaction. A near redirect
  leaves CS and its special reset cache intact; a far redirect reloads CS.
- A redirect without an IP write, or a CS load without redirect, raises
  `control_error` combinationally and suppresses the entire state transaction.
  Independent bus progress may continue. Reset overrides all state transactions.

`fetch_request && fetch_request_ready` accepts a sequential fetch request on
the rising edge. Reset and valid redirects request their first fetch
automatically. Only one transaction and one response can exist. A response is
accepted on `fetch_valid && fetch_ready`; it contains `fetch_ip`, `fetch_count`
(1 or 2) and `fetch_data`, with the earliest byte in bits 7:0. A single byte is
zero-extended. All response fields hold while the consumer stalls. New requests
wait for the slot to become empty; no same-edge refill optimization is promised.

`debug_fetch_cursor[16]` retains an offset carry beyond FFFF. `fetch_blocked`
means the cursor is beyond the cached segment limit; it is not an exception.
Redirect clears the exhausted cursor. The instruction unit must eventually
turn an attempted execution beyond the segment into the appropriate exception.

During execution the segment read/address outputs observe the current operand
context; `segment_read_index` and `segment_offset` are setup queries only when
`execute_enable=0`. The operand service uses the same architectural GPR state
and commit path as setup. External setup must not change an executing stream's
state without a coordinated redirect. Accepted BIU requests snapshot their
physical address and write data independently of subsequent setup changes.

Phase 3 adds `debug_modrm`, `debug_displacement`, `debug_effective_offset` and
`debug_operand_segment` (ES/CS/SS/DS encoding above). They describe captured
instruction context, not future bytes at the queue head. `operand_blocked`
means the whole word exceeded the cached segment limit before any data request;
it is sticky until reset/redirect and is not architectural exception delivery.
Memory read/write visibility is available on the shared bus and SingleStep
compares resulting RAM. See [BUS_INTERFACE.md](BUS_INTERFACE.md).

`tools/state_vectors.py` demonstrates the data boundary using the existing
`SingleStepCase` reader. It emits an initialization stream for the C++ driver,
which loads GPRs/data segments normally, then atomically reloads CS/IP with a
redirect. A synthetic byte memory serves the bus. The snapshot is read through
datapath ports and includes all current state and the returned fetch bytes.
This is initialization verification only, with zero instructions executed.

## Phase 4 FLAGS ownership

With execute_enable=1, executor COMMIT_FLAGS owns the existing FLAGS write port,
including data and mask. Setup FLAGS writes still apply only while paused.
No architectural storage module or writable-bit contract changes. The executor
holds candidate values and an effective mask, not a second architectural FLAGS
register. Arithmetic updates 08D5; logic updates 08C5 and leaves undefined AF
stored unchanged. IF_WRITE result disposition completes before FLAGS commit,
then END retires. Pausing cannot duplicate either commit. Redirect clears
pending candidates but does not undo a previously completed FLAGS/GPR write.
See PHASE4_SCOPE.md for the exact instruction and undefined-flag policy.

## Phase 6 event state and completion

New synchronous inputs are `intr`, `nmi` and `hold_request`. New architectural
observations are `halted`, `shutdown` and `event_completed`. Debug observations
include `debug_event_vector`, `debug_event_kind`, `debug_instruction_ip`,
`debug_nmi_pending`, `debug_nmi_blocked` and `debug_sti_shadow`.
Kinds are 1 fault, 2 sampled trap, 3 NMI, 4 INTR and 5 software event.

A fault has event completion without target retirement. An executed software
INT retires once when entry completes. A post-retirement trap or external event
adds no retirement. Event entry's internal END is not a guest instruction.
The saved start address, architectural consumed-byte/next IP and speculative
fetch cursor are distinct. CS selector/cache/IP are installed coherently.

Operand limit flags are now real #GP producers; known invalid owned group
encodings produce #UD. Legal unsupported instructions and internal microcode
errors remain distinct diagnostics. Speculative fetch exhaustion becomes #GP
only when a byte is required and prior boundary events have been serviced.
Debug cancellation clears transient event/candidate state while accepted physical
operations drain; it does not roll back SP increments or completed memory writes.
The [commit matrix](INTERRUPTS_EXCEPTIONS.md) records partial effects and the
[review](PHASE6_ARCHITECTURAL_REVIEW.md) records unvalidated interruptibility rules.

## Phase 7 byte/prefix service update

The public CPU ports remain unchanged. Internal executor writeback now carries
`gpr_write_byte`; the existing architectural register file performs byte-half
updates. `operand_byte`, `request_byte` and `memory_byte` carry explicit operand
width across functional and physical services.

`debug_instruction_ip` identifies the first prefix when one exists. The consumed
IP advances for every prefix/opcode/displacement/immediate byte, with a separate
counter enforcing ten-byte maximum instruction length. Final opcode effects
are distinct from first-byte event sampling. Prefix state clears on completion,
event cancellation, explicit redirect and reset; it never becomes guest state.
No new public iteration/restart interface is claimed.

The direct scalar increment adds captured internal source/destination GPR
selectors. They are instruction metadata, not architectural copies. Existing
public state ports, register layout and FLAGS ownership are unchanged. CWD reads
AX and writes DX; LAHF writes AH and preserves AL. SAHF writes mask 00D5 only.
INC/DEC register operations preserve CF; TEST never enables destination writes.

Shift/rotate state is internal and transient: operand/kind/width/count/carry
snapshots, arithmetic progress and a pending response. It clears on reset or
cancellation and freezes on pause. The executor's result suppression flag
clears at instruction start/cancel and supports count-zero disposal. No public
CPU state layout or architectural register owner changes.

Data-transfer operations add an internal address override and offset temporary,
cleared at instruction start, cancellation and reset. Source/target read muxes
observe the existing GPR owner; they are not additional architectural storage.
XCHG cancellation does not roll back a completed RM or register write. The
public CPU/debug state layout remains unchanged. LEA exposes no data-bus request.

Decoded dispatch adds internal branch request/target/valid metadata and one
operand-context reuse bit. The original macro entry, prefix state and first-byte
restart address survive a branch. Start/cancel/reset clear cached reuse; pause
holds it. The executor's operand reversal and constants add no architectural
storage. Public CPU/debug ports and GPR/FLAGS ownership remain unchanged.

Decimal/radix operations add internal arithmetic operands, progress, held result
and pending-fault state. The existing AX/FLAGS owners perform commits. AAM
radix zero preserves AX and exposes its observed fault flags to the existing
exception frame path. Cancellation keeps completed architectural commits and
clears pending results/faults; all public CPU state ports remain unchanged.

## Semantic segment reloads

Internal READ_SEG16/WRITE_SEG16 operations use the captured decoded segment
index and TMP0; no second selector/cache state is introduced. A completed SS
reload informs the event owner. Prefix acquisition retains its inhibition;
the next opcode dispatch transfers protection to active-instruction ownership.
Reset, accepted events and debug cancellation clear this transient state.
Setup/debug CS/IP priority and the existing externally visible ports are unchanged.

## Frame cursor and conditional microcode state

The executor owns transient auxiliary/allocation values, a five-bit loop counter,
a parent address and an ENTER stack cursor. Accepted stack completion updates
that cursor while architectural SP retains its restart value. Final allocation
installs SP after BP; cancel/reset remove the transient ownership. Pauses freeze
all these values. Generated branch metadata is valid only for its symbolic
instruction-local branch controls. Existing architectural and external CPU ports
remain the same; debug micro-PC/source mapping includes the new programs.

## Far pointer/control candidate ownership

Far programs reuse TMP0/TMP1 plus the existing auxiliary and allocation storage.
CHECK_PUSH2/CHECK_POP2 validate a complete return frame; ADD_ALLOCATION_SP applies
the captured unsigned RETF allocation. The ordinary stack owner commits SP, and
the existing context interface installs CS:IP and flushes prefetched bytes.
Reset/cancel invalidate pending pointer, address and allocation state. A far
return is not an IRET and leaves the event owner's NMI blocking intact.
