# T286REF: short fixed-work 286 DOS timing reference

`T286REF.COM` measures three real-mode kernels with 8086 instructions and no FPU.
It is intended first for the original 286 implementation in 86Box at 6 MHz and
the profile labelled 12 MHz (actual 12.5 MHz), then for collaborators' physical
286 PCs at 6 and 12 MHz. It measures elapsed PIT ticks, not CPU pins or a
cycle-accurate EU/BIU trace. No measured MHz is inferred.

## Run

Use plain DOS without memory managers or TSRs, and identify the machine, BIOS,
memory configuration and speed separately with the CSV. The argument is a
literal nominal frequency label; it never changes the amount of work:

```dos
T286REF 6 > REF6.CSV
T286REF 12.5 > REF12.CSV
```

Use `12` for a physical machine set to 12 MHz. `12.5` identifies the native
86Box entry labelled `12`; it is not the physical collaborator's 12 MHz setting.
The tested executable is `build/p06-timing-reference-20261003/T286REF.COM`.
Its frozen copy and listing are retained in
[`docs/evidence/p06-timing-reference-20261003`](../../docs/evidence/p06-timing-reference-20261003).

Each case runs seven baseline and seven gross samples, always 256 iterations.
`R0` contains four register operations, `B0` contains a not-taken conditional
branch, a taken conditional branch and a taken short jump, and `M0` uses four
aligned word locations. The common baseline contains only the same outer
`LOOP`, dispatch, register setup and measurement overhead. Gross numbers remain
primary: the baseline is provided separately and is not silently subtracted.
AX/BX/CX/DX/DI are stored before the end latch with identical overhead for
baseline and gross samples, then checked outside the timed interval. R0 expects
`AX=09B4h,BX=5778h,CX=0,DX=9ABCh,DI=DEF0h`; B0 and every baseline expect
`AX=1234h,BX=5678h,CX=0,DX=9ABCh,DI=DEF0h`; M0 expects AX=68ACh with the other
baseline registers, and checks its final two written words. All samples and
min/median/max summaries are printed to DOS standard output for redirection.
DOS handle writes reject carry/error or a short write with exit code1, without
recursively attempting more output to the failed handle.
The signatures check workload integrity; they are not comprehensive instruction
correctness tests.

## Timer contract and qualification limit

This requires an AT-compatible **8254**, not an 8253. The program issues only
counter0 count/status read-back command `0xC2` to port `0x43`, then reads status,
count low and count high from `0x40`. It never programs a PIT mode/divisor, PIC
or IRQ vector. The short read-back sequence is atomic and restores its caller's
IF. Main polling occurs with IF enabled. The timed interval disables maskable
interrupts and restores IF before any DOS output. Entry with IF disabled is
rejected; that unsupported entry enables interrupts before calling DOS to
report/exit. All supported measurements preserve their incoming IF=1.

The observed mode must be binary mode2 or mode3, LSB/MSB, with null count clear
and stable status. Mode3 samples also require an even count. Intel's mode6/7
aliases are interpreted as mode2/3. The BIOS divisor is recorded as **65536,
`ASSUMED_STANDARD_BIOS`**. A probe observes two OUT transitions (mode3) or
reloads (mode2), and a raw zero or a raw count at least 65280. This rejects
clearly incompatible settings; **a latch does not reveal the reload register**,
so the probe cannot certify an exact divisor of 65536. Every CSV therefore
retains `timer_qualification,NOT_CALIBRATED`. A reviewer must establish the BIOS
timer configuration before treating normalized ticks as calibrated timing.

Conditional on the standard divisor:

- Mode2 phase is `(-count) modulo 65536`.
- Even mode3 phase is `((-count) modulo 65536)/2`, plus 32768 when OUT is low.
  Its count decreases by two and reloads at both OUT transitions; a raw count
  difference alone would overstate elapsed ticks by two.

The start phase must be 8192 through 16383, away from IRQ0 and mode3 reloads.
The endpoint must advance by at most 10000 ticks (about 8.38 ms at the nominal
1.193182 MHz PIT input) and must still have OUT high in mode3. The kernels are
short fixed work intended to stay well below that at 6 MHz. Failing status,
probe, window or kernel-result checks produces a `REJECT_*` result and a nonzero DOS exit
code. No adaptive loop calibration hides work differences between frequencies.

