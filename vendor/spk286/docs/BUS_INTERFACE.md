# Native Bus Boundary

Current Phase 7 integration uses ordered microcode formats 15/16/17 (100 entries,
612 words), shared CPU owners and the D-037 functional acceptance contract.
See [PHASE7_FUNCTIONAL_POLICY.md](PHASE7_FUNCTIONAL_POLICY.md),
[PHASE7_MEMORY_STRINGS.md](PHASE7_MEMORY_STRINGS.md), [PHASE7_IO.md](PHASE7_IO.md)
and [PHASE7_EMULATOR_REFERENCE.md](PHASE7_EMULATOR_REFERENCE.md). Earlier
increment counts and pending inventories below are historical snapshots.

This document records the normalized Phase 3 transaction contract. It is not
a cycle-accurate implementation of the physical 80286 pins.

| Signal | Direction | Meaning |
| --- | --- | --- |
| `clk` | input | Synchronous core clock. |
| `reset` | input | Active-high synchronous state reset; inhibits bus output while asserted. |
| `ready` | input | Completes the outstanding bus request when asserted. |
| `address[23:0]` | output | Physical address. |
| `data_in[15:0]` | input | Read data sampled on an active request's READY edge. |
| `data_out[15:0]` | output | Write data positioned on the selected byte lanes. |
| `data_oe` | output | Data-drive enable; zero for the fetch request. |
| `bus_valid` | output | Request is active. |
| `bus_write` | output | Request is a write; zero for code fetch. |
| `bus_bhe_n` | output | Active-low upper-byte enable. |
| `bus_status[3:0]` | output | `0xD` CODE, `0x5` MEMR, `0x6` MEMW, `0xF` passive. |
| `bus_lock` | output | LOCK indication for an explicit/implicit locked operation or INTA/frame chain. |
| `hlda` | output | HOLD grant at a free physical-cycle boundary; no new CPU transaction is exposed while asserted. |

The interface is intentionally small and normalized. A later native wrapper may
translate it to pin polarity and the complete S0/S1/M/IO/COD/INTA contract.
The authoritative architectural requirements remain in `SPK286_SPEC.md`.

The debug-only `debug_bus_transaction[3:0]` metadata identifies the protected
logical activity associated with an active normalized request. It is zero when
no request is active and uses the following values: `1` descriptor, `2` TSS,
`3` gate, `4` frame/stack and `5` protected instruction fetch. The metadata is
held by the same functional request qualifiers while `READY` is low; it is
diagnostic evidence, not a historical Ts/Tc timing claim and does not alter
bus ownership or completion.

The first request after reset remains FFFFF0, now formed using the architectural
CS cache. Address, BHE and CODE status hold while `bus_valid && !ready`, even
if architectural state changes. READY when no request is active has no effect.
Response data is retained until its consumer accepts it.

For code fetch, an even word request uses both lanes (A0=0, BHE_n=0); an odd request returns one
byte from D15:8 (A0=1, BHE_n=0). A final even byte at the cached segment limit
uses only D7:0 (BHE_n=1). Inactive byte data is discarded. The next request is
word-aligned after an odd byte. No request crosses the cached segment limit;
the cursor retains exhaustion instead of wrapping. This does not yet generate
an architectural exception. Data words have a separate whole-width limit check.

On redirect, an outstanding request completes unchanged and its response is
discarded. The new stream starts afterward. RESET can abort the request. HOLD
is sampled only at a free boundary and is represented by `hlda`; it cannot
split a waiting/locked transaction. There is no Ts/Tc/Ti timing or cycle-match
claim in this contract. No bus-error/abort input is currently exposed by the
CPU-only boundary, so no bus-error behavior is implied by `ready` or by
`cancel_data`.

## Logical data words and arbitration

`spk286_biu` accepts a logical data operation on `data_request &&
data_request_ready`. Address, direction and write word are snapshotted on that
edge. It accepts at most one logical operation, retaining a completion under
`data_response_valid` until `data_response_ready`. Reads return the assembled
word; writes use the same completion handshake with no meaningful read data.
The operand service must not resubmit while its request is pending.

At a free physical-cycle boundary an accepted data request wins over code.
Once either client exposes a waiting bus cycle, ownership is retained until
READY, including when a data request arrives during a code wait. Address,
status, direction, BHE and driven data remain stable throughout the wait.
Only the owner sees completion. Code can resume while a completed data response
is held; ordinary data access never invalidates the instruction queue.

