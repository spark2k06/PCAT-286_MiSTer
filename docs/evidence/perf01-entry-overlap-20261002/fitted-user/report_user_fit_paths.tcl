# Bounded path extraction from the preserved P17 fitted netlist. No compilation.
package require ::quartus::project
package require ::quartus::sta
lassign $quartus(args) revision output
if {[llength $quartus(args)] != 2 || [file exists $output]} {error "REVISION NEW_OUTPUT required"}
file mkdir $output
project_open $revision -revision $revision
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set clk50 [get_clocks FPGA_CLK2_50]
if {[get_collection_size $clk50] != 1} {error "Missing 50 MHz clock"}
set code [get_registers -nowarn {*u_at_sdram_read_buffer|*}]
set data [get_registers -nowarn {*u_at_ram_read_buffer|*}]
set port [get_registers -nowarn {*u_at_memory_port|*}]
set bridge [get_registers -nowarn {*u_at_machine|u_bridge|*}]
set groups [list clk50 [list -from_clock $clk50 -to_clock $clk50] \
    bridge [list -to $bridge] port [list -to $port] code [list -to $code] \
    data [list -to $data] global {}]
set counts [open "$output/path_counts.txt" w]
foreach condition [get_available_operating_conditions] {
    set_operating_conditions $condition
    update_timing_netlist
    set corner [string map {" " "_" "/" "_"} $condition]
    set dir "$output/$corner"
    file mkdir $dir
    report_clocks -file "$dir/clocks.rpt"
    report_clock_fmax_summary -file "$dir/fmax.rpt"
    foreach kind {setup hold} {
        foreach {label selectors} $groups {
            set result [eval report_timing -$kind $selectors -npaths 10 \
                -detail full_path -file "$dir/${label}_${kind}.rpt"]
            puts $counts "$corner $label $kind $result"
            flush $counts
        }
    }
}
close $counts
delete_timing_netlist
project_close -dont_export_assignments
puts "P17_USER_FIT_PATHS_EXTRACTED"
