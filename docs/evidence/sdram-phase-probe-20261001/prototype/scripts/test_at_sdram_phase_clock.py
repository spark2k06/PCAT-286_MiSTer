#!/usr/bin/env python3
"""Check PLL configuration, forwarding waveform and actual lock/reset guards.

The PLL is a behavioral phase/lock model, not a vendor analog PLL model.
The DDR primitive is the official Quartus altera_mf simulation model.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('output',type=Path);ap.add_argument('altera_mf',type=Path)
args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
library=args.altera_mf.resolve()
top=(root/'PCAT-286.sv').read_text()
pllpath=root/'rtl/spk286_integration/spk286_at_sdram_phase_clock.sv'
pll=pllpath.read_text()
expected={'reference_clock_frequency':'50.0 MHz','output_clock_frequency0':'50.0 MHz',
          'phase_shift0':'-3000 ps','operation_mode':'direct','fractional_vco_multiplier':'false'}
for n,v in expected.items():assert re.search(r'\.'+n+r'\("'+re.escape(v)+r'"\)',pll),n
assert '.number_of_clocks(1)' in pll and '.duty_cycle0(50)' in pll
phase=-3.0;period=20.0
clock_instance=re.search(r'    spk286_at_sdram_phase_clock u_at_sdram_phase_clock \(.*?\n    \);',top,re.S).group(0)
ddr_instance=re.search(r'    altddio_out #\(.*?\) sdram_clock_ddr \(.*?\n    \);',top,re.S).group(0)
sync=re.search(r'    always_ff @\(posedge CLK_50M or posedge RESET\) begin\n        if \(RESET\) sdram_phase_lock_sync_q.*?\n    end',top,re.S).group(0)
init=next(b for b in re.findall(r'    always_ff @\(posedge CLK_50M or posedge RESET\) begin.*?\n    end',top,re.S) if 'sdram_initialized_q <=' in b)
boot=re.search(r'    wire at_boot_reset =.*?;',top,re.S).group(0)
assert '.outclock(sdram_shifted_clock)' in ddr_instance
owner=re.search(r'spk286_at_mister_sdram_owner u_at_sdram_owner \((.*?)\n    \);',top,re.S).group(1)
assert '.reset                  (RESET || !sdram_clock_ready)' in owner
assert '.clk                    (CLK_50M)' in owner
sdc=(root/'SYSTEM.sdc').read_text()
assert '-source $at_sdram_phase_target' in sdc and '-master_clock [get_clock_info -name $AT_SDRAM_PHASE]' in sdc
# Phase delay is modulo a period. This models the programmed edge location,
# not PLL acquisition, physical propagation, jitter or silicon quantization.
model='''`timescale 1ns/1ps
module altera_pll #(
parameter fractional_vco_multiplier="false",reference_clock_frequency="50.0 MHz",
operation_mode="direct",number_of_clocks=1,output_clock_frequency0="50.0 MHz",
phase_shift0="-3000 ps",duty_cycle0=50,pll_type="General",pll_subtype="General"
)(input refclk,rst,fbclk,output reg outclk=0,output locked,fboutclk);
integer ref_edges=0;
reg lock_enabled=1;
assign locked=!rst && ref_edges>=6 && lock_enabled;
assign fboutclk=0;
always @(posedge refclk) begin
 ref_edges<=ref_edges+1;
 outclk<=#17 1'b1;
 outclk<=#27 1'b0;
end
endmodule
'''
tb='''`timescale 1ns/1ps
module tb;
logic CLK_50M=0,RESET=0;
always #10 CLK_50M=~CLK_50M;
wire sdram_shifted_clock,sdram_phase_locked,SDRAM_CLK;
logic [1:0] sdram_phase_lock_sync_q;
wire sdram_clock_ready=sdram_phase_lock_sync_q[1];
logic sdram_initialized_q;
wire physical_idle=1;
wire [127:0] hps_status=0;
wire [1:0] hps_buttons=0;
wire main_rom_loaded=1,at_video_pll_locked=1;
'''+clock_instance+'\n'+ddr_instance+'\n'+sync+'\n'+init+'\n'+boot+'''
logic [1:0] expected_sync=0;
logic expected_init=0;
integer checks=0,edges=0;
realtime last_edge=-1;
always @(posedge CLK_50M) begin
 expected_init=(!RESET && expected_sync[1]);
 expected_sync=RESET?2'b00:{expected_sync[0],sdram_phase_locked};
 #0.001;
 if(sdram_phase_lock_sync_q!==expected_sync) $fatal(1,"Lock synchronizer mismatch");
 if(sdram_initialized_q!==expected_init) $fatal(1,"Initialization lock guard mismatch");
 if(at_boot_reset!==!expected_sync[1]) $fatal(1,"Boot lock guard mismatch");
 checks=checks+3;
end
always @(sdram_shifted_clock) begin
 #0.001;
 if(SDRAM_CLK!==sdram_shifted_clock) $fatal(1,"DDR forwarding mismatch");
 if(last_edge>=0 && $abs($realtime-last_edge-10.0)>0.001) $fatal(1,"Non-50MHz edge interval");
 last_edge=$realtime;
 edges=edges+1;
end
always @(posedge SDRAM_CLK) begin
 if($abs($realtime-20.0*$floor($realtime/20.0)-7.0)>0.002) $fatal(1,"PLL phase mismatch");
end
initial begin
 #1 RESET=1;
 #1 RESET=0;
 #1000 u_at_sdram_phase_clock.pll.lock_enabled=0;
 #1000 u_at_sdram_phase_clock.pll.lock_enabled=1;
 #1000 RESET=1;
 #1;
 if(sdram_clock_ready!==0 || sdram_initialized_q!==0) $fatal(1,"Reset assertion guard");
 #19 RESET=0;
 #1000;
 if(checks<500 || edges<350) $fatal(1,"Coverage too short");
 $display("SDRAM_PHASE_CLOCK_PASS checks=%d edges=%d period_ns=20 phase_ns=-3 lock_loss=1 reset=1",checks,edges);
 $finish;
end
endmodule
'''
(out/'pll-model.sv').write_text(model);(out/'tb.sv').write_text(tb)
cmd=['iverilog','-g2012','-s','tb','-o',str(out/'test.vvp'),str(library),str(out/'pll-model.sv'),str(pllpath),str(out/'tb.sv')]
r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'build.log').write_text(r.stdout)
assert r.returncode==0,r.stdout[-3000:]
r=subprocess.run(['vvp',str(out/'test.vvp')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/'run.log').write_text(r.stdout)
assert r.returncode==0 and 'SDRAM_PHASE_CLOCK_PASS' in r.stdout,r.stdout
print(r.stdout)
(out/'receipt.json').write_text(json.dumps({'status':'PROGRAMMED_PHASE_DDR_FORWARDING_AND_LOCK_GUARDS_PASS','period_ns':period,'phase_ns':phase,'scope':'actual root instances/synchronizer/init/boot logic; actual PLL parameters; behavioral phase/lock PLL model and official DDR primitive; no analog PLL or post-fit gate simulation; real phase and path latencies must be checked in Quartus','sha256':{str(p.relative_to(root)) if p.is_relative_to(root) else str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (library,pllpath,root/'PCAT-286.sv',root/'SYSTEM.sdc',Path(__file__),out/'pll-model.sv',out/'tb.sv',out/'run.log')}},indent=2)+'\n')
