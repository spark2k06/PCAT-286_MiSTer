# Selected PCAT-286 fit resource attribution

Extracted from the selected 2026-10-03 seed 1 production fitter report.

- `resources.json`: all 553 hierarchy rows, disjoint functional groups and CPU
  children; source report, summary, selection and RBF hashes.
- `hierarchy.rpt`: original hierarchy section, normalized LF extraction.
- `PCAT-286.fit.summary`: exact bytes, matched to the frozen selected summary.
- `blocks.md`, `cpu.md`: generated tables with percentages and reconciled totals.
- `manifest.json`: analysis artifact and analyzer hashes.

Recreate in a new directory:

```sh
python3 scripts/analyze_pcat_resources.py \
  --report build/fixed50-admission-retained-fdc-seed1-fit-20261003/work/output_files/PCAT-286.fit.rpt \
  --analysis build/pcat-resources-reproduce
```

The analyzer verifies RBF and summary binding, hierarchy uniqueness, additive
own contributions, functional group sums and CPU-child sums. Cost attribution
is not a standalone synthesis delta or a guarantee of reclaimable placed ALMs.
Private P06 timing pilots are excluded from this production fit.
