# Protected-mode entry CPL correction — 2026-09-29

## Failure observed with Windows 3.1

The SPK286 backend in 86Box recorded a shutdown while entering protected mode:

```text
CS:IP at fault = 292E:0AE2, PE=1, #GP error=0078
CS cache = base 0292E0, limit FFFF
GDTR = 110800:011F
GDT[0078] = FFFF 92E0 9A02 0000
```

The destination is valid present, nonconforming DPL0 code, with base `0292E0`
and limit `FFFF`. The outgoing CS still contains its real-mode value. The
executor nevertheless received `CS[1:0]` (`2`) as CPL and rejected the jump
to DPL0 with `#GP(0078)`. Delivery of that exception then attempted an
unnecessary ring transition using a TSS which had not yet been initialized,
ending in shutdown. The log's lookup of old CS `292E` against the LDT is not
evidence that Windows supplied a bad protected CS descriptor: CS had not yet
been reloaded after LMSW.

## Architectural basis and change

- Intel 210498-005, section 10.4, describes initial protection bits of zero
  and the real-mode and protected-mode initialization sequences. Section
  10.4.2 permits privileged initialization after setting PE, before the first
  protected control transfer. The local reference is
  `build/references/intel-286-programmer.pdf` (text copy in the same directory).
- The local 86Box reference derives CPL from its internal CS access state
  (`src/cpu/cpu.h`), rather than interpreting an arbitrary real-mode CS value
  as a protected selector.
- SPK286 now keeps CPL zero while CS still has a real-mode cache. After a
  protected CS load, it continues using the normalized CS.RPL, preserving
  the existing conforming-code and privilege-transition semantics. LOADALL
  and the micro-executor consume the same CPL signal. Protected LOADALL
  contexts retain their existing privilege behavior.

The change is at the CPU integration boundary in `rtl/spk286.sv`; no address,
selector value, BIOS, operating system, or clock frequency is special-cased.

## Reproducer and validation

`spk286_protected_entry_tb` executes LGDT/LMSW from all eight combinations of
the low three real-mode CS bits, plus the captured `292E` value. It exercises
an immediate far jump, CLTS before the jump, and protected LOADALL before any
protected CS reload. Each case runs under all three timing policies with
READY stalls. It checks preservation of the old CS/cache at LMSW and successful
DPL0 code/stack execution without exception requests.

- Before the functional change: Icarus reports **63 failures / 81 cases**.
  Every nonzero low-two-bit CS value fails; zero values succeed.
- After the change: **162 checks / 81 cases pass in both Verilator and Icarus**.
- Verilator lint and generated microcode consistency pass.
- Existing protected-system coverage: **538 checks pass in both simulators**,
  including conforming code and protected control transfers.
- Existing protected LOADALL coverage: CPL1 still receives `#GP(0)` in both
  simulators, with the expected saved state and error frame.
- Existing CLTS/system privilege coverage: **13 checks pass in both simulators**.
- Protected event outer-level coverage: **6 checks pass in both simulators**.
- Task-gate event privilege coverage: **448 checks / 144 cases pass in both
  simulators**.
- The same new entry test passes all 81 cases in both simulators against the
  downstream PCAT vendor copy used by 86Box. Its separate fetch-wrap change
  is preserved.
- Reset/first-fetch smoke passes in both simulators.

### Checkpoint validation scope

On 2026-09-29 the user explicitly requested committing with the completed
directed checks and stopping the extensive regression. `make regression` was
started in SPK286 and the downstream vendor tree, then cancelled as requested.
No failure had been reported when it was stopped, but neither full regression
is recorded as passed. The synthesis stage of those runs was not reached.
Partial logs are retained as `build/cpl-commit-regression.log` in each tree.

Build logs are under `build/protected-entry-*.log` and `build/entry-*.log`.

## User-observed integration result

The subsequent user run on 2026-09-29 no longer restarted at the initial
Windows protected-mode entry. Live samples confirmed that Windows had loaded
its protected code, LDT and TSS and executed beyond that transition.

The complete Windows boot is still failing later: a repeated `#GP(0)` in the
MS-DOS Extender's error-reporting path leaves the display black. A captured
error buffer identifies `0053:1E4D`; this is a secondary failure, and the first
exception that led there remains under investigation. The 86Box bridge now
logs fault entries before handler delivery to capture that earlier cause.

This checkpoint records the corrected CPL transition and the observed progress,
without claiming a successful Windows desktop boot or physical 80286 validation.
