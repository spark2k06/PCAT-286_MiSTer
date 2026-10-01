# Video-statistics physical routing audit

The P07 seed-three fit still fails warm setup by 0.289 ns on the
`video_stats` held snapshot. The source launches after approximately
8.659 ns of clock latency and the destination clock reaches its register
after approximately 5.154 ns. With the existing 5 ns maximum-delay
relationship, -3.505 ns clock skew and 0.210 ns uncertainty, a measured
1.574 ns data route fails that requirement. The data alone is shorter
than 5 ns; that observation does not pass the actual existing constraint.

The installed Quartus Lite 17.0.2 `set_max_delay -long_help` explicitly
includes clock latency and has no `-ignore_clock_latency` option. No
unsupported option, phase assumption or setup false path is introduced.
The acknowledged snapshot's two request stages and stable payload remain
unchanged. Physical experiments add a tighter data-route requirement while
retaining the original 5 ns setup requirement.

## Complete edge audit and negative control

`scripts/report_at_net_delay.tcl` reports all bounded nets without a
top-N limit and separately reports the payload's setup paths. Both fitted
register collections contain all 163 bits. `scripts/check_at_net_delay.py`
requires exactly one bound, one matching source/capture edge per bit,
all 163 edges in each of four corners, the expected delay budget and
consistent summary/arithmetic. Negative slack is a failed audit. Eight
small parser tests reject missing/duplicate/wrong bits, changed budgets,
inconsistent arithmetic and an optimistic summary.

A read-only probe applies an additional 0.600 ns bound to the existing
seed-three netlist. All 163 slow-corner edges fail it, with worst actual
data delay 1.576 ns warm and 1.540 ns cold. The checker rejects that
candidate as expected. The original fitted RBF, QSF and SDC hashes are
unchanged. This is analysis of an existing fit, not physical improvement
or a new bitstream. Evidence: `docs/evidence/video-stats-net-probe-20261002`.

Fresh RTC-plus-routing experiments compare the 0.600 ns target with a
1.000 ns target, both retaining the original 5 ns setup bound. The latter
targets a shorter achievable route with margin below the measured
approximately 1.2 ns allowance after skew and uncertainty. Results are
pending. A candidate requires its own complete setup/hold and edge audit;
the added constraint must not be treated as proof the fitter satisfied it.
