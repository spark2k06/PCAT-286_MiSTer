# Phase 8 downstream transfer record

Date: 2026-09-10

Status: verified CPU payload transferred to `PCAT-286_MiSTer`; the user has
confirmed successful synthesis and that the resulting RBF works.

## Source and destination snapshots

| Item | Commit |
| --- | --- |
| SPK286 Phase 7 functional base | `0464a8c0261d6e93b903c48c62cfb8b85e0363ab` |
| SPK286 8A BIU HOLD/LOCK correction | `34ecb9c2dca913bd6fd4e9a6fe02d69eb79d5d1f` |
| SPK286 8B ESC correction | `b86d30edb80e2794e90059c8122cc06c83abaa30` |
| SPK286 review and whole-core validation snapshot | `87b597ea97c859e0240155d0c6905b255266f962` |
| SPK286 Phase 8 mutation audit | `05d4e77af309600967799e97110dab01eb216b91` |
| SPK286 CI Phase 8 audit hook | `9ee3f2dd66bdf89d18924c5c191b1ee37f1f414b` |
| SPK286 ordered Phase 8 development gate | `e36f8f6` |
| PCAT candidate before transfer | `409292dcb06ea507099e4e68cf6d691d9b7294e8` |
| PCAT transfer commit | `b6c3035e716fcd640523c7189480e59941067472` |
| PCAT mutation-audit follow-up | `af74c70108db8ede90a62a4f6bcff6d8da86057d` |

The PCAT commit is on `codex/spk286-xt-integration`. It was committed without
staging the pre-existing PCAT changes in `PCAT_286_MISTER_SPEC.md`,
`docs/KNOWN_LIMITATIONS.md`, `SW/ROMs/test/`, `entry` or the RBF artifact.
Nothing was pushed by this transfer.

## Transfer scope

The commit carries the Phase 8 CPU/microcode/test payload under
`PCAT-286_MiSTer/vendor/spk286/`:

- 8A BIU source and direct/whole-core HOLD/LOCK tests;
- 8B decoder, authoritative ESC microcode source, regenerated ROM artifacts,
  audit/fixture updates and complete D8–DF tests;
- decoder and unit-test registration updates;
- isolated Phase 8 mutation audit with pristine controls;
- Phase 8 manifests, independent review and whole-core validation records.

No PCAT bus overlay, DMA/DACK implementation, XT serializer, MiSTer top-level,
BIOS source or BIOS image was changed by this commit.

The PCAT vendor has a consumer-specific debug boundary. Its `spk286_biu.sv`
retains the `debug_detail` output consumed by `spk286.sv`, and its test signal
include retains `debug_biu_detail`; the direct BIU test declares its matching
debug wire. These are consumer/test-interface adaptations, not additions to
the portable SPK286 source.

## SHA-256 comparison

All hashes below are SHA-256 and compare the PCAT payload with the committed
SPK286 transfer snapshot `87b597ea97c859e0240155d0c6905b255266f962`.
`same` means the source file was copied byte-for-byte. `consumer-adapted`
identifies only the preserved PCAT debug boundary or its test wiring.

