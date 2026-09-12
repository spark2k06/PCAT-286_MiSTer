`timescale 1ns/1ps
module reset_audit_baseline_tb;
 logic clk=0, boot_reset=1, tick=0;
 wire splash, valid;
 wire cpu_reset=boot_reset | splash;
 wire [23:0] address;
 always #5 clk=~clk;
 spk286_at_splash_control splash_control(.clk(clk),.reset(boot_reset),.option_off(1'b0),.second_tick(tick),.splash_active(splash));
 spk286_fetch fetch(.clk(clk),.reset(cpu_reset),.ready(1'b0),.data_in(16'h00EA),.code_base(24'hFF0000),.code_limit(16'hFFFF),.restart(1'b0),.restart_ip(16'hFFF0),.request(1'b1),.suspend(1'b0),.response_ready(1'b1),.bus_valid(valid),.address(address));
 initial begin
  repeat(3) @(negedge clk);
  boot_reset=0;
  repeat(5) @(negedge clk);
  if(valid && address==24'hFFFFF0 && !splash && !cpu_reset) $display("PRE_SPLASH_FETCH_REPRODUCED address=%h splash=%b reset=%b",address,splash,cpu_reset);
  else $fatal(1,"baseline unexpected");
  tick=1;
  @(negedge clk); tick=0;
  @(negedge clk);
  if(!splash || !cpu_reset || valid) $fatal(1,"splash reset mismatch");
  $display("SECOND_CPU_RESET_REPRODUCED splash=%b reset=%b",splash,cpu_reset);
  $finish;
 end
endmodule
