# H16: null LDTR selectors and visible readback

Date: 2026-10-01. Baseline SPK286 `fcc67f0`, PCAT `4f92ca0`.
Contract recorded before the implementation and directed executable tests.

## Rule and evidence

Intel 80286/80287 PRM 210498-005 (1987), 6.6.2 describes the complete 16-bit
visible LDTR selector, its INDEX/TI/RPL fields, and LLDT/SLDT readback. Section
7.2.3 defines a null selector by INDEX=0 and TI=0, independently of RPL.
Section 10.3 explicitly permits an absent LDT in a task; LLDT on B-66 marks a
null LDT invalid. SWITCH_TASKS B-12/B-13 loads the incoming visible selector
before descriptor validation. These rules are combined here to apply the same
null classification to explicit and task-loaded LDTR. The task-initialization
example's `0000` is not a separate definition that makes RPL part of INDEX.

[Primary manual](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf),
SHA-256 `ad487ba99b48cd9f61b14c0fe912a04c7cdb4c7c14a18419aa9faf62d8962460`.
This is a specification-derived rule; no physical protected task-load capture
for `0001..0003` is available. The manual's general field definition and its
task example are recorded distinctly rather than claiming an explicit four-value
task-switch example or a silicon observation.

| Selector | LLDT | Task-loaded LDTR | Descriptor access |
|---|---|---|---|
| 0000..0003 | Preserve raw visible selector; invalid LDT | Same | No GDT entry-zero read |
| 0004..0007 | #GP(0004), old LDTR preserved | #TS(0004), incoming state already published | No LDT descriptor read |
| Valid GDT LDT descriptor | Load selector/cache | Load selector/cache | Validate selected GDT descriptor |

An invalid/null LDT cannot supply a task CS or SS with TI=1. Such a segment
load raises #TS with that segment selector's normalized error code, retaining
H15's completed earlier stages. LDT entry zero with a valid LDTR is usable;
the selector `0004` is not a null segment selector.

LLDT's null path must not canonicalize the visible selector to zero. SLDT
stores the supplied selector, including RPL. Native 86Box preserves that raw
selector, but its LLDT and 16-bit task routines also read a descriptor
unconditionally and omit relevant selector checks. Native completion alone
cannot establish no-fetch or exception conformance for this story.

## Validation recipe recorded before implementation

Execute original reset programs with all four task-entry forms and LDTR
`0000..0007`; use valid GDT segments, null-LDT CS/SS references, valid-LDT
entry-zero positive controls, and LLDT/SLDT cases. Inspect descriptor bus reads,
raw selector, hidden validity, first exception and task publication. Run baseline
and Max timing policies with READY stalls in both simulators and the PCAT vendor.
Retain private native/SPK 86Box observations and isolated mutation controls.
No full regression, OS boot or FPGA timing certification is implied.

## Reproduction and implementation

The pre-change executable program for incoming LDTR `0001` raises #TS during
the LDT stage, instead of running with a disabled LDT and valid global segments.
An independent explicit `LLDT 0001` / `SLDT` program reads back `0000` before
the correction. These failures are retained in the before logs.

The task null predicate now tests INDEX/TI together (`selector[15:2]==0`),
and explicit LLDT commits the raw operand into the visible selector even when
the cache is invalid. Null-task cache fields remain disabled, and the valid-LDT
entry-zero controls retain TI=1 segment semantics. No GDT entry-zero descriptor
fetch is added to either null path.

The same matrix exposed unnormalized RPL bits in the composite task service's
raw LDTR error. The CPU executor already removed these bits at its boundary;
this change aligns the service's own contract and directed tests. It is not
reported as a newly different architectural CPU error code. TI is retained,
RPL is removed, and existing EXT propagation remains at the caller.

Private 86Box runs demonstrate:

| Program | Native 286 | SPK286 before | SPK286 after |
|---|---|---|---|
| Incoming null LDTR 0001, global task segments | Task runs, SLDT=0001 | Unexpected exception task | Task runs, SLDT=0001 |
| LLDT 0001 / SLDT checkpoint | 0001 | 0000 | 0001 |
| Incoming illegal LDTR.TI 0005 | Incorrectly accepts it | #TS | #TS |
| Explicit LLDT.TI 0005 | Incorrectly accepts it | #GP(0004), old LDT | Same |

The native path's unconditional entry-zero loads and omitted TI validation remain
reference limitations. Saved complete records also retain other differences,
including native task-CALL stack handling; no whole-task equivalence is claimed.
The no-fetch acceptance checks come from executable RTL bus observations,
with valid LDT entry-zero positive controls to prove the observer sees those reads.

The shared reset source gains parameterized H16 cases. Assembling all 80 default
H15 cases proves their ROM bytes identical to H15's committed receipt. No disk,
production profile, CPU board port or microcode is modified.

## Directed closure

H16 is closed for this field/classification/readback scope. The
[receipt](REGRESSION_H16_NULL_LDTR_20261001.json) contains source/ROM/log hashes,
before failures, raw native/SPK observations and the evidence limits above.

- Both simulators pass 80 ROM programs in baseline and Max modes: 160 executions
  and 1,336 checks each, with READY stalls, all four task entries, null/TI values,
  missing-LDT CS/SS references and valid LDT entry-zero controls.
- The composite service passes 102 checks, including non-null LDTR RPL and absent
  descriptor errors. Affected system-access (2,112 cases / 9,144 checks), protected
  system, task-LDT and nested-IRET banks pass in both simulators.
- PCAT with P01/P02/P05 passes the same H16, service, system-access and task-LDT
  banks in both simulators. Its fetch-wrap customization is preserved.
- Microcode check/audit, Verilator lint, portable mapped Yosys synthesis and 352
  Python tests pass. All four isolated mutants are rejected, with separate
  pristine CPU and service controls passing.
- All 15,000 real-mode 9A/EA/CF physical captures pass without skips. There is
  no physical protected LLDT/null-task capture in this milestone.
- Eight private ROM cases complete in both native/SPK 86Box before and after.
  The production SPK executable is rebuilt from the vendor with P02/P05; test
  processes are closed. No new operating-system boot or FPGA run is claimed.

The first error-RPL mutation survived the CPU observer because the executor's
existing normalization masked the service defect. The final audit uses the
direct service observer for that mutation and rejects it. This initial failed
audit is retained, not counted as a successful run.

The full project regression remains a separate task. H02/H05/H17/H19/H20 and
the downstream PERF01 measurement remain pending; no NT, LOCK, LSL or event-order
policy is changed here. Work stops after the H16 commits at the user's request.
