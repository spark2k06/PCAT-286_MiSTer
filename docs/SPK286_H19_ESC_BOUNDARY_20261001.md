# SPK286 H19: ESC first-word boundary fix

Date: 2026-10-01. Vendor baseline `eda6218` / upstream `4452d14`.

The vendor ESC program now checks the first memory word after EM/TS and
address decoding, without reading the operand or executing an 80287. This
resolves all 33 physical real-mode D8 FFFF failures identified during H18.
All 5,000 D8 captures and all 5,000 WAIT captures pass upstream.

The vendor passes the directed boundary, H18, legacy ESC, operand lifecycle
and stack-control banks under both simulators with P01/P02/P05 enabled.
The board's top/fetch real-mode wrap integration is preserved. No FPGA
synthesis or new hardware run is claimed. Remaining H19 boundaries stay open.

Detailed specification and reproducible evidence:
[H19 ESC](../vendor/spk286/docs/PROTECTED_MODE_H19_ESC_BOUNDARY_20261001.md),
[receipt](../vendor/spk286/docs/REGRESSION_H19_ESC_BOUNDARY_20261001.json).