| Relative path | SPK286 source | PCAT vendor copy | Result |
| --- | --- | --- | --- |
| `docs/DECISIONS.md` | `DA2B5D59D40018360148F0856EB028A37587A801842A6E1FD3F26EB1B4A61386` | `DA2B5D59D40018360148F0856EB028A37587A801842A6E1FD3F26EB1B4A61386` | same |
| `docs/PHASE8_8A_MANIFEST.md` | `6FA5A4420CF07649D9B79D4EA83EEFDBD64519360D19A289B1614BB9A43B63D9` | `6FA5A4420CF07649D9B79D4EA83EEFDBD64519360D19A289B1614BB9A43B63D9` | same |
| `docs/PHASE8_8B_MANIFEST.md` | `2449B84E6DE5E2B2EF12BEEDE6D0F5EC95DE4C090A906B7937CADC5C20C85F14` | `2449B84E6DE5E2B2EF12BEEDE6D0F5EC95DE4C090A906B7937CADC5C20C85F14` | same |
| `microcode/generated/spk286_microcode_pkg.sv` | `388C12F55E964DCE1A4F817944EAF4D9C6EFFA97B86A9B4A27D6ED4578FA8D98` | `388C12F55E964DCE1A4F817944EAF4D9C6EFFA97B86A9B4A27D6ED4578FA8D98` | same |
| `microcode/generated/spk286_microcode_rom.sv` | `C30905B8B42EE916ECA88C65D39619FA8AD2F464530CB3F1EC71BBC12A799779` | `C30905B8B42EE916ECA88C65D39619FA8AD2F464530CB3F1EC71BBC12A799779` | same |
| `microcode/source/zzzzzzzzzzzzzzzz_esc.mc` | `03AF6F53D08B46B5068CE1194D8B4B168BF82C5BCBB2947D88E1E71CDBA8DA82` | `03AF6F53D08B46B5068CE1194D8B4B168BF82C5BCBB2947D88E1E71CDBA8DA82` | same |
| `rtl/spk286_decoder.sv` | `B18B3F6B8BB520046196068F96FFF6C928B858C2E6985539DD61A3BBD2FACF95` | `B18B3F6B8BB520046196068F96FFF6C928B858C2E6985539DD61A3BBD2FACF95` | same |
| `rtl/spk286_biu.sv` | `0C17999947F7D3ED4E044E10893516D9DFD1ED30A3B4AF1578DCC6CFC8202D33` | `3218A8A76338FA28CF26EC5C84BEE82CCAFF64F8E249E1405710AEBEAE904D28` | consumer-adapted |
| `sim/unit/spk286_biu_hold_lock_tb.sv` | `5580B41F61A86FABB8DE477DC8B61EF568552810DF25702A07415B6DE1CA75B0` | `C4B1D6E8B095DFBD06437B6C37585136DA2CEF558FE85142EF8E6B11243B0282` | consumer-adapted |
| `sim/unit/spk286_signals.svh` | `CF72B27F671056A13A7E374F699B89F1EE09E5205A09BD78007443070028F1C7` | `830AA4558AE7C9D3AA5F292FC74CFB1A388BF5840A518B33A8E61511C781BD77` | consumer-adapted |
| `sim/unit/spk286_xchg_hold_lock_tb.sv` | `CA2CA5D201A6AD596E3DFF9F04F2BF8E9C03880EA44C8AFB53136EE373F2C018` | `CA2CA5D201A6AD596E3DFF9F04F2BF8E9C03880EA44C8AFB53136EE373F2C018` | same |
| `sim/unit/spk286_esc_instructions_tb.sv` | `B23C817468B170D3C8155697E29821276C10E2CBBDCFA614DDA9180B15CFD44C` | `B23C817468B170D3C8155697E29821276C10E2CBBDCFA614DDA9180B15CFD44C` | same |
| `tests/fixtures/microcode_phase8.json` | `C2A5AC76314EFCCB22386AA6376932F72E7B8E33401BD3E0AF6254DC1E6334C3` | `C2A5AC76314EFCCB22386AA6376932F72E7B8E33401BD3E0AF6254DC1E6334C3` | same |
| `tests/test_microcode_io.py` | `A8CA4E412BFA23886E3BAE319170D3121035B750643097D555AEC41CDBA5318F` | `A8CA4E412BFA23886E3BAE319170D3121035B750643097D555AEC41CDBA5318F` | same |
| `tools/microcode/audit_microcode.py` | `D64041D3F37E39C10AF57A53AEBEA9AFDD21498E01376C643CDF089E9EA2063C` | `D64041D3F37E39C10AF57A53AEBEA9AFDD21498E01376C643CDF089E9EA2063C` | same |
| `tools/audit_phase8.py` | `D434C68877857A30DCE6E35FD14669467105D38A74C42C9F4AC2B00D437B895A` | `D434C68877857A30DCE6E35FD14669467105D38A74C42C9F4AC2B00D437B895A` | same |
| `Makefile` | `0A360F520609963AE787AA71AAB68307854974279CA29C7A1835E3558AE8BB99` | `0A360F520609963AE787AA71AAB68307854974279CA29C7A1835E3558AE8BB99` | same |

The remaining transferred manifests, generated listing/symbol/validation
artifacts, decoder test, test-unit registration and microcode test files were
also checked byte-for-byte and are recorded in the PCAT commit. The three
consumer-adapted rows above are intentional interface-preservation changes.

## Consumer validation

Executed after the transfer from the PCAT vendor root:

