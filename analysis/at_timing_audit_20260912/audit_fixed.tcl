package require ::quartus::project
package require ::quartus::sta
project_open /build/PCAT-286_AT_FAST -revision PCAT-286_AT_FAST
file mkdir /audit/sdram_clock_fixed
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set cpu [get_registers -nowarn {*u_at_machine|u_cpu|*}]
puts "AUDIT_CPU_REGISTERS=[get_collection_size $cpu]"
set machine_clock [get_clocks FPGA_CLK2_50]
puts "AUDIT_GLOBAL=[report_timing -setup -npaths 20 -detail full_path -file /audit/sdram_clock_fixed/global_setup.rpt]"
puts "AUDIT_50MHZ=[report_timing -setup -from_clock $machine_clock -to_clock $machine_clock -npaths 30 -detail full_path -file /audit/sdram_clock_fixed/clk50_setup.rpt]"
if {[get_collection_size $cpu] != 0} {
    puts "AUDIT_CPU=[report_timing -setup -from $cpu -to $cpu -npaths 30 -detail full_path -file /audit/sdram_clock_fixed/cpu_setup.rpt]"
}
puts "AUDIT_TO_50MHZ=[report_timing -setup -to_clock $machine_clock -npaths 20 -detail full_path -file /audit/sdram_clock_fixed/to_clk50_setup.rpt]"
report_ucp -file /audit/sdram_clock_fixed/unconstrained.rpt
report_clocks -file /audit/sdram_clock_fixed/clocks.rpt
report_timing -setup -from [get_ports {SDRAM_DQ[*]}] -npaths 16 -detail full_path -file /audit/sdram_clock_fixed/sdram_read_setup.rpt
report_timing -hold -from [get_ports {SDRAM_DQ[*]}] -npaths 16 -detail full_path -file /audit/sdram_clock_fixed/sdram_read_hold.rpt
report_timing -setup -to [get_ports {SDRAM_DQ[*] SDRAM_A[*] SDRAM_DQM* SDRAM_n* SDRAM_BA[*] SDRAM_CKE}] -npaths 16 -detail full_path -file /audit/sdram_clock_fixed/sdram_write_setup.rpt
report_timing -hold -to [get_ports {SDRAM_DQ[*] SDRAM_A[*] SDRAM_DQM* SDRAM_n* SDRAM_BA[*] SDRAM_CKE}] -npaths 16 -detail full_path -file /audit/sdram_clock_fixed/sdram_write_hold.rpt
delete_timing_netlist
project_close

