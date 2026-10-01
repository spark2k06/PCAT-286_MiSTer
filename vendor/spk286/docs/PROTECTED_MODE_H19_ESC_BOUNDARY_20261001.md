# H19: ESC first-word boundary validation

Date: 2026-10-01. Baseline SPK286 `4452d14`, PCAT `eda6218`.

## Contract and evidence

ESC D8..DF must validate the first word of a memory operand after the CPU's
EM/TS check and address decoding, including when no numeric processor is
connected. Register forms need no segment access. No numeric execution or
operand bus transfer is introduced.

Intel 80286/80287 PRM 210498-005 (1987), sections 7.4 and 9.6.3, distinguish
the CPU's first-word check from an NPX overrun on later words (#9). The pinned
SingleStepTests/80286 corpus `37c73caf53dcd22d3dd369ff09305d13d117a4fe`
supplies 33 independent real-mode D8 captures with #GP at offset FFFF.
All failed before and after H18; this change makes all 33 pass without
exclusions or changes to expected state, masks or exception frames.

Native 86Box `b8ec886a8ae72b073d40d8c9bf4c808b0ead4b7a`,
`src/cpu/x87_ops.h::op_nofpu_a16`, decodes the address without validating
this boundary. Its no-FPU result is insufficient as the oracle here.

## Implementation

The ESC microprogram is now `CHECK_NPX_ESC; DECODE_MODRM; CHECK_RM16; END`.
The existing pure word check validates segment validity, readability and
normal/expand-down limits without requesting a memory read or write. #NM
remains ahead of ModR/M consumption and every operand predicate. A protected
SS failure gives #SS(0), other protected operand failures #GP(0), and the
real-mode FFFF crossing gives #GP with no error word. The first prefix is
saved; the failing ESC does not retire or change GPRs/FLAGS/selectors.

Microcode format 27 adds one ROM word (123 entries, 743 words). Historical
format-26 parsing and its frozen H18 fixture remain supported. The independent
format-27 fixture relocates the format-26 image by one word; rejection tests
cover missing, misplaced, duplicated and effectful substitutions. No new
functional RTL operation or historical timing policy is added.

## Directed validation

- Both simulators: 3,849 ESC boundary/lifecycle cases, 24,759 assertions each.
  All D8..DF, real mode and CPL0..3, ES/CS/SS/DS overrides, normal and expand-down
  limits, empty DS/ES caches, read-only data, execute-only code, register forms,
  #NM priority, pause/resume and cancellation. Baseline and Max policies.
- The null-cache fixture restores selector zero **and an empty hidden cache**.
  LOADALL with selector zero but AR=93 is a distinct undocumented cache state
  and does not stand in for a normally loaded null segment.
- Both simulators: inherited H18 matrix, 9,079 cases / 58,615 assertions each;
  seven affected instruction, operand, stack, compiler-ROM and fault banks.
- Physical D8: 5,000/5,000; WAIT: 5,000/5,000. No prefix or exception skips.
  Upstream parser and independent wire exception/mask checks agree for all
  10,000 identities; all 33 formerly failing identities are preserved.
- Python/compiler tests, deterministic regeneration, independent ROM audit,
  lint, reset smokes, state vectors and portable mapped synthesis.
- Exact PCAT vendor: both simulators for the new bank, H18, legacy ESC,
  operand lifecycle and stack control, with P01/P02/P05 enabled; lint/audit.
  PCAT's real-mode fetch wrap changes remain intact.

See [machine-readable receipt](REGRESSION_H19_ESC_BOUNDARY_20261001.json).
This is a directed regression of the affected behavior, not a full project
regression or a new OS/hardware run. H19's remaining multiword/restart matrix
stays open. External NPX transfers and #9 delivery are separately scoped.

## Reproduction

From the SPK286 root under WSL:

```sh
export SPK286_BUILD_DIR=$PWD/build/h19-20261001 SPK286_BUILD_JOBS=4
bash scripts/test_units.sh both spk286_esc_boundaries
bash scripts/test_units.sh both spk286_npx_traps
make state-smoke microcode-test microcode-audit lint
python3 -m tools.run_singlestep --opcode D8 --opcode 9B --full --include-prefixes --include-exceptions
```

Primary source: [Intel 286 PRM](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf).
