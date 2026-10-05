# LOADALL hardware probe

`LOADALL.COM` is a small DOS program for a real 80286. It is intended to
resolve the remaining hardware questions in the SPK286 Milestone 7 evidence,
not to benchmark an emulator.

The program stays in real mode and writes the result to the screen only. It
does not create or depend on a log file. It installs temporary handlers for
invalid opcode (`INT 06h`) and general protection (`INT 0Dh`), restores them
before returning to DOS, and restores the 102 bytes it temporarily uses at
physical `000800h`.

The exception vectors are saved and installed directly through the real-mode
interrupt vector table; DOS vector-management calls are not used in this
critical path.

Screen lines are emitted through BIOS `INT 10h`, not DOS handle `1`, so a
failure in DOS console/file services cannot hide the diagnostic phase.

The probe deliberately does not execute `STR` or `SLDT` while collecting the
initial state. Intel documents both instructions as invalid in 80286
real-address mode, so `TR=0000` and `LDTR=0000` are recorded under the stated
precondition of clean real-mode DOS. Testing those instructions would require a
separate protected-mode transition and is outside this non-resetting probe.

## What it tests

1. `0F 04`: whether the CPU raises `#UD` or treats the opcode as LOADALL. If
   it is accepted, the program supplies a controlled image and records the
   successful return.
2. `0F 05`: the same controlled real-mode LOADALL image.
3. Resulting FLAGS after an image containing reserved high bits (`F002h`).
4. A hidden DS cache base of `100000h`, when A20 is enabled and RAM at
   physical `102000h` is writable. The test uses different markers at the
   low and high aliases, so it can distinguish a loaded hidden base from the
   ordinary real-mode DS base.

It does not enter protected mode, execute `LOADALLD`, or attempt to enable A20.
If A20 or extended RAM is unavailable, the hidden-cache test is reported as
skipped; the opcode and FLAGS tests still run.

## How to run

Use clean real-mode DOS on the 286: no EMM386, Windows, DPMI, or other
protected-mode manager. Copy `LOADALL.COM` to a writable DOS directory and run:

```text
LOADALL
```

Wait for `Probe complete`. Do not press keys or generate interrupts while it is
running. If the machine resets, hangs, or shows a debug trap, photograph the
screen showing the last visible `Phase:` line and return that image. The phase
lines are deliberately emitted immediately before the sensitive operation so
the last one identifies the point of failure.

Please return all of the following:

- exact CPU marking and board/model;
- DOS version and whether A20 was already enabled;
- a photograph of the final screen, or the last screen before a hang/reset;
- whether the program returned normally to DOS.

The result is evidence for a particular physical CPU/revision. It must not be
generalized to all 80286-compatible chips without repeating the probe.

## Build

From the repository root, with NASM 2.16 or newer:

```sh
python3 -m research.loadall_probe.build --output build/loadall-probe
```

The reproducible output is `build/loadall-probe/LOADALL.COM`; the hand-off copy
is kept under `research/loadall_probe/release/LOADALL.COM` with a SHA-256
manifest.
