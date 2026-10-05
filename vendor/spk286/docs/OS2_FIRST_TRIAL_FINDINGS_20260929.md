# OS/2 1.3: first autonomous trial after the outer-stack fix

Date: 2026-09-29. **Findings only; no implementation changes.**

## Result and scope

One boot with the existing SPK286 executable and a copy of the user's OS/2
disk reached a new TRAP 000D. It passed the previous SGDT and RETF failures.
The important first new exception is **#GP(0210) at 13A3:33BC, POP ES**.
The banner's **0228:35C7** is a second exception in the kernel's first-fault
handling path. Successful OS/2 startup is still unverified.

This run provides workload evidence for two separate defects:

1. Missing DS/ES invalidation when returning to a less privileged level:
   [global review H08](PROTECTED_MODE_GLOBAL_REVIEW_20260929.md#h08--dses-invalidation-after-outer-return-s--r-p0).
2. A failed protected POP segment leaves SP advanced:
   [global review H21](PROTECTED_MODE_GLOBAL_REVIEW_20260929.md#h21--faulting-pop-segment-advances-architectural-sp-s--r-p0).

The POP's rejection of a DPL0 data selector at CPL3 is itself correct. The
unexpected inherited selector and incorrect restart stack state are the issues;
loosening POP's privilege check would hide the problem.

## Reproducible environment

| Item | Value |
|---|---|
| SPK286 | `b81d5bff89205d34afd7a458312b39a0bb94e9e4` |
| PCAT vendor import | `4d9fcc1` |
| 86Box source | `5630619f5aeddaa5357bb32d25b69dac6b187776` |
| Binary | `D:/GitHub/86box_dev/build/spk286/86Box-linux` |
| Binary SHA-256 | `3e1a2aca871abceccd5c390e24f0ac8bc537a287c3966746169ae494ad12358e` |
| Profile | MR BIOS 286, 6 MHz, 2 MB, EGA, IDE 0:0 |
| Disk geometry | 1020 cylinders, 15 heads, 17 sectors |
| Evidence directory | `D:/GitHub/86box_dev/build/spk286/os2-audit-20260929/` |
| Test disk | `IBM_OS2.audit.vhd` in that directory |
| Original source | `D:/ISOs/MiSTer/IBM_OS2.vhd` |

The copy/profile/NVR were prepared before the user restricted further changes.
The user then specifically authorized this first trial. The existing executable
was launched in WSL with separate VM and global configuration paths. This is
the executed command, from Windows PowerShell:

```powershell
wsl.exe -d Ubuntu-24.04 -- env QT_QPA_PLATFORM=offscreen /mnt/d/GitHub/86box_dev/build/spk286/86Box-linux -N -P /mnt/d/GitHub/86box_dev/build/spk286/os2-audit-20260929 -O /mnt/d/GitHub/86box_dev/build/spk286/os2-audit-20260929/global.cfg -R /mnt/d/Desktop/86Box/roms -L /mnt/d/GitHub/86box_dev/build/spk286/os2-audit-20260929/spk286-os2.log -V SPK286-OS2-Audit
```

The monitor's `screenshot`, `pause` and `exit` commands were used. No key input
to the guest, injected CPU state, debugger writes, runtime patch, rebuilt binary
or core fix was needed. Live sampling used read-only `/proc/<pid>/mem` access
and the existing `live_offsets` helper. Samples taken while running are not
atomic instruction snapshots; the final full RAM capture was made after the
monitor acknowledged pause. Pre-delivery exception records are the stronger
evidence for each fault's CPU state.

## 1. Progress beyond the preceding RETF failure

The previous capture, `os2-trap-20260929-172143/spk286-os2.log`, recorded
`0270:0985` RETF with this outer return frame:

```text
return CS:IP = 13A3:32D0       new SS:SP = 0067:0800
ES = 0210, base 111B40, limit 207F, access 93 (present DPL0 data)
DS = 0BF0, base 00BF00, limit 638F, access F3 (present DPL3 data)
```

The new run reaches code later in that ring-3 entry. In the frozen RAM,
CS 13A3 has base 1E7960, limit 819E and access FB. Its startup sequence is:

```text
32D0  PUSH 0278
32D3  POP DS
32D4  CMP BYTE [1700],43
32D9  JNZ 32DE
32DB  CALL 3354
...
3354  PUSH DS
3355  PUSH ES
3356  PUSHA
...   OS calls and temporary use of ES
33A2  PUSH 0BF0
33A5  POP ES
...
33BB  POPA
33BC  POP ES       ; first relevant new fault
33BD  POP DS
33BE  RET
```

At `33BC`, the saved ES word is **0210**. The selector's descriptor is still
present DPL0 writable data. It is correctly inaccessible to a new CPL3 load.
Intel's outer-return rule would have nulled that inherited ES before entering
32D0; the corresponding saved word would then have been zero and POP ES legal.
DS was DPL3 and remains usable under that rule.

The connection to the preceding RETF is a strong source-and-capture inference:
the older pre-return record has ES=0210, the new stack preserves that value at
PUSH ES, the startup instructions in between do not load ES, and the RTL lacks
the required invalidation. There is no continuous new-run trace of the RETF
commit itself. The retained selector and the subsequent POP fault are observed
directly; the exact causal return should be isolated by the proposed small test.

## 2. First relevant new exception: POP ES

`spk286-os2.log`, lines 2228 onwards, exception snapshot 25/256:

```text
CS:IP = 13A3:33BC      opcode = 07       event vector = 0D
latched event error = 0210
FLAGS=0202 AX=1124 CX=0009 DX=0000 BX=01F8
SP=07FC BP=0000 SI=0000 DI=0000
ES=0BF0:00BF00/638F    DS=0278:1E2760/51DF
SS=0067:1D75E0/07FF    CS=13A3:1E7960/819E
GDTR=110020:1AFF       IDTR=113336:03FF
LDTR=0028:1DE420/009F  TR=0010:00C910/002B
GDT[0210] @110230 = 207F 1B40 9311 0000
```

The event error is the relevant latched value. The adapter also prints a
live combinational `fault=... error=...` line that can already differ after the
fault has been accepted; do not substitute that later value for `event-error`.

The original client stack is intact in the final RAM image:

| SS 0067 offset | Word | Meaning |
|---|---|---|
| 07FA | 0210 | Selector read by the failing POP ES |
| 07FC | 0278 | Saved DS for the following POP DS |
| 07FE | 32DE | Near return address |

The kernel frame independently confirms that the exception saved **07FC**:

| SS 0038 offset | Word | Meaning |
|---|---|---|
| F8EE | 0210 | #GP error code |
| F8F0 | 33BC | Fault IP |
| F8F2 | 13A3 | Fault CS |
| F8F4 | 0202 | Fault FLAGS |
| F8F6 | 07FC | Saved old SP, already advanced |
| F8F8 | 0067 | Saved old SS |

For a restartable POP segment, the source SP must remain **07FA** if selector
validation fails. Otherwise a handler retry consumes saved DS instead of the
faulting selector. This is a separate defect even if correct outer-return
invalidation prevents this particular workload from reaching the fault.

## 3. Secondary exception and final banner

Snapshot 26/256 records `0228:35C7`, bytes `8A 45 05`, a read of `[DI+5]`.
Here DS=0030 has base 1DE420 and limit 009F, while DI=13A0. The resulting offset
13A5 is outside that ordinary data segment, explaining #GP(0).

The handler code obtained DI from the saved CS, masked it to 13A0, and called
its selector-table helpers before the read. This records the secondary failure;
it does not prove why the handler selected that table for this unexpected
startup exception. The banner reports TRAP 000D and `0228:383D` as its internal
error location, with the fault register display pointing at 0228:35C7.

Do not alter the `[DI+5]` segment limit check to make the banner disappear.
Earlier #NP records at `0220:CBC2` belong to the segment-loading sequence and
were followed by progress. Repeated shutdown messages from `0090:072C` occur
during protected/real-mode transitions and are not, alone, proof of the new fault.

## 4. Intel and native 86Box comparison

Primary reference:
[Intel 210498-005 (1987)](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf),
RET B-94/B-95, POP B-83/B-84, and 11.2's restartable segment loading.

- Outer return must remove access through data registers that are invalid at
  the new privilege. For the observed ordinary DPL0 ES at new CPL3, the selector
  and access state must become null. Some prose/OCR comparisons in chapter 7
  are inconsistent; use the detailed algorithm and its privilege rationale.
- Failed segment loading must allow repair and retry of the original operation,
  including retaining the stack word for POP.

The reviewed local native 86Box paths are:

- `src/cpu/x86seg.c::pmoderetf[_2386]`, line 1514: checks DS and ES after
  switching to the outer context.
- `x86seg.c::check_seg_valid`, line 216: DPL0 data is invalid at CPL3 and is
  replaced through `op_loadseg(0, ...)`.
- `src/cpu/x86_ops_stack.h::POP_SEG_OPS`, line 605: restores saved ESP if
  `op_loadseg` faults. `opPOP_SS_w` does the same at line 647.

This comparison is source-level. A native 86Box boot with an identical copied
profile was not run in this trial, and no physical 286 measurement is claimed.

## 5. Proposed focused reproductions, deferred

**A. Invalidation:** start CPL0 with DS=DPL3 and ES=DPL0; RETF to CPL3 using
an empty SS:SP=0067:0800-style stack; observe DS preserved and ES nulled;
PUSH ES / POP ES must complete. Also test both invalid registers, both valid,
readable conforming code, IRET and RETF immediate variants.

**B. POP restart:** at CPL3 place a DPL0 selector at SS:07FA, attempt POP ES,
and inspect the ring-0 #GP frame. Require saved SP=07FA and unchanged ES cache.
Repair the word to zero and IRET; the retry must pop that zero and finish with
SP=07FC. Extend to absent descriptors, POP DS and POP SS, checking shadow rules.

These tests and fixes are intentionally not implemented here. The user requested
findings/specifications and authorized only this initial OS/2 trial. The global
review gives the wider matrix for joint follow-up.

## 6. Preserved artifacts and shutdown

The process started at host-log time 18:05:04. A screenshot showing the new
trap was taken at 18:13:22, and a paused state/RAM capture at 18:14:00. These
times are WSL-local timestamps, not guest elapsed time or a boot benchmark.
The monitor then exited normally; no test emulator process remains running.

Files under the evidence directory:

- `spk286-os2.log`: complete trace, including snapshots 25/26.
- `guest-ram.bin`: 2 MiB guest RAM, captured after pause.
- `audit-state.jsonl`, `capture-state.json`: live samples and final paused state.
- `first-case-disassembly.txt`: client, handler, helper disassembly and stack/table words.
- `maps.txt`, `cmdline.txt`, `symbols.txt`: live process evidence.
- `screenshots/Monitor_1_1260829-181322-662.png`: final TRAP screen.
- `86box.cfg`, `global.cfg`, `nvr/`: isolated test profile state.

SHA-256 manifest:

| Artifact | SHA-256 |
|---|---|
| Original VHD, before and after | `cd4dfe0440df06d85410c931114e49d1e88a63318762ed10e99bf5882a260901` |
| Test VHD, before and after | `cd4dfe0440df06d85410c931114e49d1e88a63318762ed10e99bf5882a260901` |
| RAM | `501d5bf23785697c89e817b03279608b966690add4ada2f4b5ff0d324bb1d14b` |
| Log | `292587376253cd3c7d7bf069616c94580bf54833b9a641275d9457cd7d6c6476` |
| Disassembly | `041246b30037a82b028203d41e423bcf774d22af9a362890a33b881844999015` |
| TRAP screenshot | `e5b57f95a3422bd0530a4352ed0875ea1f554f6bfda6010aba027af83dd5cb00` |

The original disk and production profiles were not changed. 86Box normalized
the copy profile's disk path to a relative filename when saving on exit.
Diagnostic artifacts remain in the ignored build directory; this commit adds
documentation only, not the OS/2 disk or guest RAM to Git.