Endpoint checks alone cannot detect a pathological CPU stall lasting one or
more complete timer periods. They also do not certify an exact PIT crystal,
SMI/NMI effects, bus READY behavior or interrupt delivery latency. Running on
an unqualified timer or a machine with exceptionally long waits cannot be
accepted as calibrated evidence. These are short latency kernels, not an IRQ
benchmark or proof that every BIOS tick is preserved under arbitrary stalls.

## CSV

`meta` rows record the nominal label, timer assumption, observed mode/status,
probe maximum/zero observation, program segment and aligned-word offset. There
are no inferred CPU cycle counts or MHz. Successful completion is
`result,PASS_RAW_FIXED_WORK` and **does not change `NOT_CALIBRATED`**.

`sample` fields are:

```text
case,kind,rep,loops,status_start,count_start,out_start,phase_start,
status_end,count_end,out_end,phase_end,raw_delta,ticks,
result_ax,result_bx,result_cx,result_dx,result_di
```

`raw_delta` is `(count_start-count_end) modulo 65536`. `ticks` uses the
conditional phase conversion above. `summary` fields are:

```text
case,kind,loops,min_ticks,median_ticks,max_ticks
```

## Build

From WSL/Linux with NASM and Python3:

```sh
python3 SW/CPUTIME/build_t286ref.py
```

The default output is `build/p06-timing-reference-20261003/T286REF.COM`, with a
NASM listing and SHA256 receipt. The builder assembles twice and verifies byte
identity. `cpu 8086` makes NASM reject later-generation instructions. It does
not run the program or certify timing. The separate native 86Box runner checks
the actual CPU dispatch, wait-state configuration and memory/prefetch globals;
`cpu_waitstates=0` means automatic memory timing, not zero instruction cycles.

Primary timer reference: Intel 8254 datasheet, order 231164-005, read-back
operation and mode3 even-count operation
([Intel datasheet PDF](https://www.scs.stanford.edu/23wi-cs212/pintos/specs/8254.pdf)).
P06/P12 define the interpretation and evidence required beyond these DOS
measurements.

## Validation and initial reference

[Native results](../../docs/optimization/P06_NATIVE_REFERENCE_RESULTS_20261003.md)
retain the two completed original-286 controls, at actual 6 and 12.5 MHz.
Each passed the guest exit/signature checks and all 42 samples/six summaries;
the final emulator process also exited with code 0. Both observed PIT mode 2.
Mode 3 has host arithmetic, synthetic CSV and source-review coverage here,
not an executed DOS mode-3 control. Physical 6/12 MHz results remain pending.

Validate a returned CSV on the host:

```sh
python3 SW/CPUTIME/validate_t286ref.py REF6.CSV --expected-nominal 6
python3 SW/CPUTIME/check_t286ref_math.py
python3 SW/CPUTIME/test_t286ref_parser.py --output build/t286ref-parser-check
```

The last command uses independent synthetic mode-2/mode-3 fixtures and thirteen
negative controls; it does not run the DOS binary. Use a fresh output directory.

The Linux runner requires Python 3.11+, pyfatfs, an unstripped matching native
86Box executable, ROMs, a DOS FAT disk and a profile directory containing
`86box.cfg` and `nvr/`. It clones inputs into a fresh output directory and checks
the actual native `exec386_2386` dispatcher and CPU/memory timing globals.
Its process-memory layout is specific to the inspected local Linux64 build;
it is not a generic runner for arbitrary 86Box releases.

```sh
python3 SW/CPUTIME/run_native_reference.py \
  --output build/t286ref-native6-repeat \
  --disk /path/to/source-dos.vhd --profile /path/to/calibrated-native6-profile \
  --program build/p06-timing-reference-20261003/T286REF.COM \
  --exe /path/to/86Box-native --roms /path/to/86box/roms --hz 6000000
```

For the other native control use a separately calibrated 12.5 MHz profile,
`--hz 12500000` and a different fresh output directory. MRBIOS may require a
speed-change acknowledgment and F10 to record CMOS; the final references used
CMOS already calibrated by preceding runs. No periodic screenshots were used
in the accepted final runs. Initial host teardown failures are retained as
failed runs in the evidence, independently of valid guest CSV output.
