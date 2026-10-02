# P08: fitted video register placement and remaining paths - 2026-10-02

## Measured scope

The stack-offset seed-2 fit has positive CPU setup/hold in all four models,
but complete-design timing is still open. A read-only extraction retains
all 163 payload-to-capture paths per model, the worst 200 global setup
paths, the complete register location inventory, and diagnostic selectors
partitioning paths outside that bank. Global timing acceptance remains
unfiltered in `check_at_timing_closure.py`.

| Model | Global setup | Statistics setup | Other-source setup |
| --- | ---: | ---: | ---: |
| Slow 100 C | -0.255 ns | -0.255 ns | -0.214 ns |
| Slow -40 C | -0.033 ns | -0.033 ns | -0.013 ns |
| Fast 100 C | +2.277 ns | +2.277 ns | +2.493 ns |
| Fast -40 C | +2.506 ns | +2.506 ns | +2.802 ns |

No statistics payload register drives a timed destination outside its
capture bank. The warm statistics report has ten negative endpoints;
the cold report has one. The warm non-statistics minimum is scaled HDMI
output bit 25. Cold non-statistics failures include the horizontal
accumulator and five vertical counter endpoints, from -0.013 to -0.007 ns.
These are measured endpoint/path reports, not an exhaustive path census.

The worst held-payload pair, bit 21, is placed at `FF_X11_Y55_N1` and
`FF_X11_Y52_N14`. It has no data logic, 0.910 ns interconnect plus
0.567 ns destination cell delay, and -3.568 ns clock skew. The original
5 ns max-delay requirement includes clock latency in Quartus 17.
Packing the pair more closely is a physical hypothesis; the requirement,
source/capture edges, request/acknowledgement protocol and RTL are retained.

The warm HDMI path starts at `FF_X34_Y45_N28`, passes its mux at
`LABCELL_X33_Y24_N27`, and reaches `DDIOOUTCELL_X60_Y0_N27`.
Its two data interconnect segments are 1.902 and 4.634 ns. Moving just the
exceptional source/direct registers toward the established HDMI register
cluster is a separate physical hypothesis. The I/O register and clocks
are unchanged.

## Rejected four-register packing

Both initial fresh seed-2 variants assign all 326 statistics endpoints,
with two source/capture pairs per ALM. Quartus rejects the four-register
groups with errors 170208/170017: not all LUT and FF inputs are routable.
Both full compilations terminate with 12 compilation errors and produce
no new RBF. These are failed placement experiments, not timing results.
Their sources, assignments, failure logs and receipts are retained.

The next experiments use one source/capture pair per ALM across 17 LABs,
and compare statistics-only placement with statistics plus two HDMI
register assignments. A successful fit must bind every requested location
and pass the original complete-design setup/hold requirements. Neither
experimental layout is selected in production before this verification.

The two sparse frozen snapshots match the baseline in all 848 RTL, sys,
vendor, clock and budget inputs checked. Their QSF difference is exactly
the appended 326/328 requested FF locations. Of the baseline's 1187
snapshot inputs, 1185 are unchanged; the other changed file is the
nonfunctional ROM checker already validated in commit `c7419eb`. Its exact
committed version is checked separately. Newly added diagnostic tools are
listed in `docs/evidence/video-sparse-placement-inputs-20261002/receipt.json`.
The existing build-date generation is audited after compilation.

## Reproducible extraction and binding guard

Run `report_at_video_register_placement.tcl` with `quartus_sta -t` against
the completed frozen work directory and a fresh output directory. It
checks both 163-register banks, records physical locations with the
documented `get_node_info -location` API, and reads all four models.
It closes the project without exporting assignments.

For a candidate fit with the extraction in `video-register-placement`:

```text
python3 scripts/check_at_video_register_placement.py build/RUN --expect-count 326 --output build/RUN/placement-bindings.json
```

Use 328 when the two HDMI assignments are present. The guard requires
the frozen QSF identity and successful full compilation, exact endpoint
sets, unique requested sites and register names, and exact agreement of
every requested FF with its fitted location. This checks binding; it
does not establish timing closure or replace the functional/source audit.

Eleven directed controls pass against the real baseline location
inventory: known 326/328 locations match, and wrong sites, absent or
duplicate requests, unrelated endpoints, overlapping sites, unquoted
syntax, missing/duplicate fitted nodes and malformed inventory are
rejected. The positive controls use synthetic requests for already
known baseline locations; they are not newly compiled placement results.

Evidence: `docs/evidence/video-register-placement-20261002`.
No RTL, CPU instruction cycles or SDRAM/held-bus budgets change in these
experiments. No complete CPU regression or new hardware benchmark is run.

Primary references: [Quartus FF assignment message](https://www.intel.com/content/www/us/en/programmable/quartushelp/18.1/msgs/msgs/ifitcc_fitcc_declare_ff_location_assignment.htm)
and [Intel design optimization guide](https://www.intel.com/programmable/technical-pdfs/683641.pdf),
which describes deriving exact register locations from fitted timing
reports. Actual Quartus 17 results determine legality and timing here.
