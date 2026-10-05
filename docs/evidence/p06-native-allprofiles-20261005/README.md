# P06 native all-profile evidence, 2026-10-05

Fourteen selected controls cover actual 6/8/10/12.5/16/20/25 MHz with Automatic
and the visible zero-wait override. All have guest and host exit 0, 42 valid
samples and six recomputed summaries. The 6 and 12.5 MHz visible-zero receipts
are reused unchanged from the 2026-10-04 physical-reference native bundle.
All Automatic controls have newly sampled disabled internal/external caches.

`verification.json` contains the selected statistics, runtime fields, hashes
and provenance. `preflight.json` freezes source, executable, ROM and DOS-disk
identity. Each control retains byte-exact CSV/status/receipts, initial/final
configuration, startup/runtime samples, logs and initial CMOS. New controls
also retain final CMOS. The emulator executable and private disks are excluded.
The initial preparation-only error is retained without its temporary disk.

`T286REF.COM` is the same frozen 2,840-byte program. Source snapshots and the
private diagnostic runner are retained; production RTL and DOS program were
not changed. Native-source files and ROM hashes match the earlier archive.
`run_all.py` is the exact orchestration source used for the original captures.
Use the relocatable `reproduce_native.py` for a fresh control, with Python,
pyfatfs and nm installed. The named original binary, ROM directory and DOS VHD
must remain available; the wrapper checks their expected hashes and the runner
refuses to overwrite existing output directories.

```text
python3 reproduce_native.py --output /mnt/d/GitHub/PCAT-286_MiSTer/build/p06-native-reproduce/native8-auto --disk /mnt/d/ISOs/MiSTer/286_win3.1.vhd --exe /mnt/d/GitHub/86Box_dev/build/spk286/native-50mhz-reference/86Box-native --roms /mnt/d/Desktop/86Box/roms --profile 8 --selection auto
```

Each selected profile retains its initial CMOS. For 20/25 MHz, an observed MR
BIOS speed-change prompt can require Enter and then F10 in setup. The runner's
explicit `control.json` interface accepts `{"screenshot":true}` and, after
observing the prompt, `{"key":"enter"}` or `{"key":"f10"}`. These operate only
the owned emulator. Record and retain the reproduction receipts and raw CSV.

Owned-emulator BIOS acknowledgment screenshots, when needed, remain with the
corresponding control alongside the runner's recorded keyboard events.

`comparison.json` records 84 direct gross/baseline comparisons with the
already committed MiSTer ready-chain analysis, whose complete source hash is
recorded. The user captures are not copied into this native evidence bundle.
Reproduce with:

```text
python compare_native_mister.py --native verification.json --mister ../p06-mister-ready-chain-20261005/analysis.json --output reproduced-comparison.json
```

Times are gross PIT input ticks for fixed 256-iteration work, including timer,
setup, loop and signature-store overhead. Baselines are independent samples.
The PIT remains NOT_CALIBRATED with nominal 1,193,182 Hz and assumed divisor
65536. This bundle is an emulator reference, not physical instruction timing
or certification of the historical FPGA profiles.
