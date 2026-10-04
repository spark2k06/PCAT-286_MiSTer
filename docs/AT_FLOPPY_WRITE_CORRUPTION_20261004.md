# AT floppy DMA write corruption

Date: 2026-10-04. Source baseline: `3bbb82c`. Status: **concrete RTL defect
identified by static review; correction and directed reproduction pending**.

The user reports that copying files to a floppy appears successful in DOS,
but after ejecting and remounting the image all directory entries disappear,
including files that existed before the copy. Reads work. The same operation
works in the PCXT-EGA core. The affected image path/geometry and its before
and after sector bytes have not been supplied.

The production PCAT DMA-to-FDC path consumes a memory response one fabric
clock after that response expires. It also derives its byte lane from the
DMA address after the controller has advanced it. In the current MiSTer
memory chain, the expired response is zero. This can fill written sectors
with zeros. It explains the reported behavior plausibly; no captured damaged
image or new guest/simulation run establishes the particular sectors altered
in the user's copy operation.

## Response and consumption sequence

The current source paths and their hashes are recorded in the
[audit manifest](evidence/at-floppy-write-audit-20261004/manifest.json).

| Moment | Memory and DMA | FDC |
| --- | --- | --- |
| Before response edge N | P03 `STATE_BYPASS` presents the correct 16-bit word with READY. DMA still selects the lane of the current address. | No completion ACK yet. |
| Edge N | DMA registers completion and advances the address/count. P03 and the memory port finish the response. | FIFO has not consumed the DMA byte yet. |
| Between N and N+1 | P03 is idle and its default read data is `0000h`. The live DMA lane usually refers to the next address. | Registered DMA completion drives `fdc_dma_ack`. |
| Edge N+1 | The original response is not retained at the machine/device boundary. | FIFO writes the current low byte of its input, which is zero in the present production chain. |

Relevant source points:

- `rtl/spk286_integration/spk286_at_sdram_read_buffer.sv:218` defaults
  `in_read_data` to zero. The BYPASS response at lines 294–307 passes valid
  backend data, then its completion at lines 443–452 returns to IDLE.
- `PCAT-286.sv:664` connects that P03 response to the common memory port.
  The port passes `backend_read_data` through to `dma_read_data` without a
  response payload register.
- `rtl/spk286_integration/spk286_at_dma.sv:186` derives the byte lane from
  `current_address_q`. Lines 353–385 register completion and update that
  address on the response edge. Auto-initialize can also change the lane
  on terminal count by restoring the base address.
- `rtl/spk286_integration/spk286_at_machine.sv:978` feeds the device input
  directly from `dma_memory_data_in`, normalized using that live lane.
- `rtl/spk286_integration/spk286_at_fdc.sv:139` uses registered completion
  as the FDC ACK. It feeds the current low input byte to the common FDC.
- `rtl/common/floppy.v:888` qualifies the FIFO write with ACK and uses
  `dma_readdata` at the FIFO's consuming edge.

Two contracts are missing at this boundary: retaining the data until the
consumer's ACK edge, and retaining the byte selection belonging to that
same completed transfer. Keeping only the backend word would still leave
the lane error for ordinary increment/decrement transfers.

Reading a floppy transfers bytes in the opposite direction, FDC to RAM;
it does not consume this delayed memory response. Its success is therefore
compatible with the write defect. A directory whose first entry becomes
zero is treated as having no further entries by DOS. A DOS directory buffer
can explain the initially successful DIR, but the user's actual caching
configuration and image contents have not been inspected.

## Contrast with PCXT EGA

The local reference is `D:/GitHub/PCXT-EGA_MiSTer_devel`. In
`rtl/KFPC-XT/HDL/Peripherals.sv:1639`, PCXT-EGA captures the data bus into
`write_to_fdd` while IOW is active. That register remains stable until the
falling-DACK ACK at line 1662; line 1684 connects it to `dma_readdata`.
PCAT's normalized integration has a different handshake and omitted the
equivalent payload retention.

The common `hps_ext.v` and `simple_fifo.v` are byte-identical between the
two inspected checkouts. The common floppy controller differs through the
optional separate I/O write address introduced for PCAT, but its sector,
DMA and FIFO tail is unchanged. The inspected CHS/LBA and write states do
not show a new write-specific sector-selection defect.

The local Main source `support/x86/x86.cpp:686` reads the FDC request and
its LBA, drains the FIFO at `F2FF`, and writes the received bytes to the image.
The shared `hps_ext` read strobe samples the data before advancing the FIFO
on the following fabric edge. No independent host persistence or FIFO
latency bug was established by this review. Host identity on the user's
MiSTer has not been independently verified.

## History

The delayed ACK and direct memory-to-device connection are present in the
full AT FDC integration, **`31168df`, 2026-09-12**. The byte normalization
uses the live DMA address there. P03's idle-zero response exists in its
initial implementation, **`92bf7e1`, 2026-09-14**.

The defect identified in source therefore predates both the retained FDC
I/O timing optimization (`35c6453`) and the new speed profiles (`31d595f`).
These source dates establish when the relevant code existed; they do not
identify the first failing hardware RBF without a historical reproduction.

## Existing coverage gap

