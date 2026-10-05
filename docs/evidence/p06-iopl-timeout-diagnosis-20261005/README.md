# IOPL historical-profile timeout diagnosis

The root Icarus compatibility invocation exceeded its 300-second external wall
limit. Replaying its existing compiled fixture without a trace also exceeded a
shorter 120-second diagnostic limit. A bounded original observer showed normal
progress through 142,363 fabric edges in 20.01 seconds, without assertion output.
The observer run was deliberately terminated and is not accepted as a PASS.

The exact existing fixture then completed in Verilator at 6 MHz: all 2,772
cases and 49,334 checks passed. All functional assertions, stimulus, fixed
delays and fixture watchdogs were unchanged. The passive observer remains in
the fixture, with trace disabled by omitting its plusarg. No production RTL was
edited for this diagnosis. This is a directed compatibility result, not an
acceptance of the unfinished full Icarus/profile matrix or a paired trace proof.

The archive contains frozen RTL inputs, the exact original adapted fixture,
diagnostic script, bounded samples, logs and receipts; it contains no compiler
objects or executables. To reproduce the completed directed fixture, extract
the archive into a fresh workspace build directory and run
`python3 -B source/build/p06-iopl-timeout-diagnosis-20261005/verilator_existing_fixture.py`
from its extracted packet directory using WSL with Verilator installed.
