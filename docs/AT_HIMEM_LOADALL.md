# HIMEM extended-memory stop: missing LOADALL integration

## Diagnosis

The 2026-09-22 hardware capture stops during HIMEM's extended-memory test at
`CS:IP=0000:A748`, `OP=05`, with `ERR U=1` and `SHD=0`. In the preceding CPU
decoder, ordinary opcode `05` is supported, but extended opcode `0F 05`
(`LOADALL`) is classified as legal-but-unsupported. `unsupported_q` then blocks
execution and fetching until reset. The displayed micro-PC `247` is the
previous `STRING_MOVE.done` entry, not an active memory-test loop.

The independent SPK286 repository already implements LOADALL. The downstream
copy had received invalid-opcode classification and SALC without that slice.
86Box's `src/cpu/x86_ops_misc.h::opLOADALL` implements the corresponding 286
operation, consistent with the user's successful emulator boot.

Intel's [LOADALL note](https://www.pcjs.org/documents/manuals/intel/80286/loadall/)
describes a 102-byte image at physical `000800h`, including visible registers
and hidden segment caches. The hidden 24-bit bases allow extended-memory
access with PE clear. Thus this stop does not, by itself, establish a failure
of Windows 3.1's later protected-mode execution.

## Integrated change and provenance

The LOADALL CPU state/service changes and three focused RTL benches come from
`spark2k06/SPK286` at `aa922e53a579db17c67aeba37962a3683353813c`, including
implementation `de76dde` and lifecycle/protected-path tests `a61ef15` and
`9e2887f`. No upstream working-tree documentation edits were imported.

The integration adds the service to the Quartus QIP, decodes `0F 05`, reads the
51 image words through the BIU, publishes registers and caches atomically,
and flushes prefetched instructions using the loaded CS:IP.
The microcode artifacts are regenerated from source. The downstream compiler
retains SALC control 171 and allocates LOADALL control 172; this deliberately
differs from upstream's numeric assignment. LOADALL is inserted immediately
before SALC, moving only the SALC entry by two words. Tests verify the prior
instruction sequences and symbolic references remain consistent.

The upstream functional scope is retained: CPL0 operation, nonzero protected
CPL causing `#GP(0)`, and rejection of protected-mode images clearing PE.
This is not certification of undocumented silicon corner cases or historical
cycle timing. No 386 instructions are introduced. Chipset behavior is unchanged.

## Reproduction

Run under WSL from the integration repository:

```sh
bash scripts/test_at_loadall_cpu.sh
bash scripts/test_at_loadall_xms.sh
AT_CPU_DIV2_TEST=1 PCAT_BUILD_DIR="$PWD/build/at-loadall-xms-div2" \
  bash scripts/test_at_loadall_xms.sh
```

`loadall_xms_fixture.asm` is synthetic CPU/chipset coverage, not HIMEM.SYS.
It runs through the production CPU, AT bridge, 8042 A20 control, memory port,
read buffer, KFSDRAM and physical SDRAM pin model. It executes three LOADALLs,
writes 32 bytes above 1 MiB, changes separate byte lanes, copies them to
conventional memory with `REP MOVSW`, reloads DS normally, closes A20 and
verifies aliasing without modifying the high-memory contents. Testbench
checks of physical SDRAM independently confirm the CPU comparisons.

The same fixture with the pre-change CPU at integration HEAD `5a673b0` fails:

```text
AT_LOADALL_XMS_FAULT csip=f000:002b op=05 unsupported=1
```

With the change it passes at both CPU clock configurations:

```text
AT_LOADALL_XMS_PASS repeated_LOADALL=3 extended_copy_bytes=32 A20_alias=1 byte_lanes=1 cycles=6867
AT_LOADALL_XMS_PASS repeated_LOADALL=3 extended_copy_bytes=32 A20_alias=1 byte_lanes=1 cycles=8097
```

## Validation boundary

Generated-microcode consistency, focused compiler tests, strict Verilator lint
and Yosys synthesis of the LOADALL service pass. Machine package elaboration
and the machine-boundary regression pass (105 memory beats, 12 I/O writes,
IRQ0 and refresh activity). The focused CPU script includes decoder, LOADALL
service/integration/protected exception, register/segment state and SALC tests
under both simulators. Local logs are under `build/at-loadall-cpu/` and
`build/at-loadall-xms*/`.

The complete microcode Python suite passes all 92 tests. The stale format
mutation, active audit contract, historical phase-8 I/O image and mandatory
format-20 task-switch disposition checks are now independently covered rather
than coupled to obsolete source or generated-image assumptions.

The Phoenix AH=87h regression could not run because its exact original ROM is
absent from this checkout. No HIMEM/DOS disk image or physical MiSTer session
was exercised. A rebuilt RBF must still be tested with the user's HIMEM.SYS;
successful Windows 3.1 startup remains a separate hardware acceptance test.
