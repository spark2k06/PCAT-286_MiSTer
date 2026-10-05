# Portable RAW instruction length boundary unit

This upstream CPU-only unit covers legal ten-byte completion followed by further execution, eleven-byte #GP at first-prefix IP, READY waits 0..3, TF and NMI. Both simulators passed 10 cases / 1097 checks. Frozen old RTL fails the legal ten-byte case with an unintended #GP.

The archive contains every compiled CPU source, package, public signal include, the new unit, source order/hashes, and logs. It contains no objects or executables. It does not depend on PCAT profile modules.

For a frozen Icarus reproduction, extract this packet into a new bounded directory, validate its manifest, and compile the receipt's compiled_source_order under source/, adding source/vendor/spk286/sim/unit/spk286_length_boundary_tb.sv, -g2012, -I source/vendor/spk286/rtl, -I source/vendor/spk286/sim/unit, -s spk286_length_boundary_tb. Run the resulting vvp. For the negative control replace only source/vendor/spk286/rtl/spk286.sv with frozen_old_spk286.sv and require a nonzero exit with the retained legal-ten-byte error.

Verilator used --binary --timing --assert --language 1800-2012 with the same files/include directories and top. These focused checks do not replace the complete regression, which the user deferred.