| Existing evidence or bank | Actual scope |
| --- | --- |
| A5 device bank, `spk286_at_devices_tb.sv:868` | FDC READ DATA `66h`, DMA mode `46h`, host to FIFO to RAM, 512 bytes and IRQ/TC |
| Retained FDC DMA512 | The same A5 read-sector workload |
| Landmark cases 21 and 22 | Adapter initialization and sector reading |
| Phoenix POST | Controller initialization, READ ID and reading |
| Retained FDC write proof and bank | I/O command delivery, address/lane isolation, reset and FIFO state equivalence |
| Common memory port DMA example | DMA writes RAM, which is the opposite data direction |

`fdc_write_fifo` in these benches names a write to the command/data port;
it does not establish disk sector write correctness. Equivalence to the
old I/O path can preserve an existing DMA payload defect. No composed
RAM-to-FDC write-sector test with a disappearing READY response and image
remount verification was identified in the inspected coverage.

## Proposed correction and acceptance

Capture the response payload at the valid memory response edge, using the
byte lane of that transfer, and retain the normalized byte until the FDC
consumes its completion ACK. Preserve the existing completion pulse,
terminal count, channel ownership and read-sector path.

Sound Blaster uses the shared device input and captures memory data during
`dma_memory_data_valid`. A correction at the machine boundary must preserve
that valid-response behavior, or retain the FDC payload locally with an
explicit memory-data-valid input. Exact fitted resource cost is not measured.

Directed acceptance still to implement and run:

1. Execute WRITE DATA with channel-2 memory-to-I/O DMA, using a full 512-byte
   pattern whose neighboring bytes differ. Compare every host-bound byte.
2. Exercise even and odd start addresses, increment/decrement, terminal
   count and auto-initialize, plus responses with variable backend latency.
3. Withdraw or replace the backend data immediately after READY. The device
   must consume the retained old byte and no extra beat.
4. Read the written sector back and compare the complete bytes. Use the
   actual memory port and P03 path, not an always-stable abstract data bus.
5. On a disposable image containing existing files, copy a new file, eject
   and remount. Verify both previous files and the new file, their contents,
   FAT copies and untouched surrounding sectors.
6. Preserve existing sector reads and Sound Blaster DMA behavior. Bind any
   accepted correction and directed evidence to its source revision.

The original investigation was static. The following follow-up implements
and tests the correction; it does not change that historical evidence.

## Correction and directed validation

`spk286_at_machine.sv` now captures the normalized DMA memory response while
the current transfer and its response are valid. During the registered
memory-to-device completion it supplies that retained value. During the
valid-response phase it continues supplying the live value, as Sound Blaster
requires. Completion, channel selection, terminal count and DMA addressing
are unchanged.

The new `scripts/test_at_floppy_write.py` bank extracts the actual machine
adapter and its endpoint binding. It composes the production DMA controller,
serialized memory port, P03 code buffer, data buffer, posted-write buffer and
FDC/FIFO. The RAM responder withdraws its data immediately after READY.
Both Icarus and Verilator check:

- Five 512-byte WRITE DATA transfers, comparing all 2,560 host-bound bytes.
- Four 512-byte READ DATA readbacks, comparing all 2,048 destination bytes.
- Even/odd addresses, decrement, variable response stalls, terminal count,
  IRQ6, result bytes, management LBA and auto-initialize followed by another
  write without reprogramming the DMA channel.
- A negative control using the original machine connection from `7cb6e2`.
  It must fail on FIFO byte 0: expected `A7`, observed `00`.

Additional directed banks validate DMA registers in both simulators, Sound
Blaster DMA and machine detection, and the actual CPU/AT diagnostic in all
eight speed profiles. The simulation bus driver and Sound Blaster machine
runner have been updated to include the existing CPU profile interface.

The evidence is preserved in
`docs/evidence/at-floppy-write-fix-20261004`. The tests model physical SDRAM
and the host image peer; they do not run DOS COPY, MiSTer Main, an SD-card
filesystem or physical image remounting. Hardware COPY/remount confirmation
was the remaining check of the user's complete scenario. On 2026-10-04 the
user confirmed correct floppy operation with the new
[RBF](AT_FLOPPY_RBF_20261004.md). The reported corruption correction is
therefore accepted in hardware; individual write-protection combinations
remain covered by the directed simulation matrix.

## Follow-up static audit

The production `DMA_REGISTERED_MEMORY_COMPLETION=1` binding matches the new
bank. The ACK edge uses the final retained byte before the controller's
`dma_has_terminated` can introduce filler zeros. The completion interlock
keeps the active channel stable until the endpoint consumes it.

The local MiSTer Main `x86.cpp` floppy path sends 512 `spi_w16` operations,
each containing one useful byte, rather than 256 packed words. This matches
the management FIFO's low-eight-bit convention and the directed peer. Its
FIFO address `F2FF` and the bank's `F20F` decode to the same register. DMA RAM
reads bypass the code/data hits; RAM writes update matching data-buffer lanes
and invalidate matching code lines. No further concrete floppy defect was
identified by this audit.

One separate Sound Blaster coverage gap was identified: the production
endpoint first accepts when the memory response becomes valid, while DMA
acceptance and completion occur on separate edges. The memory port can retire
READY between those edges and later recapture the still-valid DMA request,
potentially reading the same RAM beat twice. This is a static hypothesis about
an existing integration cost, not a measured regression or corruption. The
SB component bank does not compose that memory-port handshake; the SB machine
bank checks detection with memory DMA disabled. A future composed SB playback
test should count backend reads per delivered byte before changing that path.
The floppy payload fix preserves the live-response phase used by Sound Blaster.
