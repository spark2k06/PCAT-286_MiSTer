package require ::quartus::project
package require ::quartus::sta
project_open /build/PCAT-286_AT_FAST -revision PCAT-286_AT_FAST
create_timing_netlist -model slow
read_sdc /source/sys/sys_top.sdc
read_sdc /audit/baseline_PCAT-286.sdc
update_timing_netlist
set cpu [get_registers -nowarn {*u_at_machine|u_cpu|*}]
puts "AUDIT_CPU_REGISTERS=[get_collection_size $cpu]"
set machine_clock [get_clocks FPGA_CLK2_50]
puts "AUDIT_GLOBAL=[report_timing -setup -npaths 20 -detail full_path -file /audit/global_setup.rpt]"
puts "AUDIT_50MHZ=[report_timing -setup -from_clock $machine_clock -to_clock $machine_clock -npaths 30 -detail full_path -file /audit/clk50_setup.rpt]"
if {[get_collection_size $cpu] != 0} {
    puts "AUDIT_CPU=[report_timing -setup -from $cpu -to $cpu -npaths 30 -detail full_path -file /audit/cpu_setup.rpt]"
}
puts "AUDIT_TO_50MHZ=[report_timing -setup -to_clock $machine_clock -npaths 20 -detail full_path -file /audit/to_clk50_setup.rpt]"
report_ucp -file /audit/unconstrained.rpt
report_clocks -file /audit/clocks.rpt
delete_timing_netlist
project_close