The internal code client holds `code_valid`, `code_address` and `code_bhe_n`
until `code_ready`. The fetch client's registered transaction metadata supplies
that guarantee even across redirects. The BIU retains the physical owner; it
does not duplicate the code client's metadata registers. The logical operand
caller likewise holds operation identity/context through completion, may pause
semantic acceptance, and must cancel before replacing an executing context.

| Logical word at N | First cycle | Second cycle |
| --- | --- | --- |
| N even | A=N, A0=0, BHE_n=0; D7:0=low, D15:8=high | None |
| N odd | A=N, A0=1, BHE_n=0; D15:8=low | A=N+1, A0=0, BHE_n=1; D7:0=high |

Each physical cycle independently waits for READY. The BIU retains data
ownership between the two cycles of an odd word. Memory commits only the
selected lanes on the READY edge. `data_oe` is asserted only for active writes.
The second address increments on the 24-bit physical path, without motherboard
A20 masking. The logical operand service checks `offset + 1 <= limit` using
17-bit arithmetic before submitting either cycle. A word at FFFF is blocked,
not split across a wrapped segment offset. Exception delivery is not implemented.

Pausing semantic execution leaves an accepted physical operation running and
holds its response. Redirect discards responses and drains an accepted complete
logical word, including remaining write bytes; reset aborts the transaction.
The remaining native pin-cycle fidelity work is tracked in the planned
[Phase 9 timing-fidelity plan](PHASE9_TIMING_FIDELITY.md).
This development cancellation contract cannot roll back external side effects
and is not a precise exception or interrupt interface.

## Phase 6 normalized acknowledgement and ownership

INTR is level sensitive; NMI is sampled on a low-to-high transition. Inputs are
synchronous to `clk`; an external native wrapper owns asynchronous synchronization
and physical setup/hold requirements. Testbench/default clients drive them low.
`hold_request` requests ownership at a free physical boundary; `hlda` indicates
a grant and prevents new CPU transactions.

BIU acknowledgement uses two separately READY-qualified transactions with
`bus_status=0`, `address=0`, `bus_bhe_n=1`, `bus_write=0`, `data_oe=0`. Only D7:0
of the second response supplies the vector. LOCK links both transactions and
the first complete stack push; HOLD cannot split that chain or an odd word.
Data/status/address/control remain stable throughout each READY wait. A canceled
acknowledgement drains both cycles and releases LOCK without constructing a frame.

Idle halt and shutdown use status 4 with address 2 and 0 respectively, with
`bus_valid=0`; they are indications rather than READY-qualified memory transfers.
An already owned transaction retains its metadata until completion. Broader native
pin-cycle timing remains deferred. These normalized transactions are not a claim
of historical 80286 cycle equivalence. See [event semantics](INTERRUPTS_EXCEPTIONS.md).

## Phase 7 byte and port-capable BIU increment

The logical BIU request adds `data_byte` and `data_io`. An accepted request
captures width, address space, direction and payload. A byte request uses one
selected lane and never splits. An odd word uses two ordered lane transfers.
The initial port address is zero-extended from 16 bits; an odd port word at FFFF
has its second physical transfer at 010000, retaining A16 carry observed in the
pinned ED/EF/6D/6F captures. Normalized I/O statuses are 9 (read) and A (write).
Memory, code and INTA retain their separate request and completion contracts.

`lock_request` holds bus ownership over an explicit LOCK instruction and
coexists with the inherited B-2 INTA/first-frame-word lock chain. HOLD never
splits a logical odd word or a locked RMW. READY and response backpressure
remain real dependencies. Cancellation drains accepted transactions and prevents
stale response reuse; it cannot undo an accepted external side effect.

The production CPU currently ties `data_io` low: port capability is verified at
the BIU boundary, while the IN/OUT CPU prototype remains isolated. Directed
lane/side-effect counters are transaction checks, not cycle-accurate Ts/Tc claims.

## Independently reviewed isolated Phase 7 candidate - 2026-09-09

The complete ordered candidate now drives scalar and string port operations
through this same BIU. Independent review found no second bus owner and verified
accepted-transfer retention, cancellation drain, odd-word ownership and LOCK/HOLD
separation. A verification gap was repaired with input data changing after each
accepted logical INS sample; both halves of an odd port word use one sample and
READY waits consume none. This is preserved candidate work, not production I/O
delivery or an E7 acquisition repair. Current gates and recovery are in
PHASE7_CLOSURE_20260909.md. Future consumer adaptation is specified only as
preparation in PHASE8_PREPARATION.md.
