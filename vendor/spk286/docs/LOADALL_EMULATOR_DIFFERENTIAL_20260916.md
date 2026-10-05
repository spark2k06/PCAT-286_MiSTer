# 80286 LOADALL emulator differential — 2026-09-16

Status: **bounded functional differential recorded; not a silicon or timing
claim**.

This experiment addresses the Milestone 7 Gate 5 requirement to compare the
observable LOADALL behavior with 86Box and one other emulator. It executes the
original `opLOADALL` functions from the local 86Box and PCem source trees in a
small generated C host. The host provides controlled memory, records every
logical read, and exposes the architectural state and general-protection
callback. It does not run a full machine, emulate prefetch or descriptor
validation, or copy third-party code into SPK286.

## Reproduction

The Windows checkout has no native C compiler in the normal PATH, while the
configured Ubuntu WSL instance has `cc`. From the SPK286 root:

```text
wsl.exe python3 /mnt/d/GitHub/SPK286/research/loadall_emulator_differential.py \
  --source-86box /mnt/d/GitHub/86Box_dev \
  --source-pcem /mnt/d/GitHub/pcem \
  --build-dir /mnt/d/GitHub/SPK286/build/loadall-emulator-differential-N \
  --cc cc
```

The build directory must be new or empty. It receives the generated host,
compiler log, raw JSONL observations, and `summary.json`; it is ignored by Git.
The checked-in driver is
`research/loadall_emulator_differential.py`.

Observed run: `build/loadall-emulator-differential-2/summary.json`.

## Input provenance

| Reference | Revision/status | Files used | SHA-256 |
| --- | --- | --- | --- |
| 86Box | `de4a54c96fbdb9b3a233703646f354e7b2f2b8ff`; dirty only in unrelated `src/disk/hdc_xtide.c` | `src/cpu/x86_ops_misc.h`, `src/cpu/386_ops.h` | `7cca59f327985989ef2b3ca5e530dfea2ee0d012261e6d4023bf9bf69b28e441`, `a4b1a63b67bfc7c96963f92e404989d8525e56fd7f222e2a98e059d4a02d9527` |
| PCem | `3a9b8b704b81c77a4e072e27448766b8056b585a`; clean | `includes/private/cpu/x86_ops_misc.h`, `includes/private/cpu/386_ops.h` | `eb4ef7e813c0b872ff2dd9d20600fda573c4acaebba6d23ec7a7982e813176ae`, `d7ce794fff24a029a291422ec7c5824f8636a4155ea192fdffe0b62703c101d5` |

Both repositories remain outside the SPK286 source tree and were not modified.
The two emulators share a very similar implementation for this instruction;
their agreement is therefore two compatible implementation observations, not
two independent hardware measurements.

## Classification result

The first row of each 286 `0F` opcode table was inspected by the driver:

| Encoding | 86Box 286 table | PCem 286 table | SPK286 |
| --- | --- | --- | --- |
| `0F 04` | `ILLEGAL` | `ILLEGAL` | invalid-opcode path |
| `0F 05` | `opLOADALL` | `opLOADALL` | dedicated 80286 LOADALL |
| `0F 07` | `ILLEGAL` | `ILLEGAL` | invalid-opcode path; no 386 behavior |

This independently confirms the classification already selected from the
80286 evidence review. It does not resolve the historical Intel note's
`0F04H`/`0F05H` textual inconsistency.

## Functional observations

The harness uses one deterministic 51-word image at physical `000800h` and
executes these cases in both references:

| Case | 86Box vs PCem | Observable result |
| --- | --- | --- |
| Real mode, ordinary FLAGS | Agree | 47 logical image reads; complete register, selector, cache and table state agrees with the independent image model |
| Real mode, image FLAGS=`FFFFh` | Agree | Both publish `(image FLAGS & FFD5h) | 0002h = FFD7h` |
| Protected mode, CPL=0, image MSW PE=1 | Agree | Complete LOADALL state is published; existing PE remains set |
| Protected mode, CPL=1 | Agree | `#GP(0)` before any image read |
| Protected mode, CPL=0, image MSW PE=0 | Agree | Both complete; effective MSW remains protected because they preserve the old PE bit |

The source functions expose 47 logical reads because several six-byte cache
records use byte reads for the high base/access fields. SPK286 intentionally
fetches the image as 51 little-endian word bus transactions. Those traces are
compared at their common logical image-field boundary, not as if emulator
host-call granularity were a physical bus waveform.

## Differences against the current SPK286 contract

The differential is deliberately reported as
`PASS_WITH_RECORDED_DIFFERENCES`; the discrepancies are not hidden by selecting
the majority implementation.

1. **Reserved FLAGS:** 86Box and PCem normalize the image with
   `(FLAGS & FFD5h) | 0002h`. The current SPK286 service publishes the image
   word unchanged (`FFFFh` in this case). Existing Titus/integration images use
   `0202h`, so this does not affect the demonstrated game path. The 80286
   primary evidence must decide whether SPK286 should adopt the normalization.
2. **Protected image clearing PE:** 86Box and PCem read the complete image and
   preserve the current PE bit through `(old MSW & 1) | image MSW`. The current
   SPK286 service rejects a protected-mode image whose MSW word clears PE, after
   reading the first four words and before committing state. This is an
   explicit SPK286 safety/atomicity choice pending Intel or silicon evidence;
   it is not changed by this experiment.

The current source-level SPK286 comparison agrees with both references for the
ordinary real-mode image, protected CPL=0 with PE retained, and CPL!=0 fault
boundary. It records the two cases above as unresolved behavior questions.

## Evidence boundary

The experiment does not establish:

- exact Intel/Harris/AMD 80286 stepping behavior;
- physical bus cycle count, READY timing, HOLD/HLDA, interrupt sampling or
  partial commits;
- full-machine 86Box/PCem BIOS/device interaction;
- `LOADALLD`, `STOREALL`, ICE/test forms or any 386 semantics.

The results close the bounded emulator-differential part of Gate 5. The
remaining milestone gates are primary-source/silicon adjudication of the
recorded differences and the separately scoped historical timing and hardware
evidence.
