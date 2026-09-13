# AT XT-IDE detection regression

The AT profile could load the XTIDE option ROM and show a mounted VHD in the
OSD, but the BIOS reported `Master at 300h: not found`. The same media worked
with the XT-derived profile.

## Cause and fix

`spk286_at_machine.is_a5_io_port()` did not include the XT-IDE window.
Consequently the machine's unmapped-I/O sink completed reads with `FFh` and
discarded writes before they reached `spk286_at_device_router`. The IDE engine
could still be configured through the independent HPS management interface.

The fix forwards `300h–30Fh`, except the unmapped `309h` hole, to the existing
device router. This includes the `308h` high-byte latch and `30Eh` alternate
status/device-control port. It applies to `PCAT-286_AT_FAST.qsf` and the other
AT profile through the existing integration QIP; no CPU pacing change is needed.

## Reproduction and coverage

Run `bash scripts/test_at_xtide_machine.sh`. Set `AT_XTIDE_VERILATOR=1` to also
run Verilator. The test uses the production AT bridge, machine decoder, router,
IDE engine and `hps_ext`. Only the CPU instruction engine is replaced with a
bus driver; the Quartus RAM primitive uses the simulation model.

Against `94fd21d`, after configuring a present master and a ready status through
`hps_ext`, the CPU-side check failed:

```text
CPU port 0307: expected 40, got ff (sink_reads=1)
```

With the decoder fix the regression checks:

- IDE reset requests and register access through the HPS extension transport.
- Status and detection-register access from the CPU bus, including odd byte lanes.
- Software reset, delayed host responses and IRQ clearing by normal/alternate status.
- Full 256-word IDENTIFY and sector-read responses using `300h` and `308h`.
- A full 256-word sector write, checked through the host FIFO interface.
- No duplicate commands and no decoding of `2FFh`, `309h` or `310h`.

The AT bus clock is 50 MHz. Each simulation runs with zero extra CPU idle
cycles and with 32 extra cycles between accesses. Both cases pass in Icarus
and Verilator with the decoder fix. Host FIFO words are spaced
to allow the registered management read pipeline to settle; this is not a test
of physical ARM/GPIO timing. Synthetic host payloads stand in for image contents.

The earlier `test_a5_at_devices.sh` instantiated the device router directly,
so it could not detect a missing entry in the machine's upstream decoder.
This new regression covers that previously untested boundary. It does not
execute the BIOS or prove booting from physical MiSTer hardware; the rebuilt
AT_FAST RBF still needs that final hardware check.