| Check | Result |
| --- | --- |
| BIU direct, Icarus/Verilator | `BIU_HOLD_LOCK PASS: 13 checks; 2 physical writes` |
| CPU XCHG, Icarus/Verilator | `XCHG_HOLD_LOCK PASS: 47 checks; 2 data reads/2 writes` |
| D8–DF ESC, Icarus/Verilator | `ESC_INSTRUCTIONS PASS: 24 cases; 1463 checks` |
| Decoder, Icarus/Verilator | `DECODER PASS: 256 opcode checks` |
| Microcode audit and compile check | `MICROCODE AUDIT PASS`; `101 entries, 614 words` |
| Consumer Yosys synthesis sanity | `SYNTH_CHECK PASS` |
| Phase 8 mutation audit | `PHASE8_AUDIT PASS: 2 rejected RTL mutants; 3 pristine controls; production bytes unchanged` |

The SPK286 source snapshot also passed the reproducible ordered development
gate after transfer preparation:

```text
make phase8-check
PHASE8_CHECK PASS: focused, microcode, lint, whole-core, mutation, synthesis and regression stages passed
```

This gate is recorded in SPK286 commit `e36f8f6`; its per-stage logs are
retained under `build/phase8-complete/logs/` and are intentionally not part of
the portable PCAT vendor payload.

## Subsequent consumer FPGA evidence

The consumer checkout now records a downstream I5 FPGA build separately from
the CPU transfer commits. `docs/I5_FPGA_BUILD.md` reports Quartus Prime 17.0.2
on Cyclone V `5CSEBA6U23I7`, with successful analysis/synthesis, fit and
assembler output. Its delivered artifact is:

```text
PCAT-286_20260910.rbf
SHA-256: 3b74166d744005a56953b2572668bfb5519cea0ba46cdd736b40b7de7b1ae97a
```

The focused SPK286, bridge and 50 MHz timing paths are reported with positive
slack. Whole-machine timing remains qualified by inherited video, HPS and
SDIO setup groups, as documented by the consumer; this is FPGA-build evidence,
not a physical-board result.

The consumer `docs/I6_BOARD_CHECKLIST.md` still requires the exact RBF and
diagnostic ROM hashes, a diagnostic-ROM run, changing `SNAP`/CPU observations,
LED and transaction evidence, and repeated reset observations. Exploratory
BIOS/game observations used an earlier candidate without a captured RBF hash,
so they did not by themselves close I6 or the Phase 8 hardware checkpoint.

## User hardware confirmation

On 2026-09-10 the user explicitly confirmed in the task that they performed
the Quartus synthesis and verified that the resulting RBF works. This is the
authoritative user-owned hardware result required by the Phase 8 execution
prompt, and it closes the Phase 8 hardware checkpoint. No board model,
diagnostic-ROM hash, or per-page overlay capture was supplied in that message,
so this record makes no narrower I6 telemetry claims beyond the user's
confirmation.

The unchanged BIOS boundary smoke used:

```text
SW/ROMs/test/xtsergey_mod.rom
SHA-256: df25bbc8aba4e35eb56ca585b2c7054da1d7435278b2bfe0f0c7ffae2f85f443
EXTERNAL_ROM_BOUNDARY_PASS cs_ip=f000:e0ac opcode=81 port80=1 beats=128 code=125 io_r=0 io_w=1
```

This is a bounded reset-vector/ROM/bridge simulation, not a complete BIOS boot.
The BIOS image was not patched or committed. The user-owned Quartus/RBF and
board result is recorded above; it is not inferred from this simulation.

## Recovery and handoff

To inspect the delivered payload, use `git show
b6c3035e716fcd640523c7189480e59941067472` in the PCAT checkout. If a later
review identifies a transfer-only problem, revert that commit on the PCAT
branch with `git revert b6c3035e716fcd640523c7189480e59941067472`, preserving
the unrelated user changes. The portable source of truth remains the SPK286
review snapshot above; generated microcode must be regenerated from its source,
not edited in the vendor copy. The mutation-audit follow-up is inspected with
`git show af74c70108db8ede90a62a4f6bcff6d8da86057d` and can be reverted
separately if required.

The user confirmation above completes the required hardware checkpoint. Phase
8 is therefore closed with the inherited D-037 notes remaining explicitly
tracked and the BIOS adaptation still outside scope.
