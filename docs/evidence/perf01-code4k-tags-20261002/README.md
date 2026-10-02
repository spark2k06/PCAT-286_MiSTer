# 4 KiB instruction-buffer RAM-mapping evidence

See [P14](../../optimization/P14_CODE_BUFFER_RAM_MAPPING_20261002.md).

- `mapping-comparison.json` compares Analysis & Synthesis counts and identifies
  the complete reports by SHA256. It records the reviewed QSF export and the
  unchanged production inputs. These counts are not Fitter occupancy.
- `before.map.summary.txt` and `after.map.summary.txt` preserve the map summaries.
  `before-entity-and-ram.txt` and `after-entity-and-ram.txt` retain the buffer rows.
- `input-manifest.json` identifies the frozen full-project inputs. Its HEAD
  predates subsequent documentation commits; the source hashes include the
  uncommitted RAM-inference correction used for this run.
- `qsf-before-export.txt` and `qsf-after-export.txt` preserve Quartus's QSF
  side effect. All 258 appended commands match assignments already present in
  the original QSF or `config.tcl`, `sys/sys.tcl`, `sys/sys_analog.tcl`,
  `files.qip`. The first strict post-run check failed on this file; the complete
  difference was then reviewed, rather than allowing arbitrary source changes.
- `isolated/` records the independent memory dimensions, tool identity,
  generated wrapper and input hashes.
- `perf01-code4k-tags-final-directed/` retains all twelve simulator results.
- `perf01-code4k-tags-final-pipeline/` retains the RAM and composed chain checks.
- `perf01-code4k-tags-equivalence/` records the paired bus-output comparison
  against commit `0399806` and the unchanged source hashes.

Full reports and frozen sources remain locally in
`D:/GitHub/PCAT-286_MiSTer/build/perf01-code4k-tags-full-map-20261002/` and
`D:/GitHub/PCAT-286_MiSTer/build/perf01-code4k-tags-map-final/`.
The preserved baseline is under
`D:/GitHub/PCAT-286_MiSTer/build/perf01-code4k-user-fit-20261002/`.
The capture script is retained locally as
`build/perf01-real-memory-20261002/capture_code4k_mapping.py`.
No Fitter, timing analysis, new RBF or full regression was performed for P14.
