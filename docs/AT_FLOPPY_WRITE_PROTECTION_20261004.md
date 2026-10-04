# Floppy write protection — OSD and host qualification

## Existing production support

The production OSD already exposes one **Write Protect** entry immediately
below **Floppy A:** and **Floppy B:**. Its choices are **None**, **A:**, **B:**
and **A: & B:**. No duplicate control or new status bits are required.

`OJK` uses status bits 19 and 20, forwarded as `hps_status[20:19]` through the
machine, device router and storage adapter to the FDC's two-bit `wp` input.
The common controller combines it with the mounted image's host readonly
mask using `wp_sys | wp`. Selecting **None** therefore does not override
an image mounted readonly by the host.

## Directed tests

Run `scripts/test_at_floppy_write_protect.sh` or the Python runner with a
fresh `--output` directory under WSL. Both Icarus and Verilator are required.
The receipt checks the production OSD entry, bit mapping and every forwarding
boundary, as well as source hashes before and after simulation.

The matrix covers all four OSD masks × all four host readonly masks × both
drives: 32 cases per simulator.

- All 32 cases check Sense Drive Status and a complete 512-byte READ DATA.
- All 24 protected cases reject WRITE DATA and FORMAT, report write
  protection and issue no DMA or host write request.
- All eight unprotected cases compare the complete WRITE DATA payload and
  result, and verify the first permitted FORMAT sector's filler.
- Protection of one drive allows writing the other when its host mask also
  permits it.

Evidence is preserved in `docs/evidence/at-floppy-write-protect-20261004`.
The bank uses the actual FDC wrapper/controller/FIFO with explicit DMA and
management peers. It does not simulate CPU instructions, SDRAM, MiSTer Main
or physical SD-card persistence. Permitted FORMAT tests stop after the first
sector; they do not claim complete disk-format coverage.

This milestone qualifies and documents the existing feature in a separate
commit. It adds regression coverage without duplicating working RTL.

## Hardware check

Use a disposable image. With **None**, copy a file, eject/remount and verify
both previous files and the new file's contents. Select protection for that
drive and repeat COPY: DOS should report a write-protected disk and the image
must remain unchanged. Repeat for the other drive and **A: & B:**. Reads and
directory listings must remain available in every protection setting.
